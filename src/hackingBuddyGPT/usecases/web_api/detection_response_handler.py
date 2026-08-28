"""Detection-phase endpoint-exploration state machine.

This is the documentation/detection engine's response handler. It drives the ``ExploreStep``
ladder (root -> instance -> subresource -> related -> multi-level -> query), steering the next
request path from a large pool of common REST endpoints and tracking which paths have been
found / tried / rejected.

It used to live inside ``utils.web_api.ResponseHandler`` and was constructed by both web-API
phases, even though only the detection phase ever exercised this machinery. It now subclasses
the slim, phase-agnostic ``ResponseHandler`` (which keeps ``evaluate_result`` /
``extract_key_elements_of_response`` / ``parse_http_status_line`` for the testing phase) and
holds all the detection-only state and steering logic here, next to the detection engine.
"""
import json
import random
import re
from itertools import cycle
from typing import Any
from urllib.parse import urlencode

import pydantic_core
from rich.panel import Panel

from hackingBuddyGPT.utils.prompt_generation.information import PromptContext
from hackingBuddyGPT.utils.prompt_generation.information import PenTestingInformation
from hackingBuddyGPT.utils.prompt_generation.prompt_generation_helper import PromptGenerationHelper
from hackingBuddyGPT.utils.web_api.endpoint_categorizer import categorize_by_structure
from hackingBuddyGPT.utils.web_api.exploration_steps import ExploreStep
from hackingBuddyGPT.utils.web_api.llm_handler import LLMHandler
from hackingBuddyGPT.utils.web_api.pattern_matcher import PatternMatcher
from hackingBuddyGPT.utils.web_api.response_handler import ResponseHandler
from hackingBuddyGPT.utils import tool_message


