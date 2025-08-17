import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta
import json

# Add the parent directory to Python path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

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

# Test get_glific_settings
def test_get_glific_settings(mock_frappe):
    """Test get_glific_settings function"""
    try:
        from glific_integration import get_glific_settings
    except ImportError as e:
        pytest.skip(f"Could not import module: {e}")
    
    mock_settings = Mock()
    mock_frappe.get_single.return_value = mock_settings
    
    result = get_glific_settings()
    
    mock_frappe.get_single.assert_called_once_with("Glific Settings")
    assert result == mock_settings

# Test get_glific_auth_headers - valid token
def test_get_glific_auth_headers_valid_token(mock_frappe):
    """Test get_glific_auth_headers with valid non-expired token"""
    try:
        from glific_integration import get_glific_auth_headers
    except ImportError as e:
        pytest.skip(f"Could not import module: {e}")
    
    mock_settings = Mock()
    mock_settings.access_token = "valid_token"
    mock_settings.token_expiry_time = datetime.now(timezone.utc) + timedelta(hours=1)
    mock_frappe.get_single.return_value = mock_settings
    
    result = get_glific_auth_headers()
    
    expected = {
        "authorization": "valid_token",
        "Content-Type": "application/json"
    }
    assert result == expected

# Test get_glific_auth_headers - timezone replacement
def test_get_glific_auth_headers_timezone_replacement(mock_frappe):
    """Test get_glific_auth_headers with timezone-naive datetime that needs timezone replacement"""
    try:
        from glific_integration import get_glific_auth_headers
    except ImportError as e:
        pytest.skip(f"Could not import module: {e}")

    mock_settings = Mock()
    mock_settings.access_token = "valid_token"
    # Timezone-naive datetime - should trigger line 19
    mock_settings.token_expiry_time = datetime(2025, 12, 31, 23, 59, 59)
    mock_frappe.get_single.return_value = mock_settings

    result = get_glific_auth_headers()

    # Should add timezone and return valid token
    assert result == {
        "authorization": "valid_token",
        "Content-Type": "application/json"
    }

# Test get_glific_auth_headers - string token expiry
def test_get_glific_auth_headers_string_token_expiry(mock_frappe):
    """Test get_glific_auth_headers with string token_expiry_time"""
    try:
        from glific_integration import get_glific_auth_headers
    except ImportError as e:
        pytest.skip(f"Could not import module: {e}")

    with patch('glific_integration.isoparse') as mock_isoparse:
        mock_settings = Mock()
        mock_settings.access_token = "valid_token"
        mock_settings.token_expiry_time = "2025-12-31T23:59:59Z"  # String format
        
        # Mock isoparse to return a timezone-aware datetime
        parsed_datetime = datetime(2025, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        mock_isoparse.return_value = parsed_datetime
        
        mock_frappe.get_single.return_value = mock_settings
        
        result = get_glific_auth_headers()
        
        mock_isoparse.assert_called_once_with("2025-12-31T23:59:59Z")
        assert result == {
            "authorization": "valid_token",
            "Content-Type": "application/json"
        }

# Test get_glific_auth_headers - expired token refresh
def test_get_glific_auth_headers_expired_token(mock_frappe):
    """Test get_glific_auth_headers when token is expired - should refresh"""
    try:
        from glific_integration import get_glific_auth_headers
    except ImportError as e:
        pytest.skip(f"Could not import module: {e}")

    with patch('glific_integration.requests') as mock_requests, \
         patch('glific_integration.isoparse') as mock_isoparse:
        
        mock_settings = Mock()
        mock_settings.access_token = "expired_token"
        mock_settings.token_expiry_time = datetime.now(timezone.utc) - timedelta(hours=1)
        mock_settings.api_url = "https://api.glific.com"
        mock_settings.phone_number = "1234567890"
        mock_settings.password = "password"
        mock_settings.name = "settings_name"
        mock_frappe.get_single.return_value = mock_settings
        
        # Mock isoparse for token expiry parsing
        mock_isoparse.return_value = datetime.now(timezone.utc) + timedelta(hours=1)
        
        # Mock successful auth response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "access_token": "new_token",
                "renewal_token": "new_renewal",
                "token_expiry_time": "2025-12-31T23:59:59Z"
            }
        }
        mock_requests.post.return_value = mock_response
        
        result = get_glific_auth_headers()
        
        expected = {
            "authorization": "new_token",
            "Content-Type": "application/json"
        }
        assert result == expected

