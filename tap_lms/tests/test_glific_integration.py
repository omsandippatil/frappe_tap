# Replace these 3 failing test functions in your test file:

def test_get_glific_auth_headers_timezone_replacement(mock_frappe):
    """Test get_glific_auth_headers with timezone-naive datetime that needs timezone replacement"""

    try:
        from glific_integration import get_glific_auth_headers
    except ImportError as e:
        pytest.skip(f"Could not import module: {e}")

    from datetime import timezone, datetime
    
    # Mock settings with timezone-naive datetime
    mock_settings = Mock()
    mock_settings.access_token = "valid_token"
    mock_settings.token_expiry_time = datetime(2025, 12, 31, 23, 59, 59)  # No timezone
    mock_frappe.get_single.return_value = mock_settings

    # Don't patch datetime - let it work normally
    result = get_glific_auth_headers()

    # Should add timezone and return valid token
    assert result == {
        "authorization": "valid_token",
        "Content-Type": "application/json"
    }

def test_update_contact_fields_general_exception(mock_frappe):
    """Test update_contact_fields when general exception occurs"""
    
    try:
        from glific_integration import update_contact_fields
    except ImportError as e:
        pytest.skip(f"Could not import module: {e}")

    # Mock logger
    mock_frappe.logger.return_value.error = Mock()

    # Patch to raise exception during execution
    with patch('glific_integration.requests.post') as mock_post:
        mock_post.side_effect = Exception("General error")
        
        result = update_contact_fields("123", {"new_field": "new_value"})
        
        assert result is False

def test_update_contact_fields_json_decode_error_complete(mock_frappe):
    """Test update_contact_fields JSON decode error - covers lines 180-182"""

    try:
        from glific_integration import update_contact_fields
    except ImportError as e:
        pytest.skip(f"Could not import module: {e}")

    with patch('glific_integration.requests') as mock_requests, \
         patch('glific_integration.get_glific_settings') as mock_get_settings, \
         patch('glific_integration.get_glific_auth_headers') as mock_get_headers, \
         patch('glific_integration.datetime') as mock_datetime:

        mock_get_settings.return_value = Mock(api_url="https://api.glific.com")
        mock_get_headers.return_value = {"authorization": "token"}
        mock_datetime.now.return_value.isoformat.return_value = "2025-01-01T00:00:00Z"

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

        # Mock logger
        mock_frappe.logger.return_value.error = Mock()
        mock_frappe.logger.return_value.info = Mock()

        result = update_contact_fields("123", {"new_field": "new_value"})

        # Should succeed despite JSON error (sets existing_fields = {} and continues)
        assert result is True