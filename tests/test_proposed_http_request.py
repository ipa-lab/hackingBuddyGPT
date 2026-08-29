import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from hackingBuddyGPT.usecases.web_api.proposed_http_request import ProposedHTTPRequest
from hackingBuddyGPT.utils.prompt_generation.information import PromptPurpose


def _make(sub_step, current_user=None, accounts=None, send_result="HTTP/1.1 200 OK\r\n\r\n{}"):
    http_request = AsyncMock(return_value=send_result)
    prompt_helper = SimpleNamespace(
        current_sub_step=sub_step,
        current_user=current_user if current_user is not None else {"x": 0},
        accounts=accounts if accounts is not None else [],
    )
    pentesting_information = SimpleNamespace(resources={})
    cap = ProposedHTTPRequest(
        http_request=http_request,
        prompt_helper=prompt_helper,
        pentesting_information=pentesting_information,
    )
    return cap, http_request


class TestProposedHTTPRequest(unittest.TestCase):
    def _call(self, cap, **kwargs):
        return asyncio.run(cap(**kwargs))

    def test_non_setup_overrides_path_keeps_method_and_body(self):
        cap, http_request = _make({"purpose": PromptPurpose.AUTHENTICATION, "path": "/scripted", "token": None})
        self._call(cap, method="GET", path="/model-proposed", body="payload")
        sent = http_request.call_args.kwargs
        self.assertEqual(sent["path"], "/scripted")   # test-step path wins over the model's
        self.assertEqual(sent["method"], "GET")        # method unchanged outside SETUP
        self.assertEqual(sent["body"], "payload")      # non-empty body unchanged
        self.assertIsNone(sent["headers"])             # no token -> no auth header

    def test_setup_forces_post_and_fills_empty_body(self):
        user = {"x": 0, "email": "a@b.c"}
        cap, http_request = _make({"purpose": PromptPurpose.SETUP, "path": "/register", "token": None}, current_user=user)
        self._call(cap, method="GET", path="/whatever", body=None)
        sent = http_request.call_args.kwargs
        self.assertEqual(sent["method"], "POST")       # SETUP forces POST
        self.assertEqual(sent["path"], "/register")
        self.assertEqual(sent["body"], user)           # empty body filled with current user

    def test_templated_token_resolved_from_account(self):
        cap, http_request = _make(
            {"purpose": PromptPurpose.AUTHENTICATION, "path": "/p", "token": "{{token}}"},
            current_user={"x": 1},
            accounts=[{"x": 1, "token": "REALTOKEN"}],
        )
        self._call(cap, method="GET", path="/p")
        self.assertEqual(http_request.call_args.kwargs["headers"], {"Authorization": "Bearer REALTOKEN"})

    def test_none_step_path_restores_model_path(self):
        cap, http_request = _make({"purpose": PromptPurpose.AUTHENTICATION, "path": None, "token": None})
        self._call(cap, method="GET", path="/model-proposed")
        self.assertEqual(http_request.call_args.kwargs["path"], "/model-proposed")

    def test_returns_send_result(self):
        cap, _ = _make({"purpose": PromptPurpose.AUTHENTICATION, "path": "/p", "token": None},
                       send_result="HTTP/1.1 201 Created\r\n\r\n{}")
        self.assertEqual(self._call(cap, method="GET", path="/p"), "HTTP/1.1 201 Created\r\n\r\n{}")


if __name__ == "__main__":
    unittest.main()
