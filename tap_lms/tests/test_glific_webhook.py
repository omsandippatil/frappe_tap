import unittest
from unittest.mock import Mock, patch, MagicMock, call
import json
import sys
import os

# Add the parent directory to the path to allow imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock frappe and related modules BEFORE importing glific_webhook
sys.modules['frappe'] = MagicMock()
sys.modules['frappe.utils'] = MagicMock()

# Now we can safely import glific_webhook
import glific_webhook


class TestGlificWebhook(unittest.TestCase):
    """Comprehensive test suite for Glific webhook integration"""
    
    def setUp(self):
        """Setup test fixtures before each test"""
        # Mock Teacher document
        self.mock_teacher_doc = Mock()
        self.mock_teacher_doc.doctype = "Teacher"
        self.mock_teacher_doc.name = "TEST-TEACHER-001"
        self.mock_teacher_doc.glific_id = "123"
        self.mock_teacher_doc.first_name = "John"
        self.mock_teacher_doc.last_name = "Doe"
        self.mock_teacher_doc.phone = "9876543210"
        self.mock_teacher_doc.language = "English"
        self.mock_teacher_doc.get = Mock(side_effect=lambda x: getattr(self.mock_teacher_doc, x, None))
        
        # Mock Glific settings
        self.mock_settings = Mock()
        self.mock_settings.api_url = "https://api.glific.test"
        
        # Mock auth headers
        self.mock_headers = {
            "Authorization": "Bearer test_token",
            "Content-Type": "application/json"
        }
        
        # Mock Glific contact
        self.mock_glific_contact = {
            "id": "123",
            "name": "John Doe",
            "language": {
                "id": "1",
                "label": "English"
            },
            "fields": json.dumps({
                "first_name": {
                    "value": "John",
                    "type": "string",
                    "inserted_at": "2024-01-01T00:00:00"
                },
                "phone": {
                    "value": "9876543210",
                    "type": "string",
                    "inserted_at": "2024-01-01T00:00:00"
                }
            })
        }
    
    def tearDown(self):
        """Cleanup after each test"""
        self.mock_teacher_doc = None
        self.mock_settings = None
        self.mock_headers = None
        self.mock_glific_contact = None