# Test get_glific_auth_headers - authentication failure
def test_get_glific_auth_headers_auth_failure(mock_frappe):
    """Test get_glific_auth_headers when authentication fails"""
    try:
        from glific_integration import get_glific_auth_headers
    except ImportError as e:
        pytest.skip(f"Could not import module: {e}")

    with patch('glific_integration.requests') as mock_requests:
        mock_settings = Mock()
        mock_settings.access_token = None
        mock_settings.token_expiry_time = None
        mock_settings.api_url = "https://api.glific.com"
        mock_settings.phone_number = "1234567890"
        mock_settings.password = "password"
        mock_frappe.get_single.return_value = mock_settings
        
        # Mock failed auth response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_requests.post.return_value = mock_response
        
        with pytest.raises(Exception):
            get_glific_auth_headers()

# Test create_contact - success
def test_create_contact_success(mock_frappe):
    """Test create_contact function with successful response"""
    try:
        from glific_integration import create_contact
    except ImportError as e:
        pytest.skip(f"Could not import module: {e}")
    
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
        
        result = create_contact("Test User", "1234567890", "Test School", "Test Model", "1", "batch123")
        
        assert result is not None
        assert result["id"] == "123"
        assert result["name"] == "Test User"

# Test create_contact - with errors
def test_create_contact_with_errors(mock_frappe):
    """Test create_contact function with API errors"""
    try:
        from glific_integration import create_contact
    except ImportError as e:
        pytest.skip(f"Could not import module: {e}")
    
    with patch('glific_integration.requests') as mock_requests, \
         patch('glific_integration.get_glific_settings') as mock_get_settings, \
         patch('glific_integration.get_glific_auth_headers') as mock_get_headers:
        
        mock_settings = Mock()
        mock_settings.api_url = "https://api.glific.com"
        mock_get_settings.return_value = mock_settings
        mock_get_headers.return_value = {"authorization": "token"}
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "error"
        mock_response.json.return_value = {
            "errors": [{"message": "Contact creation failed"}]
        }
        mock_requests.post.return_value = mock_response
        
        mock_frappe.logger.return_value.info = Mock()
        mock_frappe.logger.return_value.error = Mock()
        
        result = create_contact("Test User", "1234567890", "Test School", "Test Model", "1", "batch123")
        
        assert result is None

# Test create_contact - unexpected response structure
def test_create_contact_unexpected_response_structure(mock_frappe):
    """Test create_contact when response structure is unexpected"""
    try:
        from glific_integration import create_contact
    except ImportError as e:
        pytest.skip(f"Could not import module: {e}")

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
        
        result = create_contact("Test Name", "919876543210", "Test School", "Test Model", "1", "batch1")
        
        assert result is None

# Test create_contact - bad status code
def test_create_contact_bad_status_code(mock_frappe):
    """Test create_contact when API returns bad status code"""
    try:
        from glific_integration import create_contact
    except ImportError as e:
        pytest.skip(f"Could not import module: {e}")

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
        
        result = create_contact("Test Name", "919876543210", "Test School", "Test Model", "1", "batch1")
        
        assert result is None

# Test update_contact_fields - success
def test_update_contact_fields_success(mock_frappe):
    """Test update_contact_fields function with success"""
    try:
        from glific_integration import update_contact_fields
    except ImportError as e:
        pytest.skip(f"Could not import module: {e}")
    
    with patch('glific_integration.requests') as mock_requests, \
         patch('glific_integration.get_glific_settings') as mock_get_settings, \
         patch('glific_integration.get_glific_auth_headers') as mock_get_headers:
        
        mock_settings = Mock()
        mock_settings.api_url = "https://api.glific.com"
        mock_get_settings.return_value = mock_settings
        mock_get_headers.return_value = {"authorization": "token"}
        
        # Mock fetch response
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
        
        # Mock update response
        update_response = Mock()
        update_response.status_code = 200
        update_response.text = "success"
        update_response.raise_for_status = Mock()
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
        
        mock_requests.post.side_effect = [fetch_response, update_response]
        mock_requests.exceptions = Mock()
        mock_requests.exceptions.RequestException = Exception
        
        mock_frappe.logger.return_value.info = Mock()
        
        result = update_contact_fields("123", {"new_field": "new_value"})
        
        assert result is True

