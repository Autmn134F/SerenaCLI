import unittest
from unittest.mock import MagicMock, patch
from serena_native.cli import main
import sys
import io
import json

class TestCLI(unittest.TestCase):
    def setUp(self):
        self.capturedOutput = io.StringIO()
        sys.stdout = self.capturedOutput

    def tearDown(self):
        sys.stdout = sys.__stdout__

    @patch('serena_native.cli.SerenaClient')
    def test_project_status_json(self, MockClient):
        mock_instance = MockClient.return_value
        mock_instance.get_status.return_value = {
            "serena_available": True,
            "project_detected": True,
            "index_state": "configured"
        }

        with patch('sys.argv', ['serena-native', '--format', 'json', 'project', 'status']):
            main()

        output = json.loads(self.capturedOutput.getvalue())
        self.assertTrue(output['serena_available'])
        self.assertEqual(output['index_state'], 'configured')

    @patch('serena_native.cli.SerenaClient')
    def test_find_symbol(self, MockClient):
        mock_instance = MockClient.return_value
        mock_instance.find_symbol.return_value = [
            {"name": "TestClass", "kind": "class", "relative_path": "test.py"}
        ]

        with patch('sys.argv', ['serena-native', 'query', 'find-symbol', '--name', 'TestClass']):
            main()

        output = self.capturedOutput.getvalue()
        self.assertIn("TestClass", output)
        self.assertIn("test.py", output)

if __name__ == '__main__':
    unittest.main()
