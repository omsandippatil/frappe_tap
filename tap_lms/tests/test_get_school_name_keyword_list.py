import pytest
import requests
import json
from unittest.mock import patch, MagicMock

# Base URL for the API
BASE_URL = "http://localhost:8080"

# Test data
TEST_API_KEY = "test-valid-api-key"

#! -------------------------------------- START OF FIXTURES -------------------------------------------------------
@pytest.fixture
def mock_get_school_name_keyword_list_success_response():
    """Mock a successful school keyword list response"""
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "school_name": "TAP School",
                "teacher_keyword": "teacher001",
                "whatsapp_link": "https://wa.me/123456789"
            },
            {
                "school_name": "Another School",
                "teacher_keyword": "teacher002",
                "whatsapp_link": "https://wa.me/987654321"
            }
        ]
        mock_post.return_value = mock_response
        yield mock_post


@pytest.fixture
def mock_get_school_name_keyword_list_empty_response():
    """Mock a response when no schools are found"""
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_post.return_value = mock_response
        yield mock_post


@pytest.fixture
def mock_get_school_name_keyword_list_invalid_api_key_response():
    """Mock a response for invalid API key"""
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            "status": "error",
            "message": "Invalid API key"
        }
        mock_post.return_value = mock_response
        yield mock_post

#! ----------------------------------- END OF FIXTURES ----------------------------------------------------------


# ---------------------------------- START OF TEST CASES --------------------------------------------------------------
def test_get_school_name_keyword_list_success(mock_get_school_name_keyword_list_success_response):
    """Test successful fetch of school keyword list"""
    # Make API request with valid API key
    response = requests.post(
        f"{BASE_URL}/api/method/tap_lms.api.get_school_name_keyword_list",
        data={"api_key": TEST_API_KEY}
    )
    
    # Assert that the API was called with the correct parameters
    mock_get_school_name_keyword_list_success_response.assert_called_once()
    
    # Check response status code and content
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "school_name" in data[0]
    assert "teacher_keyword" in data[0]
    assert "whatsapp_link" in data[0]


def test_get_school_name_keyword_list_empty(mock_get_school_name_keyword_list_empty_response):
    """Test when no schools are found"""
    # Make API request with valid API key
    response = requests.post(
        f"{BASE_URL}/api/method/tap_lms.api.get_school_name_keyword_list",
        data={"api_key": TEST_API_KEY}
    )
    
    # Assert that the API was called
    mock_get_school_name_keyword_list_empty_response.assert_called_once()
    
    # Check response status code and content
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_get_school_name_keyword_list_invalid_api_key(mock_get_school_name_keyword_list_invalid_api_key_response):
    """Test with invalid API key"""
    # Make API request with invalid API key
    response = requests.post(
        f"{BASE_URL}/api/method/tap_lms.api.get_school_name_keyword_list",
        data={"api_key": "invalid-key"}
    )
    
    # Assert that the API was called
    mock_get_school_name_keyword_list_invalid_api_key_response.assert_called_once()
    
    # Check response status code and content
    assert response.status_code == 401
    data = response.json()
    assert data["status"] == "error"
    assert "Invalid API key" in data["message"]