class DetectionResponseHandler(ResponseHandler):
    """Response handler for the documentation/detection phase (the ``ExploreStep`` FSM)."""

    def __init__(self, llm_handler: LLMHandler, prompt_context: PromptContext, config: Any,
                 prompt_helper: PromptGenerationHelper, pentesting_information: PenTestingInformation = None) -> None:
        super().__init__(llm_handler, prompt_context, config, prompt_helper, pentesting_information)
        self.no_new_endpoint_counter = 0
        self.all_query_combinations = []
        self.no_action_counter = 0
        self.common_endpoints = ['autocomplete', '/api', '/auth', '/login', '/admin', '/register', '/users', '/photos', '/images',
                                 '/products', '/orders',
                                 '/search', '/posts', '/todos', '/1', '/resources', '/categories',
                                 '/cart', '/checkout', '/payments', '/transactions', '/invoices', '/teams', '/comments',
                                 '/jobs',
                                 '/notifications', '/messages', '/files', '/settings', '/status', '/health',
                                 '/healthcheck',
                                 '/info', '/docs', '/swagger', '/openapi', '/metrics', '/logs', '/analytics',
                                 '/feedback',
                                 '/support', '/profile', '/account', '/reports', '/dashboard', '/activity',
                                 '/subscriptions', '/webhooks',
                                 '/events', '/upload', '/download', '/images', '/videos', '/user/login', '/api/v1',
                                 '/api/v2',
                                 '/auth/login', '/auth/logout', '/auth/register', '/auth/refresh', '/users/{id}',
                                 '/users/me', '/products/{id}'
                                              '/users/profile', '/users/settings', '/products/{id}', '/products/search',
                                 '/orders/{id}',
                                 '/orders/history', '/cart/items', '/cart/checkout', '/checkout/confirm',
                                 '/payments/{id}',
                                 '/payments/methods', '/transactions/{id}', '/transactions/history',
                                 '/notifications/{id}',
                                 '/messages/{id}', '/messages/send', '/files/upload', '/files/{id}', '/admin/users',
                                 '/admin/settings',
                                 '/settings/preferences', '/search/results', '/feedback/{id}', '/support/tickets',
                                 '/profile/update',
                                 '/password/reset', '/password/change', '/account/delete', '/account/activate',
                                 '/account/deactivate',
                                 '/account/settings', '/account/preferences', '/reports/{id}', '/reports/download',
                                 '/dashboard/stats',
                                 '/activity/log', '/subscriptions/{id}', '/subscriptions/cancel', '/webhooks/{id}',
                                 '/events/{id}',
                                 '/images/{id}', '/videos/{id}', '/files/download/{id}', '/support/tickets/{id}']
        self.common_endpoints_categorized_cycle, self.common_endpoints_categorized = self.categorize_endpoints()
        self.query_counter = 0
        self.repeat_counter = 0
        self.variants_of_found_endpoints = []
        self.name = config.get("name")
        self.token = config.get("token")
        self.last_path = ""
        self.pattern_matcher = PatternMatcher()
        self.saved_endpoints = {}

    def categorize_endpoints(self):
        # Buckets keyed 1..5 by structural depth, matching the exploration steps.
        buckets = categorize_by_structure(self.common_endpoints, id_token="{id}")
        ordered = [
            buckets["root_level"],
            buckets["instance_level"],
            buckets["subresource"],
            buckets["related_resource"],
            buckets["multi_level_resource"],
        ]
        cycles = {i + 1: cycle(bucket) for i, bucket in enumerate(ordered)}
        plain = {i + 1: bucket for i, bucket in enumerate(ordered)}
        return cycles, plain


    async def handle_response(self, response, completion, prompt_history, log, categorized_endpoints, move_type):
        """
        Evaluates the response to determine if it is acceptable.

        Args:
            response (str): The response to evaluate.
            completion (Completion): The completion object with tool call results.
            prompt_history (list): History of prompts and responses.
            log (Log): Logging object for console output.

        Returns:
            tuple: (bool, prompt_history, result, result_str) indicating if response is acceptable.
        """
        # Extract message and tool call information
        message = completion.choices[0].message
        tool_call_id = message.tool_calls[0].id
        if "undefined" in response.action.path :
            response.action.path = response.action.path.replace("undefined", "1")
        if "Id" in response.action.path:
            path = response.action.path.split("/")
            if len(path) > 2:
                response.action.path = f"/{path[0]}/1/{path[2]}"
            else:
                response.action.path = f"/{path[0]}/1"




        if self.repeat_counter == 3:
            self.repeat_counter = 0
            if self.prompt_helper.current_step == ExploreStep.INSTANCE:
                adjusted_path = self.adjust_path_if_necessary(response.action.path)
                self.prompt_helper.hint_for_next_round = f'Try this endpoint in the next round {adjusted_path}'
                self.no_action_counter += 1
                return False, prompt_history, None, None

        if response.__class__.__name__ == "RecordNote":
            prompt_history.append(tool_message(response, tool_call_id))
            return False, prompt_history, None, None

        else:
            return await self.handle_http_response(response, prompt_history, log, completion, message, categorized_endpoints,
                                             tool_call_id, move_type)

    async def handle_http_response(self, response: Any, prompt_history: Any, log: Any, completion: Any, message: Any,
                             categorized_endpoints, tool_call_id, move_type) -> Any:

        response = self.adjust_path(response, move_type)
        # Add Authorization header if token is available
        if self.token:
                response.action.headers = {"Authorization": f"Bearer {self.token}"}

        # Convert response to JSON and display it
        command = json.loads(pydantic_core.to_json(response).decode())
        log.console.print(Panel(json.dumps(command, indent=2), title="assistant"))

        # Execute the command and parse the result
        with log.console.status("[bold green]Executing command..."):


            result = await response.execute()
            self.query_counter += 1
            result_dict = self.extract_json(result)
            log.console.print(Panel(result, title="tool"))
            if "Could not request" in result:
                return False, prompt_history, result, ""

        if response.action.__class__.__name__ != "RecordNote":
            self.prompt_helper.tried_endpoints.append(response.action.path)

            # Parse HTTP status and request path
            result_str = self.parse_http_status_line(result)
            request_path = response.action.path

            if "action" not in command:
                return False, prompt_history, response, completion

            # Check response success
            is_successful = result_str.startswith("200")
            msg = {"role": message.role, "content": message.content, "tool_calls": message.tool_calls}
            prompt_history.append(msg)
            self.last_path = request_path

            status_message = self.check_if_successful(is_successful, request_path, result_dict, result_str, categorized_endpoints)
            log.console.print(Panel(status_message, title="system"))

            prompt_history.append(tool_message(status_message, tool_call_id))

        else:
            prompt_history.append(tool_message(result, tool_call_id))
        is_successful = False
        result_str = result[:20]

        return is_successful, prompt_history, result, result_str

    def extract_params(self, url):

        params = re.findall(r'(\w+)=([^&]*)', url)
        extracted_params = {key: value for key, value in params}

        return extracted_params

    def extract_json(self, response: str) -> dict:
        try:
            # Find the start of the JSON body by locating the first '{' character
            json_start = response.index('{')
            # Extract the JSON part of the response
            json_data = response[json_start:]
            # Convert the JSON string to a dictionary
            data_dict = json.loads(json_data)
            return data_dict
        except (ValueError, json.JSONDecodeError) as e:
            print(f"Error extracting JSON: {e}")
            return {}

    def get_next_path(self, path):
        counter = 0
        if self.prompt_helper.current_step >= ExploreStep.QUERY:
            new_path = self.create_common_query_for_endpoint(path)
            if path == "params":
                return path
            return new_path
        try:

            new_path = next(self.common_endpoints_categorized_cycle[self.prompt_helper.current_step])
            while not new_path in self.prompt_helper.found_endpoints or not new_path in self.prompt_helper.unsuccessful_paths:
                new_path = next(self.common_endpoints_categorized_cycle[self.prompt_helper.current_step])
                counter = counter + 1
                if counter >= 6:
                    return new_path

            return new_path
        except StopIteration:
            return path


    def finalize_path(self, path: str) -> str:
            """
            Final processing on the path before returning: replace any '{id}'
            placeholder with the generic instance id '1'.
            """
            if path is None:
                l = self.common_endpoints_categorized[self.prompt_helper.current_step]
                return random.choice(l)
            path = path.replace("{id}", "1")
            return path

    def adjust_path_if_necessary(self, path: str) -> str:
            """
            Steer the next request path according to the current exploration step.

            The body is a ladder over ``self.prompt_helper.current_step`` (see
            :class:`ExploreStep`): each step picks the next candidate path of the
            matching shape, falling back to a fresh instance/sub/related/multi-level
            endpoint (or a random common endpoint) when the current path has already
            been tried. Steps:

            - ``ROOT``: prefer the root of a multi-part path, else advance.
            - ``INSTANCE``: build/keep a ``/{id}`` instance path.
            - ``SUBRESOURCE`` / ``RELATED`` / ``MULTI_LEVEL``: derive the deeper
              endpoint via the corresponding prompt-helper builder.
            - ``QUERY``: append a query parameter to the endpoint.

            The result is finalized by :meth:`finalize_path`.
            """
            # Ensure path starts with a slash
            if not path.startswith("/"):
                path = "/" + path

            parts = [part for part in path.split("/") if part]
            pattern_replaced_path = self.pattern_matcher.replace_according_to_pattern(path)

            # Reset logic
            if self.no_action_counter == 5:
                self.no_action_counter = 0
                # Return next path (finalize it)
                return self.finalize_path(self.get_next_path(path))

            if parts:
                root_path = '/' + parts[0]

                if self.prompt_helper.current_step == ExploreStep.ROOT:
                    if len(parts) > 1:
                        if root_path not in (
                                self.prompt_helper.found_endpoints or self.prompt_helper.unsuccessful_paths):
                            self.save_endpoint(path)
                            return self.finalize_path(root_path)
                        else:
                            self.save_endpoint(path)
                            return self.finalize_path(self.get_next_path(path))
                    else:
                        # Single-part path
                        if (path in self.prompt_helper.found_endpoints or
                                path in self.prompt_helper.unsuccessful_paths or
                                path == self.last_path):
                            return self.finalize_path(self.get_next_path(path))

                elif self.prompt_helper.current_step == ExploreStep.INSTANCE:
                    if len(parts) != 2:
                        if path in self.prompt_helper.unsuccessful_paths:
                            ep = self.prompt_helper._get_instance_level_endpoint(self.name)
                            return self.finalize_path(ep)

                        if path in self.prompt_helper.found_endpoints and len(parts) == 1:
                            return self.finalize_path(f"{path}/1")

                        ep = self.prompt_helper._get_instance_level_endpoint(self.name)
                        return self.finalize_path(ep)

                elif self.prompt_helper.current_step == ExploreStep.SUBRESOURCE:
                    if path in self.prompt_helper.unsuccessful_paths:
                        ep = self.prompt_helper._get_sub_resource_endpoint(
                            random.choice(self.prompt_helper.found_endpoints),
                            self.common_endpoints, self.name
                        )
                        return self.finalize_path(ep)

                    ep = self.prompt_helper._get_sub_resource_endpoint(path, self.common_endpoints, self.name)
                    return self.finalize_path(ep)

                elif self.prompt_helper.current_step == ExploreStep.RELATED:
                    if path in self.prompt_helper.unsuccessful_paths:
                        ep = self.prompt_helper._get_related_resource_endpoint(
                            random.choice(self.prompt_helper.found_endpoints),
                            self.common_endpoints,
                            self.name
                        )
                        return self.finalize_path(ep)

                    ep = self.prompt_helper._get_related_resource_endpoint(path, self.common_endpoints, self.name)
                    return self.finalize_path(ep)

                elif self.prompt_helper.current_step == ExploreStep.MULTI_LEVEL:
                    if path in self.prompt_helper.unsuccessful_paths:
                        ep = self.prompt_helper._get_multi_level_resource_endpoint(
                            random.choice(self.prompt_helper.found_endpoints),
                            self.common_endpoints,
                            self.name
                        )
                    else:
                        ep = self.prompt_helper._get_multi_level_resource_endpoint(path, self.common_endpoints, self.name)
                    return self.finalize_path(ep)

                elif (self.prompt_helper.current_step == ExploreStep.QUERY and
                      "?" not in path):
                    new_path = self.create_common_query_for_endpoint(path)
                    # If "no params", keep original path, else use new_path
                    return self.finalize_path(path if new_path == "no params" else new_path)

                # Already-handled paths
                if (path in {self.last_path,
                             *self.prompt_helper.unsuccessful_paths,
                             *self.prompt_helper.found_endpoints}
                        and self.prompt_helper.current_step != ExploreStep.QUERY):
                    return self.finalize_path(random.choice(self.common_endpoints))

                # Pattern-based check
                if (pattern_replaced_path in self.prompt_helper.found_endpoints or
                    pattern_replaced_path in self.prompt_helper.unsuccessful_paths) and self.prompt_helper.current_step != ExploreStep.INSTANCE:
                    return self.finalize_path(random.choice(self.common_endpoints))

            else:
                # No parts
                if self.prompt_helper.current_step == ExploreStep.ROOT:
                    root_level_endpoints = self.prompt_helper._get_root_level_endpoints()
                    chosen = root_level_endpoints[0] if root_level_endpoints else self.get_next_path(path)
                    return self.finalize_path(chosen)

                if self.prompt_helper.current_step == ExploreStep.INSTANCE:
                    ep = self.prompt_helper._get_instance_level_endpoint(self.name)
                    return self.finalize_path(ep)

            # If none of the above conditions matched, we finalize the path or get_next_path
            if path:
                return self.finalize_path(path)
            return self.finalize_path(self.get_next_path(path))



    def save_endpoint(self, path):

        parts = [part.strip() for part in path.split("/") if part.strip()]
        if len(parts) not in self.saved_endpoints.keys():
            self.saved_endpoints[len(parts)] = []
        if path not in self.saved_endpoints[len(parts)]:
            self.saved_endpoints[len(parts)].append(path)
        if path not in self.prompt_helper.saved_endpoints:
            self.prompt_helper.saved_endpoints.append(path)

    def create_common_query_for_endpoint(self, endpoint):
        """
        Constructs complete URLs with one query parameter for each API endpoint.


        Returns:
            list: A list of full URLs with appended query parameters.
        """

        endpoint = endpoint + "?"
        # Define common query parameters
        common_query_params = [
            "page", "limit", "sort", "filter", "search", "api_key", "access_token",
            "callback", "fields", "expand", "since", "until", "status", "lang",
            "locale", "region", "embed", "version", "format", "username"
        ]

        # Sample dictionary of parameters for demonstration
        full_params = {
            "page": 2,
            "limit": 10,
            "sort": "date_desc",
            "filter": "status:active",
            "search": "example query",
            "api_key": "YourAPIKeyHere",
            "access_token": "YourAccessToken",
            "callback": "myFunction",
            "fields": "id,name,status",
            "expand": "details,owner",
            "since": "2020-01-01T00:00:00Z",
            "until": "2022-01-01T00:00:00Z",
            "status": "active",
            "lang": "en",
            "locale": "en_US",
            "region": "North America",
            "embed": "true",
            "version": "1.0",
            "format": "json",
            "username": "test"
        }

        urls_with_params = []

        # Iterate through all found endpoints
        # Pick one random parameter from the common query params
        random_param_key = random.choice(common_query_params)

        # Check if the selected key is in the full_params
        if random_param_key in full_params:
            sampled_params = {random_param_key: full_params[random_param_key]}
        else:
            sampled_params = {}

        # Encode the parameters into a query string
        query_string = urlencode(sampled_params)

        # Ensure the endpoint doesn't end with a slash
        if endpoint.endswith('/') or endpoint.endswith("?"):
            endpoint = endpoint[:-1]

        # Construct the full URL with the query parameter
        full_url = f"{endpoint}?{query_string}"
        urls_with_params.append(full_url)
        if endpoint in self.prompt_helper.query_endpoints_params.keys():
            if random_param_key not in self.prompt_helper.query_endpoints_params[endpoint]:
                if random_param_key not in self.prompt_helper.tried_endpoints_with_params[endpoint]:
                    return full_url

        if urls_with_params == None:
            return "no params"
        return random.choice(urls_with_params)

    def adjust_path(self, response, move_type):
            """
            Adjusts the response action path based on current step, unsuccessful paths, and move type.

            Args:
                response (Any): The HTTP response object containing the action and path.
                move_type (str): The type of move (e.g., 'exploit') influencing path adjustment.

            Returns:
                Any: The updated response object with an adjusted path.
            """
            old_path = response.action.path

            if "?" not in response.action.path and self.prompt_helper.current_step == ExploreStep.QUERY:
                if response.action.path not in self.prompt_helper.saved_endpoints:
                    if response.action.query is not None:
                        return response
            # Process action if it's not RecordNote
            if response.action.__class__.__name__ != "RecordNote":
                if self.prompt_helper.current_step == ExploreStep.QUERY :
                    response.action.path = self.create_common_query_for_endpoint(response.action.path)

                if response.action.path in self.prompt_helper.unsuccessful_paths:
                    self.repeat_counter += 1

                if self.no_action_counter == 5:
                    response.action.path = self.get_next_path(response.action.path)
                    self.no_action_counter = 0
                parts = response.action.path.split("/")
                len_path = len([part.strip() for part in parts if part.strip()])
                if self.prompt_helper.current_step == ExploreStep.INSTANCE:
                    if len_path  <2 or len_path > 2 or response.action.path  in self.prompt_helper.unsuccessful_paths:
                        id = self.prompt_helper.get_possible_id_for_instance_level_ep(parts[0])
                        if id:
                            response.action.path = parts[0] + f"/{id}"
                else:
                    if self.prompt_helper.current_step != ExploreStep.QUERY and not response.action.path.endswith("?"):
                        adjusted_path = self.adjust_path_if_necessary(response.action.path)
                        if adjusted_path != None:
                            response.action.path = adjusted_path

                        if move_type == "exploit" and self.repeat_counter == 3:
                            if len(self.prompt_helper.endpoints_to_try) != 0:
                                exploit_endpoint = self.prompt_helper.endpoints_to_try[0]
                                response.action.path = self.create_common_query_for_endpoint(exploit_endpoint)
                            else:
                                exploit_endpoint = self.prompt_helper._get_instance_level_endpoint(self.name)
                                self.repeat_counter = 0

                                if exploit_endpoint and response.action.path not in self.prompt_helper._get_instance_level_endpoints(self.name):
                                    response.action.path = exploit_endpoint
            if move_type != "exploit":
                response.action.method = "GET"

            if response.action.path == None:
                response.action.path = old_path

            return response

    def check_if_successful(self, is_successful, request_path, result_dict, result_str, categorized_endpoints):
        self.prompt_helper.new_endpoint_found = False
        if is_successful:
            self.prompt_helper.new_endpoint_found =True
            if "?" in request_path and request_path not in self.prompt_helper.found_query_endpoints:
                self.prompt_helper.found_query_endpoints.append(request_path)
            ep = request_path.split("?")[0]
            if ep in self.prompt_helper.endpoints_to_try:
                self.prompt_helper.endpoints_to_try.remove(ep)
            if ep in self.saved_endpoints:
                self.saved_endpoints[1].remove(ep)
            if ep in self.prompt_helper.saved_endpoints:
                self.prompt_helper.saved_endpoints.remove(ep)
            if ep not in self.prompt_helper.found_endpoints:
                self.prompt_helper.found_endpoints.append(ep)

            self.prompt_helper.query_endpoints_params.setdefault(ep, [])
            self.prompt_helper.tried_endpoints_with_params.setdefault(ep, [])
            if ep not in self.prompt_helper.found_endpoints:
                if "?" not in ep and ep not in self.prompt_helper.found_endpoints:
                    self.prompt_helper.found_endpoints.append(ep)
                if "?" in ep and ep not in self.prompt_helper.found_query_endpoints:
                    self.prompt_helper.found_query_endpoints.append(ep)

            for key in self.extract_params(request_path):
                if ep not in self.prompt_helper.query_endpoints_params:
                    self.prompt_helper.query_endpoints_params[ep] = []
                if ep not  in self.prompt_helper.tried_endpoints_with_params:
                    self.prompt_helper.tried_endpoints_with_params[ep] = []
                self.prompt_helper.query_endpoints_params[ep].append(key)
                self.prompt_helper.tried_endpoints_with_params[ep].append(key)

            status_message = f"{request_path} is a correct endpoint"
            self.no_new_endpoint_counter= 0
        else:
            error_msg = result_dict.get("error", {}).get("message", "unknown error") if isinstance(
                result_dict.get("error", {}), dict) else result_dict.get("error", "unknown error")
            self.no_new_endpoint_counter +=1
            if error_msg == "unknown error" and (result_str.startswith("4") or result_str.startswith("5")):
                error_msg = result_str

            if result_str.startswith("400") or result_str.startswith("401") or result_str.startswith("403"):
                status_message = f"{request_path} is a correct endpoint, but encountered an error: {error_msg}"
                self.prompt_helper.endpoints_to_try.append(request_path)
                self.prompt_helper.bad_request_endpoints.append(request_path)
                self.save_endpoint(request_path)
                if request_path not in self.prompt_helper.saved_endpoints:
                    self.prompt_helper.saved_endpoints.append(request_path)

                if error_msg not in self.prompt_helper.correct_endpoint_but_some_error:
                    self.prompt_helper.correct_endpoint_but_some_error[error_msg] = []
                self.prompt_helper.correct_endpoint_but_some_error[error_msg].append(request_path)
            else:
                self.prompt_helper.unsuccessful_paths.append(request_path)
                status_message = f"{request_path} is not a correct endpoint; Reason: {error_msg}"

            ep = request_path.split("?")[0]
            self.prompt_helper.tried_endpoints_with_params.setdefault(ep, [])
            for key in self.extract_params(request_path):
                self.prompt_helper.tried_endpoints_with_params[ep].append(key)

        return status_message
