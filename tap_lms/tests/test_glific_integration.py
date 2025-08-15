# import pytest
# import sys
# import os
# from unittest.mock import Mock, patch, MagicMock
# from datetime import datetime, timezone, timedelta
# import json

# # Add the parent directory to Python path for imports
# current_dir = os.path.dirname(os.path.abspath(__file__))
# parent_dir = os.path.dirname(current_dir)
# if parent_dir not in sys.path:
#     sys.path.insert(0, parent_dir)

# @pytest.fixture
# def mock_frappe():
#     """Mock frappe module with common methods"""
#     with patch.dict('sys.modules', {
#         'frappe': Mock(),
#         'requests': Mock(),
#         'json': Mock(),
#         'datetime': Mock(),
#         'dateutil': Mock(),
#         'dateutil.parser': Mock(),
#     }):
#         mock_frappe = sys.modules['frappe']
#         mock_frappe.get_single.return_value = Mock()
#         mock_frappe.get_doc.return_value = Mock()
#         mock_frappe.get_all.return_value = []
#         mock_frappe.new_doc.return_value = Mock()
#         mock_frappe.db = Mock()
#         mock_frappe.logger.return_value = Mock()
#         mock_frappe.throw = Mock(side_effect=Exception("Frappe throw"))
#         mock_frappe.utils = Mock()
#         mock_frappe.utils.now_datetime.return_value = datetime.now()
#         yield mock_frappe

# def test_get_glific_settings(mock_frappe):
#     """Test get_glific_settings function"""
    
#     try:
#         from glific_integration import get_glific_settings
#     except ImportError as e:
#         pytest.skip(f"Could not import module: {e}")
    
#     # Mock settings object
#     mock_settings = Mock()
#     mock_frappe.get_single.return_value = mock_settings
    
#     result = get_glific_settings()
    
#     mock_frappe.get_single.assert_called_once_with("Glific Settings")
#     assert result == mock_settings

# def test_get_glific_auth_headers_valid_token(mock_frappe):
#     """Test get_glific_auth_headers with valid non-expired token"""
    
#     try:
#         from glific_integration import get_glific_auth_headers
#     except ImportError as e:
#         pytest.skip(f"Could not import module: {e}")
    
#     with patch('glific_integration.datetime') as mock_datetime:
#         # Mock settings with valid token
#         mock_settings = Mock()
#         mock_settings.access_token = "valid_token"
#         mock_settings.token_expiry_time = datetime.now(timezone.utc) + timedelta(hours=1)
#         mock_frappe.get_single.return_value = mock_settings
        
#         # Mock datetime.now to return a consistent time
#         mock_datetime.now.return_value = datetime.now(timezone.utc)
#         mock_datetime.datetime = datetime  # For isinstance checks
        
#         result = get_glific_auth_headers()
        
#         expected = {
#             "authorization": "valid_token",
#             "Content-Type": "application/json"
#         }
#         assert result == expected

# def test_get_glific_auth_headers_expired_token(mock_frappe):
#     """Test get_glific_auth_headers with expired token - should refresh"""
    
#     try:
#         from glific_integration import get_glific_auth_headers
#     except ImportError as e:
#         pytest.skip(f"Could not import module: {e}")
    
#     with patch('glific_integration.requests') as mock_requests, \
#          patch('glific_integration.datetime') as mock_datetime, \
#          patch('glific_integration.isoparse') as mock_isoparse:
        
#         # Mock settings with expired token
#         mock_settings = Mock()
#         mock_settings.access_token = "expired_token"
#         mock_settings.token_expiry_time = datetime.now(timezone.utc) - timedelta(hours=1)
#         mock_settings.api_url = "https://api.glific.com"
#         mock_settings.phone_number = "1234567890"
#         mock_settings.password = "password"
#         mock_settings.name = "settings_name"
#         mock_frappe.get_single.return_value = mock_settings
        
#         # Mock datetime.now to return a consistent time
#         mock_datetime.now.return_value = datetime.now(timezone.utc)
#         mock_datetime.datetime = datetime
        
#         # Mock isoparse for token expiry parsing
#         mock_isoparse.return_value = datetime.now(timezone.utc) + timedelta(hours=1)
        
#         # Mock successful auth response
#         mock_response = Mock()
#         mock_response.status_code = 200
#         mock_response.json.return_value = {
#             "data": {
#                 "access_token": "new_token",
#                 "renewal_token": "new_renewal",
#                 "token_expiry_time": "2025-12-31T23:59:59Z"
#             }
#         }
#         mock_requests.post.return_value = mock_response
        
#         result = get_glific_auth_headers()
        
#         # Verify API call was made
#         mock_requests.post.assert_called_once()
        
#         # Verify database update
#         mock_frappe.db.set_value.assert_called_once()
#         mock_frappe.db.commit.assert_called_once()
        
#         expected = {
#             "authorization": "new_token",
#             "Content-Type": "application/json"
#         }
#         assert result == expected

