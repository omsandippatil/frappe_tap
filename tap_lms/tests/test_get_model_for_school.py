import pytest
import requests
import json
from unittest.mock import patch, MagicMock

# Base URL for the API
BASE_URL = "http://localhost:8080"

# Test data
TEST_API_KEY = "test-valid-api-key"
TEST_SCHOOL_ID = "SCH001"

#! -------------------------------------- START OF FIXTURES -------------------------------------------------------
@pytest.fixture
def mock_get_school_model_success_response():
    """Mock a successful response for getting a school model"""
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "model": "Math Curriculum Model"
        }
        mock_post.return_value = mock_response
        yield mock_post


@pytest.fixture
def mock_get_school_model_fallback_response():
    """Mock a response when using the school's default model as fallback"""
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "model": "Default School Model",
            "is_fallback": True
        }
        mock_post.return_value = mock_response
        yield mock_post


@pytest.fixture
def mock_get_school_model_not_found_response():
    """Mock a response when no model is found"""
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {
            "status": "error",
            "message": "No model name found for school"
        }
        mock_post.return_value = mock_response
        yield mock_post


@pytest.fixture
def mock_get_school_model_invalid_api_key_response():
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
def test_get_school_model_success(mock_get_school_model_success_response):
    """Test successful retrieval of a school model"""
    # Make API request
    response = requests.post(
        f"{BASE_URL}/api/method/tap_lms.api.get_school_model",
        data={
            "api_key": TEST_API_KEY,
            "school_id": TEST_SCHOOL_ID
        }
    )
    
    # Assert that the API was called
    mock_get_school_model_success_response.assert_called_once()
    
    # Check response status code and content
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["model"] == "Math Curriculum Model"


def test_get_school_model_fallback(mock_get_school_model_fallback_response):
    """Test retrieving fallback model when no active batch onboardings exist"""
    # Make API request
    response = requests.post(
        f"{BASE_URL}/api/method/tap_lms.api.get_school_model",
        data={
            "api_key": TEST_API_KEY,
            "school_id": TEST_SCHOOL_ID
        }
    )
    
    # Assert that the API was called
    mock_get_school_model_fallback_response.assert_called_once()
    
    # Check response status code and content
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["model"] == "Default School Model"
    assert data["is_fallback"] == True


def test_get_school_model_not_found(mock_get_school_model_not_found_response):
    """Test when no model is found for a school"""
    # Make API request
    response = requests.post(
        f"{BASE_URL}/api/method/tap_lms.api.get_school_model",
        data={
            "api_key": TEST_API_KEY,
            "school_id": "NONEXISTENT_SCHOOL"
        }
    )
    
    # Assert that the API was called
    mock_get_school_model_not_found_response.assert_called_once()
    
    # Check response status code and content
    assert response.status_code == 404
    data = response.json()
    assert data["status"] == "error"
    assert "No model name found for school" in data["message"]


def test_get_school_model_invalid_api_key(mock_get_school_model_invalid_api_key_response):
    """Test with invalid API key"""
    # Make API request with invalid API key
    response = requests.post(
        f"{BASE_URL}/api/method/tap_lms.api.get_school_model",
        data={
            "api_key": "invalid-key",
            "school_id": TEST_SCHOOL_ID
        }
    )
    
    # Assert that the API was called
    mock_get_school_model_invalid_api_key_response.assert_called_once()
    
    # Check response status code and content
    assert response.status_code == 401
    data = response.json()
    assert data["status"] == "error"
    assert data["message"] == "Invalid API key"