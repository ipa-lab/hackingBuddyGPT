import unittest
from unittest.mock import MagicMock

from hackingBuddyGPT.utils.web_api.llm_handler import LLMHandler


class TestLLMHandler(unittest.TestCase):
    def setUp(self):
        self.llm_mock = MagicMock()
        self.capabilities = {"cap1": MagicMock(), "cap2": MagicMock()}
        self.llm_handler = LLMHandler(self.llm_mock, self.capabilities)

    def test_add_created_object(self):
        created_object = MagicMock()
        object_type = "test_type"

        self.llm_handler._add_created_object(created_object, object_type)

        self.assertIn(object_type, self.llm_handler.created_objects)
        self.assertIn(created_object, self.llm_handler.created_objects[object_type])

    def test_add_created_object_limit(self):
        created_object = MagicMock()
        object_type = "test_type"

        for _ in range(8):  # Exceed the limit of 7 objects
            self.llm_handler._add_created_object(created_object, object_type)

        self.assertEqual(len(self.llm_handler.created_objects[object_type]), 7)


if __name__ == "__main__":
    unittest.main()
