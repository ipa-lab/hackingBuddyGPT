import spacy
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
        model_name = "en_core_web_sm"

        # Check if the model is already installed
        from spacy.util import is_package
        if not is_package(model_name):
            print(f"Model '{model_name}' is not installed. Installing now...")
            spacy.cli.download(model_name)

        # Load the model
        self.nlp = spacy.load(model_name)

        self.nlp = spacy.load("en_core_web_sm")
        self._prompt_history = history
        self.prompt = self._prompt_history
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
        return str("\n".join(self._prompt_history[self.round]["content"] + [self.prompt]))

    def get_http_action_template(self, method):
        """Helper to construct a consistent HTTP action description."""
        if method == "POST" and method == "PUT":
            return (
                f"Create HTTPRequests of type {method} considering the found schemas: {self.schemas} and understand the responses. Ensure that they are correct requests."
                )

        else:
            return (
                f"Create HTTPRequests of type {method} considering only the object with id=1 for the endpoint and understand the responses. Ensure that they are correct requests.")


    def chain_of_thought(self, doc=False, hint=""):
        """
        Generates a prompt using the chain-of-thought strategy.
        If 'doc' is True, it follows a detailed documentation-oriented prompt strategy based on the round number.
        If 'doc' is False, it provides general guidance for early round numbers and focuses on HTTP methods for later rounds.

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

        http_methods = [ "POST", "PUT", "DELETE"]
        http_phase = {
            5: http_methods[0],
            10: http_methods[1], # Delete one of instance of this:{self.llm_handler.get_created_objects()}",
            15: http_methods[2]
        }

        if doc:
            if self.round < 5:

                chain_of_thought_steps = [
                                             f"Identify all available endpoints via GET Requests. Exclude those in this list: {self.found_endpoints}", f"Note down the response structures, status codes, and headers for each endpoint.",
                                             f"For each endpoint, document the following details: URL, HTTP method, "
                                             f"query parameters and path variables, expected request body structure for  requests, response structure for successful and error responses."
                                         ] + common_steps
            else:
                if self.round <= 15:
                    phase = http_phase.get(min(filter(lambda x: self.round <= x, http_phase.keys())))
                    print(f'phase:{phase}')
                    if phase != "DELETE":
                        chain_of_thought_steps = [
                                             f"Identify for all endpoints {self.found_endpoints} excluding {self.endpoint_found_methods[phase]} a valid HTTP method {phase} call.",
                                             self.get_http_action_template(phase)
                                         ] + common_steps
                    else:
                        chain_of_thought_steps = [
                                                 f"Check for all endpoints the DELETE method. Delete the first instance for all endpoints. ",
                                                 self.get_http_action_template(phase)
                                             ] + common_steps
                else:
                    endpoints_needing_help = []
                    endpoints_and_needed_methods = {}

                    # Standard HTTP methods
                    http_methods = {"GET", "POST", "PUT", "DELETE"}

                    for endpoint in self.endpoint_methods:
                        # Calculate the missing methods for the current endpoint
                        missing_methods = http_methods - set(self.endpoint_methods[endpoint])

                        if len(self.endpoint_methods[endpoint]) < 4:
                            endpoints_needing_help.append(endpoint)
                            # Add the missing methods to the dictionary
                            endpoints_and_needed_methods[endpoint] = list(missing_methods)

                    print(f'endpoints_and_needed_methods: {endpoints_and_needed_methods}')
                    print(f'first endpoint in list: {endpoints_needing_help[0]}')
                    print(f'methods needed for first endpoint: {endpoints_and_needed_methods[endpoints_needing_help[0]][0]}')

                    chain_of_thought_steps = [f"For enpoint {endpoints_needing_help[0]} find this missing method :{endpoints_and_needed_methods[endpoints_needing_help[0]][0]} "
                                              f"If all the HTTP methods have already been found for an endpoint, then do not include this endpoint in your search. ",]

        else:
            if self.round == 0:
                chain_of_thought_steps = ["Let's think step by step."]  # Zero shot prompt
            elif self.round <= 20:
                focus_phases = ["endpoints", "HTTP method GET", "HTTP method POST and PUT", "HTTP method DELETE"]
                focus_phase = focus_phases[self.round // 5]
                chain_of_thought_steps = [f"Just focus on the {focus_phase} for now."]
            else:
                chain_of_thought_steps = ["Look for exploits."]

        print(f'chain of thought steps: {chain_of_thought_steps}')
        prompt = self.check_prompt(self.previous_prompt,
                                   chain_of_thought_steps + [hint] if hint else chain_of_thought_steps)
        return prompt

    def token_count(self, text):
        """
        Counts the number of word tokens in the provided text using spaCy's tokenizer.

        Args:
            text (str): The input text to tokenize and count.

        Returns:
            int: The number of tokens in the input text.
        """
        # Process the text through spaCy's pipeline
        doc = self.nlp(text)
        # Count tokens that aren't punctuation marks
        tokens = [token for token in doc if not token.is_punct]
        print(f'TOKENS: {len(tokens)}')
        return len(tokens)


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