# def test_get_glific_auth_headers_auth_failure(mock_frappe):
#     """Test get_glific_auth_headers when authentication fails"""
    
#     try:
#         from glific_integration import get_glific_auth_headers
#     except ImportError as e:
#         pytest.skip(f"Could not import module: {e}")
    
#     with patch('glific_integration.requests') as mock_requests:
#         # Mock settings with expired token
#         mock_settings = Mock()
#         mock_settings.access_token = None
#         mock_settings.token_expiry_time = None
#         mock_settings.api_url = "https://api.glific.com"
#         mock_settings.phone_number = "1234567890"
#         mock_settings.password = "password"
#         mock_frappe.get_single.return_value = mock_settings
        
#         # Mock failed auth response
#         mock_response = Mock()
#         mock_response.status_code = 401
#         mock_requests.post.return_value = mock_response
        
#         with pytest.raises(Exception):  # Should throw exception
#             get_glific_auth_headers()

# def test_create_contact_success(mock_frappe):
#     """Test create_contact function with successful response"""
    
#     try:
#         from glific_integration import create_contact
#     except ImportError as e:
#         pytest.skip(f"Could not import module: {e}")
    
#     with patch('glific_integration.requests') as mock_requests, \
#          patch('glific_integration.get_glific_settings') as mock_get_settings, \
#          patch('glific_integration.get_glific_auth_headers') as mock_get_headers:
        
#         # Mock dependencies
#         mock_settings = Mock()
#         mock_settings.api_url = "https://api.glific.com"
#         mock_get_settings.return_value = mock_settings
#         mock_get_headers.return_value = {"authorization": "token"}
        
#         # Mock successful response
#         mock_response = Mock()
#         mock_response.status_code = 200
#         mock_response.text = "success"
#         mock_response.json.return_value = {
#             "data": {
#                 "createContact": {
#                     "contact": {
#                         "id": "123",
#                         "name": "Test User",
#                         "phone": "1234567890"
#                     }
#                 }
#             }
#         }
#         mock_requests.post.return_value = mock_response
        
#         result = create_contact("Test User", "1234567890", "Test School", "Test Model", "1", "batch123")
        
#         # Verify result
#         assert result is not None
#         assert result["id"] == "123"
#         assert result["name"] == "Test User"
        
#         # Verify API call
#         mock_requests.post.assert_called_once()

# def test_create_contact_with_errors(mock_frappe):
#     """Test create_contact function with API errors"""
    
#     try:
#         from glific_integration import create_contact
#     except ImportError as e:
#         pytest.skip(f"Could not import module: {e}")
    
#     with patch('glific_integration.requests') as mock_requests, \
#          patch('glific_integration.get_glific_settings') as mock_get_settings, \
#          patch('glific_integration.get_glific_auth_headers') as mock_get_headers:
        
#         # Mock dependencies
#         mock_settings = Mock()
#         mock_settings.api_url = "https://api.glific.com"
#         mock_get_settings.return_value = mock_settings
#         mock_get_headers.return_value = {"authorization": "token"}
        
#         # Mock error response
#         mock_response = Mock()
#         mock_response.status_code = 200
#         mock_response.text = "error"
#         mock_response.json.return_value = {
#             "errors": [{"message": "Contact creation failed"}]
#         }
#         mock_requests.post.return_value = mock_response
        
#         result = create_contact("Test User", "1234567890", "Test School", "Test Model", "1", "batch123")
        
#         assert result is None

# def test_create_contact_exception(mock_frappe):
#     """Test create_contact function with exception"""
    
#     try:
#         from glific_integration import create_contact
#     except ImportError as e:
#         pytest.skip(f"Could not import module: {e}")
    
#     with patch('glific_integration.requests') as mock_requests, \
#          patch('glific_integration.get_glific_settings') as mock_get_settings, \
#          patch('glific_integration.get_glific_auth_headers') as mock_get_headers:
        
#         # Mock dependencies
#         mock_get_settings.return_value = Mock(api_url="https://api.glific.com")
#         mock_get_headers.return_value = {"authorization": "token"}
        
#         # Mock exception
#         mock_requests.post.side_effect = Exception("Network error")
        
#         result = create_contact("Test User", "1234567890", "Test School", "Test Model", "1", "batch123")
        
#         assert result is None

# def test_update_contact_fields_success(mock_frappe):
#     """Test update_contact_fields function with success"""
    
#     try:
#         from glific_integration import update_contact_fields
#     except ImportError as e:
#         pytest.skip(f"Could not import module: {e}")
    
#     with patch('glific_integration.requests') as mock_requests, \
#          patch('glific_integration.get_glific_settings') as mock_get_settings, \
#          patch('glific_integration.get_glific_auth_headers') as mock_get_headers, \
#          patch('glific_integration.datetime') as mock_datetime, \
#          patch('glific_integration.json') as mock_json:
        
