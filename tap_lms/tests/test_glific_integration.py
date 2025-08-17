import pytest
import sys
import os
from unittest.mock import Mock, patch
from datetime import datetime, timezone, timedelta
import json

# Add the exact path where glific_integration.py is located
sys.path.insert(0, '/home/frappe/frappe-bench/apps/tap_lms/tap_lms')

@pytest.fixture
def mock_frappe():
    """Mock frappe module with common methods"""
    with patch.dict('sys.modules', {
        'frappe': Mock(),
        'requests': Mock(),
        'json': Mock(),
        'datetime': Mock(),
        'dateutil': Mock(),
        'dateutil.parser': Mock(),
    }):
        mock_frappe = sys.modules['frappe']
        mock_frappe.get_single.return_value = Mock()
        mock_frappe.get_doc.return_value = Mock()
        mock_frappe.get_all.return_value = []
        mock_frappe.new_doc.return_value = Mock()
        mock_frappe.db = Mock()
        mock_frappe.logger.return_value = Mock()
        mock_frappe.throw = Mock(side_effect=Exception("Frappe throw"))
        mock_frappe.utils = Mock()
        mock_frappe.utils.now_datetime.return_value = datetime.now()
        yield mock_frappe

def test_get_glific_settings(mock_frappe):
    """Test get_glific_settings function"""
    import glific_integration
    
    mock_settings = Mock()
    mock_frappe.get_single.return_value = mock_settings
    
    result = glific_integration.get_glific_settings()
    
    mock_frappe.get_single.assert_called_once_with("Glific Settings")
    assert result == mock_settings

def test_get_glific_auth_headers_timezone_replacement(mock_frappe):
    """Test get_glific_auth_headers with timezone-naive datetime that needs timezone replacement"""
    import glific_integration

    mock_settings = Mock()
    mock_settings.access_token = "valid_token"
    mock_settings.token_expiry_time = datetime(2025, 12, 31, 23, 59, 59)
    mock_frappe.get_single.return_value = mock_settings

    result = glific_integration.get_glific_auth_headers()

    assert result == {
        "authorization": "valid_token",
        "Content-Type": "application/json"
    }

def test_update_contact_fields_json_decode_error_complete(mock_frappe):
    """Test update_contact_fields JSON decode error"""
    import glific_integration

    with patch('glific_integration.requests') as mock_requests, \
         patch('glific_integration.get_glific_settings') as mock_get_settings, \
         patch('glific_integration.get_glific_auth_headers') as mock_get_headers:

        mock_get_settings.return_value = Mock(api_url="https://api.glific.com")
        mock_get_headers.return_value = {"authorization": "token"}

        fetch_response = Mock()
        fetch_response.status_code = 200
        fetch_response.raise_for_status = Mock()
        fetch_response.json.return_value = {
            "data": {
                "contact": {
                    "contact": {
                        "id": "123",
                        "name": "Test User",
                        "fields": "not valid json"
                    }
                }
            }
        }

        update_response = Mock()
        update_response.status_code = 200
        update_response.raise_for_status = Mock()
        update_response.json.return_value = {
            "data": {
                "updateContact": {
                    "contact": {"id": "123", "name": "Test User"}
                }
            }
        }

        mock_requests.post.side_effect = [fetch_response, update_response]
        mock_requests.exceptions.RequestException = Exception

        mock_frappe.logger.return_value.error = Mock()
        mock_frappe.logger.return_value.info = Mock()

        result = glific_integration.update_contact_fields("123", {"new_field": "new_value"})
        assert result is True

def test_update_contact_fields_general_exception(mock_frappe):
    """Test update_contact_fields when general exception occurs"""
    import glific_integration

    mock_frappe.logger.return_value.error = Mock()

    with patch('glific_integration.requests.post') as mock_post:
        mock_post.side_effect = Exception("General error")
        
        result = glific_integration.update_contact_fields("123", {"new_field": "new_value"})
        assert result is False

def test_create_contact_success(mock_frappe):
    """Test create_contact function with successful response"""
    import glific_integration
    
    with patch('glific_integration.requests') as mock_requests, \
         patch('glific_integration.get_glific_settings') as mock_get_settings, \
         patch('glific_integration.get_glific_auth_headers') as mock_get_headers:
        
        mock_settings = Mock()
        mock_settings.api_url = "https://api.glific.com"
        mock_get_settings.return_value = mock_settings
        mock_get_headers.return_value = {"authorization": "token"}
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "success"
        mock_response.json.return_value = {
            "data": {
                "createContact": {
                    "contact": {
                        "id": "123",
                        "name": "Test User",
                        "phone": "1234567890"
                    }
                }
            }
        }
        mock_requests.post.return_value = mock_response
        
        mock_frappe.logger.return_value.info = Mock()
        
        result = glific_integration.create_contact("Test User", "1234567890", "Test School", "Test Model", "1", "batch123")
        
        assert result is not None
        assert result["id"] == "123"
        assert result["name"] == "Test User"

