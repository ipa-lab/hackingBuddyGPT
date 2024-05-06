

from utils import openai

class PromptEngineer(object):
    '''Prompt engineer that creates prompts of different types'''

    def __init__(self, strategy, api_key, host, flag_format_description, history):
        """
        Initializes the PromptEngineer with a specific strategy and API key.

        Args:
            strategy (PromptStrategy): The prompt engineering strategy to use.
            api_key (str): The API key for OpenAI.
            host (str): The host for OpenAI API.
            flag_format_description (str): Description format for flag.
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

        self.host = host
        self.flag_format_description = flag_format_description

        # Initialize prompt history
        self._prompt_history = history
        self.prompt = self._prompt_history

        # Set up strategy map
        self.strategies = {
            PromptStrategy.IN_CONTEXT: self.in_context_learning,
            PromptStrategy.CHAIN_OF_THOUGHT: self.chain_of_thought,
            PromptStrategy.TREE_OF_THOUGHT: self.tree_of_thought
        }

    def generate_prompt(self):
        """
        Generates a prompt based on the specified strategy and gets a response.

        This method directly calls the appropriate strategy method to generate
        a prompt and then gets a response using that prompt.
        """
        # Directly call the method using the strategy mapping
        prompt_func = self.strategies.get(self.strategy)
        if prompt_func:
            prompt = prompt_func()
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

    def generate_initial_prompt(self):
        """
        Generates the initial prompt history based on OpenAPI specification.

        Returns:
            None
        """
        self._prompt_history.append(
            {
                "role": "system",
                "content": f"You are a senior penetration tester, having received a new project of testing a website at {self.host}."
                           f"Your goal is first to explore the website, building up your knowledge about its parts and inner workings, and then try to plan and execute possible exploitations.\n"
                           f"Make sure to take lots of notes about the pages you visit, so that you can later more easily work through the page.\n"
                           f"Do not brute-force anything, all information that you might need can be found on the webserver.\n"
                           f"THE MOST IMPORTANT THING TO DO IS, that if you see a flag ({self.flag_format_description}), you should submit it immediately."})


    def in_context_learning(self):
        """
        Generates a prompt for in-context learning.

        This method builds a prompt using the conversation history
        and the current prompt.

        Returns:
            str: The generated prompt.
        """
        return str("\n".join(self._prompt_history[self.round]["content"] + [self.prompt]))

    def chain_of_thought(self):
        """
        Generates a prompt using the chain-of-thought strategy. https://www.promptingguide.ai/techniques/cot

        This method adds a step-by-step reasoning prompt to the current prompt.

        Returns:
            str: The generated prompt.
        """
        chain_of_thought_steps = [
            "Let's think step by step." # zero shot prompt
        ]
        return "\n".join([self._prompt_history[self.round]["content"]] + chain_of_thought_steps)



    def tree_of_thought(self):
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


