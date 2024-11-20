import re

import nltk

from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.information import PromptStrategy


class PromptGenerationHelper(object):
    """
    A helper class for managing and generating prompts, tracking endpoints, and ensuring consistency in HTTP actions.

    Attributes:
        response_handler (object): Handles responses for prompts.
        found_endpoints (list): A list of discovered endpoints.
        endpoint_methods (dict): A dictionary mapping endpoints to their HTTP methods.
        endpoint_found_methods (dict): A dictionary mapping HTTP methods to endpoints.
        schemas (dict): A dictionary of schemas used for constructing HTTP requests.
    """

    def __init__(self,
                 host: str = ""):
        """
        Initializes the PromptAssistant with a response handler and downloads necessary NLTK models.

        Args:
            response_handler (object): The response handler used for managing responses.
            schemas(tuple):  Schemas used
        """
        self.current_category = "root_level"
        self.correct_endpoint_but_some_error = {}
        self.hint_for_next_round = ""
        self.schemas = []
        self.endpoints = []
        self.found_endpoints = []
        self.endpoint_methods = {}
        self.endpoint_found_methods = {}
        self.host = host
        self.unsuccessful_paths = ["/"]
        self.current_step = 1
        self.document_steps = 0

    def setup_prompt_information(self, schemas, endpoints):
        self.schemas = schemas
        self.endpoints = endpoints
        self.current_endpoint = endpoints[0]

    def find_missing_endpoint(self, endpoints: dict) -> str:
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
            match = re.match(r'^/([^/]+)(/|/:id)?$', endpoint)
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
                if f'/{resource}/:id' in self.unsuccessful_paths:
                    continue
                return f'/{resource}/:id'

        # Return an empty string if no missing endpoints are found
        return ""

    def get_endpoints_needing_help(self, info=""):
        """
        Identifies missing endpoints first, then checks for endpoints needing additional HTTP methods,
        returning guidance accordingly.

        Args:
            info (str): Additional information to include in the response.

        Returns:
            list: A list containing guidance for the first missing endpoint or the first missing method
                  of an endpoint that needs help.
        """

        # Step 1: Check for missing endpoints
        missing_endpoint = self.find_missing_endpoint(endpoints=self.found_endpoints)

        if missing_endpoint and not missing_endpoint in self.unsuccessful_paths:
            formatted_endpoint = missing_endpoint.replace(":id", "1") if ":id" in missing_endpoint else missing_endpoint
            return [
                f"{info}\n",
                f"For endpoint {formatted_endpoint}, find this missing method: GET."
            ]

        # Step 2: Check for endpoints needing additional HTTP methods
        http_methods_set = {"GET", "POST", "PUT", "DELETE"}
        for endpoint, methods in self.endpoint_methods.items():
            missing_methods = http_methods_set - set(methods)
            if missing_methods:
                needed_method = next(iter(missing_methods))
                formatted_endpoint = endpoint.replace(":id", "1") if ":id" in endpoint else endpoint
                return [
                    f"{info}\n",
                    f"For endpoint {formatted_endpoint}, find this missing method: {needed_method}."
                ]

        return [
            f"Look for any endpoint that might be missing, exclude endpoints from this list :{self.unsuccessful_paths}"]

    def get_http_action_template(self, method):
        """
        Constructs a consistent HTTP action description based on the provided method.

        Args:
            method (str): The HTTP method to construct the action description for.

        Returns:
            str: The constructed HTTP action description.
        """
        if method in ["POST", "PUT"]:
            return f"Create HTTPRequests of type {method} considering the found schemas: {self.schemas} and understand the responses. Ensure that they are correct requests."
        else:
            return f"Create HTTPRequests of type {method} considering only the object with id=1 for the endpoint and understand the responses. Ensure that they are correct requests."

    def _get_initial_documentation_steps(self, common_steps, strategy):
        """
        Provides the initial steps for identifying available endpoints and documenting their details.

        Args:
            common_steps (list): A list of common steps to be included.

        Returns:
            list: A list of initial steps combined with common steps.
        """
        self.unsuccessful_paths = list(set(self.unsuccessful_paths))
        self.found_endpoints = list(set(self.found_endpoints))
        endpoints_missing_id_or_query = []
        hint = ""

        if self.current_step == 2:

            if "Missing required field: ids" in self.correct_endpoint_but_some_error.keys():
                endpoints_missing_id_or_query = list(
                    set(self.correct_endpoint_but_some_error['Missing required field: ids']))
                hint = f"ADD an id after these endpoints: {endpoints_missing_id_or_query}" + f' avoid getting this error again : {self.hint_for_next_round}'
                if "base62" in self.hint_for_next_round:
                    hint += "Try a id like 6rqhFgbbKwnb9MLmUQDhG6"
            else:
                if "base62" in self.hint_for_next_round:
                    hint = " ADD an id after endpoints!"

        if self.current_step == 3:
            if "No search query" in self.correct_endpoint_but_some_error.keys():
                endpoints_missing_id_or_query = list(set(self.correct_endpoint_but_some_error['No search query']))
                hint = f"First, try out these endpoints: {endpoints_missing_id_or_query}"
            if self.current_step == 4:
                endpoints_missing_id_or_query = [endpoint for endpoint in self.found_endpoints if "id" in endpoint]

        if "Missing required field: ids" in self.hint_for_next_round and self.current_step > 1:
            hint += "ADD an id after endpoints"

        if self.hint_for_next_round != "":
            hint += self.hint_for_next_round
        endpoints = list(set([endpoint.replace(":id", "1") for endpoint in self.found_endpoints] + ['/']))

        # Documentation steps, emphasizing mandatory header inclusion with token if available
        documentation_steps = [
            [f"Objective: Identify all accessible endpoints via GET requests for {self.host}. """],

            [
                "Query Endpoints of Type `/resource`",
                "Identify all endpoints of type `/resource`: Begin by scanning through all available endpoints and select only those that match the format `/resource`.",
                "Make GET requests to these `/resource` endpoints."
                f"Exclude already found endpoints: {self.found_endpoints}."
                f"Exclude already unsuccessful endpoints and do not try to add resources after it: {self.unsuccessful_paths}."
            ],
            [
                "Query Instance-level resource endpoint",
                f"Look for Instance-level resource endpoint : Identify endpoints of type `/resource/id` where id is the parameter for the id.",
                "Query these `/resource/id` endpoints to see if an `id` parameter resolves the request successfully."
                "Ids can be integers, longs or base62 (like 6rqhFgbbKwnb9MLmUQDhG6)."
            ],
            [
                "Query endpoints with query parameters",
                "Construct and make GET requests to these endpoints using common query parameters or based on documentation hints, testing until a valid request with query parameters is achieved."
            ],
            [
                "Query for related resource endpoints",
                "Identify related resource endpoints that match the format `/resource/id/other_resource`: "
                f"First, scan for the follwoing endpoints where an `id` in the middle position and follow them by another resource identifier.",
                "Second, look for other endpoints and query these endpoints with appropriate `id` values to determine their behavior and document responses or errors."
            ],
            [
                "Query multi-level resource endpoints",
                "Search for multi-level endpoints of type `/resource/other_resource/another_resource`: Identify any endpoints in the format with three resource identifiers.",
                "Test requests to these endpoints, adjusting resource identifiers as needed, and analyze responses to understand any additional parameters or behaviors."
            ]
        ]

        # Strategy check with token emphasis in steps
        if strategy in {PromptStrategy.IN_CONTEXT, PromptStrategy.TREE_OF_THOUGHT}:
            self.document_steps = len(documentation_steps)

            steps = documentation_steps[0] + documentation_steps[self.current_step] + [hint]
        else:
            chain_of_thought_steps = self.generate_chain_of_thought_prompt(endpoints)
            self.document_steps = len(chain_of_thought_steps)

            steps = chain_of_thought_steps[0] + chain_of_thought_steps[self.current_step] + [hint]

        return steps

    def generate_chain_of_thought_prompt(self, endpoints: list) -> list:
        """
        Creates a chain of thought prompt to guide the model through the API documentation process.

        Args:
            use_token (str): A string indicating whether authentication is required.
            endpoints (list): A list of endpoints to exclude from testing.

        Returns:
            str: A structured chain of thought prompt for documentation.
        """
        return [
            [
                f"        Objective: Find accessible endpoints via GET requests for API documentation of {self.host}. """
            ],

            [
                f""" Step 1: Check root-level resource endpoints.
Only send GET requests to root-level endpoints with a single path component after the root. This means each path should have exactly one '/' followed by a single word (e.g., '/users', '/products').                    1. Send GET requests to new paths only, avoiding any in the lists above.
                    2. Do not reuse previously tested paths."""

            ],
            [
                "Step 2: Query Instance-level resource endpoint with id",
                "Look for Instance-level resource endpoint : Identify endpoints of type `/resource/id` where id is the parameter for the id.",
                "Query these `/resource/id` endpoints to see if an `id` parameter resolves the request successfully."
                "Ids can be integers, longs or base62."
                f"Exclude already unsuccessful endpoints: {self.unsuccessful_paths}."

            ],
            [
                "Step 3: Query Subresource Endpoints",
                "Identify subresource endpoints of the form `/resource/other_resource`.",
                "Query these endpoints to check if they return data related to the main resource without requiring an `id` parameter."
                f"Exclude already unsuccessful endpoints: {self.unsuccessful_paths}."
                f"Exclude already found endpoints: {self.found_endpoints}."

            ],
            [
                "Step 4: Query endpoints with query parameters",
                "Construct and make GET requests to these endpoints using common query parameters or based on documentation hints, testing until a valid request with query parameters is achieved."
                "Limit the output to the first two entries."
                f"Exclude already unsuccessful endpoints: {self.unsuccessful_paths}."
                f"Exclude already found endpoints: {self.found_endpoints}."
            ],
            [
                "Step 5: Query for related resource endpoints",
                "Identify related resource endpoints that match the format `/resource/id/other_resource`: "
                f"First, scan for the follwoing endpoints where an `id` in the middle position and follow them by another resource identifier.",
                "Second, look for other endpoints and query these endpoints with appropriate `id` values to determine their behavior and document responses or errors."
                f"Exclude already unsuccessful endpoints: {self.unsuccessful_paths}."
                f"Exclude already found endpoints: {self.found_endpoints}."
            ],
            [
                "Step 6: Query multi-level resource endpoints",
                "Search for multi-level endpoints of type `/resource/other_resource/another_resource`: Identify any endpoints in the format with three resource identifiers.",
                "Test requests to these endpoints, adjusting resource identifiers as needed, and analyze responses to understand any additional parameters or behaviors."
                f"Exclude already unsuccessful endpoints: {self.unsuccessful_paths}."
                f"Exclude already found endpoints: {self.found_endpoints}."
            ]
        ]

    def token_count(self, text):
        """
        Counts the number of word tokens in the provided text using NLTK's tokenizer.

        Args:
            text (str): The input text to tokenize and count.

        Returns:
            int: The number of tokens in the input text.
        """
        if not isinstance(text, str):
            text = str(text)
        tokens = re.findall(r"\b\w+\b", text)
        words = [token.strip("'") for token in tokens if token.strip("'").isalnum()]
        return len(words)

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

        if not all(step in previous_prompt for step in steps):
            if isinstance(steps, list):
                potential_prompt = "\n".join(str(element) for element in steps)
            else:
                potential_prompt = str(steps) + "\n"
            return validate_prompt(potential_prompt)

        return validate_prompt(previous_prompt)
