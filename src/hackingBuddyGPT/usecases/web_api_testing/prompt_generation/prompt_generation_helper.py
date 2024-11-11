import re

import nltk

from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.information import PromptStrategy
from hackingBuddyGPT.usecases.web_api_testing.response_processing.response_handler import ResponseHandler


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
                 response_handler: ResponseHandler = None,
                 schemas: dict = None,
                 endpoints: dict = None,
                 description: str = ""):
        """
        Initializes the PromptAssistant with a response handler and downloads necessary NLTK models.

        Args:
            response_handler (object): The response handler used for managing responses.
            schemas(tuple):  Schemas used
        """
        if schemas is None:
            schemas = {}

        self.response_handler = response_handler
        self.found_endpoints = []
        self.endpoint_methods = {}
        self.endpoint_found_methods = {}
        self.schemas = schemas
        self.endpoints = endpoints
        self.description = description
        self.unsuccessful_paths = ["/"]
        self.current_step = 1

    import re

    import re

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
            f"Look for any endpoint that might be missing, exclude enpoints from this list :{self.unsuccessful_paths}"]

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

        endpoints = list(set([endpoint.replace(":id", "1") for endpoint in self.found_endpoints] + ['/']))

        # Documentation steps, emphasizing mandatory header inclusion with token if available
        documentation_steps = [
            [f"""
            Identify all accessible endpoints via GET requests for {self.description}. 
            """],

            [f"""Exclude:
                - Already identified endpoints: {endpoints}.
                - Paths previously marked as unsuccessful: {self.unsuccessful_paths}.
                Only seek new paths not on the exclusion list."""],

            [f"""Endpoint Identification Steps:
                - Start with general endpoints like "/resource" or "/resource/1".
                - Test specific numbered endpoints, e.g., "/todos/2", "/todos/3".
                - Include paths ending with "1", those without numbers, and patterns like "number/resource".
                **Note:** Always include Authorization headers with each request if token is available.
                """],

            [f"""For each identified endpoint, document:
                - URL and HTTP Method.
                - Query parameters and path variables.
                - Expected request body, if applicable.
                - Success and error response structures, including status codes and headers.
                - **Reminder:** Include Authorization headers in documentation for endpoints requiring authentication.
                """]
        ]

        # Strategy check with token emphasis in steps
        if strategy in {PromptStrategy.IN_CONTEXT, PromptStrategy.TREE_OF_THOUGHT}:
            steps = documentation_steps
        else:
            chain_of_thought_steps = self.generate_chain_of_thought_prompt(endpoints)
            steps = chain_of_thought_steps

        return steps

    def generate_chain_of_thought_prompt(self,  endpoints: list) -> list:
        """
        Creates a chain of thought prompt to guide the model through the API documentation process.

        Args:
            use_token (str): A string indicating whether authentication is required.
            endpoints (list): A list of endpoints to exclude from testing.

        Returns:
            str: A structured chain of thought prompt for documentation.
        """

        return [
            [f"Objective: Identify all accessible endpoints via GET requests for {self.description}. """],

            [f"**Step 1: Identify Accessible Endpoints**",
             f"- Use GET requests to list available endpoints.",
             f"- **Do NOT search** the following paths:",
             f"  - Exclude root path: '/' (Do not include this in the search results). and found endpoints: {self.found_endpoints}",
             f"  - Exclude any paths previously identified as unsuccessful, including: {self.unsuccessful_paths}",
             f"- Only search for new paths not on the exclusion list above.\n"],

            [f"**Step 2: Endpoint Search Strategy**",
             f"- Start with general endpoints like '/resource' or '/resource/1'.",
             f"- Check for specific numbered endpoints, e.g., '/todos/2', '/todos/3'.",
             f"- Include endpoints matching:",
             f"  - Paths ending in '1'.",
             f"  - Paths without numbers.",
             f"  - Patterns like 'number/resource'.\n"],

            [f"**Step 3: Document Each Endpoint**",
             f"Document the following details for each identified endpoint:",
             f"- **URL**: Full endpoint URL.",
             f"- **HTTP Method**: Method used for this endpoint.",
             f"- **Query Parameters and Path Variables**: List required parameters.",
             f"- **Request Body** (if applicable): Expected format and fields.",
             f"- **Response Structure**: Include success and error response details, including:",
             f"  - **Status Codes**",
             f"  - **Response Headers**",
             f"  - **Response Body Structure**\n"],

            ["**Final Step: Verification**",
             f"- Ensure all documented endpoints are accurate and meet initial criteria.",
             f"- Verify no excluded endpoints are included.",
             f"- Review each endpoint for completeness and clarity."]
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
            #shortened_prompt = self.response_handler.get_response_for_prompt("Shorten this prompt: " + str(prompt))
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