class TestGetGlificContact(TestGlificWebhook):
    """Test cases for get_glific_contact function"""
    
    @patch('glific_webhook.get_glific_auth_headers')
    @patch('glific_webhook.get_glific_settings')
    @patch('glific_webhook.requests.post')
    def test_get_contact_success(self, mock_post, mock_settings, mock_headers):
        """Test successful retrieval of Glific contact"""
        # Arrange
        mock_settings.return_value = self.mock_settings
        mock_headers.return_value = self.mock_headers
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "contact": {
                    "contact": self.mock_glific_contact
                }
            }
        }
        mock_post.return_value = mock_response
        
        # Act
        result = glific_webhook.get_glific_contact("123")
        
        # Assert
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], "123")
        self.assertEqual(result["name"], "John Doe")
        self.assertIn("language", result)
        self.assertIn("fields", result)
        
        # Verify API call
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], "https://api.glific.test/api")
        self.assertIn("query", call_args[1]["json"])
        self.assertIn("variables", call_args[1]["json"])
        self.assertEqual(call_args[1]["json"]["variables"]["id"], "123")
    
    @patch('glific_webhook.get_glific_auth_headers')
    @patch('glific_webhook.get_glific_settings')
    @patch('glific_webhook.requests.post')
    def test_get_contact_not_found(self, mock_post, mock_settings, mock_headers):
        """Test contact not found scenario"""
        # Arrange
        mock_settings.return_value = self.mock_settings
        mock_headers.return_value = self.mock_headers
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {}
        }
        mock_post.return_value = mock_response
        
        # Act
        result = glific_webhook.get_glific_contact("999")
        
        # Assert
        self.assertIsNone(result)
    
    @patch('glific_webhook.get_glific_auth_headers')
    @patch('glific_webhook.get_glific_settings')
    @patch('glific_webhook.requests.post')
    def test_get_contact_empty_response(self, mock_post, mock_settings, mock_headers):
        """Test empty response from API"""
        # Arrange
        mock_settings.return_value = self.mock_settings
        mock_headers.return_value = self.mock_headers
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_post.return_value = mock_response
        
        # Act
        result = glific_webhook.get_glific_contact("123")
        
        # Assert
        self.assertIsNone(result)
    
    @patch('glific_webhook.get_glific_auth_headers')
    @patch('glific_webhook.get_glific_settings')
    @patch('glific_webhook.requests.post')
    def test_get_contact_non_200_status(self, mock_post, mock_settings, mock_headers):
        """Test non-200 HTTP status code"""
        # Arrange
        mock_settings.return_value = self.mock_settings
        mock_headers.return_value = self.mock_headers
        
        mock_response = Mock()
        mock_response.status_code = 404
        mock_post.return_value = mock_response
        
        # Act
        result = glific_webhook.get_glific_contact("123")
        
        # Assert
        self.assertIsNone(result)
    
    @patch('glific_webhook.get_glific_auth_headers')
    @patch('glific_webhook.get_glific_settings')
    @patch('glific_webhook.requests.post')
    def test_get_contact_network_error(self, mock_post, mock_settings, mock_headers):
        """Test network connection error"""
        # Arrange
        mock_settings.return_value = self.mock_settings
        mock_headers.return_value = self.mock_headers
        
        import requests
        mock_post.side_effect = requests.exceptions.ConnectionError("Network error")
        
        # Act & Assert
        with self.assertRaises(requests.exceptions.ConnectionError):
            glific_webhook.get_glific_contact("123")
    
    @patch('glific_webhook.get_glific_auth_headers')
    @patch('glific_webhook.get_glific_settings')
    @patch('glific_webhook.requests.post')
    def test_get_contact_timeout(self, mock_post, mock_settings, mock_headers):
        """Test request timeout"""
        # Arrange
        mock_settings.return_value = self.mock_settings
        mock_headers.return_value = self.mock_headers
        
        import requests
        mock_post.side_effect = requests.exceptions.Timeout("Request timeout")
        
        # Act & Assert
        with self.assertRaises(requests.exceptions.Timeout):
            glific_webhook.get_glific_contact("123")
    
    @patch('glific_webhook.get_glific_auth_headers')
    @patch('glific_webhook.get_glific_settings')
    @patch('glific_webhook.requests.post')
    def test_get_contact_invalid_json_response(self, mock_post, mock_settings, mock_headers):
        """Test invalid JSON in response"""
        # Arrange
        mock_settings.return_value = self.mock_settings
        mock_headers.return_value = self.mock_headers
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_post.return_value = mock_response
        
        # Act & Assert
        with self.assertRaises(json.JSONDecodeError):
            glific_webhook.get_glific_contact("123")


