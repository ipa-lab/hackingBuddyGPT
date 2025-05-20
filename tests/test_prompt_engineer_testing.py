import os
import unittest
from unittest.mock import MagicMock

from openai.types.chat import ChatCompletionMessage

from hackingBuddyGPT.usecases.web_api_testing.documentation.parsing import OpenAPISpecificationParser
from hackingBuddyGPT.utils.prompt_generation import PromptGenerationHelper
from hackingBuddyGPT.utils.prompt_generation.information import PenTestingInformation
from hackingBuddyGPT.utils.prompt_generation.information import (
    PromptContext, PromptPurpose,
)
from hackingBuddyGPT.utils.prompt_generation.prompt_engineer import (
    PromptEngineer
)
from hackingBuddyGPT.usecases.web_api_testing.utils.configuration_handler import ConfigurationHandler


class TestPromptEngineer(unittest.TestCase):
    def setUp(self):
        self.llm_handler = MagicMock()
        self.history = [{"content": "initial_prompt", "role": "system"}]
        self.schemas = MagicMock()
        self.response_handler = MagicMock()
        self.config_path = os.path.join(os.path.dirname(__file__), "test_files","fakeapi_config.json")
        self.configuration_handler = ConfigurationHandler(self.config_path)
        self.config = self.configuration_handler._load_config(self.config_path)
        self._openapi_specification_parser = OpenAPISpecificationParser(self.config_path)
        self._openapi_specification = self._openapi_specification_parser.api_data

        self.token, self.host, self.description, self.correct_endpoints, self.query_params = self.configuration_handler._extract_config_values(
            self.config)
        self.categorized_endpoints = self._openapi_specification_parser.classify_endpoints()

        self.prompt_helper = PromptGenerationHelper(self.host, self.description)

    def test_in_context_learning_no_hint(self):
        prompt_engineer = self.generate_prompt_engineer("icl")

        expected_prompt = """Based on this information :

Objective: Identify all accessible endpoints via GET requests for No host URL provided.. See https://jsonplaceholder.typicode.com/
 Query root-level resource endpoints.
                               Find root-level endpoints for No host URL provided..
                               Only send GET requests to root-level endpoints with a single path component after the root. This means each path should have exactly one '/' followed by a single word (e.g., '/users', '/products').  
                               1. Send GET requests to new paths only, avoiding any in the lists above.
                               2. Do not reuse previously tested paths.
"""
        actual_prompt = prompt_engineer.generate_prompt(hint="", turn=1)
        self.assertIn(" Create an account by sending a POST HTTP request to the correct endpoint from this /users with these credentials of user:", actual_prompt[0].get("content"))
    def test_in_context_learning_with_hint(self):
        prompt_engineer = self.generate_prompt_engineer("icl")
        expected_prompt = """Based on this information :

        Objective: Identify all accessible endpoints via GET requests for No host URL provided.. See https://jsonplaceholder.typicode.com/
         Query root-level resource endpoints.
                                       Find root-level endpoints for No host URL provided..
                                       Only send GET requests to root-level endpoints with a single path component after the root. This means each path should have exactly one '/' followed by a single word (e.g., '/users', '/products').  
                                       1. Send GET requests to new paths only, avoiding any in the lists above.
                                       2. Do not reuse previously tested paths.
        """
        hint = "This is a hint."
        actual_prompt = prompt_engineer.generate_prompt(hint=hint, turn=1)
        self.assertIn(hint, actual_prompt[0].get("content"), )

    def test_in_context_learning_with_doc_and_hint(self):
        prompt_engineer = self.generate_prompt_engineer("icl")
        hint = "This is another hint."
        expected_prompt = """Objective: Identify all accessible endpoints via GET requests for No host URL provided.. See https://jsonplaceholder.typicode.com/
 Query root-level resource endpoints.
                               Find root-level endpoints for No host URL provided..
                               Only send GET requests to root-level endpoints with a single path component after the root. This means each path should have exactly one '/' followed by a single word (e.g., '/users', '/products').  
                               1. Send GET requests to new paths only, avoiding any in the lists above.
                               2. Do not reuse previously tested paths.

This is another hint."""
        actual_prompt = prompt_engineer.generate_prompt(hint=hint, turn=1)
        self.assertIn(hint,actual_prompt[0].get("content"))

    def test_generate_prompt_chain_of_thought(self):
        prompt_engineer = self.generate_prompt_engineer("cot")
        self.response_handler.get_response_for_prompt = MagicMock(return_value="response_text")
        prompt_engineer.evaluate_response = MagicMock(return_value=True)

        prompt_history = prompt_engineer.generate_prompt(turn=1)

        self.assertEqual(1, len(prompt_history))

    def test_generate_prompt_tree_of_thought(self):
        prompt_engineer = self.generate_prompt_engineer("tot")
        self.response_handler.get_response_for_prompt = MagicMock(return_value="response_text")
        prompt_engineer.evaluate_response = MagicMock(return_value=True)

        # Create mock previous prompts with valid roles
        previous_prompts = [
            ChatCompletionMessage(role="assistant", content="initial_prompt"),
            ChatCompletionMessage(role="assistant", content="previous_prompt"),
        ]

        # Assign the previous prompts to prompt_engineer._prompt_history
        prompt_engineer._prompt_history = previous_prompts

        # Generate the prompt
        prompt_history = prompt_engineer.generate_prompt(turn=1)

        # Check if the prompt history length is as expected
        self.assertEqual(1, len(prompt_history))  # Adjust to 3 if previous prompt exists + new prompt

    def generate_prompt_engineer(self, param):
        config, strategy = self.configuration_handler.load(param)
        self.pentesting_information = PenTestingInformation(self._openapi_specification_parser, config)

        prompt_engineer = PromptEngineer(
            strategy=strategy,
            prompt_helper=self.prompt_helper,
            context=PromptContext.PENTESTING,
            open_api_spec=self._openapi_specification,
            rest_api_info=(self.token, self.description, self.correct_endpoints, self.categorized_endpoints),
        )
        self.pentesting_information.pentesting_step_list = [
                                     PromptPurpose.SETUP,
                                     PromptPurpose.VERIY_SETUP
                                     ]
        prompt_engineer.set_pentesting_information(pentesting_information=self.pentesting_information)

        return prompt_engineer


if __name__ == "__main__":
    unittest.main()
