import nltk
from nltk.tokenize import word_tokenize
from instructor.retry import InstructorRetryException


class PromptEngineer(object):
    '''Prompt engineer that creates prompts of different types'''

    def __init__(self, strategy, llm_handler, history, schemas, response_handler):
        """
        Initializes the PromptEngineer with a specific strategy and handlers for LLM and responses.

        Args:
            strategy (PromptStrategy): The prompt engineering strategy to use.
            llm_handler (object): The LLM handler.
            history (dict, optional): The history of chats. Defaults to None.
            schemas (object): The schemas to use.
            response_handler (object): The handler for managing responses.

        Attributes:
            strategy (PromptStrategy): Stores the provided strategy.
            llm_handler (object): Handles the interaction with the LLM.
            nlp (spacy.lang.en.English): The spaCy English model used for NLP tasks.
            _prompt_history (dict): Keeps track of the conversation history.
            prompt (dict): The current state of the prompt history.
            previous_prompt (str): The previous prompt content based on the conversation history.
            schemas (object): Stores the provided schemas.
            response_handler (object): Manages the response handling logic.
            round (int): Tracks the current round of conversation.
            strategies (dict): Maps strategies to their corresponding methods.
        """
        self.strategy = strategy
        self.response_handler = response_handler
        self.llm_handler = llm_handler
        self.round = 0
        self.found_endpoints = ["/"]
        self.endpoint_methods = {}
        self.endpoint_found_methods = {}
        # Check if the models are already installed
        nltk.download('punkt')
        nltk.download('stopwords')
        self._prompt_history = history
        self.prompt = {self.round: {"content": "initial_prompt"}}
        self.previous_prompt = self._prompt_history[self.round]["content"]
        self.schemas = schemas

        self.strategies = {
            PromptStrategy.IN_CONTEXT: self.in_context_learning,
            PromptStrategy.CHAIN_OF_THOUGHT: self.chain_of_thought,
            PromptStrategy.TREE_OF_THOUGHT: self.tree_of_thought
        }

    def generate_prompt(self, doc=False):
        """
        Generates a prompt based on the specified strategy and gets a response.

        This method directly calls the appropriate strategy method to generate
        a prompt and then gets a response using that prompt.
        """
        # Directly call the method using the strategy mapping
        prompt_func = self.strategies.get(self.strategy)
        is_good = False
        if prompt_func:
            while not is_good:
                prompt = prompt_func(doc)
                try:
                    response_text = self.response_handler.get_response_for_prompt(prompt)
                    is_good = self.evaluate_response(prompt, response_text)
                except InstructorRetryException :
                    prompt = prompt_func(doc, hint=f"invalid prompt:{prompt}")
                if is_good:
                    self._prompt_history.append( {"role":"system", "content":prompt})
                    self.previous_prompt = prompt
                    self.round = self.round +1
                    return self._prompt_history

    def in_context_learning(self, doc=False, hint=""):
        """
        Generates a prompt for in-context learning.

        This method builds a prompt using the conversation history
        and the current prompt.

        Returns:
            str: The generated prompt.
        """
        history_content = [entry["content"] for entry in self._prompt_history]
        prompt_content = self.prompt.get(self.round, {}).get("content", "")

        # Add hint if provided
        if hint:
            prompt_content += f"\n{hint}"

        return "\n".join(history_content + [prompt_content])

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
    def chain_of_thought(self, doc=False, hint=""):
        """
        Generates a prompt using the chain-of-thought strategy.

        Args:
            doc (bool): Determines whether the documentation-oriented chain of thought should be used.
            hint (str): Additional hint to be added to the chain of thought.

        Returns:
            str: The generated prompt.
        """
        common_steps = [
            "Identify common data structures returned by various endpoints and define them as reusable schemas. Determine the type of each field (e.g., integer, string, array) and define common response structures as components that can be referenced in multiple endpoint definitions.",
            "Create an OpenAPI document including metadata such as API title, version, and description, define the base URL of the API, list all endpoints, methods, parameters, and responses, and define reusable schemas, response types, and parameters.",
            "Ensure the correctness and completeness of the OpenAPI specification by validating the syntax and completeness of the document using tools like Swagger Editor, and ensure the specification matches the actual behavior of the API.",
            "Refine the document based on feedback and additional testing, share the draft with others, gather feedback, and make necessary adjustments. Regularly update the specification as the API evolves.",
            "Make the OpenAPI specification available to developers by incorporating it into your API documentation site and keep the documentation up to date with API changes."
        ]

        http_methods = ["PUT", "DELETE"]
        http_phase = {10: http_methods[0], 15: http_methods[1]}
        if doc:
            if self.round <= 5:
                chain_of_thought_steps = self.get_initial_steps(common_steps)
            elif self.round <= 10:
                phase = http_phase.get(min(filter(lambda x: self.round <= x, http_phase.keys())))
                chain_of_thought_steps = self.get_phase_steps(phase, common_steps)
            else:
                chain_of_thought_steps = self.get_endpoints_needing_help()
        else:
            if self.round == 0:
                chain_of_thought_steps = ["Let's think step by step."]
            elif self.round <= 20:
                focus_phases = ["endpoints", "HTTP method GET", "HTTP method POST and PUT", "HTTP method DELETE"]
                focus_phase = focus_phases[self.round // 5]
                chain_of_thought_steps = [f"Just focus on the {focus_phase} for now."]
            else:
                chain_of_thought_steps = ["Look for exploits."]

        if hint:
            chain_of_thought_steps.append(hint)

        prompt = self.check_prompt(self.previous_prompt, chain_of_thought_steps)
        return prompt

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


    def check_prompt(self, previous_prompt, chain_of_thought_steps, max_tokens=900):
        def validate_prompt(prompt):
            if self.token_count(prompt) <= max_tokens:
                return prompt
            shortened_prompt = self.response_handler.get_response_for_prompt("Shorten this prompt." + prompt )
            if self.token_count(shortened_prompt) <= max_tokens:
                return shortened_prompt
            return "Prompt is still too long after summarization."

        if not all(step in previous_prompt for step in chain_of_thought_steps):
            potential_prompt = "\n".join(chain_of_thought_steps)
            return validate_prompt(potential_prompt)

        return validate_prompt(previous_prompt)

    def tree_of_thought(self, doc=False):
        """
        Generates a prompt using the tree-of-thought strategy. https://github.com/dave1010/tree-of-thought-prompting

        This method builds a prompt where multiple experts sequentially reason
        through steps.

        Returns:
            str: The generated prompt.
        """
        tree_of_thoughts_steps = [(
            "Imagine three different experts are answering this question.\n"
            "All experts will write down one step of their thinking,\n"
            "then share it with the group.\n"
            "After that, all experts will proceed to the next step, and so on.\n"
            "If any expert realizes they're wrong at any point, they will leave.\n"
            "The question is: "
        )]
        return "\n".join([self._prompt_history[self.round]["content"]] + tree_of_thoughts_steps)

    def evaluate_response(self, prompt, response_text): #TODO find a good way of evaluating result of prompt
        return True



from enum import Enum


class PromptStrategy(Enum):
    IN_CONTEXT = 1
    CHAIN_OF_THOUGHT = 2
    TREE_OF_THOUGHT = 3


