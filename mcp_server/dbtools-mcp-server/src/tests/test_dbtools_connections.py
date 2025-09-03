import unittest
from unittest import mock
from typing import Any, Dict, List, Optional
import json
import os
import requests
from src.common.connections import dbtools_connection

# Assuming the class is in a module named dbtools_connection_module for import
# But since it's provided as code, we'll define it here for the test file.
# In a real scenario, import from the module.

# The class definition is already provided, so we can proceed with tests.

class TestDbtoolsConnection(unittest.TestCase):

    @mock.patch('os.getenv')
    @mock.patch('oci.config.from_file')
    @mock.patch('oci.signer.Signer')
    @mock.patch('os.environ.get')
    @mock.patch('oci.identity.IdentityClient')
    @mock.patch('oci.resource_search.ResourceSearchClient')
    @mock.patch('oci.database.DatabaseClient')
    @mock.patch('oci.database_tools.DatabaseToolsClient')
    def test_init_success(
        self,
        mock_dbtools_client,
        mock_database_client,
        mock_search_client,
        mock_identity_client,
        mock_env_get,
        mock_signer,
        mock_from_file,
        mock_getenv,
    ):
        # Setup mocks
        mock_getenv.side_effect = lambda k, d=None: {
            'OCI_PROFILE': 'TEST_PROFILE',
            'OCI_VECTOR_MODEL': 'TEST_MODEL',
            'OCI_VECTOR_DIM': '1024'
        }.get(k, d)

        mock_from_file.return_value = {
            'tenancy': 'test_tenancy',
            'user': 'test_user',
            'fingerprint': 'test_fingerprint',
            'key_file': 'test_key_file',
            'pass_phrase': 'test_pass'
        }

        mock_env_get.return_value = 'https://dbtools.test.com/'

        mock_signer.return_value = 'test_signer'

        # Initialize
        conn = dbtools_connection()

        # Assertions
        self.assertEqual(conn.tenancy_id, 'test_tenancy')
        self.assertEqual(conn.ords_endpoint, 'https://dbtools.test.com')
        self.assertEqual(conn.MODEL_NAME, 'TEST_MODEL')
        self.assertEqual(conn.MODEL_EMBEDDING_DIMENSION, 1024)

        mock_identity_client.assert_called_with(mock_from_file.return_value, signer='test_signer')
        mock_search_client.assert_called_with(mock_from_file.return_value, signer='test_signer')
        mock_database_client.assert_called_with(mock_from_file.return_value, signer='test_signer')
        mock_dbtools_client.assert_called_with(mock_from_file.return_value, signer='test_signer')

    @mock.patch('os.getenv')
    @mock.patch('oci.config.from_file')
    @mock.patch('os.environ.get')
    def test_init_missing_ords_endpoint(self, mock_env_get, mock_from_file, mock_getenv):
        mock_getenv.return_value = 'DEFAULT'
        mock_from_file.return_value = {'tenancy': 'test_tenancy'}
        mock_env_get.return_value = None  # Missing endpoint

        with self.assertRaises(RuntimeError) as context:
            dbtools_connection()
        self.assertIn("Set DBTOOLS_ORDS_ENDPOINT", str(context.exception))

    @mock.patch('oci.resource_search.models.StructuredSearchDetails')
    def test_resource_search(self, mock_details):
        # Create instance with mocked search_client
        conn = mock.Mock()
        conn.search_client = mock.Mock()
        conn.config = {'tenancy': 'test_tenancy'}

        mock_details.return_value = 'test_details'
        mock_response = mock.Mock()
        mock_response.data = 'test_data'
        conn.search_client.search_resources.return_value = mock_response

        result = dbtools_connection.resource_search(conn, 'test_query')

        mock_details.assert_called_with(query='test_query', type='Structured', matching_context_type='NONE')
        conn.search_client.search_resources.assert_called_with(search_details='test_details', tenant_id='test_tenancy')
        self.assertEqual(result, 'test_data')

    def test_get_minimal_connection_by_name_success(self):
        conn = mock.Mock()
        conn.search_client = mock.Mock()
        conn.config = {'tenancy': 'test_tenancy'}

        mock_response = mock.Mock()
        mock_item = mock.Mock()
        mock_item.identifier = 'test_id'
        mock_item.display_name = 'test_name'
        mock_item.time_created = 'test_time'
        mock_item.compartment_id = 'test_comp'
        mock_item.lifecycle_state = 'test_state'
        mock_item.additional_details = {'type': 'test_type', 'connectionString': 'test_conn_str'}
        mock_response.data.items = [mock_item]
        conn.search_client.search_resources.return_value = mock_response

        result = dbtools_connection.get_minimal_connection_by_name(conn, 'test_display')

        expected = {
            'id': 'test_id',
            'display_name': 'test_name',
            'time_created': 'test_time',
            'compartment_id': 'test_comp',
            'lifecycle_state': 'test_state',
            'type': 'test_type',
            'connection_string': 'test_conn_str'
        }
        self.assertEqual(result, expected)

    def test_get_minimal_connection_by_name_no_items(self):
        conn = mock.Mock()
        conn.search_client = mock.Mock()
        conn.config = {'tenancy': 'test_tenancy'}

        mock_response = mock.Mock()
        mock_response.data.items = []
        conn.search_client.search_resources.return_value = mock_response

        result = dbtools_connection.get_minimal_connection_by_name(conn, 'test_display')
        self.assertIsNone(result)

    def test_get_minimal_connection_by_name_exception(self):
        conn = mock.Mock()
        conn.search_client = mock.Mock()
        conn.search_client.search_resources.side_effect = Exception('test_error')

        result = dbtools_connection.get_minimal_connection_by_name(conn, 'test_display')
        self.assertIsNone(result)

    @mock.patch('requests.post')
    def test_execute_sql_by_connection_id_success_json(self, mock_post):
        conn = mock.Mock()
        conn.ords_endpoint = 'https://test.com'
        conn.auth_signer = 'test_signer'

        mock_response = mock.Mock()
        mock_response.json.return_value = {'key': 'value'}
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        result = dbtools_connection.execute_sql_by_connection_id(conn, 'test_id', 'SELECT 1', [{'name': 'param'}])

        mock_post.assert_called_with(
            'https://test.com/ords/test_id/_/sql',
            json={'statementText': 'SELECT 1', 'binds': [{'name': 'param'}]},
            auth='test_signer',
            headers={'Content-Type': 'application/json'}
        )
        self.assertEqual(result, json.dumps({'key': 'value'}, indent=2))

    @mock.patch('requests.post')
    def test_execute_sql_by_connection_id_non_json_fallback(self, mock_post):
        conn = mock.Mock()
        conn.ords_endpoint = 'https://test.com'
        conn.auth_signer = 'test_signer'

        mock_response = mock.Mock()
        mock_response.json.side_effect = Exception('not json')
        mock_response.status_code = 400
        mock_response.text = 'error text'
        mock_post.return_value = mock_response

        result = dbtools_connection.execute_sql_by_connection_id(conn, 'test_id', 'SELECT 1')

        self.assertEqual(result, json.dumps({'status_code': 400, 'text': 'error text'}, indent=2))

    @mock.patch('requests.post')
    def test_execute_sql_by_connection_id_exception(self, mock_post):
        conn = mock.Mock()
        conn.ords_endpoint = 'https://test.com'
        conn.auth_signer = 'test_signer'

        mock_post.side_effect = Exception('request error')

        result = dbtools_connection.execute_sql_by_connection_id(conn, 'test_id', 'SELECT 1', [{'name': 'param'}])

        expected = json.dumps({
            'error': 'Error executing SQL: request error',
            'sql_script': 'SELECT 1',
            'binds': [{'name': 'param'}]
        }, indent=2)
        self.assertEqual(result, expected)

if __name__ == '__main__':
    unittest.main()