def test_create_contact_unexpected_response_structure(mock_frappe):
    """Test create_contact when response structure is unexpected"""
    import glific_integration

    with patch('glific_integration.requests') as mock_requests, \
         patch('glific_integration.get_glific_settings') as mock_get_settings, \
         patch('glific_integration.get_glific_auth_headers') as mock_get_headers:

        mock_get_settings.return_value = Mock(api_url="https://api.glific.com")
        mock_get_headers.return_value = {"authorization": "token"}
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "createContact": {}  # Missing contact field
            }
        }
        mock_response.text = '{"data": {"createContact": {}}}'
        mock_requests.post.return_value = mock_response
        
        mock_frappe.logger.return_value.info = Mock()
        mock_frappe.logger.return_value.error = Mock()
        
        result = glific_integration.create_contact("Test Name", "919876543210", "Test School", "Test Model", "1", "batch1")
        
        assert result is None

def test_create_contact_bad_status_code(mock_frappe):
    """Test create_contact when API returns bad status code"""
    import glific_integration

    with patch('glific_integration.requests') as mock_requests, \
         patch('glific_integration.get_glific_settings') as mock_get_settings, \
         patch('glific_integration.get_glific_auth_headers') as mock_get_headers:

        mock_get_settings.return_value = Mock(api_url="https://api.glific.com")
        mock_get_headers.return_value = {"authorization": "token"}
        
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_requests.post.return_value = mock_response
        
        mock_frappe.logger.return_value.info = Mock()
        mock_frappe.logger.return_value.error = Mock()
        
        result = glific_integration.create_contact("Test Name", "919876543210", "Test School", "Test Model", "1", "batch1")
        
        assert result is None

def test_update_contact_fields_contact_not_found(mock_frappe):
    """Test update_contact_fields when contact is not found"""
    import glific_integration

    with patch('glific_integration.requests') as mock_requests, \
         patch('glific_integration.get_glific_settings') as mock_get_settings, \
         patch('glific_integration.get_glific_auth_headers') as mock_get_headers:

        mock_get_settings.return_value = Mock(api_url="https://api.glific.com")
        mock_get_headers.return_value = {"authorization": "token"}
        
        fetch_response = Mock()
        fetch_response.status_code = 200
        fetch_response.raise_for_status = Mock()
        fetch_response.json.return_value = {
            "data": {
                "contact": {}  # Missing contact field
            }
        }
        
        mock_requests.post.return_value = fetch_response
        mock_requests.exceptions = Mock()
        mock_requests.exceptions.RequestException = Exception
        
        mock_frappe.logger.return_value.error = Mock()
        
        result = glific_integration.update_contact_fields("123", {"new_field": "new_value"})
        
        assert result is False

def test_update_contact_fields_update_errors(mock_frappe):
    """Test update_contact_fields when update operation returns errors"""
    import glific_integration

    with patch('glific_integration.requests') as mock_requests, \
         patch('glific_integration.get_glific_settings') as mock_get_settings, \
         patch('glific_integration.get_glific_auth_headers') as mock_get_headers:

        mock_get_settings.return_value = Mock(api_url="https://api.glific.com")
        mock_get_headers.return_value = {"authorization": "token"}
        
        # Mock successful fetch response
        fetch_response = Mock()
        fetch_response.status_code = 200
        fetch_response.raise_for_status = Mock()
        fetch_response.json.return_value = {
            "data": {
                "contact": {
                    "contact": {
                        "id": "123",
                        "name": "Test User",
                        "fields": '{"existing_field": {"value": "existing_value"}}'
                    }
                }
            }
        }
        
        # Mock update response with errors
        update_response = Mock()
        update_response.status_code = 200
        update_response.text = "error response"
        update_response.raise_for_status = Mock()
        update_response.json.return_value = {
            "errors": [{"message": "Update failed"}]
        }
        
        mock_requests.post.side_effect = [fetch_response, update_response]
        mock_requests.exceptions = Mock()
        mock_requests.exceptions.RequestException = Exception
        
        mock_frappe.logger.return_value.info = Mock()
        mock_frappe.logger.return_value.error = Mock()
        
        result = glific_integration.update_contact_fields("123", {"new_field": "new_value"})
        
        assert result is False

