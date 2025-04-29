import pytest
import requests
import json
from unittest.mock import patch, MagicMock

# Base URL for the API
BASE_URL = "http://localhost:8080" 

# Test data
TEST_API_KEY = "test_valid_api_key"
TEST_KEYWORD = "some-existing-keyword"

#! -------------------------------------- START OF FIXTURES -------------------------------------------------------
@pytest.fixture
def mock_verify_keyword_success_response():
    """Mock a successful keyword verification response"""
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "school_name": "Test School",
            "message": "Keyword verified successfully"
        }
        mock_post.return_value = mock_response
        yield mock_post


@pytest.fixture
def mock_verify_keyword_missing_keyword_response():
    """Mock a response for missing keyword parameter"""
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "status": "failure",
            "error": "Keyword parameter is missing"
        }
        mock_post.return_value = mock_response
        yield mock_post


@pytest.fixture
def mock_verify_keyword_invalid_api_key_response():
    """Mock a response for invalid API key"""
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
def mock_verify_keyword_not_found_response():
    """Mock a response for keyword not found"""
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {
            "status": "failure",
            "message": "Keyword not found"
        }
        mock_post.return_value = mock_response
        yield mock_post

#! ----------------------------------- END OF FIXTURES ----------------------------------------------------------


# ---------------------------------- START OF TEST CASES --------------------------------------------------------------
def test_verify_keyword_success(mock_verify_keyword_success_response):
    """Test successful keyword verification"""
    # Make API request
    response = requests.post(
        f"{BASE_URL}/api/method/tap_lms.api.verify_keyword",
        data={
            "api_key": TEST_API_KEY,
            "keyword": TEST_KEYWORD
        }
    )
    
    # Assert that the API was called with the correct parameters
    mock_verify_keyword_success_response.assert_called_once()
    
    # Check response status code and content
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "school_name" in data


def test_verify_keyword_missing_keyword(mock_verify_keyword_missing_keyword_response):
    """Test keyword verification with missing keyword parameter"""
    # Make API request without keyword
    response = requests.post(
        f"{BASE_URL}/api/method/tap_lms.api.verify_keyword",
        data={
            "api_key": TEST_API_KEY
            # Missing keyword
        }
    )
    
    # Assert that the API was called
    mock_verify_keyword_missing_keyword_response.assert_called_once()
    
    # Check response status code and content
    assert response.status_code == 400
    data = response.json()
    assert data["status"] == "failure"
    assert data["error"] == "Keyword parameter is missing"


def test_verify_keyword_invalid_api_key(mock_verify_keyword_invalid_api_key_response):
    """Test keyword verification with invalid API key"""
    # Make API request with invalid API key
    response = requests.post(
        f"{BASE_URL}/api/method/tap_lms.api.verify_keyword",
        data={
            "api_key": "invalid-key",
            "keyword": TEST_KEYWORD
        }
    )
    
    # Assert that the API was called
    mock_verify_keyword_invalid_api_key_response.assert_called_once()
    
    # Check response status code and content
    assert response.status_code == 401
    data = response.json()
    assert data["status"] == "failure"


def test_verify_keyword_not_found(mock_verify_keyword_not_found_response):
    """Test keyword verification with non-existent keyword"""
    # Make API request with non-existent keyword
    response = requests.post(
        f"{BASE_URL}/api/method/tap_lms.api.verify_keyword",
        data={
            "api_key": TEST_API_KEY,
            "keyword": "non-existent-keyword"
        }
    )
    
    # Assert that the API was called
    mock_verify_keyword_not_found_response.assert_called_once()
    
    # Check response status code and content
    assert response.status_code == 404
    data = response.json()
    assert data["status"] == "failure"
    assert "Keyword not found" in data["message"]