#         # Mock dependencies
#         mock_settings = Mock()
#         mock_settings.api_url = "https://api.glific.com"
#         mock_get_settings.return_value = mock_settings
#         mock_get_headers.return_value = {"authorization": "token"}
        
#         # Mock datetime for timestamp
#         mock_datetime.now.return_value.isoformat.return_value = "2025-01-01T00:00:00Z"
        
#         # Mock json.loads for existing fields
#         mock_json.loads.return_value = {"existing_field": {"value": "existing_value"}}
#         mock_json.dumps.return_value = '{"updated": "fields"}'
        
#         # Mock fetch response (get current contact)
#         fetch_response = Mock()
#         fetch_response.status_code = 200
#         fetch_response.raise_for_status = Mock()
#         fetch_response.json.return_value = {
#             "data": {
#                 "contact": {
#                     "contact": {
#                         "id": "123",
#                         "name": "Test User",
#                         "fields": '{"existing_field": {"value": "existing_value"}}'
#                     }
#                 }
#             }
#         }
        
#         # Mock update response
#         update_response = Mock()
#         update_response.status_code = 200
#         update_response.text = "success"
#         update_response.raise_for_status = Mock()
#         update_response.json.return_value = {
#             "data": {
#                 "updateContact": {
#                     "contact": {
#                         "id": "123",
#                         "name": "Test User"
#                     }
#                 }
#             }
#         }
        
#         mock_requests.post.side_effect = [fetch_response, update_response]
        
#         # Create a proper RequestException for the except clause
#         mock_requests.exceptions = Mock()
#         mock_requests.exceptions.RequestException = Exception
        
#         result = update_contact_fields("123", {"new_field": "new_value"})
        
#         assert result is True
#         assert mock_requests.post.call_count == 2

# def test_update_contact_fields_fetch_error(mock_frappe):
#     """Test update_contact_fields function with fetch error"""
    
#     try:
#         from glific_integration import update_contact_fields
#     except ImportError as e:
#         pytest.skip(f"Could not import module: {e}")
    
#     with patch('glific_integration.requests') as mock_requests, \
#          patch('glific_integration.get_glific_settings') as mock_get_settings, \
#          patch('glific_integration.get_glific_auth_headers') as mock_get_headers:
        
#         # Mock dependencies
#         mock_get_settings.return_value = Mock(api_url="https://api.glific.com")
#         mock_get_headers.return_value = {"authorization": "token"}
        
#         # Mock fetch error response
#         fetch_response = Mock()
#         fetch_response.status_code = 200
#         fetch_response.json.return_value = {
#             "errors": [{"message": "Contact not found"}]
#         }
#         mock_requests.post.return_value = fetch_response
        
#         result = update_contact_fields("123", {"new_field": "new_value"})
        
#         assert result is False

# def test_get_contact_by_phone_success(mock_frappe):
#     """Test get_contact_by_phone function with success"""
    
#     try:
#         from glific_integration import get_contact_by_phone
#     except ImportError as e:
#         pytest.skip(f"Could not import module: {e}")
    
#     with patch('glific_integration.requests') as mock_requests, \
#          patch('glific_integration.get_glific_settings') as mock_get_settings, \
#          patch('glific_integration.get_glific_auth_headers') as mock_get_headers:
        
#         # Mock dependencies
#         mock_get_settings.return_value = Mock(api_url="https://api.glific.com")
#         mock_get_headers.return_value = {"authorization": "token"}
        
#         # Mock successful response
#         mock_response = Mock()
#         mock_response.status_code = 200
#         mock_response.json.return_value = {
#             "data": {
#                 "contactByPhone": {
#                     "contact": {
#                         "id": "123",
#                         "name": "Test User",
#                         "phone": "1234567890"
#                     }
#                 }
#             }
#         }
#         mock_requests.post.return_value = mock_response
        
#         result = get_contact_by_phone("1234567890")
        
#         assert result is not None
#         assert result["id"] == "123"

# def test_get_contact_by_phone_not_found(mock_frappe):
#     """Test get_contact_by_phone function when contact not found"""
    
#     try:
#         from glific_integration import get_contact_by_phone
#     except ImportError as e:
#         pytest.skip(f"Could not import module: {e}")
    
#     with patch('glific_integration.requests') as mock_requests, \
#          patch('glific_integration.get_glific_settings') as mock_get_settings, \
#          patch('glific_integration.get_glific_auth_headers') as mock_get_headers:
        
#         # Mock dependencies
#         mock_get_settings.return_value = Mock(api_url="https://api.glific.com")
#         mock_get_headers.return_value = {"authorization": "token"}
        
#         # Mock not found response
#         mock_response = Mock()
#         mock_response.status_code = 200
#         mock_response.json.return_value = {
#             "data": {
#                 "contactByPhone": {
#                     "contact": None
#                 }
#             }
#         }
#         mock_requests.post.return_value = mock_response
        