# Test update_contact_fields - JSON decode error
def test_update_contact_fields_json_decode_error_complete(mock_frappe):
    """Test update_contact_fields JSON decode error - covers lines 180-182"""
    try:
        from glific_integration import update_contact_fields
    except ImportError as e:
        pytest.skip(f"Could not import module: {e}")

    with patch('glific_integration.requests') as mock_requests, \
         patch('glific_integration.get_glific_settings') as mock_get_settings, \
         patch('glific_integration.get_glific_auth_headers') as mock_get_headers:

        mock_get_settings.return_value = Mock(api_url="https://api.glific.com")
        mock_get_headers.return_value = {"authorization": "token"}

        # Mock fetch response with invalid JSON that will cause decode error
        fetch_response = Mock()
        fetch_response.status_code = 200
        fetch_response.raise_for_status = Mock()
        fetch_response.json.return_value = {
            "data": {
                "contact": {
                    "contact": {
                        "id": "123",
                        "name": "Test User",
                        "fields": "not valid json"  # This will fail json.loads()
                    }
                }
            }
        }

        # Mock successful update response
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

        result = update_contact_fields("123", {"new_field": "new_value"})

        # Should succeed despite JSON error (sets existing_fields = {} and continues)
        assert result is True

# Test update_contact_fields - contact not found
def test_update_contact_fields_contact_not_found(mock_frappe):
    """Test update_contact_fields when contact is not found"""
    try:
        from glific_integration import update_contact_fields
    except ImportError as e:
        pytest.skip(f"Could not import module: {e}")

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
        
        result = update_contact_fields("123", {"new_field": "new_value"})
        
        assert result is False

# Test update_contact_fields - fetch errors
def test_update_contact_fields_fetch_errors(mock_frappe):
    """Test update_contact_fields when fetching contact fails with GraphQL errors"""
    try:
        from glific_integration import update_contact_fields
    except ImportError as e:
        pytest.skip(f"Could not import module: {e}")

    with patch('glific_integration.requests') as mock_requests, \
         patch('glific_integration.get_glific_settings') as mock_get_settings, \
         patch('glific_integration.get_glific_auth_headers') as mock_get_headers:

        mock_get_settings.return_value = Mock(api_url="https://api.glific.com")
        mock_get_headers.return_value = {"authorization": "token"}
        
        fetch_response = Mock()
        fetch_response.status_code = 200
        fetch_response.raise_for_status = Mock()
        fetch_response.json.return_value = {
            "errors": [{"message": "Contact not found"}]
        }
        
        mock_requests.post.return_value = fetch_response
        mock_requests.exceptions = Mock()
        mock_requests.exceptions.RequestException = Exception
        
        mock_frappe.logger.return_value.error = Mock()
        
        result = update_contact_fields("123", {"new_field": "new_value"})
        
        assert result is False

# Test update_contact_fields - update errors
def test_update_contact_fields_update_errors(mock_frappe):
    """Test update_contact_fields when update operation returns errors"""
    try:
        from glific_integration import update_contact_fields
    except ImportError as e:
        pytest.skip(f"Could not import module: {e}")

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
        
        result = update_contact_fields("123", {"new_field": "new_value"})
        
        assert result is False

# Test update_contact_fields - update no contact
def test_update_contact_fields_update_no_contact(mock_frappe):
    """Test update_contact_fields when update response doesn't contain contact"""
    try:
        from glific_integration import update_contact_fields
    except ImportError as e:
        pytest.skip(f"Could not import module: {e}")

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
        
        result = update_contact_fields("123", {"new_field": "new_value"})
        
        assert result is False

# Test update_contact_fields - request exception
def test_update_contact_fields_request_exception(mock_frappe):
    """Test update_contact_fields when request exception occurs"""
    try:
        from glific_integration import update_contact_fields
    except ImportError as e:
        pytest.skip(f"Could not import module: {e}")

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
        
        result = update_contact_fields("123", {"new_field": "new_value"})
        
        assert result is False