def test_update_contact_fields_update_no_contact(mock_frappe):
    """Test update_contact_fields when update response doesn't contain contact"""
    import glific_integration

    with patch('glific_integration.requests') as mock_requests, \
         patch('glific_integration.get_glific_settings') as mock_get_settings, \
         patch('glific_integration.get_glific_auth_headers') as mock_get_headers:

        mock_get_settings.return_value = Mock(api_url="https://api.glific.com")
        mock_get_headers.return_value = {"authorization": "token"}
        
        # Mock successful fetch response
        fetch_response = Mock()
        fetch_response.status_code = 200
        fetch_response.raise_for_status = Mock()
        fetch_response.json.return_value = {
            "data": {
                "contact": {
                    "contact": {
                        "id": "123",
                        "name": "Test User",
                        "fields": '{"existing_field": {"value": "existing_value"}}'
                    }
                }
            }
        }
        
        # Mock update response without contact data
        update_response = Mock()
        update_response.status_code = 200
        update_response.text = "success"
        update_response.raise_for_status = Mock()
        update_response.json.return_value = {
            "data": {
                "updateContact": {}  # Missing contact field
            }
        }
        
        mock_requests.post.side_effect = [fetch_response, update_response]
        mock_requests.exceptions = Mock()
        mock_requests.exceptions.RequestException = Exception
        
        mock_frappe.logger.return_value.info = Mock()
        mock_frappe.logger.return_value.error = Mock()
        
        result = glific_integration.update_contact_fields("123", {"new_field": "new_value"})
        
        assert result is False

def test_update_contact_fields_request_exception(mock_frappe):
    """Test update_contact_fields when request exception occurs"""
    import glific_integration

    with patch('glific_integration.requests') as mock_requests, \
         patch('glific_integration.get_glific_settings') as mock_get_settings, \
         patch('glific_integration.get_glific_auth_headers') as mock_get_headers:

        mock_get_settings.return_value = Mock(api_url="https://api.glific.com")
        mock_get_headers.return_value = {"authorization": "token"}
        
        # Mock request exception
        mock_requests.post.side_effect = Exception("Network error")
        mock_requests.exceptions = Mock()
        mock_requests.exceptions.RequestException = Exception
        
        mock_frappe.logger.return_value.error = Mock()
        
        result = glific_integration.update_contact_fields("123", {"new_field": "new_value"})
        
        assert result is False

def test_get_contact_by_phone_api_errors(mock_frappe):
    """Test get_contact_by_phone when API returns errors"""
    import glific_integration

    with patch('glific_integration.requests') as mock_requests, \
         patch('glific_integration.get_glific_settings') as mock_get_settings, \
         patch('glific_integration.get_glific_auth_headers') as mock_get_headers:

        mock_get_settings.return_value = Mock(api_url="https://api.glific.com")
        mock_get_headers.return_value = {"authorization": "token"}
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = {
            "errors": [{"message": "Contact lookup failed"}]
        }
        mock_requests.post.return_value = mock_response
        mock_requests.exceptions = Mock()
        mock_requests.exceptions.RequestException = Exception
        
        mock_frappe.logger.return_value.error = Mock()
        
        result = glific_integration.get_contact_by_phone("919876543210")
        
        assert result is None

def test_add_student_to_glific_for_onboarding_with_optional_fields(mock_frappe):
    """Test add_student_to_glific_for_onboarding with all optional fields"""
    import glific_integration

    with patch('glific_integration.get_contact_by_phone') as mock_get_contact, \
         patch('glific_integration.get_glific_settings') as mock_get_settings, \
         patch('glific_integration.get_glific_auth_headers') as mock_get_headers, \
         patch('glific_integration.requests') as mock_requests, \
         patch('glific_integration.optin_contact') as mock_optin, \
         patch('glific_integration.add_contact_to_group') as mock_add_to_group:

        # Mock no existing contact
        mock_get_contact.return_value = None
        
        mock_get_settings.return_value = Mock(api_url="https://api.glific.com")
        mock_get_headers.return_value = {"authorization": "token"}
        
        # Mock successful contact creation
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "createContact": {
                    "contact": {"id": "123", "name": "Test Student", "phone": "919876543210"}
                }
            }
        }
        mock_requests.post.return_value = mock_response
        
        mock_optin.return_value = True
        mock_add_to_group.return_value = True
        
        mock_frappe.logger.return_value.info = Mock()
        
        result = glific_integration.add_student_to_glific_for_onboarding(
            "Test Student", "9876543210", "Test School", "Test Batch", 
            "group123", language_id="2", course_level_name="Advanced", 
            course_vertical_name="Science", grade="10"
        )
        
        assert result is not None
        assert result["id"] == "123"