#         result = get_contact_by_phone("1234567890")
        
#         assert result is None

# def test_optin_contact_success(mock_frappe):
#     """Test optin_contact function with success"""
    
#     try:
#         from glific_integration import optin_contact
#     except ImportError as e:
#         pytest.skip(f"Could not import module: {e}")
    
#     with patch('glific_integration.requests') as mock_requests, \
#          patch('glific_integration.get_glific_settings') as mock_get_settings, \
#          patch('glific_integration.get_glific_auth_headers') as mock_get_headers:
        
#         # Mock dependencies
#         mock_get_settings.return_value = Mock(api_url="https://api.glific.com")
#         mock_get_headers.return_value = {"authorization": "token"}
        
#         # Mock successful response
#         mock_response = Mock()
#         mock_response.status_code = 200
#         mock_response.json.return_value = {
#             "data": {
#                 "optinContact": {
#                     "contact": {
#                         "id": "123",
#                         "phone": "1234567890",
#                         "name": "Test User"
#                     }
#                 }
#             }
#         }
#         mock_requests.post.return_value = mock_response
        
#         result = optin_contact("1234567890", "Test User")
        
#         assert result is True

# def test_start_contact_flow_success(mock_frappe):
#     """Test start_contact_flow function with success"""
    
#     try:
#         from glific_integration import start_contact_flow
#     except ImportError as e:
#         pytest.skip(f"Could not import module: {e}")
    
#     with patch('glific_integration.requests') as mock_requests, \
#          patch('glific_integration.get_glific_settings') as mock_get_settings, \
#          patch('glific_integration.get_glific_auth_headers') as mock_get_headers:
        
#         # Mock dependencies
#         mock_get_settings.return_value = Mock(api_url="https://api.glific.com")
#         mock_get_headers.return_value = {"authorization": "token"}
        
#         # Mock successful response
#         mock_response = Mock()
#         mock_response.status_code = 200
#         mock_response.json.return_value = {
#             "data": {
#                 "startContactFlow": {
#                     "success": True
#                 }
#             }
#         }
#         mock_requests.post.return_value = mock_response
        
#         result = start_contact_flow("flow123", "contact123", {"key": "value"})
        
#         assert result is True

# def test_update_student_glific_ids(mock_frappe):
#     """Test update_student_glific_ids function"""
    
#     try:
#         from glific_integration import update_student_glific_ids
#     except ImportError as e:
#         pytest.skip(f"Could not import module: {e}")
    
#     with patch('glific_integration.get_contact_by_phone') as mock_get_contact:
#         # Mock students data - create objects with attributes, not dicts
#         class MockStudent:
#             def __init__(self, name, phone):
#                 self.name = name
#                 self.phone = phone
        
#         mock_students = [
#             MockStudent("student1", "9876543210"),
#             MockStudent("student2", "9876543211")
#         ]
#         mock_frappe.get_all.return_value = mock_students
        
#         # Mock contact response
#         mock_get_contact.return_value = {"id": "glific123"}
        
#         result = update_student_glific_ids(batch_size=2)
        
#         assert result == 2
#         assert mock_frappe.db.set_value.call_count == 2
#         mock_frappe.db.commit.assert_called_once()

# def test_update_student_glific_ids_invalid_phone(mock_frappe):
#     """Test update_student_glific_ids with invalid phone numbers"""
    
#     try:
#         from glific_integration import update_student_glific_ids
#     except ImportError as e:
#         pytest.skip(f"Could not import module: {e}")
    
#     # Mock students with invalid phone - create objects with attributes, not dicts
#     class MockStudent:
#         def __init__(self, name, phone):
#             self.name = name
#             self.phone = phone
    
#     mock_students = [
#         MockStudent("student1", "invalid_phone")
#     ]
#     mock_frappe.get_all.return_value = mock_students
    
#     result = update_student_glific_ids(batch_size=1)
    
#     assert result == 1
#     # Should not call set_value for invalid phone
#     mock_frappe.db.set_value.assert_not_called()

# def test_check_glific_group_exists_found(mock_frappe):
#     """Test check_glific_group_exists when group exists"""
    
#     try:
#         from glific_integration import check_glific_group_exists
#     except ImportError as e:
#         pytest.skip(f"Could not import module: {e}")
    
#     with patch('glific_integration.requests') as mock_requests, \
#          patch('glific_integration.get_glific_settings') as mock_get_settings, \
#          patch('glific_integration.get_glific_auth_headers') as mock_get_headers:
        
#         # Mock dependencies
#         mock_get_settings.return_value = Mock(api_url="https://api.glific.com")
#         mock_get_headers.return_value = {"authorization": "token"}
        
#         # Mock successful response
#         mock_response = Mock()
#         mock_response.status_code = 200
#         mock_response.json.return_value = {
#             "data": {
#                 "groups": [
#                     {"id": "group123", "label": "Test Group"}
#                 ]
#             }
#         }
#         mock_requests.post.return_value = mock_response
        
