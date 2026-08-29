"""The web-API *testing* phase's request capability.

The pentest is script-driven: the test cases (not the model) decide which request to send, so the
model's proposed request is *finalised* against the current test step before it is sent, and some
state (tokens, ids, resources) is captured from the response afterwards.

Previously the testing use-case gave the model a raw ``HTTPRequest`` and did this finalisation in
``SimpleWebAPITesting.adjust_action`` / ``execute_response`` *between* the model's tool call and the
execution — which is why the web-API needed its own ``LLMHandler`` that returned the action
un-executed. ``ProposedHTTPRequest`` moves that logic *inside* the capability's ``__call__``: it
mutates the proposed request, delegates the actual send to the injected ``HTTPRequest``, then runs
the post-send account/resource updates. Because everything happens inside the capability, the testing
round can run on the standard ``get_response`` + ``CapabilityManager.run_capability_json`` loop.
"""
import json
from dataclasses import dataclass
from typing import Any, Dict, Literal, Optional

from hackingBuddyGPT.capabilities import Capability
from hackingBuddyGPT.capabilities.http_request import HTTPRequest
from hackingBuddyGPT.utils.prompt_generation.information import PromptPurpose


@dataclass
class ProposedHTTPRequest(Capability):
    """Finalise the model's proposed request against the current test step, then send it.

    Collaborators:
        http_request: the real network capability the send is delegated to (host-bound).
        prompt_helper: holds ``current_sub_step`` (the active test step), ``current_user`` and
            ``accounts`` used to finalise the request and capture response state.
        pentesting_information: holds ``resources`` updated from responses.
    """

    http_request: HTTPRequest
    prompt_helper: Any
    pentesting_information: Any

    def describe(self) -> str:
        # Same request contract as the underlying HTTPRequest so the model calls it identically.
        return self.http_request.describe()

    async def __call__(
        self,
        method: Literal["GET", "HEAD", "POST", "PUT", "DELETE", "OPTION", "PATCH"],
        path: str,
        query: Optional[str] = None,
        body: Optional[str] = None,
        body_is_base64: Optional[bool] = False,
        headers: Optional[Dict[str, str]] = None,
        hide_binary_response: Optional[bool] = True,
    ) -> str:
        original_path = path
        method, path, body, headers = self._finalise_request(method, path, body, headers, original_path)

        result = await self.http_request(
            method=method,
            path=path,
            query=query,
            body=body,
            body_is_base64=body_is_base64,
            headers=headers,
            hide_binary_response=hide_binary_response,
        )

        self._adjust_user(result)
        return result

    # ------------------------------------------------------------------ mutation (pre-send)
    def _finalise_request(self, method, path, body, headers, original_path):
        """Override the model's proposal with the scripted test step (the former ``adjust_action``).

        - force ``POST`` during account-setup steps;
        - set ``Authorization: Bearer <token>``, resolving a ``{{...}}`` token placeholder from the
          acting account;
        - replace the path with the test step's path (and unwrap a dict path);
        - fill an empty body with the current user's data;
        - restore the model's original path if the step left it ``None``.
        """
        sub_step = self.prompt_helper.current_sub_step

        if sub_step.get("purpose") == PromptPurpose.SETUP:
            method = "POST"

        token = sub_step.get("token")
        if token is not None and "{{" in token:
            for account in self.prompt_helper.accounts:
                if account["x"] == self.prompt_helper.current_user["x"]:
                    token = account["token"]
                    break
        if token and (token != "" or token is not None):
            headers = {"Authorization": f"Bearer {token}"}

        if path != sub_step.get("path"):
            path = sub_step.get("path")

        if isinstance(path, dict):
            path = path.get("path")

        if body is None:
            body = self.prompt_helper.current_user

        if path is None:
            path = original_path

        return method, path, body, headers

    # ------------------------------------------------------------------ state capture (post-send)
    def _adjust_user(self, result):
        """Capture key/id/resource data from the response into the acting account (former ``adjust_user``)."""
        if "Could not" in result:
            return
        headers, body = result.split("\r\n\r\n", 1)
        if "html" in body:
            return

        if "key" in body:
            data = json.loads(body)
            for account in self.prompt_helper.accounts:
                if account.get("x") == self.prompt_helper.current_user.get("x"):
                    account["key"] = data.get("key")

        if "posts" in body:
            data = json.loads(body)
            id_resources = self._extract_ids(data)
            if len(self.pentesting_information.resources) == 0:
                self.pentesting_information.resources = id_resources
            else:
                self.pentesting_information.resources.update(id_resources)

        if "id" in body and self.prompt_helper.current_sub_step.get("purpose") == PromptPurpose.SETUP:
            data = json.loads(body)
            user_id = data.get("id")
            for account in self.prompt_helper.accounts:
                if account.get("x") == self.prompt_helper.current_user.get("x"):
                    account["id"] = user_id
                    break

    def _extract_ids(self, data, id_resources=None, parent_key=""):
        """Recursively collect string ``*id`` values grouped by resource category (former ``extract_ids``)."""
        if id_resources is None:
            id_resources = {}
        if isinstance(data, dict):
            for key, value in data.items():
                new_key = f"{parent_key}.{key}" if parent_key else key
                if "id" in key and isinstance(value, str):
                    category = key.replace("id", "").rstrip("_").lower()
                    if category == "":
                        category = parent_key.split(".")[-1]
                    category = category.rstrip("s")
                    if category != "id":
                        category = category + "_id"
                    if category in id_resources:
                        id_resources[category].append(value)
                    else:
                        id_resources[category] = [value]
                else:
                    self._extract_ids(value, id_resources, new_key)
        elif isinstance(data, list):
            for index, item in enumerate(data):
                self._extract_ids(item, id_resources, f"{parent_key}[{index}]")
        return id_resources
