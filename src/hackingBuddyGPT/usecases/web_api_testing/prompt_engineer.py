
from hackingBuddyGPT.capabilities.capability import capabilities_to_action_model
from hackingBuddyGPT.utils import openai
import spacy


class PromptEngineer(object):
    '''Prompt engineer that creates prompts of different types'''

    def __init__(self, strategy, llm,  history, capabilities):
        """
        Initializes the PromptEngineer with a specific strategy and API key.

        Args:
            strategy (PromptStrategy): The prompt engineering strategy to use.
            llm : The LLM model.

            history (dict, optional): The history of chats. Defaults to None.

        Attributes:
            strategy (PromptStrategy): Stores the provided strategy.
            llm : LLM model
            host (str): Stores the provided host for OpenAI API.
            flag_format_description (str): Stores the provided flag description format.
            prompt_history (list): A list that keeps track of the conversation history.
            initial_prompt (str): The initial prompt used for conversation.
            prompt (str): The current prompt to be used.
            strategies (dict): Maps strategies to their corresponding methods.
        """
        self.strategy = strategy
        '''self.api_key = api_key
        # Set the OpenAI API key
        openai.api_key = self.api_key'''
        self.llm = llm
        self.capabilities = capabilities
        self.round = 0
        # Load the small English model
        self.nlp = spacy.load("en_core_web_sm")

        # Initialize prompt history
        self._prompt_history = history
        self.prompt = self._prompt_history
        self.previous_prompt = self._prompt_history[self.round]["content"]

        # Set up strategy map
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
                response_text = self.get_response_for_prompt(prompt)
                is_good = self.evaluate_response(prompt, response_text)
                if is_good:
                    self._prompt_history.append( {"role":"system", "content":prompt})
                    self.previous_prompt = prompt
                    self.round = self.round +1
                    return self._prompt_history

    def get_response_for_prompt(self, prompt):
        """
        Sends a prompt to OpenAI's API and retrieves the response.

        Args:
            prompt (str): The prompt to be sent to the API.

        Returns:
            str: The response from the API.
        """
        messages = [{"role": "user", "content": prompt}]

        response, completion = self.llm.instructor.chat.completions.create_with_completion(model=self.llm.model,
                                                                                           messages=messages,
                                                                                           response_model=capabilities_to_action_model(
                                                                                               self.capabilities))
        # Update history
        response_text = response.choices[0].text.strip()
        self._prompt_history.extend([f"[User]: {prompt}", f"[System]: {response_text}"])

        return response_text



    def in_context_learning(self, doc=False):
        """
        Generates a prompt for in-context learning.

        This method builds a prompt using the conversation history
        and the current prompt.

        Returns:
            str: The generated prompt.
        """
        return str("\n".join(self._prompt_history[self.round]["content"] + [self.prompt]))

    def chain_of_thought(self, doc=False):
        """
        Generates a prompt using the chain-of-thought strategy.
        If 'doc' is True, it follows a detailed documentation-oriented prompt strategy based on the round number.
        If 'doc' is False, it provides general guidance for early round numbers and focuses on HTTP methods for later rounds.

        Args:
            doc (bool): Determines whether the documentation-oriented chain of thought should be used.

        Returns:
            str: The generated prompt.
        """

        def get_http_action_template(method):
            """Helper to construct a consistent HTTP action description."""
            if method == "POST" and method == "PUT":
                return (
                    f"Create HTTPRequests of type {method} and understand the responses. Ensure that they are correct requests."
                    f"Note down the response structures, status codes, and headers for each endpoint.",
                    f"For each endpoint, document the following details: URL, HTTP method {method}, "
                    f"query parameters and path variables, expected request body structure for {method} requests, response structure for successful and error responses.")

            else:
                return (
                f"Create HTTPRequests of type {method} and understand the responses. Ensure that they are correct requests. "
                f"the action should look similar to this: "
                f"'action':{{'method':'{method}','path':'/posts','query':null,'body':null,'body_is_base64':null,'headers':null}}."
                f"For each endpoint, document the following details: URL, HTTP method {method}, "
                )

        if doc:
            common_steps = [

                "Identify common data structures returned by various endpoints and define them as reusable schemas. Determine the type of each field (e.g., integer, string, array) and define common response structures as components that can be referenced in multiple endpoint definitions.",
                "Create an OpenAPI document including metadata such as API title, version, and description, define the base URL of the API, list all endpoints, methods, parameters, and responses, and define reusable schemas, response types, and parameters.",
                "Ensure the correctness and completeness of the OpenAPI specification by validating the syntax and completeness of the document using tools like Swagger Editor, and ensure the specification matches the actual behavior of the API.",
                "Refine the document based on feedback and additional testing, share the draft with others, gather feedback, and make necessary adjustments. Regularly update the specification as the API evolves.",
                "Make the OpenAPI specification available to developers by incorporating it into your API documentation site and keep the documentation up to date with API changes."
            ]

            http_methods = ["GET", "POST", "PUT", "DELETE"]
            if self.round < len(http_methods) * 5:
                index = self.round // 5
                method = http_methods[index]
                chain_of_thought_steps = [
                                             f"Identify all available endpoints. Valid methods are {', '.join(http_methods)}.",
                                             get_http_action_template(method)] + common_steps
            else:
                chain_of_thought_steps = [
                                             "Explore the API by reviewing any available documentation to learn about the API endpoints, data models, and behaviors.",
                                             "Identify all available endpoints."] + common_steps
        else:
            if self.round == 0:
                chain_of_thought_steps = ["Let's think step by step."]  # Zero shot prompt
            elif self.round <= 20:
                focus_phase = ["endpoints", "HTTP method GET", "HTTP method POST and PUT", "HTTP method DELETE"][
                    self.round // 5]
                chain_of_thought_steps = [f"Just Focus on the {focus_phase} for now."]
            else:
                chain_of_thought_steps = ["Look for exploits."]

        #prompt = "\n".join([self.previous_prompt] + chain_of_thought_steps)
        prompt = self.check_prompt(self.previous_prompt, chain_of_thought_steps)
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
        return len(tokens)

    def shorten_prompt(self, prompt): # TODO rework
        """Uses the LLM's create_with_completion to generate a shortened or summarized prompt."""
        print(f'NewPrompT:\n{prompt}')
        messages = [{"role": "user", "content": prompt}]
        # Simulate the capabilities as you might need them. Adjust according to your implementation.
        response_model = capabilities_to_action_model({
        })
        response, completion = self.llm.instructor.chat.completions.create_with_completion(
            model=self.llm.model,
            messages=messages,
            response_model=response_model
        )
        # Assuming the completion includes a single message with the summarized content
        return completion.choices[0].message.content.strip()

    def check_prompt(self,  previous_prompt, chain_of_thought_steps, max_tokens=1000):
        if not all(step in previous_prompt for step in chain_of_thought_steps):
            potential_prompt = "\n".join([] + chain_of_thought_steps)
            if self.token_count(potential_prompt) <= max_tokens:
                return potential_prompt
            else:
                # Handle the case where the combined prompt is too long
                shortened_prompt = self.shorten_prompt( potential_prompt)
                if self.token_count(shortened_prompt) <= max_tokens:
                    return shortened_prompt
                else:
                    # Further handling if the shortened prompt is still too long
                    return "Prompt is still too long after summarization."
        else:
            if self.token_count(previous_prompt) <= max_tokens:
                return previous_prompt
            else:
                # Handle the case where the combined prompt is too long
                shortened_prompt = self.shorten_prompt(previous_prompt)
                if self.token_count(shortened_prompt) <= max_tokens:
                    return shortened_prompt
                else:
                    # Further handling if the shortened prompt is still too long
                    return "Prompt is still too long after summarization."

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

    def evaluate_response(self, prompt, response_text):
        return True


from enum import Enum


class PromptStrategy(Enum):
    IN_CONTEXT = 1
    CHAIN_OF_THOUGHT = 2
    TREE_OF_THOUGHT = 3