#         result = check_glific_group_exists("Test Group")
        
#         assert result is not None
#         assert result["id"] == "group123"

# def test_check_glific_group_exists_not_found(mock_frappe):
#     """Test check_glific_group_exists when group not found"""
    
#     try:
#         from glific_integration import check_glific_group_exists
#     except ImportError as e:
#         pytest.skip(f"Could not import module: {e}")
    
#     with patch('glific_integration.requests') as mock_requests, \
#          patch('glific_integration.get_glific_settings') as mock_get_settings, \
#          patch('glific_integration.get_glific_auth_headers') as mock_get_headers:
        
#         # Mock dependencies
#         mock_get_settings.return_value = Mock(api_url="https://api.glific.com")
#         mock_get_headers.return_value = {"authorization": "token"}
        
#         # Mock empty response
#         mock_response = Mock()
#         mock_response.status_code = 200
#         mock_response.json.return_value = {
#             "data": {
#                 "groups": []
#             }
#         }
#         mock_requests.post.return_value = mock_response
        
#         result = check_glific_group_exists("Nonexistent Group")
        
#         assert result is None

# def test_create_glific_group_success(mock_frappe):
#     """Test create_glific_group function with success"""
    
#     try:
#         from glific_integration import create_glific_group
#     except ImportError as e:
#         pytest.skip(f"Could not import module: {e}")
    
#     with patch('glific_integration.requests') as mock_requests, \
#          patch('glific_integration.get_glific_settings') as mock_get_settings, \
#          patch('glific_integration.get_glific_auth_headers') as mock_get_headers:
        
#         # Mock dependencies
#         mock_get_settings.return_value = Mock(api_url="https://api.glific.com")
#         mock_get_headers.return_value = {"authorization": "token"}
        
#         # Mock successful response
#         mock_response = Mock()
#         mock_response.status_code = 200
#         mock_response.json.return_value = {
#             "data": {
#                 "createGroup": {
#                     "group": {
#                         "id": "group123",
#                         "label": "New Group",
#                         "description": "Test Description"
#                     }
#                 }
#             }
#         }
#         mock_requests.post.return_value = mock_response
        
#         result = create_glific_group("New Group", "Test Description")
        
#         assert result is not None
#         assert result["id"] == "group123"

# def test_create_or_get_glific_group_for_batch_existing(mock_frappe):
#     """Test create_or_get_glific_group_for_batch with existing mapping"""
    
#     try:
#         from glific_integration import create_or_get_glific_group_for_batch
#     except ImportError as e:
#         pytest.skip(f"Could not import module: {e}")
    
#     # Mock existing mapping
#     mock_frappe.get_all.return_value = [
#         {
#             "name": "mapping1",
#             "group_id": "group123",
#             "label": "Set: Test Batch"
#         }
#     ]
    
#     result = create_or_get_glific_group_for_batch("batch123")
    
#     assert result is not None
#     assert result["group_id"] == "group123"

# def test_create_or_get_glific_group_for_batch_new(mock_frappe):
#     """Test create_or_get_glific_group_for_batch creating new group"""
    
#     try:
#         from glific_integration import create_or_get_glific_group_for_batch
#     except ImportError as e:
#         pytest.skip(f"Could not import module: {e}")
    
#     with patch('glific_integration.check_glific_group_exists') as mock_check, \
#          patch('glific_integration.create_glific_group') as mock_create:
        
#         # Mock no existing mapping
#         mock_frappe.get_all.return_value = []
        
#         # Mock batch document
#         mock_batch = Mock()
#         mock_batch.set_name = "Test Batch"
#         mock_frappe.get_doc.return_value = mock_batch
        
#         # Mock no existing group in Glific
#         mock_check.return_value = None
        
#         # Mock successful group creation
#         mock_create.return_value = {
#             "id": "group123",
#             "label": "Set: Test Batch"
#         }
        
#         # Mock new document creation
#         mock_new_doc = Mock()
#         mock_frappe.new_doc.return_value = mock_new_doc
        
#         result = create_or_get_glific_group_for_batch("batch123")
        
#         assert result is not None
#         assert result["group_id"] == "group123"
#         mock_new_doc.insert.assert_called_once()

# def test_add_contact_to_group_success(mock_frappe):
#     """Test add_contact_to_group function with success"""
    
#     try:
#         from glific_integration import add_contact_to_group
#     except ImportError as e:
#         pytest.skip(f"Could not import module: {e}")
    
#     with patch('glific_integration.requests') as mock_requests, \
#          patch('glific_integration.get_glific_settings') as mock_get_settings, \
#          patch('glific_integration.get_glific_auth_headers') as mock_get_headers:
        
#         # Mock dependencies
#         mock_get_settings.return_value = Mock(api_url="https://api.glific.com")
#         mock_get_headers.return_value = {"authorization": "token"}
        
