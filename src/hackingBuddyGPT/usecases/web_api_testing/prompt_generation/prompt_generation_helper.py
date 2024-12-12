import json
import re

import nltk

from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.information import PromptStrategy


class PromptGenerationHelper(object):
    """
        Assists in generating prompts for web API testing by managing endpoint data,
        tracking interactions, and providing utilities for analyzing and responding to API behavior.

        Attributes:
            host (str): Base URL for the API.
            description (str): Description of the API's purpose or functionality.
            found_endpoints (list): Endpoints that have been successfully interacted with.
            tried_endpoints (list): Endpoints that have been tested, regardless of the outcome.
            unsuccessful_paths (list): Endpoints that failed during testing.
            current_step (int): Current step in the testing or documentation process.
            document_steps (int): Total number of documentation steps processed.
            endpoint_methods (dict): Maps endpoints to the HTTP methods successfully used with them.
            unsuccessful_methods (dict): Maps endpoints to the HTTP methods that failed.
            endpoint_found_methods (dict): Maps HTTP methods to the endpoints where they were found successful.
            schemas (list): Definitions of data schemas used for constructing requests and validating responses.
        """

    def __init__(self,
                 host: str = "",
                 description: str=""):
        """
          Initializes the PromptGenerationHelper with an optional host and description.

          Args:
              host (str): The base URL of the API.
              description (str): A brief description of what the API offers or its testing scope.
          """
        self.current_test_step = None
        self.current_category = "root_level"
        self.correct_endpoint_but_some_error = {}
        self.hint_for_next_round = ""
        self.description = description
        self.schemas = []
        self.endpoints = []
        self.tried_endpoints = []
        self.found_endpoints = []
        self.endpoint_methods = {}
        self.unsuccessful_methods = {}
        self.endpoint_found_methods = {}
        self.host = host
        self.unsuccessful_paths = ["/"]
        self.current_step = 1
        self.document_steps = 0
        self.tried_methods_by_enpoint = {}

        self.current_user = None

    def setup_prompt_information(self, schemas, endpoints):
        """
        Sets up essential data for prompt generation based on provided schemas and endpoints.

        Args:
            schemas (list): Data schemas for the API.
            endpoints (list): Initial list of API endpoints to test.
        """
        self.schemas = schemas
        self.endpoints = endpoints
        self.current_endpoint = endpoints[0]

    def get_user_from_prompt(self,prompts):
        """
            Extracts the user information after 'user:' from the given prompts.

            Args:
                prompts (list): A list of dictionaries representing prompts.

            Returns:
                list: A list of extracted user information.
            """
        user_info = {}
        for steps in prompts.get("steps", []):
            step = steps.get("step", "")
            # Search for the substring containing 'user:'
            if "user:" in step:
                # Extract the part after 'user:' and add it to the user_info list
                data_string = step.split("user:")[1].split(".\n")[0]
                # Replace single quotes with double quotes for JSON compatibility
                data_string_json = data_string.replace("'", '"')

                # Parse the string into a dictionary
                user_info = json.loads(data_string_json)

        return user_info

    def find_missing_endpoint(self, endpoints: list) -> str:
        """
        Identifies and returns the first missing endpoint path found.

        Args:
            endpoints (dict): A dictionary of endpoint paths (e.g., {'/resources': {...}, '/resources/:id': {...}}).

        Returns:
            str: The first missing endpoint path found.
                 Example: '/resources/:id' or '/products'
        """
        general_endpoints = set()
        parameterized_endpoints = set()

        # Extract resource names and categorize them using regex
        for endpoint in endpoints:
            # Match both general and parameterized patterns and categorize them
            match = re.match(r'^/([^/]+)(/|/{id})?$', endpoint)
            if match:
                resource = match.group(1)
                if match.group(2) == '/' or match.group(2) is None:
                    general_endpoints.add(resource)
                elif match.group(2) == '/:id':
                    parameterized_endpoints.add(resource)

        # Find missing endpoints during the comparison
        for resource in parameterized_endpoints:
            if resource not in general_endpoints:
                return f'/{resource}'
        for resource in general_endpoints:
            if resource not in parameterized_endpoints:
                if f'/{resource}/'+ '{id}' in self.unsuccessful_paths:
                    continue
                return f'/{resource}/'+ '{id}'

        # Return an empty string if no missing endpoints are found
        return ""

    def get_endpoints_needing_help(self, info=""):
        """
        Determines which endpoints need further testing or have missing methods.

        Args:
            info (str): Additional information to enhance the guidance.

        Returns:
            list: Guidance for missing endpoints or methods.
        """

        # Step 1: Check for missing endpoints
        missing_endpoint = self.find_missing_endpoint(endpoints=self.found_endpoints)

        if (missing_endpoint and not missing_endpoint in self.unsuccessful_paths
                and not 'GET' in self.unsuccessful_methods
                and missing_endpoint in self.tried_methods_by_enpoint.keys()
                and not 'GET' in self.tried_methods_by_enpoint[missing_endpoint]):
            formatted_endpoint = missing_endpoint.replace("{id}", "1") if "{id}" in missing_endpoint else missing_endpoint
            if missing_endpoint not in self.tried_methods_by_enpoint:
                self.tried_methods_by_enpoint[missing_endpoint] = []
            self.tried_methods_by_enpoint[missing_endpoint].append('GET')
            return [
                f"{info}\n",
                f"For endpoint {formatted_endpoint}, find this missing method: GET."
            ]

        # Step 2: Check for endpoints needing additional HTTP methods
        http_methods_set = {"GET", "POST", "PUT", "DELETE"}
        for endpoint, methods in self.endpoint_methods.items():
            missing_methods = http_methods_set - set(methods)
            if missing_methods and endpoint not in self.unsuccessful_paths:
                for needed_method in missing_methods:  # Iterate directly over missing methods
                    if endpoint not in self.tried_methods_by_enpoint:
                        self.tried_methods_by_enpoint[endpoint] = []

                    # Avoid retrying methods that were already unsuccessful
                    if (needed_method in self.unsuccessful_methods.get(endpoint, [])
                            or needed_method in self.tried_methods_by_enpoint[endpoint]):
                        continue

                    # Format the endpoint and append the method as tried
                    formatted_endpoint = endpoint.replace("{id}", "1") if "{id}" in endpoint else endpoint
                    self.tried_methods_by_enpoint[endpoint].append(needed_method)

                    return [
                        f"{info}\n",
                        f"For endpoint {formatted_endpoint}, find this missing method: {needed_method}."
                    ]

        return [
            f"Look for any endpoint that might be missing, exclude endpoints from this list :{self.unsuccessful_paths}"]

    def get_http_action_template(self, method):
        """
                Provides a template for HTTP actions based on the method specified.

                Args:
                    method (str): The HTTP method for the action.

                Returns:
                    str: A template describing the HTTP action to take.
        """
        if method in ["POST", "PUT"]:
            return f"Create HTTPRequests of type {method} considering the found schemas: {self.schemas} and understand the responses. Ensure that they are correct requests."
        else:
            return f"Create HTTPRequests of type {method} considering only the object with id=1 for the endpoint and understand the responses. Ensure that they are correct requests."

    def _get_initial_documentation_steps(self, common_steps, strategy, strategy_steps):
        """
        Constructs a series of documentation steps to guide the testing and documentation of API endpoints.
        These steps are formulated based on the strategy specified and integrate common steps that are essential
        across different strategies. The function also sets the number of documentation steps and determines specific
        steps based on the current testing phase.

        Args:
            common_steps (list): A list of common documentation steps that should be included in every strategy.
            strategy (PromptStrategy): The strategy to be used, which affects the specific steps included in the documentation.

        Returns:
            list: A comprehensive list of documentation steps tailored to the provided strategy, enhanced with common steps and hints for further actions.

        Detailed Steps:
            - Updates the list of unsuccessful paths and found endpoints to ensure uniqueness.
            - Depending on the strategy, it includes specific steps tailored to either in-context learning, tree of thought, or other strategies.
            - Each step is designed to methodically explore different types of endpoints (root-level, instance-level, etc.),
              focusing on various aspects such as parameter inclusion, method testing, and handling of special cases like IDs.
            - The steps are formulated to progressively document and test the API, ensuring comprehensive coverage.
        """
        # Ensure uniqueness of paths and endpoints
        self.unsuccessful_paths = list(set(self.unsuccessful_paths))
        self.found_endpoints = list(set(self.found_endpoints))
        hint = self.get_hint()

        # Combine common steps with strategy-specific steps

        self.document_steps = len(strategy_steps)
        steps = strategy_steps[0] + strategy_steps[self.current_step] + [hint]

        return steps



    def check_prompt(self, previous_prompt: list, steps: str, max_tokens: int = 900) -> str:
        """
        Validates and shortens the prompt if necessary to ensure it does not exceed the maximum token count.

        Args:
            previous_prompt (list): The previous prompt content.
            steps (str): A list of steps to be included in the new prompt.
            max_tokens (int, optional): The maximum number of tokens allowed. Defaults to 900.

        Returns:
            str: The validated and possibly shortened prompt.
        """

        def validate_prompt(prompt):
            print(f'Prompt: {prompt}')
            # if self.token_count(prompt) <= max_tokens:
            return prompt
            # shortened_prompt = self.response_handler.get_response_for_prompt("Shorten this prompt: " + str(prompt))
            # if self.token_count(shortened_prompt) <= max_tokens:
            #   return shortened_prompt
            # return "Prompt is still too long after summarization."

        if steps != None and not all(step in previous_prompt for step in steps):
            if isinstance(steps, list):
                potential_prompt = "\n".join(str(element) for element in steps)
            else:
                potential_prompt = str(steps) + "\n"
            return validate_prompt(potential_prompt)

        return validate_prompt(previous_prompt)

    def get_endpoint_for_query_params(self):
        """
        Searches for an endpoint in the found endpoints list that has query parameters.

        Returns:
            str: The first endpoint that includes a query parameter, or None if no such endpoint exists.
        """
        for endpoint in self.found_endpoints:
            if any(endpoint + "?" in element for element in self.found_endpoints):
                return endpoint
        return None

    def get_instance_level_endpoint(self):
        """
        Retrieves an instance level endpoint that has not been tested or found unsuccessful.

        Returns:
            str: A templated instance level endpoint ready to be tested, or None if no such endpoint is available.
        """
        for endpoint in self.get_instance_level_endpoints():
            templated_endpoint = endpoint.replace("1", "{id}")
            if templated_endpoint not in self.found_endpoints and endpoint not in self.unsuccessful_paths:
                return endpoint
        return None

    def get_instance_level_endpoints(self):
        """
        Generates a list of instance-level endpoints from the root-level endpoints by appending '/1'.

        Returns:
            list: A list of potentially testable instance-level endpoints derived from root-level endpoints.
        """
        instance_level_endpoints = []
        for endpoint in self.get_root_level_endpoints():
            if not endpoint + "/{id}" in self.found_endpoints or \
                    not endpoint + "/1" in self.unsuccessful_paths:
                instance_level_endpoints.append(endpoint + "/1")
        print(f'instance_level_endpoints: {instance_level_endpoints}')
        return instance_level_endpoints

    def get_hint(self):
        """
        Generates a hint based on the current step in the testing process, incorporating specific checks and conditions.

        Returns:
            str: A tailored hint that provides guidance based on the current testing phase and identified needs.
        """
        hint = ""
        if self.current_step == 2:
            instance_level_found_endpoints = [ep for ep in self.found_endpoints if "id" in ep]
            if "Missing required field: ids" in self.correct_endpoint_but_some_error:
                endpoints_missing_id_or_query = list(
                    set(self.correct_endpoint_but_some_error["Missing required field: ids"]))
                hint = f"ADD an id after these endpoints: {endpoints_missing_id_or_query} avoid getting this error again: {self.hint_for_next_round}"
            if "base62" in self.hint_for_next_round and "Missing required field: ids" not in self.correct_endpoint_but_some_error:
                hint += " Try an id like 6rqhFgbbKwnb9MLmUQDhG6"
            new_endpoint = self.get_instance_level_endpoint()
            if new_endpoint:
                hint += f" Create a GET request for this endpoint: {new_endpoint}"

        elif self.current_step == 3 and "No search query" in self.correct_endpoint_but_some_error:
            endpoints_missing_query = list(set(self.correct_endpoint_but_some_error['No search query']))
            hint = f"First, try out these endpoints: {endpoints_missing_query}"

        if self.current_step == 6:
            hint = f'Use this endpoint: {self.get_endpoint_for_query_params()}'

        if self.hint_for_next_round:
            hint += self.hint_for_next_round

        return hint

    def get_root_level_endpoints(self):
        """
        Retrieves all root-level endpoints which consist of only one path component.

        Returns:
            list: A list of root-level endpoints.
        """
        root_level_endpoints = []
        for endpoint in self.found_endpoints:
            parts = [part for part in endpoint.split("/") if part]
            if len(parts) == 1 and not endpoint+ "/{id}" in self.found_endpoints :
                root_level_endpoints.append(endpoint)
        return root_level_endpoints