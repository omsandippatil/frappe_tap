import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timezone, timedelta
import json
import requests

# Add the parent directory to the Python path to import the module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import your module - ADJUST THIS PATH BASED ON YOUR ACTUAL MODULE NAME
# If your file is named 'glific_integration.py', change this line to:
# import glific_integration as glific_module
# Or if it's in a package, use the appropriate import path

try:
    # Try to import from common names - adjust as needed
    import glific_integration as glific_module
except ImportError:
    try:
        from . import glific_integration as glific_module
    except ImportError:
        # Create a mock module for demonstration - REMOVE THIS IN ACTUAL TESTS
        print("WARNING: Could not import the actual module. Using mock for demonstration.")
        print("Please update the import statement with your actual module name.")
        
        class MockModule:
            def get_glific_settings(self): pass
            def get_glific_auth_headers(self): pass
            def create_contact(self, *args): pass
            def update_contact_fields(self, *args): pass
            def get_contact_by_phone(self, phone): pass
            def optin_contact(self, phone, name): pass
            def check_glific_group_exists(self, label): pass
            def create_glific_group(self, label, desc=""): pass
            def add_contact_to_group(self, contact_id, group_id): pass
            def add_student_to_glific_for_onboarding(self, *args): pass
            def create_or_get_glific_group_for_batch(self, set_id): pass
            def create_or_get_teacher_group_for_batch(self, *args): pass
        
        glific_module = MockModule()