#         # Mock successful response
#         mock_response = Mock()
#         mock_response.status_code = 200
#         mock_response.json.return_value = {
#             "data": {
#                 "updateGroupContacts": {
#                     "groupContacts": [{"id": "contact123"}],
#                     "numberDeleted": 0
#                 }
#             }
#         }
#         mock_requests.post.return_value = mock_response
        
#         result = add_contact_to_group("contact123", "group123")
        
#         assert result is True

# def test_add_contact_to_group_invalid_params(mock_frappe):
#     """Test add_contact_to_group with invalid parameters"""
    
#     try:
#         from glific_integration import add_contact_to_group
#     except ImportError as e:
#         pytest.skip(f"Could not import module: {e}")
    
#     # Test with None contact_id
#     result = add_contact_to_group(None, "group123")
#     assert result is False
    
#     # Test with None group_id
#     result = add_contact_to_group("contact123", None)
#     assert result is False

# def test_add_student_to_glific_for_onboarding_existing_contact(mock_frappe):
#     """Test add_student_to_glific_for_onboarding with existing contact"""
    
#     try:
#         from glific_integration import add_student_to_glific_for_onboarding
#     except ImportError as e:
#         pytest.skip(f"Could not import module: {e}")
    
#     with patch('glific_integration.get_contact_by_phone') as mock_get_contact, \
#          patch('glific_integration.optin_contact') as mock_optin, \
#          patch('glific_integration.add_contact_to_group') as mock_add_to_group, \
#          patch('glific_integration.update_contact_fields') as mock_update:
        
#         # Mock existing contact
#         mock_get_contact.return_value = {
#             "id": "contact123",
#             "bspStatus": "NONE"
#         }
#         mock_optin.return_value = True
#         mock_add_to_group.return_value = True
#         mock_update.return_value = True
        
#         result = add_student_to_glific_for_onboarding(
#             "Test Student", "9876543210", "Test School", "Test Batch", 
#             "group123", "1", "Level 1", "Math", "Grade 5"
#         )
        
#         assert result is not None
#         assert result["id"] == "contact123"
#         mock_optin.assert_called_once()
#         mock_add_to_group.assert_called_once()
#         mock_update.assert_called_once()

# def test_add_student_to_glific_for_onboarding_new_contact(mock_frappe):
#     """Test add_student_to_glific_for_onboarding creating new contact"""
    
#     try:
#         from glific_integration import add_student_to_glific_for_onboarding
#     except ImportError as e:
#         pytest.skip(f"Could not import module: {e}")
    
#     with patch('glific_integration.get_contact_by_phone') as mock_get_contact, \
#          patch('glific_integration.optin_contact') as mock_optin, \
#          patch('glific_integration.add_contact_to_group') as mock_add_to_group, \
#          patch('glific_integration.requests') as mock_requests, \
#          patch('glific_integration.get_glific_settings') as mock_get_settings, \
#          patch('glific_integration.get_glific_auth_headers') as mock_get_headers:
        
#         # Mock no existing contact
#         mock_get_contact.return_value = None
        
#         # Mock settings
#         mock_settings = Mock()
#         mock_settings.api_url = "https://api.glific.com"
#         mock_get_settings.return_value = mock_settings
#         mock_get_headers.return_value = {"authorization": "token"}
        
#         # Mock successful contact creation
#         mock_response = Mock()
#         mock_response.status_code = 200
#         mock_response.json.return_value = {
#             "data": {
#                 "createContact": {
#                     "contact": {
#                         "id": "new_contact123",
#                         "name": "Test Student",
#                         "phone": "919876543210"
#                     }
#                 }
#             }
#         }
#         mock_requests.post.return_value = mock_response
#         mock_optin.return_value = True
#         mock_add_to_group.return_value = True
        
#         result = add_student_to_glific_for_onboarding(
#             "Test Student", "9876543210", "Test School", "Test Batch", 
#             "group123", "1", "Level 1", "Math", "Grade 5"
#         )
        
#         assert result is not None
#         assert result["id"] == "new_contact123"
#         mock_optin.assert_called_once()
#         mock_add_to_group.assert_called_once()

# def test_add_student_to_glific_for_onboarding_invalid_phone(mock_frappe):
#     """Test add_student_to_glific_for_onboarding with invalid phone"""
    
#     try:
#         from glific_integration import add_student_to_glific_for_onboarding
#     except ImportError as e:
#         pytest.skip(f"Could not import module: {e}")
    
#     result = add_student_to_glific_for_onboarding(
#         "Test Student", "invalid_phone", "Test School", "Test Batch", 
#         "group123", "1", "Level 1", "Math", "Grade 5"
#     )
    
#     assert result is None

# def test_create_or_get_teacher_group_for_batch_existing(mock_frappe):
#     """Test create_or_get_teacher_group_for_batch with existing mapping"""
    
#     try:
#         from glific_integration import create_or_get_teacher_group_for_batch
#     except ImportError as e:
#         pytest.skip(f"Could not import module: {e}")
    
