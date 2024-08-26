import os
import unittest
from unittest.mock import MagicMock
from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.utils.prompt_generation_helper import PromptGenerationHelper


class TestPromptHelper(unittest.TestCase):
    def setUp(self):
        self.response_handler = MagicMock()
        self.prompt_helper = PromptGenerationHelper(self.response_handler)

    @unittest.skipUnless(os.getenv('RUN_LOCAL_TESTS') == 'true', "Skipping test for CI")
    def test_token_count(self):
        text = "This is a sample text with several words."
        count = self.prompt_helper.token_count(text)
        self.assertEqual(8, count)
    def test_check_prompt(self):
        self.response_handler.get_response_for_prompt = MagicMock(return_value="shortened_prompt")
        prompt = self.prompt_helper.check_prompt(
            previous_prompt="previous_prompt", steps=["step1", "step2", "step3", "step4", "step5", "step6"],
                                                 max_tokens=2)
        self.assertEqual("shortened_prompt", prompt)


if __name__ == "__main__":
    unittest.main()