class TestPrepareUpdatePayload(TestGlificWebhook):
    """Test cases for prepare_update_payload function"""
    
    @patch('glific_webhook.frappe')
    def test_prepare_payload_with_field_changes(self, mock_frappe):
        """Test payload preparation when fields have changed"""
        # Arrange
        mock_frappe.get_all.return_value = [
            {"frappe_field": "first_name", "glific_field": "first_name"},
            {"frappe_field": "phone", "glific_field": "phone"}
        ]
        mock_frappe.utils.now_datetime().isoformat.return_value = "2024-01-15T10:00:00"
        mock_frappe.db.get_value.return_value = "1"
        
        # Change first_name
        self.mock_teacher_doc.first_name = "Jane"
        
        # Act
        result = glific_webhook.prepare_update_payload(self.mock_teacher_doc, self.mock_glific_contact)
        
        # Assert
        self.assertIsNotNone(result)
        self.assertIn("fields", result)
        
        fields = json.loads(result["fields"])
        self.assertEqual(fields["first_name"]["value"], "Jane")
        self.assertEqual(fields["phone"]["value"], "9876543210")
    
    @patch('glific_webhook.frappe')
    def test_prepare_payload_with_language_change(self, mock_frappe):
        """Test payload preparation when language changes"""
        # Arrange
        mock_frappe.get_all.return_value = [
            {"frappe_field": "first_name", "glific_field": "first_name"}
        ]
        mock_frappe.utils.now_datetime().isoformat.return_value = "2024-01-15T10:00:00"
        mock_frappe.db.get_value.return_value = "2"  # Different language ID
        
        # Act
        result = glific_webhook.prepare_update_payload(self.mock_teacher_doc, self.mock_glific_contact)
        
        # Assert
        self.assertIsNotNone(result)
        self.assertIn("languageId", result)
        self.assertEqual(result["languageId"], 2)
    
    @patch('glific_webhook.frappe')
    def test_prepare_payload_no_changes(self, mock_frappe):
        """Test payload preparation when no changes detected"""
        # Arrange
        mock_frappe.get_all.return_value = [
            {"frappe_field": "first_name", "glific_field": "first_name"},
            {"frappe_field": "phone", "glific_field": "phone"}
        ]
        mock_frappe.db.get_value.return_value = "1"  # Same language ID
        
        # Act
        result = glific_webhook.prepare_update_payload(self.mock_teacher_doc, self.mock_glific_contact)
        
        # Assert
        self.assertIsNone(result)
    
    @patch('glific_webhook.frappe')
    def test_prepare_payload_new_field(self, mock_frappe):
        """Test payload preparation with new field not in Glific"""
        # Arrange
        mock_frappe.get_all.return_value = [
            {"frappe_field": "email", "glific_field": "email"}  # New field
        ]
        mock_frappe.utils.now_datetime().isoformat.return_value = "2024-01-15T10:00:00"
        mock_frappe.db.get_value.return_value = "1"
        
        self.mock_teacher_doc.email = "john@example.com"
        
        # Act
        result = glific_webhook.prepare_update_payload(self.mock_teacher_doc, self.mock_glific_contact)
        
        # Assert
        self.assertIsNotNone(result)
        self.assertIn("fields", result)
        
        fields = json.loads(result["fields"])
        self.assertIn("email", fields)
        self.assertEqual(fields["email"]["value"], "john@example.com")
    
    @patch('glific_webhook.frappe')
    def test_prepare_payload_empty_field_mappings(self, mock_frappe):
        """Test payload preparation with no field mappings"""
        # Arrange
        mock_frappe.get_all.return_value = []
        mock_frappe.db.get_value.return_value = "1"
        
        # Act
        result = glific_webhook.prepare_update_payload(self.mock_teacher_doc, self.mock_glific_contact)
        
        # Assert
        self.assertIsNone(result)
    
    @patch('glific_webhook.frappe')
    def test_prepare_payload_none_field_value(self, mock_frappe):
        """Test payload preparation when field value is None"""
        # Arrange
        mock_frappe.get_all.return_value = [
            {"frappe_field": "middle_name", "glific_field": "middle_name"}
        ]
        mock_frappe.utils.now_datetime().isoformat.return_value = "2024-01-15T10:00:00"
        mock_frappe.db.get_value.return_value = "1"
        
        self.mock_teacher_doc.middle_name = None
        
        # Act
        result = glific_webhook.prepare_update_payload(self.mock_teacher_doc, self.mock_glific_contact)
        
        # Assert
        self.assertIsNotNone(result)
        fields = json.loads(result["fields"])
        self.assertIn("middle_name", fields)
        self.assertEqual(fields["middle_name"]["value"], None)
    
    @patch('glific_webhook.frappe')
    def test_prepare_payload_empty_glific_fields(self, mock_frappe):
        """Test payload preparation when Glific contact has no fields"""
        # Arrange
        mock_frappe.get_all.return_value = [
            {"frappe_field": "first_name", "glific_field": "first_name"}
        ]
        mock_frappe.utils.now_datetime().isoformat.return_value = "2024-01-15T10:00:00"
        mock_frappe.db.get_value.return_value = "1"
        
        # Empty fields in Glific contact
        glific_contact_empty = self.mock_glific_contact.copy()
        glific_contact_empty["fields"] = "{}"
        
        # Act
        result = glific_webhook.prepare_update_payload(self.mock_teacher_doc, glific_contact_empty)
        
        # Assert
        self.assertIsNotNone(result)
        fields = json.loads(result["fields"])
        self.assertIn("first_name", fields)
        self.assertEqual(fields["first_name"]["value"], "John")
    
    @patch('glific_webhook.frappe')
    def test_prepare_payload_null_language(self, mock_frappe):
        """Test payload preparation when language is not found"""
        # Arrange
        mock_frappe.get_all.return_value = [
            {"frappe_field": "first_name", "glific_field": "first_name"}
        ]
        mock_frappe.utils.now_datetime().isoformat.return_value = "2024-01-15T10:00:00"
        mock_frappe.db.get_value.return_value = None  # Language not found
        
        # Act
        result = glific_webhook.prepare_update_payload(self.mock_teacher_doc, self.mock_glific_contact)
        
        # Assert - Should still work without language update
        if result:
            self.assertNotIn("languageId", result)