#     # Mock existing mapping
#     mock_frappe.get_all.return_value = [
#         {
#             "name": "teacher_group1",
#             "glific_group_id": "group123",
#             "group_label": "teacher_batch_batch123"
#         }
#     ]
    
#     result = create_or_get_teacher_group_for_batch("Batch Name", "batch123")
    
#     assert result is not None
#     assert result["group_id"] == "group123"

# def test_create_or_get_teacher_group_for_batch_invalid_batch(mock_frappe):
#     """Test create_or_get_teacher_group_for_batch with invalid batch"""
    
#     try:
#         from glific_integration import create_or_get_teacher_group_for_batch
#     except ImportError as e:
#         pytest.skip(f"Could not import module: {e}")
    
#     # Test with no_active_batch_id
#     result = create_or_get_teacher_group_for_batch("Batch Name", "no_active_batch_id")
#     assert result is None
    
#     # Test with None batch_id
#     result = create_or_get_teacher_group_for_batch("Batch Name", None)
#     assert result is None
    
#     # Test with None batch_name
#     result = create_or_get_teacher_group_for_batch(None, "batch123")
#     assert result is None

# def test_function_imports_coverage(mock_frappe):
#     """Test to cover import statements in the module"""
    
#     try:
#         # This import covers the import statements in the file
#         import glific_integration
#         assert hasattr(glific_integration, 'get_glific_settings')
#         assert hasattr(glific_integration, 'create_contact')
#         assert hasattr(glific_integration, 'update_contact_fields')
#         assert hasattr(glific_integration, 'get_contact_by_phone')
#         assert hasattr(glific_integration, 'optin_contact')
#         assert hasattr(glific_integration, 'start_contact_flow')
#         assert hasattr(glific_integration, 'check_glific_group_exists')
#         assert hasattr(glific_integration, 'create_glific_group')
#         assert hasattr(glific_integration, 'add_contact_to_group')
#         assert hasattr(glific_integration, 'add_student_to_glific_for_onboarding')
#         assert hasattr(glific_integration, 'create_or_get_teacher_group_for_batch')
#     except ImportError as e:
#         pytest.skip(f"Could not import module: {e}")

# def test_edge_cases_and_error_handling(mock_frappe):
#     """Test various edge cases and error handling scenarios"""
    
#     try:
#         from glific_integration import get_glific_auth_headers
#     except ImportError as e:
#         pytest.skip(f"Could not import module: {e}")
    
#     # Test with string token_expiry_time
#     mock_settings = Mock()
#     mock_settings.access_token = "token"
#     mock_settings.token_expiry_time = "2025-12-31T23:59:59Z"  # String format
#     mock_frappe.get_single.return_value = mock_settings
    
#     with patch('glific_integration.isoparse') as mock_isoparse, \
#          patch('glific_integration.datetime') as mock_datetime:
        
#         mock_isoparse.return_value = datetime.now(timezone.utc) + timedelta(hours=1)
#         mock_datetime.now.return_value = datetime.now(timezone.utc)
#         mock_datetime.datetime = datetime  # For isinstance checks
        
#         result = get_glific_auth_headers()
        
#         assert "authorization" in result
#         mock_isoparse.assert_called_once()

# def test_complete_coverage_verification(mock_frappe):
#     """Test to ensure function execution covers all code paths"""
    
#     try:
#         from glific_integration import create_contact_old
#     except ImportError as e:
#         pytest.skip(f"Could not import module: {e}")
    
#     with patch('glific_integration.requests') as mock_requests, \
#          patch('glific_integration.get_glific_settings') as mock_get_settings, \
#          patch('glific_integration.get_glific_auth_headers') as mock_get_headers:
        
#         # Mock dependencies
#         mock_get_settings.return_value = Mock(api_url="https://api.glific.com")
#         mock_get_headers.return_value = {"authorization": "token"}
        
#         # Mock successful response for create_contact_old
#         mock_response = Mock()
#         mock_response.status_code = 200
#         mock_response.text = "success"
#         mock_response.json.return_value = {
#             "data": {
#                 "createContact": {
#                     "contact": {
#                         "id": "123",
#                         "name": "Test User",
#                         "phone": "1234567890"
#                     }
#                 }
#             }
#         }
#         mock_requests.post.return_value = mock_response
        
#         result = create_contact_old("Test User", "1234567890")
        
#         assert result is not None
#         assert result["id"] == "123"

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta
import json

# Fix 1: test_get_glific_auth_headers_timezone_replacement
# The issue is with timezone mocking. Here's the corrected version:

