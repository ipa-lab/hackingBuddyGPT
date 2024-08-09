import nltk
from nltk.tokenize import word_tokenize


class PromptHelper(object):

    def __init__(self, response_handler):
        self.response_handler = response_handler
        self.found_endpoints = ["/"]
        self.endpoint_methods = {}
        self.endpoint_found_methods = {}
        self.schemas = {}
        # Check if the models are already installed
        nltk.download('punkt')
        nltk.download('stopwords')

    def get_endpoints_needing_help(self):
        endpoints_needing_help = []
        endpoints_and_needed_methods = {}
        http_methods_set = {"GET", "POST", "PUT", "DELETE"}

        for endpoint, methods in self.endpoint_methods.items():
            missing_methods = http_methods_set - set(methods)
            if len(methods) < 4:
                endpoints_needing_help.append(endpoint)
                endpoints_and_needed_methods[endpoint] = list(missing_methods)

        if endpoints_needing_help:
            first_endpoint = endpoints_needing_help[0]
            needed_method = endpoints_and_needed_methods[first_endpoint][0]
            return [
                f"For endpoint {first_endpoint} find this missing method: {needed_method}. If all the HTTP methods have already been found for an endpoint, then do not include this endpoint in your search."]
        return []
    def get_http_action_template(self, method):
        """Helper to construct a consistent HTTP action description."""
        if method == "POST" and method == "PUT":
            return (
                f"Create HTTPRequests of type {method} considering the found schemas: {self.schemas} and understand the responses. Ensure that they are correct requests."
                )

        else:
            return (
                f"Create HTTPRequests of type {method} considering only the object with id=1 for the endpoint and understand the responses. Ensure that they are correct requests.")
    def get_initial_steps(self, common_steps):
            return [
                "Identify all available endpoints via GET Requests. Exclude those in this list: {self.found_endpoints}",
                "Note down the response structures, status codes, and headers for each endpoint.",
                "For each endpoint, document the following details: URL, HTTP method, query parameters and path variables, expected request body structure for requests, response structure for successful and error responses."
            ] + common_steps

    def get_phase_steps(self, phase, common_steps):
            if phase != "DELETE":
                return [
                    f"Identify for all endpoints {self.found_endpoints} excluding {self.endpoint_found_methods[phase]} a valid HTTP method {phase} call.",
                    self.get_http_action_template(phase)
                ] + common_steps
            else:
                return [
                    "Check for all endpoints the DELETE method. Delete the first instance for all endpoints.",
                    self.get_http_action_template(phase)
                ] + common_steps



    def token_count(self, text):
        """
            Counts the number of word tokens in the provided text using NLTK's tokenizer.

            Args:
                text (str): The input text to tokenize and count.

            Returns:
                int: The number of tokens in the input text.
            """
        # Tokenize the text using NLTK
        tokens = word_tokenize(text)
        # Filter out punctuation marks
        words = [token for token in tokens if token.isalnum()]
        return len(words)
    def check_prompt(self, previous_prompt, steps, max_tokens=900):
        def validate_prompt(prompt):
            if self.token_count(prompt) <= max_tokens:
                return prompt
            shortened_prompt = self.response_handler.get_response_for_prompt("Shorten this prompt." + prompt )
            if self.token_count(shortened_prompt) <= max_tokens:
                return shortened_prompt
            return "Prompt is still too long after summarization."

        if not all(step in previous_prompt for step in steps):
            potential_prompt = "\n".join(steps)
            return validate_prompt(potential_prompt)

        return validate_prompt(previous_prompt)