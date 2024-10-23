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

    def __init__(self, response_handler: ResponseHandler = None, schemas: dict = None, endpoints: dict = None):
        """
        Initializes the PromptAssistant with a response handler and downloads necessary NLTK models.

        Args:
            response_handler (object): The response handler used for managing responses.
            schemas(tuple):  Schemas used
        """
        if schemas is None:
            schemas = {}

        self.response_handler = response_handler
        self.found_endpoints = ["/"]
        self.endpoint_methods = {}
        self.endpoint_found_methods = {}
        self.schemas = schemas
        self.endpoints = endpoints

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
        Identifies endpoints that need additional HTTP methods and returns guidance for the first missing method.

        Args:
            info (str): Additional information to include in the response.

        Returns:
            list: A list containing guidance for the first missing method of the first endpoint that needs help.
        """
        http_methods_set = {"GET", "POST", "PUT", "DELETE"}
        for endpoint, methods in self.endpoint_methods.items():
            missing_methods = http_methods_set - set(methods)
            if missing_methods:
                needed_method = next(iter(missing_methods))
                formatted_endpoint = endpoint.replace(":id", "1") if ":id" in endpoint else endpoint
                return [
                    f"{info}\n",
                    f"For endpoint {formatted_endpoint}, find this missing method: {needed_method}. "
                ]

        # If no endpoints need help, find missing endpoints and suggest "GET"
        missing_endpoint = self.find_missing_endpoint(endpoints=self.found_endpoints)
        print(f"------------------------------------")
        print(f"------------------------------------")
        print(f"------------------------------------")
        print(f"{info}\n{missing_endpoint}")
        print(f"------------------------------------")
        print(f"------------------------------------")
        print(f"------------------------------------")

        if missing_endpoint != "":
            formatted_endpoint = missing_endpoint.replace(":id", "1") if ":id" in missing_endpoint else \
            missing_endpoint
            return [
                f"{info}\n",
                f"For endpoint {formatted_endpoint}, find this missing method: GET. "
            ]

        return []

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
        endpoints = list(set([ endpoint.replace(":id", "1") for endpoint in self.found_endpoints] + ['/']))
        documentation_steps = [
            f"""Identify all available endpoints via GET Requests. 
            Exclude those in this list: {endpoints} 
            and endpoints that match this pattern: '/resource/number' where 'number' is greater than 1 (e.g., '/todos/2', '/todos/3').
            Only include endpoints where the number is 1 or the endpoint does not end with a number at all.

            Note down the response structures, status codes, and headers for each selected endpoint.

            For each selected endpoint, document the following details: 
            - URL
            - HTTP method
            - Query parameters and path variables
            - Expected request body structure for requests
            - Response structure for successful and error responses.
            """

        ]
        if strategy == PromptStrategy.IN_CONTEXT:
            return common_steps + documentation_steps
        else:
            return documentation_steps + common_steps

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
            #if self.token_count(prompt) <= max_tokens:
            return prompt
            #shortened_prompt = self.response_handler.get_response_for_prompt("Shorten this prompt: " + str(prompt))
            #if self.token_count(shortened_prompt) <= max_tokens:
             #   return shortened_prompt
            #return "Prompt is still too long after summarization."

        if not all(step in previous_prompt for step in steps):
            if isinstance(steps, list):
                potential_prompt = "\n".join(str(element) for element in steps)
            else:
                potential_prompt = str(steps) + "\n"
            return validate_prompt(potential_prompt)

        return validate_prompt(previous_prompt)