def test_add_student_to_glific_for_onboarding_default_language_error(mock_frappe):
    """Test add_student_to_glific_for_onboarding when getting default language fails"""
    import glific_integration

    with patch('glific_integration.get_contact_by_phone') as mock_get_contact, \
         patch('glific_integration.get_glific_settings') as mock_get_settings, \
         patch('glific_integration.get_glific_auth_headers') as mock_get_headers, \
         patch('glific_integration.requests') as mock_requests, \
         patch('glific_integration.optin_contact') as mock_optin, \
         patch('glific_integration.add_contact_to_group') as mock_add_to_group:

        # Mock no existing contact
        mock_get_contact.return_value = None
        
        mock_get_settings.return_value = Mock(api_url="https://api.glific.com")
        mock_get_headers.return_value = {"authorization": "token"}
        
        # Mock frappe.db.get_single_value to raise exception
        mock_frappe.db.get_single_value.side_effect = Exception("No default language")
        
        # Mock successful contact creation
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "createContact": {
                    "contact": {"id": "123", "name": "Test Student", "phone": "919876543210"}
                }
            }
        }
        mock_requests.post.return_value = mock_response
        
        mock_optin.return_value = True
        mock_add_to_group.return_value = True
        
        mock_frappe.logger.return_value.warning = Mock()
        mock_frappe.logger.return_value.info = Mock()
        
        result = glific_integration.add_student_to_glific_for_onboarding(
            "Test Student", "9876543210", "Test School", "Test Batch", 
            "group123", language_id=None  # This will trigger default language lookup
        )
        
        assert result is not None

def test_add_student_to_glific_for_onboarding_invalid_language_id(mock_frappe):
    """Test add_student_to_glific_for_onboarding with invalid language_id"""
    import glific_integration

    with patch('glific_integration.get_contact_by_phone') as mock_get_contact, \
         patch('glific_integration.get_glific_settings') as mock_get_settings, \
         patch('glific_integration.get_glific_auth_headers') as mock_get_headers, \
         patch('glific_integration.requests') as mock_requests, \
         patch('glific_integration.optin_contact') as mock_optin, \
         patch('glific_integration.add_contact_to_group') as mock_add_to_group:

        # Mock no existing contact
        mock_get_contact.return_value = None
        
        mock_get_settings.return_value = Mock(api_url="https://api.glific.com")
        mock_get_headers.return_value = {"authorization": "token"}
        
        # Mock successful contact creation
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "createContact": {
                    "contact": {"id": "123", "name": "Test Student", "phone": "919876543210"}
                }
            }
        }
        mock_requests.post.return_value = mock_response
        
        mock_optin.return_value = True
        mock_add_to_group.return_value = True
        
        mock_frappe.logger.return_value.warning = Mock()
        mock_frappe.logger.return_value.info = Mock()
        
        result = glific_integration.add_student_to_glific_for_onboarding(
            "Test Student", "9876543210", "Test School", "Test Batch", 
            "group123", language_id="invalid"  # Invalid language ID
        )
        
        # Should use default language_id = 1 when invalid
        assert result is not None

def test_add_student_to_glific_for_onboarding_optin_error(mock_frappe):
    """Test add_student_to_glific_for_onboarding when optin fails"""
    import glific_integration

    with patch('glific_integration.get_contact_by_phone') as mock_get_contact, \
         patch('glific_integration.get_glific_settings') as mock_get_settings, \
         patch('glific_integration.get_glific_auth_headers') as mock_get_headers, \
         patch('glific_integration.requests') as mock_requests, \
         patch('glific_integration.optin_contact') as mock_optin, \
         patch('glific_integration.add_contact_to_group') as mock_add_to_group:

        # Mock no existing contact
        mock_get_contact.return_value = None
        
        mock_get_settings.return_value = Mock(api_url="https://api.glific.com")
        mock_get_headers.return_value = {"authorization": "token"}
        
        # Mock successful contact creation
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "createContact": {
                    "contact": {"id": "123", "name": "Test Student", "phone": "919876543210"}
                }
            }
        }
        mock_requests.post.return_value = mock_response
        
        # Mock failed optin with exception
        mock_optin.side_effect = Exception("Optin failed")
        mock_add_to_group.return_value = True
        
        mock_frappe.logger.return_value.info = Mock()
        mock_frappe.logger.return_value.warning = Mock()
        
        result = glific_integration.add_student_to_glific_for_onboarding(
            "Test Student", "9876543210", "Test School", "Test Batch", 
            "group123", language_id="1"
        )
        
        # Should still return contact even if opt-in fails
        assert result is not None