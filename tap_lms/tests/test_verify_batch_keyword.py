import pytest
import requests
import json
from unittest.mock import patch, MagicMock

# Base URL for the API
BASE_URL = "http://localhost:8080" 

# Test data
VALID_API_KEY = "valid_api_key"
VALID_KEYWORD = "valid_keyword"
INVALID_API_KEY = "invalid_api_key"
INVALID_KEYWORD = "invalid_keyword"

#! -------------------------------------- START OF FIXTURES -------------------------------------------------------
@pytest.fixture
def mock_verify_batch_keyword_valid_response():
    """Mock a successful batch keyword verification (status 200)"""
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "message": "Batch keyword verified successfully"
        }
        mock_post.return_value = mock_response
        yield mock_post


@pytest.fixture
def mock_verify_batch_keyword_invalid_api_key_response():
    """Mock response for invalid API key (status 401)"""
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            "status": "failure",
            "message": "Invalid API key"
        }
        mock_post.return_value = mock_response
        yield mock_post


@pytest.fixture
def mock_verify_batch_keyword_invalid_keyword_response():
    """Mock response for invalid keyword (status 202)"""
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_response.json.return_value = {
            "status": "failure",
            "message": "Invalid batch keyword"
        }
        mock_post.return_value = mock_response
        yield mock_post

#! ----------------------------------- END OF FIXTURES ----------------------------------------------------------


# ---------------------------------- START OF TEST CASES --------------------------------------------------------------
def test_verify_batch_keyword_valid(mock_verify_batch_keyword_valid_response):
    """Test successful batch keyword verification"""
    # Make API request with valid API key and valid keyword
    response = requests.post(
        f"{BASE_URL}/api/method/tap_lms.api.verify_batch_keyword",
        data={
            "api_key": VALID_API_KEY,
            "batch_skeyword": VALID_KEYWORD
        }
    )
    
    # Assert that the API was called
    mock_verify_batch_keyword_valid_response.assert_called_once()
    
    # Check response status code
    assert response.status_code == 200
    

def test_verify_batch_keyword_invalid_api_key(mock_verify_batch_keyword_invalid_api_key_response):
    """Test batch keyword verification with invalid API key"""
    # Make API request with invalid API key
    response = requests.post(
        f"{BASE_URL}/api/method/tap_lms.api.verify_batch_keyword",
        data={
            "api_key": INVALID_API_KEY,
            "batch_skeyword": VALID_KEYWORD
        }
    )
    
    # Assert that the API was called
    mock_verify_batch_keyword_invalid_api_key_response.assert_called_once()
    
    # Check response status code
    assert response.status_code == 401


def test_verify_batch_keyword_invalid_keyword(mock_verify_batch_keyword_invalid_keyword_response):
    """Test batch keyword verification with invalid keyword"""
    # Make API request with invalid keyword
    response = requests.post(
        f"{BASE_URL}/api/method/tap_lms.api.verify_batch_keyword",
        data={
            "api_key": VALID_API_KEY,
            "batch_skeyword": INVALID_KEYWORD
        }
    )
    
    # Assert that the API was called
    mock_verify_batch_keyword_invalid_keyword_response.assert_called_once()
    
    # Check response status code
    assert response.status_code == 202