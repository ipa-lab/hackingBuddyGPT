from openai.types.chat import ChatCompletionMessage

from hackingBuddyGPT.utils import openai

class PromptEngineer(object):
    '''Prompt engineer that creates prompts of different types'''

    def __init__(self, strategy, api_key,  history):
        """
        Initializes the PromptEngineer with a specific strategy and API key.

        Args:
            strategy (PromptStrategy): The prompt engineering strategy to use.
            api_key (str): The API key for OpenAI.

            history (dict, optional): The history of chats. Defaults to None.

        Attributes:
            strategy (PromptStrategy): Stores the provided strategy.
            api_key (str): Stores the provided API key.
            host (str): Stores the provided host for OpenAI API.
            flag_format_description (str): Stores the provided flag description format.
            prompt_history (list): A list that keeps track of the conversation history.
            initial_prompt (str): The initial prompt used for conversation.
            prompt (str): The current prompt to be used.
            strategies (dict): Maps strategies to their corresponding methods.
        """
        self.strategy = strategy
        self.api_key = api_key
        # Set the OpenAI API key
        openai.api_key = self.api_key
        self.round = 0



        # Initialize prompt history
        self._prompt_history = history
        self.prompt = self._prompt_history

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
        if prompt_func:
            print(f'prompt history:{self._prompt_history[self.round]}')
            if not isinstance(self._prompt_history[self.round],ChatCompletionMessage ):
                prompt = prompt_func(doc)
                self._prompt_history[self.round]["content"] = prompt
            self.round = self.round +1
            return self._prompt_history
            #self.get_response(prompt)

    def get_response(self, prompt):
        """
        Sends a prompt to OpenAI's API and retrieves the response.

        Args:
            prompt (str): The prompt to be sent to the API.

        Returns:
            str: The response from the API.
        """
        response = openai.Completion.create(
            engine="text-davinci-002",
            prompt=prompt,
            max_tokens=150,
            n=1,
            stop=None,
            temperature=0.7,
        )
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
        Generates a prompt using the chain-of-thought strategy. https://www.promptingguide.ai/techniques/cot

        This method adds a step-by-step reasoning prompt to the current prompt.

        Returns:
            str: The generated prompt.
        """

        previous_prompt = self._prompt_history[self.round]["content"]

        if doc :
            chain_of_thought_steps = [
            "Explore the API by reviewing any available documentation to learn about the API endpoints, data models, and behaviors.",
            "Identify all available endpoints.",
            "Create GET, POST, PUT, DELETE requests to understand the responses.",
            "Note down the response structures, status codes, and headers for each endpoint.",
            "For each endpoint, document the following details: URL, HTTP method (GET, POST, PUT, DELETE), query parameters and path variables, expected request body structure for POST and PUT requests, response structure for successful and error responses.",
            "First execute the GET requests, then POST, then PUT and DELETE."
            "Identify common data structures returned by various endpoints and define them as reusable schemas. Determine the type of each field (e.g., integer, string, array) and define common response structures as components that can be referenced in multiple endpoint definitions.",
            "Create an OpenAPI document including metadata such as API title, version, and description, define the base URL of the API, list all endpoints, methods, parameters, and responses, and define reusable schemas, response types, and parameters.",
            "Ensure the correctness and completeness of the OpenAPI specification by validating the syntax and completeness of the document using tools like Swagger Editor, and ensure the specification matches the actual behavior of the API.",
            "Refine the document based on feedback and additional testing, share the draft with others, gather feedback, and make necessary adjustments. Regularly update the specification as the API evolves.",
            "Make the OpenAPI specification available to developers by incorporating it into your API documentation site and keep the documentation up to date with API changes."
            ]
        else:
            if round == 0:
                chain_of_thought_steps = [
                "Let's think step by step." # zero shot prompt
                ]
            elif self.round <= 5:
                chain_of_thought_steps = ["Just Focus on the endpoints for now."]
            elif self.round >5 and self.round <= 10:
                chain_of_thought_steps = ["Just Focus on the HTTP method GET for now."]
            elif self.round > 10 and self.round <= 15:
                chain_of_thought_steps = ["Just Focus on the HTTP method POST and PUT for now."]
            elif self.round > 15 and self.round <= 20:
                chain_of_thought_steps = ["Just Focus on the HTTP method DELETE for now."]
            else:
                chain_of_thought_steps = ["Look for exploits."]


        return "\n".join([previous_prompt] + chain_of_thought_steps)



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




from enum import Enum


class PromptStrategy(Enum):
    IN_CONTEXT = 1
    CHAIN_OF_THOUGHT = 2
    TREE_OF_THOUGHT = 3