class TestGlificIntegration(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.mock_settings = Mock()
        self.mock_settings.api_url = "https://api.example.com"
        self.mock_settings.phone_number = "1234567890"
        self.mock_settings.password = "test_password"
        self.mock_settings.access_token = "test_token"
        self.mock_settings.renewal_token = "renewal_token"
        self.mock_settings.token_expiry_time = datetime.now(timezone.utc) + timedelta(hours=1)
        self.mock_settings.name = "test_settings"
        self.mock_settings.default_language_id = "1"

    @patch('frappe.get_single')
    def test_get_glific_settings(self, mock_frappe_get_single):
        """Test getting Glific settings."""
        mock_frappe_get_single.return_value = self.mock_settings
        
        result = glific_module.get_glific_settings()
        
        mock_frappe_get_single.assert_called_once_with("Glific Settings")
        self.assertEqual(result, self.mock_settings)

    @patch('requests.post')
    @patch('frappe.get_single')
    @patch('frappe.db.set_value')
    @patch('frappe.db.commit')
    def test_get_glific_auth_headers_with_valid_token(self, mock_commit, mock_set_value, mock_frappe_get_single, mock_post):
        """Test getting auth headers when token is valid."""
        mock_frappe_get_single.return_value = self.mock_settings
        
        result = glific_module.get_glific_auth_headers()
        
        expected_headers = {
            "authorization": "test_token",
            "Content-Type": "application/json"
        }
        self.assertEqual(result, expected_headers)
        mock_post.assert_not_called()

    @patch('requests.post')
    @patch('frappe.get_single')
    @patch('frappe.db.set_value')
    @patch('frappe.db.commit')
    def test_get_glific_auth_headers_token_expired(self, mock_commit, mock_set_value, mock_frappe_get_single, mock_post):
        """Test getting auth headers when token is expired."""
        # Set expired token
        self.mock_settings.token_expiry_time = datetime.now(timezone.utc) - timedelta(hours=1)
        mock_frappe_get_single.return_value = self.mock_settings
        
        # Mock successful authentication response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "access_token": "new_token",
                "renewal_token": "new_renewal",
                "token_expiry_time": "2024-12-31T23:59:59Z"
            }
        }
        mock_post.return_value = mock_response
        
        result = glific_module.get_glific_auth_headers()
        
        expected_headers = {
            "authorization": "new_token",
            "Content-Type": "application/json"
        }
        self.assertEqual(result, expected_headers)
        mock_post.assert_called_once()

    @patch('requests.post')
    @patch('frappe.get_single')
    @patch('frappe.throw')
    def test_get_glific_auth_headers_authentication_failed(self, mock_throw, mock_frappe_get_single, mock_post):
        """Test authentication failure scenario."""
        self.mock_settings.access_token = None
        mock_frappe_get_single.return_value = self.mock_settings
        
        # Mock failed authentication response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_post.return_value = mock_response
        
        glific_module.get_glific_auth_headers()
        
        mock_throw.assert_called_once_with("Failed to authenticate with Glific API")

    @patch('requests.post')
    @patch.object(glific_module, 'get_glific_auth_headers')
    @patch.object(glific_module, 'get_glific_settings')
    @patch('frappe.logger')
    def test_create_contact_success(self, mock_logger, mock_get_settings, mock_get_auth, mock_post):
        """Test successful contact creation."""
        mock_get_settings.return_value = self.mock_settings
        mock_get_auth.return_value = {"authorization": "token", "Content-Type": "application/json"}
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "success"
        mock_response.json.return_value = {
            "data": {
                "createContact": {
                    "contact": {
                        "id": "123",
                        "name": "Test User",
                        "phone": "919876543210"
                    }
                }
            }
        }
        mock_post.return_value = mock_response
        
        # Mock logger
        mock_logger_instance = Mock()
        mock_logger.return_value = mock_logger_instance
        
        result = glific_module.create_contact("Test User", "919876543210", "Test School", "Test Model", "1", "batch123")
        
        self.assertEqual(result["id"], "123")
        self.assertEqual(result["name"], "Test User")
        mock_post.assert_called_once()

    @patch('requests.post')
    @patch.object(glific_module, 'get_glific_auth_headers')
    @patch.object(glific_module, 'get_glific_settings')
    @patch('frappe.logger')
    def test_create_contact_with_errors(self, mock_logger, mock_get_settings, mock_get_auth, mock_post):
        """Test contact creation with API errors."""
        mock_get_settings.return_value = self.mock_settings
        mock_get_auth.return_value = {"authorization": "token", "Content-Type": "application/json"}
        
        # Mock error response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "error"
        mock_response.json.return_value = {
            "errors": [{"message": "Contact creation failed"}]
        }
        mock_post.return_value = mock_response
        
        # Mock logger
        mock_logger_instance = Mock()
        mock_logger.return_value = mock_logger_instance
        
        result = glific_module.create_contact("Test User", "919876543210", "Test School", "Test Model", "1", "batch123")
        
        self.assertIsNone(result)

    @patch('requests.post')
    @patch.object(glific_module, 'get_glific_auth_headers')
    @patch.object(glific_module, 'get_glific_settings')
    def test_get_contact_by_phone_success(self, mock_get_settings, mock_get_auth, mock_post):
        """Test successful contact retrieval by phone."""
        mock_get_settings.return_value = self.mock_settings
        mock_get_auth.return_value = {"authorization": "token", "Content-Type": "application/json"}
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "contactByPhone": {
                    "contact": {
                        "id": "123",
                        "name": "Test User",
                        "phone": "919876543210",
                        "bspStatus": "SESSION"
                    }
                }
            }
        }
        mock_post.return_value = mock_response
        mock_response.raise_for_status = Mock()
        
        result = glific_module.get_contact_by_phone("919876543210")
        
        self.assertEqual(result["id"], "123")
        self.assertEqual(result["bspStatus"], "SESSION")

    @patch('requests.post')
    @patch.object(glific_module, 'get_glific_auth_headers')
    @patch.object(glific_module, 'get_glific_settings')
    @patch('frappe.logger')
    def test_get_contact_by_phone_not_found(self, mock_logger, mock_get_settings, mock_get_auth, mock_post):
        """Test contact not found scenario."""
        mock_get_settings.return_value = self.mock_settings
        mock_get_auth.return_value = {"authorization": "token", "Content-Type": "application/json"}
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "contactByPhone": {
                    "contact": None
                }
            }
        }
        mock_post.return_value = mock_response
        mock_response.raise_for_status = Mock()
        
        # Mock logger
        mock_logger_instance = Mock()
        mock_logger.return_value = mock_logger_instance
        
        result = glific_module.get_contact_by_phone("919876543210")
        
        self.assertIsNone(result)

    @patch('requests.post')
    @patch.object(glific_module, 'get_glific_auth_headers')
    @patch.object(glific_module, 'get_glific_settings')
    @patch('frappe.logger')
    def test_optin_contact_success(self, mock_logger, mock_get_settings, mock_get_auth, mock_post):
        """Test successful contact opt-in."""
        mock_get_settings.return_value = self.mock_settings
        mock_get_auth.return_value = {"authorization": "token", "Content-Type": "application/json"}
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "optinContact": {
                    "contact": {
                        "id": "123",
                        "phone": "919876543210",
                        "bspStatus": "SESSION"
                    }
                }
            }
        }
        mock_post.return_value = mock_response
        mock_response.raise_for_status = Mock()
        
        # Mock logger
        mock_logger_instance = Mock()
        mock_logger.return_value = mock_logger_instance
        
        result = glific_module.optin_contact("919876543210", "Test User")
        
        self.assertTrue(result)

    @patch('requests.post')
    @patch.object(glific_module, 'get_glific_auth_headers')
    @patch.object(glific_module, 'get_glific_settings')
    @patch('frappe.logger')
    def test_update_contact_fields_success(self, mock_logger, mock_get_settings, mock_get_auth, mock_post):
        """Test successful contact field update."""
        mock_get_settings.return_value = self.mock_settings
        mock_get_auth.return_value = {"authorization": "token", "Content-Type": "application/json"}
        
        # Mock fetch contact response
        fetch_response = Mock()
        fetch_response.status_code = 200
        fetch_response.json.return_value = {
            "data": {
                "contact": {
                    "contact": {
                        "id": "123",
                        "name": "Test User",
                        "fields": '{"existing_field": {"value": "existing_value", "type": "string"}}'
                    }
                }
            }
        }
        
        # Mock update contact response
        update_response = Mock()
        update_response.status_code = 200
        update_response.json.return_value = {
            "data": {
                "updateContact": {
                    "contact": {
                        "id": "123",
                        "name": "Test User"
                    }
                }
            }
        }
        
        mock_post.side_effect = [fetch_response, update_response]
        fetch_response.raise_for_status = Mock()
        update_response.raise_for_status = Mock()
        
        # Mock logger
        mock_logger_instance = Mock()
        mock_logger.return_value = mock_logger_instance
        
        fields_to_update = {"new_field": "new_value"}
        result = glific_module.update_contact_fields("123", fields_to_update)
        
        self.assertTrue(result)
        self.assertEqual(mock_post.call_count, 2)

    @patch('requests.post')
    @patch.object(glific_module, 'get_glific_auth_headers')
    @patch.object(glific_module, 'get_glific_settings')
    def test_check_glific_group_exists_found(self, mock_get_settings, mock_get_auth, mock_post):
        """Test checking if group exists - found."""
        mock_get_settings.return_value = self.mock_settings
        mock_get_auth.return_value = {"authorization": "token", "Content-Type": "application/json"}
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "groups": [
                    {"id": "456", "label": "Test Group"}
                ]
            }
        }
        mock_post.return_value = mock_response
        mock_response.raise_for_status = Mock()
        
        result = glific_module.check_glific_group_exists("Test Group")
        
        self.assertEqual(result["id"], "456")
        self.assertEqual(result["label"], "Test Group")

    @patch('requests.post')
    @patch.object(glific_module, 'get_glific_auth_headers')
    @patch.object(glific_module, 'get_glific_settings')
    def test_create_glific_group_success(self, mock_get_settings, mock_get_auth, mock_post):
        """Test successful group creation."""
        mock_get_settings.return_value = self.mock_settings
        mock_get_auth.return_value = {"authorization": "token", "Content-Type": "application/json"}
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "createGroup": {
                    "group": {
                        "id": "789",
                        "label": "New Group",
                        "description": "Test Description"
                    }
                }
            }
        }
        mock_post.return_value = mock_response
        mock_response.raise_for_status = Mock()
        
        result = glific_module.create_glific_group("New Group", "Test Description")
        
        self.assertEqual(result["id"], "789")
        self.assertEqual(result["label"], "New Group")

    @patch('requests.post')
    @patch.object(glific_module, 'get_glific_auth_headers')
    @patch.object(glific_module, 'get_glific_settings')
    def test_add_contact_to_group_success(self, mock_get_settings, mock_get_auth, mock_post):
        """Test successfully adding contact to group."""
        mock_get_settings.return_value = self.mock_settings
        mock_get_auth.return_value = {"authorization": "token", "Content-Type": "application/json"}
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "updateGroupContacts": {
                    "groupContacts": [{"id": "contact_group_123"}]
                }
            }
        }
        mock_post.return_value = mock_response
        mock_response.raise_for_status = Mock()
        
        result = glific_module.add_contact_to_group("123", "456")
        
        self.assertTrue(result)

    @patch.object(glific_module, 'get_contact_by_phone')
    @patch.object(glific_module, 'optin_contact')
    @patch.object(glific_module, 'add_contact_to_group')
    @patch.object(glific_module, 'update_contact_fields')
    @patch('frappe.logger')
    def test_add_student_to_glific_existing_contact(self, mock_logger, mock_update, mock_add_group, mock_optin, mock_get_contact):
        """Test adding student when contact already exists."""
        # Mock existing contact
        existing_contact = {
            "id": "123",
            "name": "Test Student",
            "phone": "919876543210",
            "bspStatus": "SESSION"
        }
        mock_get_contact.return_value = existing_contact
        mock_add_group.return_value = True
        mock_update.return_value = True
        
        # Mock logger
        mock_logger_instance = Mock()
        mock_logger.return_value = mock_logger_instance
        
        result = glific_module.add_student_to_glific_for_onboarding(
            "Test Student", "9876543210", "Test School", "batch123", "group456", "1"
        )
        
        self.assertEqual(result, existing_contact)
        mock_get_contact.assert_called_once_with("919876543210")
        mock_add_group.assert_called_once_with("123", "group456")
        mock_optin.assert_not_called()  # Contact already opted in

    @patch.object(glific_module, 'get_contact_by_phone')
    @patch.object(glific_module, 'optin_contact')
    @patch.object(glific_module, 'add_contact_to_group')
    @patch.object(glific_module, 'update_contact_fields')
    @patch('frappe.logger')
    def test_add_student_to_glific_existing_contact_needs_optin(self, mock_logger, mock_update, mock_add_group, mock_optin, mock_get_contact):
        """Test adding student when contact exists but needs opt-in."""
        # Mock existing contact that needs opt-in
        existing_contact = {
            "id": "123",
            "name": "Test Student",
            "phone": "919876543210",
            "bspStatus": "NONE"
        }
        mock_get_contact.return_value = existing_contact
        mock_optin.return_value = True
        mock_add_group.return_value = True
        mock_update.return_value = True
        
        # Mock logger
        mock_logger_instance = Mock()
        mock_logger.return_value = mock_logger_instance
        
        result = glific_module.add_student_to_glific_for_onboarding(
            "Test Student", "9876543210", "Test School", "batch123", "group456", "1"
        )
        
        self.assertEqual(result, existing_contact)
        mock_optin.assert_called_once_with("919876543210", "Test Student")

    @patch('requests.post')
    @patch.object(glific_module, 'get_glific_auth_headers')
    @patch.object(glific_module, 'get_glific_settings')
    @patch.object(glific_module, 'get_contact_by_phone')
    @patch.object(glific_module, 'optin_contact')
    @patch.object(glific_module, 'add_contact_to_group')
    @patch('frappe.logger')
    def test_add_student_to_glific_create_new_contact(self, mock_logger, mock_add_group, mock_optin, mock_get_contact, mock_get_settings, mock_get_auth, mock_post):
        """Test creating new contact for student."""
        mock_get_contact.return_value = None  # No existing contact
        mock_get_settings.return_value = self.mock_settings
        mock_get_auth.return_value = {"authorization": "token", "Content-Type": "application/json"}
        
        # Mock successful contact creation
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "createContact": {
                    "contact": {
                        "id": "new123",
                        "name": "New Student",
                        "phone": "919876543210"
                    }
                }
            }
        }
        mock_post.return_value = mock_response
        
        mock_optin.return_value = True
        mock_add_group.return_value = True
        
        # Mock logger
        mock_logger_instance = Mock()
        mock_logger.return_value = mock_logger_instance
        
        result = glific_module.add_student_to_glific_for_onboarding(
            "New Student", "9876543210", "Test School", "batch123", "group456", "1"
        )
        
        self.assertEqual(result["id"], "new123")
        mock_optin.assert_called_once_with("919876543210", "New Student")
        mock_add_group.assert_called_once_with("new123", "group456")

    @patch('frappe.logger')
    def test_add_student_invalid_phone(self, mock_logger):
        """Test adding student with invalid phone number."""
        # Mock logger
        mock_logger_instance = Mock()
        mock_logger.return_value = mock_logger_instance
        
        result = glific_module.add_student_to_glific_for_onboarding(
            "Test Student", "invalid", "Test School", "batch123", "group456", "1"
        )
        
        self.assertIsNone(result)

    @patch.object(glific_module, 'check_glific_group_exists')
    @patch.object(glific_module, 'create_glific_group')
    @patch('frappe.get_all')
    def test_create_or_get_glific_group_for_batch_existing_mapping(self, mock_get_all, mock_create_group, mock_check_group):
        """Test getting existing group mapping for batch."""
        # Mock existing mapping
        mock_get_all.return_value = [{
            "name": "mapping1",
            "group_id": "existing_group_123",
            "label": "Set: Test Batch"
        }]
        
        result = glific_module.create_or_get_glific_group_for_batch("batch_set_id")
        
        self.assertEqual(result["group_id"], "existing_group_123")
        self.assertEqual(result["label"], "Set: Test Batch")
        mock_check_group.assert_not_called()
        mock_create_group.assert_not_called()

    @patch.object(glific_module, 'check_glific_group_exists')
    @patch.object(glific_module, 'create_glific_group')
    @patch('frappe.get_all')
    @patch('frappe.get_doc')
    @patch('frappe.new_doc')
    def test_create_or_get_glific_group_for_batch_create_new(self, mock_new_doc, mock_get_doc, mock_get_all, mock_create_group, mock_check_group):
        """Test creating new group for batch."""
        # Mock no existing mapping
        mock_get_all.return_value = []
        
        # Mock batch document
        mock_set = Mock()
        mock_set.set_name = "Test Batch"
        mock_get_doc.return_value = mock_set
        
        # Mock no existing group in Glific
        mock_check_group.return_value = None
        
        # Mock successful group creation
        mock_create_group.return_value = {
            "id": "new_group_456",
            "label": "Set: Test Batch"
        }
        
        # Mock new document creation
        mock_doc = Mock()
        mock_new_doc.return_value = mock_doc
        
        result = glific_module.create_or_get_glific_group_for_batch("batch_set_id")
        
        self.assertEqual(result["group_id"], "new_group_456")
        self.assertEqual(result["label"], "Set: Test Batch")
        mock_create_group.assert_called_once()
        mock_doc.insert.assert_called_once()

    @patch('frappe.logger')
    def test_create_or_get_teacher_group_for_batch_invalid_data(self, mock_logger):
        """Test teacher group creation with invalid batch data."""
        # Mock logger
        mock_logger_instance = Mock()
        mock_logger.return_value = mock_logger_instance
        
        # Test with no active batch
        result = glific_module.create_or_get_teacher_group_for_batch("batch_name", "no_active_batch_id")
        self.assertIsNone(result)
        
        # Test with None batch_id
        result = glific_module.create_or_get_teacher_group_for_batch("batch_name", None)
        self.assertIsNone(result)
        
        # Test with empty batch_name
        result = glific_module.create_or_get_teacher_group_for_batch("", "valid_batch_id")
        self.assertIsNone(result)

    @patch.object(glific_module, 'get_contact_by_phone')
    def test_phone_number_formatting_in_add_student(self, mock_get_contact):
        """Test phone number formatting logic."""
        mock_get_contact.return_value = {"id": "123", "bspStatus": "SESSION"}
        
        # Test with 10-digit number
        glific_module.add_student_to_glific_for_onboarding("Test", "9876543210", "School", "batch", "group", "1")
        mock_get_contact.assert_called_with("919876543210")
        
        # Test with already formatted 12-digit number
        glific_module.add_student_to_glific_for_onboarding("Test", "919876543210", "School", "batch", "group", "1")
        mock_get_contact.assert_called_with("919876543210")