def test_get_glific_auth_headers_timezone_replacement(mock_frappe):
    """Test get_glific_auth_headers with timezone-naive datetime that needs timezone replacement"""

    try:
        from glific_integration import get_glific_auth_headers
    except ImportError as e:
        pytest.skip(f"Could not import module: {e}")

    # Import the real timezone and datetime classes
    from datetime import timezone as real_timezone, datetime as real_datetime
    
    with patch('glific_integration.datetime') as mock_datetime:
        
        # Mock settings with timezone-naive datetime (this should trigger line 19)
        mock_settings = Mock()
        mock_settings.access_token = "valid_token"

        # Create a timezone-naive datetime using the real datetime class
        naive_datetime = real_datetime(2025, 12, 31, 23, 59, 59)  # No timezone info
        mock_settings.token_expiry_time = naive_datetime

        mock_frappe.get_single.return_value = mock_settings

        # Mock datetime.now to return a consistent time that is less than token expiry
        current_time = real_datetime(2025, 12, 31, 22, 0, 0, tzinfo=real_timezone.utc)
        mock_datetime.now.return_value = current_time
        
        # Keep the real datetime class for isinstance checks
        mock_datetime.datetime = real_datetime
        
        # Don't patch timezone - use the real one
        with patch('glific_integration.timezone', real_timezone):
            result = get_glific_auth_headers()

            # Verify the token_expiry_time was updated with timezone info
            assert mock_settings.token_expiry_time.tzinfo is not None
            assert result == {
                "authorization": "valid_token",
                "Content-Type": "application/json"
            }

# Fix 2: test_update_contact_fields_general_exception
# The issue is that we're mocking get_glific_settings to raise an exception, 
# but we also need to handle the logger mock properly

def test_update_contact_fields_general_exception(mock_frappe):
    """Test update_contact_fields when general exception occurs"""
    
    try:
        from glific_integration import update_contact_fields
    except ImportError as e:
        pytest.skip(f"Could not import module: {e}")

    # Mock logger first
    mock_logger = Mock()
    mock_frappe.logger.return_value.error = Mock()

    with patch('glific_integration.get_glific_settings') as mock_get_settings:
        # Mock exception in get_glific_settings
        mock_get_settings.side_effect = Exception("General error")
        
        result = update_contact_fields("123", {"new_field": "new_value"})
        
        assert result is False
        # The function should call logger().error, so check if logger was called
        mock_frappe.logger.return_value.error.assert_called()

# Fix 3: test_update_contact_fields_json_decode_error_complete
# The issue is the assertion. Looking at your code, when JSON decode fails,
# it sets existing_fields = {} and continues, which should result in success.
# But the test might be failing because of how we're simulating the JSON decode error.

def test_update_contact_fields_json_decode_error_complete(mock_frappe):
    """Test update_contact_fields JSON decode error - covers lines 180-182"""

    try:
        from glific_integration import update_contact_fields
    except ImportError as e:
        pytest.skip(f"Could not import module: {e}")

    with patch('glific_integration.requests') as mock_requests, \
         patch('glific_integration.get_glific_settings') as mock_get_settings, \
         patch('glific_integration.get_glific_auth_headers') as mock_get_headers, \
         patch('glific_integration.datetime') as mock_datetime, \
         patch('glific_integration.json') as mock_json:

        mock_get_settings.return_value = Mock(api_url="https://api.glific.com")
        mock_get_headers.return_value = {"authorization": "token"}
        mock_datetime.now.return_value.isoformat.return_value = "2025-01-01T00:00:00Z"

        # Mock fetch response with fields that will cause JSON decode error
        fetch_response = Mock()
        fetch_response.status_code = 200
        fetch_response.raise_for_status = Mock()
        fetch_response.json.return_value = {
            "data": {
                "contact": {
                    "contact": {
                        "id": "123",
                        "name": "Test User",
                        "fields": "invalid json string"  # This will cause JSONDecodeError
                    }
                }
            }
        }

        # Mock update response - successful update
        update_response = Mock()
        update_response.status_code = 200
        update_response.text = "success"
        update_response.raise_for_status = Mock()
        update_response.json.return_value = {
            "data": {
                "updateContact": {
                    "contact": {"id": "123", "name": "Test User"}
                }
            }
        }

        mock_requests.post.side_effect = [fetch_response, update_response]
        mock_requests.exceptions = Mock()
        mock_requests.exceptions.RequestException = Exception

        # Mock json.loads to raise JSONDecodeError specifically for the fields parsing
        import json as real_json
        def json_loads_side_effect(s):
            if s == "invalid json string":
                raise real_json.JSONDecodeError("Expecting value", "invalid json string", 0)
            return real_json.loads(s)
        
        mock_json.loads.side_effect = json_loads_side_effect
        mock_json.dumps.return_value = '{"new_field": {"value": "new_value", "type": "string", "inserted_at": "2025-01-01T00:00:00Z"}}'

        # Mock logger
        mock_frappe.logger.return_value.error = Mock()
        mock_frappe.logger.return_value.info = Mock()

        result = update_contact_fields("123", {"new_field": "new_value"})

        # The function should handle the JSON decode error gracefully and still succeed
        assert result is True