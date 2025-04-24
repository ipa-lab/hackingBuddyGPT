import unittest
from unittest.mock import MagicMock

from hackingBuddyGPT.usecases.web_api_testing.utils import LLMHandler


class TestLLMHandler(unittest.TestCase):
    def setUp(self):
        self.llm_mock = MagicMock()
        self.capabilities = {"cap1": MagicMock(), "cap2": MagicMock()}
        self.llm_handler = LLMHandler(self.llm_mock, self.capabilities)

    """@patch('hackingBuddyGPT.usecases.web_api_testing.utils.capabilities_to_action_model')
    def test_call_llm(self, mock_capabilities_to_action_model):
        prompt = [{'role': 'user', 'content': 'Hello, LLM!'}]
        response_mock = MagicMock()
        self.llm_mock.instructor.chat.completions.create_with_completion.return_value = response_mock

        # Mock the capabilities_to_action_model to return a dummy Pydantic model
        mock_model = MagicMock()
        mock_capabilities_to_action_model.return_value = mock_model

        response = self.llm_handler.call_llm(prompt)

        self.llm_mock.instructor.chat.completions.create_with_completion.assert_called_once_with(
            model=self.llm_mock.model,
            messages=prompt,
            response_model=mock_model
        )
        self.assertEqual(response, response_mock)"""

    def test_add_created_object(self):
        created_object = MagicMock()
        object_type = "test_type"

        self.llm_handler.add_created_object(created_object, object_type)

        self.assertIn(object_type, self.llm_handler.created_objects)
        self.assertIn(created_object, self.llm_handler.created_objects[object_type])

    def test_add_created_object_limit(self):
        created_object = MagicMock()
        object_type = "test_type"

        for _ in range(8):  # Exceed the limit of 7 objects
            self.llm_handler.add_created_object(created_object, object_type)

        self.assertEqual(len(self.llm_handler.created_objects[object_type]), 7)

    def test_get_created_objects(self):
        created_object = MagicMock()
        object_type = "test_type"
        self.llm_handler.add_created_object(created_object, object_type)

        created_objects = self.llm_handler.get_created_objects()

        self.assertIn(object_type, created_objects)
        self.assertIn(created_object, created_objects[object_type])
        self.assertEqual(created_objects, self.llm_handler.created_objects)


if __name__ == "__main__":
    unittest.main()
