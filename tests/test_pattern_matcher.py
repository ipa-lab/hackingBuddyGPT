import unittest

from hackingBuddyGPT.utils.web_api.pattern_matcher import PatternMatcher


class TestPatternMatcher(unittest.TestCase):
    def setUp(self):
        self.pm = PatternMatcher()

    def test_replace_numeric_segment_with_id(self):
        self.assertEqual(self.pm.replace_according_to_pattern("/users/1"), "/users/{id}")
        self.assertEqual(
            self.pm.replace_according_to_pattern("/users/1/posts/2"), "/users/{id}/posts/{id}"
        )

    def test_non_numeric_paths_unchanged(self):
        # "/v1/users": the digit is not a whole path segment, so nothing is replaced.
        self.assertEqual(self.pm.replace_according_to_pattern("/v1/users"), "/v1/users")
        self.assertEqual(self.pm.replace_according_to_pattern("/users"), "/users")
        # query values are left alone by the path generaliser
        self.assertEqual(self.pm.replace_according_to_pattern("/users?page=2"), "/users?page=2")

    def test_extract_query_params(self):
        self.assertEqual(
            self.pm.extract_query_params("/search?q=cat&page=2"), {"q": "cat", "page": "2"}
        )
        self.assertEqual(self.pm.extract_query_params("/users"), {})


if __name__ == "__main__":
    unittest.main()
