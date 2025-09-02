import unittest
from hackingBuddyGPT.utils.prompt_generation import PromptGenerationHelper


class TestPromptGenerationHelper(unittest.TestCase):
    def setUp(self):
        self.host = "https://reqres.in"
        self.description = "Fake API"
        self.prompt_helper = PromptGenerationHelper(self.host, self.description)

    def test_get_user_from_prompt(self):
        step = {
            "step": "Create a new user with user: {'email': 'eve.holt@reqres.in', 'password': 'pistol'}.\n"
        }
        accounts = [
            {"email": "eve.holt@reqres.in", "password": "pistol"}
        ]

        user_info = self.prompt_helper.get_user_from_prompt(step, accounts)

        self.assertEqual(user_info["email"], "eve.holt@reqres.in")
        self.assertEqual(user_info["password"], "pistol")
        self.assertIn("x", user_info)
        self.assertEqual(user_info["x"], "")

    def test_get_user_from_prompt_with_sql_injection(self):
        step = {
            "step": "Create user with user: {'email': \"' or 1=1--\", 'password': 'pistol'}.\n"
        }
        accounts = [
            {"email": "' or 1=1--", "password": "pistol"}
        ]

        user_info = self.prompt_helper.get_user_from_prompt(step, accounts)

        self.assertEqual(user_info["email"], " or 1=1--")
        self.assertEqual(user_info["password"], "pistol")
        self.assertIn("x", user_info)
        self.assertEqual(user_info["x"], "")


if __name__ == "__main__":
    unittest.main()