class TestGlificIntegrationEdgeCases(unittest.TestCase):
    """Test edge cases and error scenarios."""
    
    @patch('requests.post')
    @patch.object(glific_module, 'get_glific_auth_headers')
    @patch.object(glific_module, 'get_glific_settings')
    @patch('frappe.logger')
    def test_network_timeout_handling(self, mock_logger, mock_get_settings, mock_get_auth, mock_post):
        """Test network timeout handling."""
        mock_get_settings.return_value = Mock(api_url="https://api.example.com")
        mock_get_auth.return_value = {"authorization": "token", "Content-Type": "application/json"}
        
        # Mock logger
        mock_logger_instance = Mock()
        mock_logger.return_value = mock_logger_instance
        
        # Mock network timeout
        mock_post.side_effect = requests.exceptions.Timeout("Request timed out")
        
        result = glific_module.get_contact_by_phone("919876543210")
        
        self.assertIsNone(result)

    @patch('requests.post')
    @patch.object(glific_module, 'get_glific_auth_headers')
    @patch.object(glific_module, 'get_glific_settings')
    @patch('frappe.logger')
    def test_malformed_json_response(self, mock_logger, mock_get_settings, mock_get_auth, mock_post):
        """Test handling of malformed JSON responses."""
        mock_get_settings.return_value = Mock(api_url="https://api.example.com")
        mock_get_auth.return_value = {"authorization": "token", "Content-Type": "application/json"}
        
        # Mock logger
        mock_logger_instance = Mock()
        mock_logger.return_value = mock_logger_instance
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_post.return_value = mock_response
        
        result = glific_module.get_contact_by_phone("919876543210")
        
        self.assertIsNone(result)

    @patch('frappe.get_single')
    def test_database_error_handling(self, mock_frappe_get_single):
        """Test database error handling."""
        # Mock database error
        mock_frappe_get_single.side_effect = Exception("Database connection failed")
        
        with self.assertRaises(Exception):
            glific_module.get_glific_settings()

