import unittest
from unittest.mock import MagicMock

from openai.types.chat import ChatCompletionMessage

from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.information.prompt_information import (
    PromptContext,
)
from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.prompt_engineer import (
    PromptEngineer,
    PromptStrategy,
)


class TestPromptEngineer(unittest.TestCase):
    def setUp(self):
        self.strategy = PromptStrategy.IN_CONTEXT
        self.llm_handler = MagicMock()
        self.history = [{"content": "initial_prompt", "role": "system"}]
        self.schemas = MagicMock()
        self.response_handler = MagicMock()
        self.prompt_engineer = PromptEngineer(
            strategy=self.strategy,
            handlers=(self.llm_handler, self.response_handler),
            history=self.history,
            context=PromptContext.PENTESTING,
        )

    def test_in_context_learning_no_hint(self):
        self.prompt_engineer.strategy = PromptStrategy.IN_CONTEXT
        expected_prompt = "initial_prompt\ninitial_prompt"
        actual_prompt = self.prompt_engineer.generate_prompt(hint="", turn=1)
        self.assertEqual(expected_prompt, actual_prompt[1]["content"])

    def test_in_context_learning_with_hint(self):
        self.prompt_engineer.strategy = PromptStrategy.IN_CONTEXT
        hint = "This is a hint."
        expected_prompt = "initial_prompt\ninitial_prompt\nThis is a hint."
        actual_prompt = self.prompt_engineer.generate_prompt(hint=hint, turn=1)
        self.assertEqual(expected_prompt, actual_prompt[1]["content"])

    def test_in_context_learning_with_doc_and_hint(self):
        self.prompt_engineer.strategy = PromptStrategy.IN_CONTEXT
        hint = "This is another hint."
        expected_prompt = "initial_prompt\ninitial_prompt\nThis is another hint."
        actual_prompt = self.prompt_engineer.generate_prompt(hint=hint, turn=1)
        self.assertEqual(expected_prompt, actual_prompt[1]["content"])

    def test_generate_prompt_chain_of_thought(self):
        self.prompt_engineer.strategy = PromptStrategy.CHAIN_OF_THOUGHT
        self.response_handler.get_response_for_prompt = MagicMock(return_value="response_text")
        self.prompt_engineer.evaluate_response = MagicMock(return_value=True)

        prompt_history = self.prompt_engineer.generate_prompt(turn=1)

        self.assertEqual(2, len(prompt_history))

    def test_generate_prompt_tree_of_thought(self):
        # Set the strategy to TREE_OF_THOUGHT
        self.prompt_engineer.strategy = PromptStrategy.TREE_OF_THOUGHT
        self.response_handler.get_response_for_prompt = MagicMock(return_value="response_text")
        self.prompt_engineer.evaluate_response = MagicMock(return_value=True)

        # Create mock previous prompts with valid roles
        previous_prompts = [
            ChatCompletionMessage(role="assistant", content="initial_prompt"),
            ChatCompletionMessage(role="assistant", content="previous_prompt"),
        ]

        # Assign the previous prompts to prompt_engineer._prompt_history
        self.prompt_engineer._prompt_history = previous_prompts

        # Generate the prompt
        prompt_history = self.prompt_engineer.generate_prompt(turn=1)

        # Check if the prompt history length is as expected
        self.assertEqual(len(prompt_history), 3)  # Adjust to 3 if previous prompt exists + new prompt


if __name__ == "__main__":
    unittest.main()