class TestSendGlificUpdate(TestGlificWebhook):
    """Test cases for send_glific_update function"""
    
    @patch('glific_webhook.get_glific_auth_headers')
    @patch('glific_webhook.get_glific_settings')
    @patch('glific_webhook.requests.post')
    def test_send_update_success(self, mock_post, mock_settings, mock_headers):
        """Test successful update send"""
        # Arrange
        mock_settings.return_value = self.mock_settings
        mock_headers.return_value = self.mock_headers
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "updateContact": {
                    "contact": {
                        "id": "123",
                        "fields": "{}",
                        "language": {"label": "English"}
                    },
                    "errors": None
                }
            }
        }
        mock_post.return_value = mock_response
        
        payload = {
            "fields": json.dumps({"first_name": {"value": "Jane"}}),
            "languageId": 1
        }
        
        # Act
        result = glific_webhook.send_glific_update("123", payload)
        
        # Assert
        self.assertTrue(result)
        mock_post.assert_called_once()
        
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], "https://api.glific.test/api")
        self.assertIn("mutation", call_args[1]["json"]["query"])
        self.assertEqual(call_args[1]["json"]["variables"]["id"], "123")
        self.assertEqual(call_args[1]["json"]["variables"]["input"], payload)
    
    @patch('glific_webhook.get_glific_auth_headers')
    @patch('glific_webhook.get_glific_settings')
    @patch('glific_webhook.requests.post')
    @patch('glific_webhook.frappe')
    def test_send_update_with_api_errors(self, mock_frappe, mock_post, mock_settings, mock_headers):
        """Test update with API errors in response"""
        # Arrange
        mock_settings.return_value = self.mock_settings
        mock_headers.return_value = self.mock_headers
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "errors": [
                {"message": "Invalid contact ID"}
            ]
        }
        mock_post.return_value = mock_response
        
        payload = {"fields": json.dumps({"test": "data"})}
        
        # Act
        result = glific_webhook.send_glific_update("123", payload)
        
        # Assert
        self.assertFalse(result)
        mock_frappe.logger().error.assert_called()
    
    @patch('glific_webhook.get_glific_auth_headers')
    @patch('glific_webhook.get_glific_settings')
    @patch('glific_webhook.requests.post')
    def test_send_update_non_200_status(self, mock_post, mock_settings, mock_headers):
        """Test update with non-200 status code"""
        # Arrange
        mock_settings.return_value = self.mock_settings
        mock_headers.return_value = self.mock_headers
        
        mock_response = Mock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response
        
        payload = {"fields": json.dumps({"test": "data"})}
        
        # Act
        result = glific_webhook.send_glific_update("123", payload)
        
        # Assert
        self.assertFalse(result)
    
    @patch('glific_webhook.get_glific_auth_headers')
    @patch('glific_webhook.get_glific_settings')
    @patch('glific_webhook.requests.post')
    def test_send_update_network_error(self, mock_post, mock_settings, mock_headers):
        """Test update with network error"""
        # Arrange
        mock_settings.return_value = self.mock_settings
        mock_headers.return_value = self.mock_headers
        
        import requests
        mock_post.side_effect = requests.exceptions.ConnectionError("Network error")
        
        payload = {"fields": json.dumps({"test": "data"})}
        
        # Act & Assert
        with self.assertRaises(requests.exceptions.ConnectionError):
            glific_webhook.send_glific_update("123", payload)
    
    @patch('glific_webhook.get_glific_auth_headers')
    @patch('glific_webhook.get_glific_settings')
    @patch('glific_webhook.requests.post')
    def test_send_update_timeout(self, mock_post, mock_settings, mock_headers):
        """Test update with timeout"""
        # Arrange
        mock_settings.return_value = self.mock_settings
        mock_headers.return_value = self.mock_headers
        
        import requests
        mock_post.side_effect = requests.exceptions.Timeout("Timeout")
        
        payload = {"fields": json.dumps({"test": "data"})}
        
        # Act & Assert
        with self.assertRaises(requests.exceptions.Timeout):
            glific_webhook.send_glific_update("123", payload)
    
    @patch('glific_webhook.get_glific_auth_headers')
    @patch('glific_webhook.get_glific_settings')
    @patch('glific_webhook.requests.post')
    def test_send_update_invalid_json_response(self, mock_post, mock_settings, mock_headers):
        """Test update with invalid JSON response"""
        # Arrange
        mock_settings.return_value = self.mock_settings
        mock_headers.return_value = self.mock_headers
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_post.return_value = mock_response
        
        payload = {"fields": json.dumps({"test": "data"})}
        
        # Act & Assert
        with self.assertRaises(json.JSONDecodeError):
            glific_webhook.send_glific_update("123", payload)


