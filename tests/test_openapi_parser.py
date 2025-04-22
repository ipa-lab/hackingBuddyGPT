import os
import unittest
from unittest.mock import mock_open, patch

import yaml

from hackingBuddyGPT.usecases.web_api_testing.documentation.parsing import (
    OpenAPISpecificationParser,
)


class TestOpenAPISpecificationParser(unittest.TestCase):
    def setUp(self):
        self.filepath = os.path.join(os.path.dirname(__file__), "test_files", "test_config.json")
        self.parser = OpenAPISpecificationParser(self.filepath)


    def test_get_servers(self):
        servers = self.parser._get_servers()
        self.assertEqual(["https://jsonplaceholder.typicode.com/"], servers)


    def test_get_paths(self):
        paths = self.parser.get_endpoints()
        expected_paths = {'/posts': {'get': {'description': 'Returns all posts',
                    'operationId': 'getPosts',
                    'responses': {'200': {'content': {'application/json': {'schema': {'$ref': '#/components/schemas/PostsList'}}},
                                          'description': 'Successful '
                                                         'response'}},
                    'tags': ['Posts']}},
 '/posts/{id}': {'get': {'description': 'Returns a post by id',
                         'operationId': 'getPost',
                         'parameters': [{'description': 'The user id.',
                                         'in': 'path',
                                         'name': 'id',
                                         'required': True,
                                         'schema': {'format': 'int64',
                                                    'type': 'integer'}}],
                         'responses': {'200': {'content': {'application/json': {'schema': {'$ref': '#/components/schemas/Post'}}},
                                               'description': 'Successful '
                                                              'response'},
                                       '404': {'description': 'Post not '
                                                              'found'}},
                         'tags': ['Posts']}}}
        self.assertEqual(expected_paths, paths)


    def test_get_operations(self):
        operations = self.parser._get_operations("/posts")
        expected_operations = {'get': {'description': 'Returns all posts',
         'operationId': 'getPosts',
         'responses': {'200': {'content': {'application/json': {'schema': {'$ref': '#/components/schemas/PostsList'}}},
                               'description': 'Successful response'}},
         'tags': ['Posts']}}
        self.assertEqual(operations, expected_operations)




if __name__ == "__main__":
    unittest.main()
