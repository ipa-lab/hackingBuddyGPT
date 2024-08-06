import unittest
from unittest.mock import MagicMock
from hackingBuddyGPT.usecases.web_api_testing.prompt_engineer import PromptStrategy, PromptEngineer


class TestPromptEngineer(unittest.TestCase):
    def setUp(self):
        self.strategy = PromptStrategy.IN_CONTEXT
        self.llm_handler = MagicMock()
        self.history = [{"content": "initial_prompt", "role": "system"}]
        self.schemas = MagicMock()
        self.response_handler = MagicMock()
        self.prompt_engineer = PromptEngineer(
            self.strategy, self.llm_handler, self.history, self.schemas, self.response_handler
        )
    def test_token_count(self):
        text = "This is a sample text with several words."
        count = self.prompt_engineer.token_count(text)
        self.assertEqual(8, count)
    def test_check_prompt(self):
        self.response_handler.get_response_for_prompt = MagicMock(return_value="shortened_prompt")
        prompt = self.prompt_engineer.check_prompt("previous_prompt",
                                                   ["step1", "step2", "step3", "step4", "step5", "step6"], max_tokens=5)
        self.assertEqual(prompt, "shortened_prompt")

    def test_in_context_learning_no_hint(self):
        expected_prompt = "initial_prompt\ninitial_prompt"
        actual_prompt = self.prompt_engineer.in_context_learning()
        self.assertEqual(expected_prompt, actual_prompt)

    def test_in_context_learning_with_hint(self):
        hint = "This is a hint."
        expected_prompt = "initial_prompt\ninitial_prompt\nThis is a hint."
        actual_prompt = self.prompt_engineer.in_context_learning(hint=hint)
        self.assertEqual(expected_prompt, actual_prompt)

    def test_in_context_learning_with_doc_and_hint(self):
        hint = "This is another hint."
        expected_prompt = "initial_prompt\ninitial_prompt\nThis is another hint."
        actual_prompt = self.prompt_engineer.in_context_learning(doc=True, hint=hint)
        self.assertEqual(expected_prompt, actual_prompt)
    def test_generate_prompt_chain_of_thought(self):
        self.prompt_engineer.strategy = PromptStrategy.CHAIN_OF_THOUGHT
        self.response_handler.get_response_for_prompt = MagicMock(return_value="response_text")
        self.prompt_engineer.evaluate_response = MagicMock(return_value=True)

        prompt_history = self.prompt_engineer.generate_prompt()

        self.assertEqual( 2, len(prompt_history))

    def test_generate_prompt_tree_of_thought(self):
        self.prompt_engineer.strategy = PromptStrategy.TREE_OF_THOUGHT
        self.response_handler.get_response_for_prompt = MagicMock(return_value="response_text")
        self.prompt_engineer.evaluate_response = MagicMock(return_value=True)

        prompt_history = self.prompt_engineer.generate_prompt()

        self.assertEqual(len(prompt_history), 2)




if __name__ == "__main__":
    unittest.main()