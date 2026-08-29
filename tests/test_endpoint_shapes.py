import unittest

from hackingBuddyGPT.utils.web_api import endpoint_shapes


class TestEndpointShapes(unittest.TestCase):
    # A single-element pool makes random.choice deterministic.
    POOL = ["/posts"]

    def test_related_resource(self):
        self.assertEqual(endpoint_shapes.related_resource("/users/1", self.POOL), "/users/1/posts")
        self.assertEqual(endpoint_shapes.related_resource("/users", self.POOL), "/users/1/posts")

    def test_sub_resource(self):
        self.assertEqual(endpoint_shapes.sub_resource("/users", self.POOL), "/users/posts")

    def test_multi_level_resource(self):
        self.assertEqual(endpoint_shapes.multi_level_resource("/users", self.POOL), "/users/posts/posts")


if __name__ == "__main__":
    unittest.main()
