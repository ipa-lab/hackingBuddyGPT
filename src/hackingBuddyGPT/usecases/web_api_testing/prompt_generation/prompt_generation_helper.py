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

    def get_endpoints_needing_help(self, info=""):
        """
        Identifies endpoints that need additional HTTP methods and returns guidance for the first missing method.

        Returns:
            list: A list containing guidance for the first missing method of the first endpoint that needs help.
        """
        endpoints_needing_help = []
        endpoints_and_needed_methods = {}
        http_methods_set = {"GET", "POST", "PUT", "DELETE"}

        for endpoint, methods in self.endpoint_methods.items():
            if len(methods) >= 4:
                continue

            # the endpoint needs help
            missing_methods = http_methods_set - set(methods)
            endpoints_needing_help.append(endpoint)
            endpoints_and_needed_methods[endpoint] = list(missing_methods)

        if endpoints_needing_help:
            first_endpoint = endpoints_needing_help[0]
            needed_method = endpoints_and_needed_methods[first_endpoint][0]
            print(F'{first_endpoint}: {needed_method}')
            if ":id" in first_endpoint:
                first_endpoint = first_endpoint.replace(":id", "1")
            return [
                info + "/n",
                f"For endpoint {first_endpoint}, find this missing method: {needed_method}. "
                #f"If all HTTP methods have already been found for an endpoint, do not include this endpoint in your search."
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
        documentation_steps = [
            f"""Identify all available endpoints via GET Requests. 
            Exclude those in this list: {[ endpoint.replace(":id", "1") for endpoint in self.found_endpoints]} 
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