# Test update_contact_fields - general exception
def test_update_contact_fields_general_exception(mock_frappe):
    """Test update_contact_fields when general exception occurs"""
    try:
        from glific_integration import update_contact_fields
    except ImportError as e:
        pytest.skip(f"Could not import module: {e}")

    mock_frappe.logger.return_value.error = Mock()

    # Patch to raise exception during execution
    with patch('glific_integration.requests.post') as mock_post:
        mock_post.side_effect = Exception("General error")
        
        result = update_contact_fields("123", {"new_field": "new_value"})
        
        assert result is False

# Test get_contact_by_phone - success
def test_get_contact_by_phone_success(mock_frappe):
    """Test get_contact_by_phone function with success"""
    try:
        from glific_integration import get_contact_by_phone
    except ImportError as e:
        pytest.skip(f"Could not import module: {e}")
    
    with patch('glific_integration.requests') as mock_requests, \
         patch('glific_integration.get_glific_settings') as mock_get_settings, \
         patch('glific_integration.get_glific_auth_headers') as mock_get_headers:
        
        mock_get_settings.return_value = Mock(api_url="https://api.glific.com")
        mock_get_headers.return_value = {"authorization": "token"}
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "contactByPhone": {
                    "contact": {
                        "id": "123",
                        "name": "Test User",
                        "phone": "1234567890"
                    }
                }
            }
        }
        mock_requests.post.return_value = mock_response
        
        result = get_contact_by_phone("1234567890")
        
        assert result is not None
        assert result["id"] == "123"

# Test get_contact_by_phone - not found
def test_get_contact_by_phone_not_found(mock_frappe):
    """Test get_contact_by_phone function when contact not found"""
    try:
        from glific_integration import get_contact_by_phone
    except ImportError as e:
        pytest.skip(f"Could not import module: {e}")
    
    with patch('glific_integration.requests') as mock_requests, \
         patch('glific_integration.get_glific_settings') as mock_get_settings, \
         patch('glific_integration.get_glific_auth_headers') as mock_get_headers:
        
        mock_get_settings.return_value = Mock(api_url="https://api.glific.com")
        mock_get_headers.return_value = {"authorization": "token"}
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "contactByPhone": {
                    "contact": None
                }
            }
        }
        mock_requests.post.return_value = mock_response
        
        result = get_contact_by_phone("1234567890")
        
        assert result is None

# Test get_contact_by_phone - API errors
def test_get_contact_by_phone_api_errors(mock_frappe):
    """Test get_contact_by_phone when API returns errors"""
    try:
        from glific_integration import get_contact_by_phone
    except ImportError as e:
        pytest.skip(f"Could not import module: {e}")

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
        
        result = get_contact_by_phone("919876543210")
        
        assert result is None

# Test optin_contact - success
def test_optin_contact_success(mock_frappe):
    """Test optin_contact function with success"""
    try:
        from glific_integration import optin_contact
    except ImportError as e:
        pytest.skip(f"Could not import module: {e}")
    
    with patch('glific_integration.requests') as mock_requests, \
         patch('glific_integration.get_glific_settings') as mock_get_settings, \
         patch('glific_integration.get_glific_auth_headers') as mock_get_headers:
        
        mock_get_settings.return_value = Mock(api_url="https://api.glific.com")
        mock_get_headers.return_value = {"authorization": "token"}
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "optinContact": {
                    "contact": {
                        "id": "123",
                        "phone": "1234567890",
                        "name": "Test User"
                    }
                }
            }
        }
        mock_requests.post.return_value = mock_response
        
        result = optin_contact("1234567890", "Test User")
        
        assert result is True

# Test add_student_to_glific_for_onboarding - with existing contact
def test_add_student_to_glific_for_onboarding_existing_contact(mock_frappe):
    """Test add_student_to_glific_for_onboarding with existing contact"""
    try:
        from glific_integration import add_student_to_glific_for_onboarding
    except ImportError as e:
        pytest.skip(f"Could not import module: {e}")
    
    with patch('glific_integration.get_contact_by_phone') as mock_get_contact, \
         patch('glific_integration.optin_contact') as mock_optin, \
         patch('glific_integration.add_contact_to_group') as mock_add_to_group, \
         patch('glific_integration.update_contact_fields') as mock_update:
        
        # Mock existing contact
        mock_get_contact.return_value = {
            "id": "contact123",
            "bspStatus": "NONE"
        }
        mock_optin.return_value = True
        mock_add_to_group.return_value = True
        mock_update.return_value = True
        
        result = add_student_to_glific_for_onboarding(
            "Test Student", "9876543210", "Test School", "Test Batch", 
            "group123", "1", "Level 1", "Math", "Grade 5"
        )
        
        assert result is not None
        assert result["id"] == "contact123"

