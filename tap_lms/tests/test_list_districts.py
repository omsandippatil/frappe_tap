import pytest
import requests
import json
from unittest.mock import patch, MagicMock

# Base URL for the API
BASE_URL = "http://localhost:8080" 

# Test data
TEST_API_KEY = "testapikey456"
TEST_STATE = "Kerala"

#! -------------------------------------- START OF FIXTURES -------------------------------------------------------
@pytest.fixture
def mock_list_districts_success_response():
    """Mock a successful districts list response"""
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "DIST001": "Thrissur",
                "DIST002": "Ernakulam"
            },
            "message": "Districts retrieved successfully"
        }
        mock_post.return_value = mock_response
        yield mock_post


@pytest.fixture
def mock_list_districts_invalid_api_key_response():
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


@pytest.fixture
def mock_list_districts_missing_fields_response():
    """Mock a response for missing required fields"""
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "status": "error",
            "message": "API key and state are required"
        }
        mock_post.return_value = mock_response
        yield mock_post


@pytest.fixture
def mock_list_districts_state_not_found_response():
    """Mock a response for state not found"""
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {
            "status": "error",
            "message": "State not found"
        }
        mock_post.return_value = mock_response
        yield mock_post

#! ----------------------------------- END OF FIXTURES ----------------------------------------------------------


# ---------------------------------- START OF TEST CASES --------------------------------------------------------------
def test_list_districts_success(mock_list_districts_success_response):
    """Test successful fetch of districts"""
    # Make API request with valid parameters
    response = requests.post(
        f"{BASE_URL}/api/method/tap_lms.api.list_districts",
        data={
            "api_key": TEST_API_KEY,
            "state": TEST_STATE
        }
    )
    
    # Assert that the API was called with the correct parameters
    mock_list_districts_success_response.assert_called_once()
    
    # Check response status code and content
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "DIST001" in data["data"]
    assert data["data"]["DIST001"] == "Thrissur"
    assert "DIST002" in data["data"]
    assert data["data"]["DIST002"] == "Ernakulam"


def test_list_districts_invalid_api_key(mock_list_districts_invalid_api_key_response):
    """Test with invalid API Key"""
    # Make API request with invalid API key
    response = requests.post(
        f"{BASE_URL}/api/method/tap_lms.api.list_districts",
        data={
            "api_key": "wrongapikey",
            "state": TEST_STATE
        }
    )
    
    # Assert that the API was called
    mock_list_districts_invalid_api_key_response.assert_called_once()
    
    # Check response status code and content
    assert response.status_code == 401
    data = response.json()
    assert data["status"] == "error"
    assert data["message"] == "Invalid API key"


def test_list_districts_missing_fields(mock_list_districts_missing_fields_response):
    """Test missing API Key or State"""
    # Make API request without state
    response = requests.post(
        f"{BASE_URL}/api/method/tap_lms.api.list_districts",
        data={
            "api_key": TEST_API_KEY
            # state is missing
        }
    )
    
    # Assert that the API was called
    mock_list_districts_missing_fields_response.assert_called_once()
    
    # Check response status code and content
    assert response.status_code == 400
    data = response.json()
    assert data["status"] == "error"
    assert data["message"] == "API key and state are required"


def test_list_districts_state_not_found(mock_list_districts_state_not_found_response):
    """Test with non-existent state"""
    # Make API request with non-existent state
    response = requests.post(
        f"{BASE_URL}/api/method/tap_lms.api.list_districts",
        data={
            "api_key": TEST_API_KEY,
            "state": "NonExistentState"
        }
    )
    
    # Assert that the API was called
    mock_list_districts_state_not_found_response.assert_called_once()
    
    # Check response status code and content
    assert response.status_code == 404
    data = response.json()
    assert data["status"] == "error"
    assert data["message"] == "State not found"