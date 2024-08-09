import unittest
from unittest.mock import MagicMock
from hackingBuddyGPT.usecases.web_api_testing.prompt_engineer import PromptStrategy, PromptEngineer
from hackingBuddyGPT.usecases.web_api_testing.utils.prompt_helper import PromptHelper


class TestPromptHelper(unittest.TestCase):
    def setUp(self):
        self.response_handler = MagicMock()
        self.prompt_helper = PromptHelper(self.response_handler)
    def test_token_count(self):
        text = "This is a sample text with several words."
        count = self.prompt_helper.token_count(text)
        self.assertEqual(8, count)
    def test_check_prompt(self):
        self.response_handler.get_response_for_prompt = MagicMock(return_value="shortened_prompt")
        prompt = self.prompt_helper.check_prompt(
            previous_prompt="previous_prompt", steps=["step1", "step2", "step3", "step4", "step5", "step6"],
                                                 max_tokens=5)
        self.assertEqual(prompt, "shortened_prompt")


if __name__ == "__main__":
    unittest.main()