class TestUpdateGlificContact(TestGlificWebhook):
    """Test cases for update_glific_contact function (main workflow)"""
    
    @patch('glific_webhook.send_glific_update')
    @patch('glific_webhook.prepare_update_payload')
    @patch('glific_webhook.get_glific_contact')
    @patch('glific_webhook.frappe')
    def test_update_contact_full_success_workflow(self, mock_frappe, mock_get, 
                                                    mock_prepare, mock_send):
        """Test complete successful update workflow"""
        # Arrange
        mock_get.return_value = self.mock_glific_contact
        mock_prepare.return_value = {
            "fields": json.dumps({"first_name": {"value": "Jane"}}),
            "languageId": 2
        }
        mock_send.return_value = True
        
        # Act
        glific_webhook.update_glific_contact(self.mock_teacher_doc, "on_update")
        
        # Assert
        mock_get.assert_called_once_with("123")
        mock_prepare.assert_called_once_with(self.mock_teacher_doc, self.mock_glific_contact)
        mock_send.assert_called_once()
        mock_frappe.logger().info.assert_called()
    
    @patch('glific_webhook.frappe')
    def test_update_contact_wrong_doctype(self, mock_frappe):
        """Test update with non-Teacher doctype - should return early"""
        # Arrange
        student_doc = Mock()
        student_doc.doctype = "Student"
        student_doc.name = "STUDENT-001"
        
        # Act
        result = glific_webhook.update_glific_contact(student_doc, "on_update")
        
        # Assert
        self.assertIsNone(result)
    
    @patch('glific_webhook.get_glific_contact')
    @patch('glific_webhook.frappe')
    def test_update_contact_not_found_in_glific(self, mock_frappe, mock_get):
        """Test when contact not found in Glific"""
        # Arrange
        mock_get.return_value = None
        
        # Act
        glific_webhook.update_glific_contact(self.mock_teacher_doc, "on_update")
        
        # Assert
        mock_get.assert_called_once_with("123")
        mock_frappe.logger().error.assert_called_once()
        error_call = mock_frappe.logger().error.call_args[0][0]
        self.assertIn("not found", error_call)
        self.assertIn("TEST-TEACHER-001", error_call)
    
    @patch('glific_webhook.prepare_update_payload')
    @patch('glific_webhook.get_glific_contact')
    @patch('glific_webhook.frappe')
    def test_update_contact_no_updates_needed(self, mock_frappe, mock_get, mock_prepare):
        """Test when no updates are needed"""
        # Arrange
        mock_get.return_value = self.mock_glific_contact
        mock_prepare.return_value = None  # No updates
        
        # Act
        glific_webhook.update_glific_contact(self.mock_teacher_doc, "on_update")
        
        # Assert
        mock_get.assert_called_once()
        mock_prepare.assert_called_once()
        mock_frappe.logger().info.assert_called_once()
        info_call = mock_frappe.logger().info.call_args[0][0]
        self.assertIn("No updates needed", info_call)
    
    @patch('glific_webhook.send_glific_update')
    @patch('glific_webhook.prepare_update_payload')
    @patch('glific_webhook.get_glific_contact')
    @patch('glific_webhook.frappe')
    def test_update_contact_send_fails(self, mock_frappe, mock_get, mock_prepare, mock_send):
        """Test when sending update fails"""
        # Arrange
        mock_get.return_value = self.mock_glific_contact
        mock_prepare.return_value = {"fields": json.dumps({"test": "data"})}
        mock_send.return_value = False  # Send fails
        
        # Act
        glific_webhook.update_glific_contact(self.mock_teacher_doc, "on_update")
        
        # Assert
        mock_send.assert_called_once()
        mock_frappe.logger().error.assert_called_once()
        error_call = mock_frappe.logger().error.call_args[0][0]
        self.assertIn("Failed to update", error_call)
    
    @patch('glific_webhook.get_glific_contact')
    @patch('glific_webhook.frappe')
    def test_update_contact_exception_handling(self, mock_frappe, mock_get):
        """Test exception handling in main function"""
        # Arrange
        mock_get.side_effect = Exception("Unexpected error")
        
        # Act
        glific_webhook.update_glific_contact(self.mock_teacher_doc, "on_update")
        
        # Assert
        mock_frappe.logger().error.assert_called_once()
        error_call = mock_frappe.logger().error.call_args[0][0]
        self.assertIn("Error updating", error_call)
        self.assertIn("Unexpected error", error_call)


