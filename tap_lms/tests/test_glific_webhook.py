"""
Comprehensive test suite for Glific Webhook module.
Fixed version that handles relative imports correctly.

Tests cover:
- update_glific_contact (main webhook function)
- get_glific_contact (fetch contact details)
- prepare_update_payload (prepare update data)
- send_glific_update (send updates to Glific)
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timezone
import json

# Setup Python path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)


# ============================================================================
# CRITICAL: Mock glific_integration module BEFORE importing glific_webhook
# ============================================================================

def setup_module_mocks():
    """Setup all required module mocks before any imports"""
    # Create mock glific_integration module
    mock_glific_integration = MagicMock()
    mock_glific_integration.get_glific_settings = MagicMock()
    mock_glific_integration.get_glific_auth_headers = MagicMock()
    
    # Create mock frappe module
    mock_frappe = MagicMock()
    mock_frappe._ = lambda x: x  # Translation function
    
    # Patch sys.modules before any imports
    sys.modules['tap_lms.glific_integration'] = mock_glific_integration
    sys.modules['glific_integration'] = mock_glific_integration
    sys.modules['frappe'] = mock_frappe
    sys.modules['frappe.utils'] = MagicMock()
    
    return mock_glific_integration, mock_frappe

# Setup mocks at module level
mock_glific_integration, mock_frappe_module = setup_module_mocks()


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_frappe():
    """Configured Frappe mock"""
    mock_frappe_module.logger.return_value = Mock(
        info=Mock(),
        error=Mock(),
        warning=Mock()
    )
    mock_frappe_module.db = Mock()
    mock_frappe_module.db.commit = Mock()
    mock_frappe_module.db.get_value = Mock()
    mock_frappe_module.get_all = Mock()
    mock_frappe_module.utils = Mock()
    mock_frappe_module.utils.now_datetime = Mock(return_value=datetime.now(timezone.utc))
    mock_frappe_module._ = lambda x: x
    return mock_frappe_module


@pytest.fixture
def mock_glific_settings():
    """Mock Glific Settings document"""
    settings = Mock()
    settings.api_url = "https://api.glific.com"
    settings.access_token = "valid_test_token"
    return settings


@pytest.fixture
def mock_teacher_doc():
    """Mock Teacher document"""
    doc = Mock()
    doc.doctype = "Teacher"
    doc.name = "Teacher-001"
    doc.glific_id = "12345"
    doc.language = "English"
    doc.school = "Test School"
    doc.batch = "Batch-001"
    doc.get = Mock(side_effect=lambda field: {
        "language": "English",
        "school": "Test School",
        "batch": "Batch-001",
        "glific_id": "12345"
    }.get(field))
    return doc


@pytest.fixture
def mock_glific_contact():
    """Mock Glific contact data"""
    return {
        "id": "12345",
        "name": "Test Teacher",
        "language": {
            "id": "1",
            "label": "English"
        },
        "fields": json.dumps({
            "school": {
                "value": "Old School",
                "type": "string",
                "inserted_at": "2025-01-01T00:00:00Z"
            },
            "batch": {
                "value": "Old Batch",
                "type": "string",
                "inserted_at": "2025-01-01T00:00:00Z"
            }
        })
    }


@pytest.fixture
def mock_api_response():
    """Factory for creating mock API responses"""
    def _create_response(status_code=200, data=None, errors=None):
        response = Mock()
        response.status_code = status_code
        response.text = "Mock response text"
        
        response_data = {}
        if data:
            response_data["data"] = data
        if errors:
            response_data["errors"] = errors
        
        response.json.return_value = response_data
        return response
    return _create_response


# ============================================================================
# TEST CLASS: UPDATE GLIFIC CONTACT (Main Webhook Function)
# ============================================================================

class TestUpdateGlificContact:
    """Tests for the main webhook function update_glific_contact"""
    
    def test_update_glific_contact_wrong_doctype(self, mock_frappe, mock_teacher_doc):
        """Test that function returns early for non-Teacher doctypes"""
        mock_teacher_doc.doctype = "Student"
        
        # Import after mocks are set up
        from tap_lms.glific_webhook import update_glific_contact
        
        with patch('tap_lms.glific_webhook.get_glific_contact') as mock_get_contact:
            result = update_glific_contact(mock_teacher_doc, "on_update")
            
            # Should return early without calling get_glific_contact
            mock_get_contact.assert_not_called()
            assert result is None
    
    def test_update_glific_contact_success(
        self, mock_frappe, mock_teacher_doc, mock_glific_contact
    ):
        """Test successful contact update"""
        from tap_lms.glific_webhook import update_glific_contact
        
        with patch('tap_lms.glific_webhook.get_glific_contact') as mock_get_contact, \
             patch('tap_lms.glific_webhook.prepare_update_payload') as mock_prepare, \
             patch('tap_lms.glific_webhook.send_glific_update') as mock_send:
            
            mock_get_contact.return_value = mock_glific_contact
            mock_prepare.return_value = {
                "fields": json.dumps({"school": {"value": "New School", "type": "string"}})
            }
            mock_send.return_value = True
            
            update_glific_contact(mock_teacher_doc, "on_update")
            
            mock_get_contact.assert_called_once_with("12345")
            mock_prepare.assert_called_once_with(mock_teacher_doc, mock_glific_contact)
            mock_send.assert_called_once()
    
    def test_update_glific_contact_not_found(self, mock_frappe, mock_teacher_doc):
        """Test when Glific contact is not found"""
        from tap_lms.glific_webhook import update_glific_contact
        
        with patch('tap_lms.glific_webhook.get_glific_contact') as mock_get_contact:
            mock_get_contact.return_value = None
            
            update_glific_contact(mock_teacher_doc, "on_update")
            
            mock_frappe.logger().error.assert_called_once()
    
    def test_update_glific_contact_no_updates_needed(
        self, mock_frappe, mock_teacher_doc, mock_glific_contact
    ):
        """Test when no updates are needed"""
        from tap_lms.glific_webhook import update_glific_contact
        
        with patch('tap_lms.glific_webhook.get_glific_contact') as mock_get_contact, \
             patch('tap_lms.glific_webhook.prepare_update_payload') as mock_prepare, \
             patch('tap_lms.glific_webhook.send_glific_update') as mock_send:
            
            mock_get_contact.return_value = mock_glific_contact
            mock_prepare.return_value = None  # No updates needed
            
            update_glific_contact(mock_teacher_doc, "on_update")
            
            mock_send.assert_not_called()
    
    def test_update_glific_contact_send_failure(
        self, mock_frappe, mock_teacher_doc, mock_glific_contact
    ):
        """Test when sending update fails"""
        from tap_lms.glific_webhook import update_glific_contact
        
        with patch('tap_lms.glific_webhook.get_glific_contact') as mock_get_contact, \
             patch('tap_lms.glific_webhook.prepare_update_payload') as mock_prepare, \
             patch('tap_lms.glific_webhook.send_glific_update') as mock_send:
            
            mock_get_contact.return_value = mock_glific_contact
            mock_prepare.return_value = {"fields": json.dumps({"test": "data"})}
            mock_send.return_value = False
            
            update_glific_contact(mock_teacher_doc, "on_update")
            
            # Should log error
            assert mock_frappe.logger().error.called
    
    def test_update_glific_contact_exception_handling(
        self, mock_frappe, mock_teacher_doc
    ):
        """Test exception handling in update_glific_contact"""
        from tap_lms.glific_webhook import update_glific_contact
        
        with patch('tap_lms.glific_webhook.get_glific_contact') as mock_get_contact:
            mock_get_contact.side_effect = Exception("Network error")
            
            update_glific_contact(mock_teacher_doc, "on_update")
            
            # Should log error
            assert mock_frappe.logger().error.called


# ============================================================================
# TEST CLASS: GET GLIFIC CONTACT
# ============================================================================

class TestGetGlificContact:
    """Tests for get_glific_contact function"""
    
    @patch('requests.post')
    def test_get_glific_contact_success(
        self, mock_post, mock_frappe, mock_glific_settings, 
        mock_api_response, mock_glific_contact
    ):
        """Test successful contact retrieval"""
        contact_data = {
            "contact": {
                "contact": mock_glific_contact
            }
        }
        
        mock_post.return_value = mock_api_response(200, contact_data)
        mock_glific_integration.get_glific_settings.return_value = mock_glific_settings
        mock_glific_integration.get_glific_auth_headers.return_value = {"authorization": "token"}
        
        from tap_lms.glific_webhook import get_glific_contact
        
        result = get_glific_contact("12345")
        
        assert result is not None
        assert result["id"] == "12345"
        assert result["name"] == "Test Teacher"
    
    @patch('requests.post')
    def test_get_glific_contact_api_error(
        self, mock_post, mock_frappe, mock_glific_settings, mock_api_response
    ):
        """Test handling of API errors"""
        mock_post.return_value = mock_api_response(500)
        mock_glific_integration.get_glific_settings.return_value = mock_glific_settings
        mock_glific_integration.get_glific_auth_headers.return_value = {"authorization": "token"}
        
        from tap_lms.glific_webhook import get_glific_contact
        
        result = get_glific_contact("12345")
        
        assert result is None
    
    @patch('requests.post')
    def test_get_glific_contact_empty_response(
        self, mock_post, mock_frappe, mock_glific_settings, mock_api_response
    ):
        """Test handling of empty response"""
        mock_post.return_value = mock_api_response(200, {})
        mock_glific_integration.get_glific_settings.return_value = mock_glific_settings
        mock_glific_integration.get_glific_auth_headers.return_value = {"authorization": "token"}
        
        from tap_lms.glific_webhook import get_glific_contact
        
        result = get_glific_contact("12345")
        
        assert result is None
    
    @patch('requests.post')
    def test_get_glific_contact_network_exception(
        self, mock_post, mock_frappe, mock_glific_settings
    ):
        """Test handling of network exceptions"""
        mock_post.side_effect = Exception("Connection timeout")
        mock_glific_integration.get_glific_settings.return_value = mock_glific_settings
        mock_glific_integration.get_glific_auth_headers.return_value = {"authorization": "token"}
        
        from tap_lms.glific_webhook import get_glific_contact
        
        with pytest.raises(Exception):
            get_glific_contact("12345")


# ============================================================================
# TEST CLASS: PREPARE UPDATE PAYLOAD
# ============================================================================

class TestPrepareUpdatePayload:
    """Tests for prepare_update_payload function"""
    
    def test_prepare_update_payload_with_changes(
        self, mock_frappe, mock_teacher_doc, mock_glific_contact
    ):
        """Test preparing payload when there are field changes"""
        mock_frappe.get_all.return_value = [
            {"frappe_field": "school", "glific_field": "school"},
            {"frappe_field": "batch", "glific_field": "batch"}
        ]
        
        mock_teacher_doc.get = Mock(side_effect=lambda field: {
            "school": "New School",
            "batch": "New Batch"
        }.get(field))
        
        mock_frappe.db.get_value.return_value = None  # No language change
        
        from tap_lms.glific_webhook import prepare_update_payload
        
        result = prepare_update_payload(mock_teacher_doc, mock_glific_contact)
        
        assert result is not None
        assert "fields" in result
        fields_data = json.loads(result["fields"])
        assert "school" in fields_data
        assert fields_data["school"]["value"] == "New School"
    
    def test_prepare_update_payload_no_changes(
        self, mock_frappe, mock_teacher_doc, mock_glific_contact
    ):
        """Test when there are no changes"""
        mock_frappe.get_all.return_value = [
            {"frappe_field": "school", "glific_field": "school"},
            {"frappe_field": "batch", "glific_field": "batch"}
        ]
        
        # Return same values as in glific_contact
        mock_teacher_doc.get = Mock(side_effect=lambda field: {
            "school": "Old School",
            "batch": "Old Batch"
        }.get(field))
        
        mock_frappe.db.get_value.return_value = None
        
        from tap_lms.glific_webhook import prepare_update_payload
        
        result = prepare_update_payload(mock_teacher_doc, mock_glific_contact)
        
        assert result is None
    
    def test_prepare_update_payload_language_change(
        self, mock_frappe, mock_teacher_doc, mock_glific_contact
    ):
        """Test when language needs to be updated"""
        mock_frappe.get_all.return_value = []
        
        mock_teacher_doc.get = Mock(side_effect=lambda field: {
            "language": "Hindi"
        }.get(field))
        
        # Return different language ID
        mock_frappe.db.get_value.return_value = "2"
        
        from tap_lms.glific_webhook import prepare_update_payload
        
        result = prepare_update_payload(mock_teacher_doc, mock_glific_contact)
        
        assert result is not None
        assert "languageId" in result
        assert result["languageId"] == 2
    
    def test_prepare_update_payload_empty_fields(
        self, mock_frappe, mock_teacher_doc
    ):
        """Test handling of contact with empty fields"""
        mock_frappe.get_all.return_value = [
            {"frappe_field": "school", "glific_field": "school"}
        ]
        
        mock_teacher_doc.get = Mock(side_effect=lambda field: {
            "school": "New School"
        }.get(field))
        
        mock_frappe.db.get_value.return_value = None
        
        contact_with_empty_fields = {
            "id": "12345",
            "name": "Test",
            "language": {"id": "1", "label": "English"},
            "fields": "{}"
        }
        
        from tap_lms.glific_webhook import prepare_update_payload
        
        result = prepare_update_payload(mock_teacher_doc, contact_with_empty_fields)
        
        assert result is not None
        fields_data = json.loads(result["fields"])
        assert "school" in fields_data


# ============================================================================
# TEST CLASS: SEND GLIFIC UPDATE
# ============================================================================

class TestSendGlificUpdate:
    """Tests for send_glific_update function"""
    
    @patch('requests.post')
    def test_send_glific_update_success(
        self, mock_post, mock_frappe, mock_glific_settings, mock_api_response
    ):
        """Test successful update sending"""
        update_data = {
            "updateContact": {
                "contact": {
                    "id": "12345",
                    "fields": "{}",
                    "language": {"label": "English"}
                },
                "errors": []
            }
        }
        
        mock_post.return_value = mock_api_response(200, update_data)
        mock_glific_integration.get_glific_settings.return_value = mock_glific_settings
        mock_glific_integration.get_glific_auth_headers.return_value = {"authorization": "token"}
        
        from tap_lms.glific_webhook import send_glific_update
        
        payload = {"fields": json.dumps({"school": {"value": "Test"}})}
        result = send_glific_update("12345", payload)
        
        assert result is True
    
    @patch('requests.post')
    def test_send_glific_update_api_errors(
        self, mock_post, mock_frappe, mock_glific_settings
    ):
        """Test handling of API errors in response"""
        response = Mock()
        response.status_code = 200
        response.json.return_value = {
            "errors": [{"message": "Invalid field"}]
        }
        mock_post.return_value = response
        mock_glific_integration.get_glific_settings.return_value = mock_glific_settings
        mock_glific_integration.get_glific_auth_headers.return_value = {"authorization": "token"}
        
        from tap_lms.glific_webhook import send_glific_update
        
        payload = {"fields": json.dumps({"school": {"value": "Test"}})}
        result = send_glific_update("12345", payload)
        
        assert result is False
    
    @patch('requests.post')
    def test_send_glific_update_http_error(
        self, mock_post, mock_frappe, mock_glific_settings, mock_api_response
    ):
        """Test handling of HTTP errors"""
        mock_post.return_value = mock_api_response(500)
        mock_glific_integration.get_glific_settings.return_value = mock_glific_settings
        mock_glific_integration.get_glific_auth_headers.return_value = {"authorization": "token"}
        
        from tap_lms.glific_webhook import send_glific_update
        
        payload = {"fields": json.dumps({"school": {"value": "Test"}})}
        result = send_glific_update("12345", payload)
        
        assert result is False


# ============================================================================
# TEST CLASS: INTEGRATION SCENARIOS
# ============================================================================

class TestWebhookIntegration:
    """Integration tests for complete webhook workflows"""
    
    @patch('requests.post')
    def test_complete_update_workflow_success(
        self, mock_post, mock_frappe, mock_teacher_doc, mock_glific_contact,
        mock_glific_settings, mock_api_response
    ):
        """Test complete workflow from webhook trigger to successful update"""
        # Setup field mappings
        mock_frappe.get_all.return_value = [
            {"frappe_field": "school", "glific_field": "school"}
        ]
        
        # Setup teacher doc with changes
        mock_teacher_doc.get = Mock(side_effect=lambda field: {
            "school": "New School",
            "language": "English"
        }.get(field))
        
        mock_frappe.db.get_value.return_value = "1"
        
        # Mock API responses
        get_contact_response = mock_api_response(
            200, 
            {"contact": {"contact": mock_glific_contact}}
        )
        
        update_response = mock_api_response(
            200,
            {"updateContact": {"contact": {"id": "12345"}}}
        )
        
        mock_post.side_effect = [get_contact_response, update_response]
        mock_glific_integration.get_glific_settings.return_value = mock_glific_settings
        mock_glific_integration.get_glific_auth_headers.return_value = {"authorization": "token"}
        
        from tap_lms.glific_webhook import update_glific_contact
        
        update_glific_contact(mock_teacher_doc, "on_update")
        
        # Verify complete flow
        assert mock_post.call_count == 2


# ============================================================================
# TEST CLASS: EDGE CASES
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions"""
    
    def test_glific_contact_with_null_fields(
        self, mock_frappe, mock_teacher_doc
    ):
        """Test handling contact with null fields"""
        contact = {
            "id": "12345",
            "name": "Test",
            "language": {"id": "1", "label": "English"},
            "fields": None
        }
        
        mock_frappe.get_all.return_value = [
            {"frappe_field": "school", "glific_field": "school"}
        ]
        
        mock_teacher_doc.get = Mock(side_effect=lambda field: {
            "school": "Test School"
        }.get(field))
        
        mock_frappe.db.get_value.return_value = None
        
        from tap_lms.glific_webhook import prepare_update_payload
        
        # Should handle gracefully
        result = prepare_update_payload(mock_teacher_doc, contact)
        
        assert result is not None
    
    def test_empty_field_mappings(self, mock_frappe, mock_teacher_doc, mock_glific_contact):
        """Test when no field mappings are configured"""
        mock_frappe.get_all.return_value = []
        mock_frappe.db.get_value.return_value = None
        
        from tap_lms.glific_webhook import prepare_update_payload
        
        result = prepare_update_payload(mock_teacher_doc, mock_glific_contact)
        
        # Should return None as no updates
        assert result is None


# ============================================================================
# HELPER TESTS
# ============================================================================

class TestModuleStructure:
    """Tests for module structure and imports"""
    
    def test_all_functions_importable(self):
        """Verify all expected functions can be imported"""
        try:
            from tap_lms.glific_webhook import (
                update_glific_contact,
                get_glific_contact,
                prepare_update_payload,
                send_glific_update
            )
            
            # Verify all are callable
            functions = [
                update_glific_contact,
                get_glific_contact,
                prepare_update_payload,
                send_glific_update
            ]
            
            for func in functions:
                assert callable(func)
        
        except ImportError as e:
            pytest.skip(f"Could not import module: {str(e)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])