# Test add_student_to_glific_for_onboarding - invalid phone
def test_add_student_to_glific_for_onboarding_invalid_phone(mock_frappe):
    """Test add_student_to_glific_for_onboarding with invalid phone"""
    try:
        from glific_integration import add_student_to_glific_for_onboarding
    except ImportError as e:
        pytest.skip(f"Could not import module: {e}")
    
    result = add_student_to_glific_for_onboarding(
        "Test Student", "invalid_phone", "Test School", "Test Batch", 
        "group123", "1", "Level 1", "Math", "Grade 5"
    )
    
    assert result is None

# Test add_student_to_glific_for_onboarding - new contact creation
def test_add_student_to_glific_for_onboarding_new_contact(mock_frappe):
    """Test add_student_to_glific_for_onboarding creating new contact"""
    try:
        from glific_integration import add_student_to_glific_for_onboarding
    except ImportError as e:
        pytest.skip(f"Could not import module: {e}")
    
    with patch('glific_integration.get_contact_by_phone') as mock_get_contact, \
         patch('glific_integration.optin_contact') as mock_optin, \
         patch('glific_integration.add_contact_to_group') as mock_add_to_group, \
         patch('glific_integration.requests') as mock_requests, \
         patch('glific_integration.get_glific_settings') as mock_get_settings, \
         patch('glific_integration.get_glific_auth_headers') as mock_get_headers:
        
        # Mock no existing contact
        mock_get_contact.return_value = None
        
        mock_settings = Mock()
        mock_settings.api_url = "https://api.glific.com"
        mock_get_settings.return_value = mock_settings
        mock_get_headers.return_value = {"authorization": "token"}
        
        # Mock successful contact creation
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "createContact": {
                    "contact": {
                        "id": "new_contact123",
                        "name": "Test Student",
                        "phone": "919876543210"
                    }
                }
            }
        }
        mock_requests.post.return_value = mock_response
        mock_optin.return_value = True
        mock_add_to_group.return_value = True
        
        result = add_student_to_glific_for_onboarding(
            "Test Student", "9876543210", "Test School", "Test Batch", 
            "group123", "1", "Level 1", "Math", "Grade 5"
        )
        
        assert result is not None
        assert result["id"] == "new_contact123"

# Test add_student_to_glific_for_onboarding - default language error
def test_add_student_to_glific_for_onboarding_default_language_error(mock_frappe):
    """Test add_student_to_glific_for_onboarding when getting default language fails"""
    try:
        from glific_integration import add_student_to_glific_for_onboarding
    except ImportError as e:
        pytest.skip(f"Could not import module: {e}")

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
        
        result = add_student_to_glific_for_onboarding(
            "Test Student", "9876543210", "Test School", "Test Batch", 
            "group123", language_id=None  # This will trigger default language lookup
        )
        
        assert result is not None

# Test add_student_to_glific_for_onboarding - invalid language_id
def test_add_student_to_glific_for_onboarding_invalid_language_id(mock_frappe):
    """Test add_student_to_glific_for_onboarding with invalid language_id"""
    try:
        from glific_integration import add_student_to_glific_for_onboarding
    except ImportError as e:
        pytest.skip(f"Could not import module: {e}")

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
        
        result = add_student_to_glific_for_onboarding(
            "Test Student", "9876543210", "Test School", "Test Batch", 
            "group123", language_id="invalid"  # Invalid language ID
        )
        
        # Should use default language_id = 1 when invalid
        assert result is not None

# Test add_student_to_glific_for_onboarding - optin error
def test_add_student_to_glific_for_onboarding_optin_error(mock_frappe):
    """Test add_student_to_glific_for_onboarding when optin fails"""
    try:
        from glific_integration import add_student_to_glific_for_onboarding
    except ImportError as e:
        pytest.skip(f"Could not import module: {e}")

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
        
        result = add_student_to_glific_for_onboarding(
            "Test Student", "9876543210", "Test School", "Test Batch", 
            "group123", language_id="1"
        )
        
        # Should still return contact even if opt-in fails
        assert result is not None