import pytest
import requests
import json
from unittest.mock import patch, MagicMock

# Base URL for the API
BASE_URL = "http://localhost:8080"

# Test data
TEST_API_KEY = "validkey"

#! -------------------------------------- START OF FIXTURES -------------------------------------------------------
@pytest.fixture
def mock_list_batch_keyword_success_response():
    """Mock a successful batch keyword list response"""
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "batch_id": "BATCH001",
                "School_name": "TAP School",
                "batch_keyword": "batchkey001",
                "active": True
            }
        ]
        mock_post.return_value = mock_response
        yield mock_post


@pytest.fixture
def mock_list_batch_keyword_invalid_api_key_response():
    """Mock response for invalid API key"""
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            "status": "error",
            "message": "Invalid API key"
        }
        mock_post.return_value = mock_response
        yield mock_post


@pytest.fixture
def mock_list_batch_keyword_no_batches_response():
    """Mock response when no batches are found"""
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_post.return_value = mock_response
        yield mock_post

#! ----------------------------------- END OF FIXTURES ----------------------------------------------------------


# ---------------------------------- START OF TEST CASES --------------------------------------------------------------
def test_list_batch_keyword_success(mock_list_batch_keyword_success_response):
    """Test successful fetch of batch keywords"""
    # Make API request with valid parameters
    response = requests.post(
        f"{BASE_URL}/api/method/tap_lms.api.list_batch_keyword",
        data={"api_key": TEST_API_KEY}
    )
    
    # Assert that the API was called with the correct parameters
    mock_list_batch_keyword_success_response.assert_called_once()
    
    # Check response status code and content
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["School_name"] == "TAP School"
    assert data[0]["batch_keyword"] == "batchkey001"
    assert data[0]["batch_id"] == "BATCH001"
    assert data[0]["active"] == True


def test_list_batch_keyword_invalid_api_key(mock_list_batch_keyword_invalid_api_key_response):
    """Test with invalid API Key"""
    # Make API request with invalid API key
    response = requests.post(
        f"{BASE_URL}/api/method/tap_lms.api.list_batch_keyword",
        data={"api_key": "wrongapikey"}
    )
    
    # Assert that the API was called
    mock_list_batch_keyword_invalid_api_key_response.assert_called_once()
    
    # Check response status code and content
    assert response.status_code == 401
    data = response.json()
    assert data["status"] == "error"
    assert data["message"] == "Invalid API key"


def test_list_batch_keyword_no_batches(mock_list_batch_keyword_no_batches_response):
    """Test when no batches are found"""
    # Make API request
    response = requests.post(
        f"{BASE_URL}/api/method/tap_lms.api.list_batch_keyword",
        data={"api_key": TEST_API_KEY}
    )
    
    # Assert that the API was called
    mock_list_batch_keyword_no_batches_response.assert_called_once()
    
    # Check response status code and content
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0
    assert isinstance(data, list)