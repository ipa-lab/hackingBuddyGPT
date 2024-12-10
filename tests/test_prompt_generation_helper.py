import unittest
from unittest.mock import MagicMock

from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.prompt_generation_helper import (
    PromptGenerationHelper,
)


class TestPromptHelper(unittest.TestCase):
    def setUp(self):
        self.response_handler = MagicMock()
        self.prompt_helper = PromptGenerationHelper(self.response_handler)

    def test_check_prompt(self):
        self.response_handler.get_response_for_prompt = MagicMock(return_value="shortened_prompt")
        prompt = self.prompt_helper.check_prompt(
            previous_prompt="previous_prompt",
            steps=["step1", "step2", "step3", "step4", "step5", "step6"],
            max_tokens=2,
        )
        self.assertEqual("shortened_prompt", prompt)


if __name__ == "__main__":
    unittest.main()