class TestEdgeCases(TestGlificWebhook):
    """Test edge cases and boundary conditions"""
    
    @patch('glific_webhook.frappe')
    def test_special_characters_in_fields(self, mock_frappe):
        """Test with special characters in field values"""
        # Arrange
        mock_frappe.get_all.return_value = [
            {"frappe_field": "first_name", "glific_field": "first_name"}
        ]
        mock_frappe.utils.now_datetime().isoformat.return_value = "2024-01-15T10:00:00"
        mock_frappe.db.get_value.return_value = "1"
        
        # Special characters
        self.mock_teacher_doc.first_name = "José María O'Brien <test@example.com>"
        
        # Act
        result = glific_webhook.prepare_update_payload(self.mock_teacher_doc, self.mock_glific_contact)
        
        # Assert
        self.assertIsNotNone(result)
        fields = json.loads(result["fields"])
        self.assertEqual(fields["first_name"]["value"], "José María O'Brien <test@example.com>")
    
    @patch('glific_webhook.frappe')
    def test_very_long_field_values(self, mock_frappe):
        """Test with very long field values"""
        # Arrange
        mock_frappe.get_all.return_value = [
            {"frappe_field": "notes", "glific_field": "notes"}
        ]
        mock_frappe.utils.now_datetime().isoformat.return_value = "2024-01-15T10:00:00"
        mock_frappe.db.get_value.return_value = "1"
        
        # Very long string
        long_value = "x" * 10000
        self.mock_teacher_doc.notes = long_value
        
        # Act
        result = glific_webhook.prepare_update_payload(self.mock_teacher_doc, self.mock_glific_contact)
        
        # Assert
        self.assertIsNotNone(result)
        fields = json.loads(result["fields"])
        self.assertEqual(len(fields["notes"]["value"]), 10000)


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)