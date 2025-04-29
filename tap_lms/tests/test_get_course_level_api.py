import pytest
import requests
import json
from unittest.mock import patch, MagicMock

# Base URL for the API
BASE_URL = "http://localhost:8080"

# Test data
TEST_API_KEY = "valid_api_key"
TEST_GRADE = "5"
TEST_VERTICAL = "Math"
TEST_BATCH_KEYWORD = "BATCH123"

#! -------------------------------------- START OF FIXTURES -------------------------------------------------------
@pytest.fixture
def mock_get_course_level_success_response():
    """Mock a successful course level API response"""
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "course_level": "CL001"
        }
        mock_post.return_value = mock_response
        yield mock_post


@pytest.fixture
def mock_get_course_level_invalid_api_key_response():
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
def mock_get_course_level_missing_fields_response():
    """Mock a response for missing required fields"""
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "status": "error",
            "message": "All fields are required"
        }
        mock_post.return_value = mock_response
        yield mock_post


@pytest.fixture
def mock_get_course_level_invalid_batch_response():
    """Mock a response for invalid batch keyword"""
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {
            "status": "error",
            "message": "Invalid batch_skeyword"
        }
        mock_post.return_value = mock_response
        yield mock_post


@pytest.fixture
def mock_get_course_level_invalid_vertical_response():
    """Mock a response for invalid vertical"""
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {
            "status": "error",
            "message": "Invalid vertical label"
        }
        mock_post.return_value = mock_response
        yield mock_post


@pytest.fixture
def mock_get_course_level_error_response():
    """Mock a response for general error"""
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {
            "status": "error",
            "message": "Something went wrong"
        }
        mock_post.return_value = mock_response
        yield mock_post

#! ----------------------------------- END OF FIXTURES ----------------------------------------------------------


# ---------------------------------- START OF TEST CASES --------------------------------------------------------------
def test_get_course_level_success(mock_get_course_level_success_response):
    """Test successful retrieval of course level"""
    # Make API request with valid parameters
    response = requests.post(
        f"{BASE_URL}/api/method/tap_lms.api.get_course_level_api",
        data={
            "api_key": TEST_API_KEY,
            "grade": TEST_GRADE,
            "vertical": TEST_VERTICAL,
            "batch_skeyword": TEST_BATCH_KEYWORD
        }
    )
    
    # Assert that the API was called
    mock_get_course_level_success_response.assert_called_once()
    
    # Check response status code and content
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["course_level"] == "CL001"


def test_get_course_level_invalid_api_key(mock_get_course_level_invalid_api_key_response):
    """Test with invalid API key"""
    # Make API request with invalid API key
    response = requests.post(
        f"{BASE_URL}/api/method/tap_lms.api.get_course_level_api",
        data={
            "api_key": "invalid_key",
            "grade": TEST_GRADE,
            "vertical": TEST_VERTICAL,
            "batch_skeyword": TEST_BATCH_KEYWORD
        }
    )
    
    # Assert that the API was called
    mock_get_course_level_invalid_api_key_response.assert_called_once()
    
    # Check response status code and content
    assert response.status_code == 401
    data = response.json()
    assert data["status"] == "error"
    assert data["message"] == "Invalid API key"


def test_get_course_level_missing_grade(mock_get_course_level_missing_fields_response):
    """Test with missing grade field"""
    # Make API request without grade
    response = requests.post(
        f"{BASE_URL}/api/method/tap_lms.api.get_course_level_api",
        data={
            "api_key": TEST_API_KEY,
            # grade is missing
            "vertical": TEST_VERTICAL,
            "batch_skeyword": TEST_BATCH_KEYWORD
        }
    )
    
    # Assert that the API was called
    mock_get_course_level_missing_fields_response.assert_called_once()
    
    # Check response status code and content
    assert response.status_code == 400
    data = response.json()
    assert data["status"] == "error"
    assert data["message"] == "All fields are required"


def test_get_course_level_missing_vertical(mock_get_course_level_missing_fields_response):
    """Test with missing vertical field"""
    # Make API request without vertical
    response = requests.post(
        f"{BASE_URL}/api/method/tap_lms.api.get_course_level_api",
        data={
            "api_key": TEST_API_KEY,
            "grade": TEST_GRADE,
            # vertical is missing
            "batch_skeyword": TEST_BATCH_KEYWORD
        }
    )
    
    # Assert that the API was called
    mock_get_course_level_missing_fields_response.assert_called_once()
    
    # Check response status code and content
    assert response.status_code == 400
    data = response.json()
    assert data["status"] == "error"
    assert data["message"] == "All fields are required"


def test_get_course_level_invalid_batch(mock_get_course_level_invalid_batch_response):
    """Test with invalid batch keyword"""
    # Make API request with invalid batch keyword
    response = requests.post(
        f"{BASE_URL}/api/method/tap_lms.api.get_course_level_api",
        data={
            "api_key": TEST_API_KEY,
            "grade": TEST_GRADE,
            "vertical": TEST_VERTICAL,
            "batch_skeyword": "INVALID_BATCH"
        }
    )
    
    # Assert that the API was called
    mock_get_course_level_invalid_batch_response.assert_called_once()
    
    # Check response status code and content
    assert response.status_code == 404
    data = response.json()
    assert data["status"] == "error"
    assert data["message"] == "Invalid batch_skeyword"


def test_get_course_level_invalid_vertical(mock_get_course_level_invalid_vertical_response):
    """Test with invalid vertical"""
    # Make API request with invalid vertical
    response = requests.post(
        f"{BASE_URL}/api/method/tap_lms.api.get_course_level_api",
        data={
            "api_key": TEST_API_KEY,
            "grade": TEST_GRADE,
            "vertical": "InvalidVertical",
            "batch_skeyword": TEST_BATCH_KEYWORD
        }
    )
    
    # Assert that the API was called
    mock_get_course_level_invalid_vertical_response.assert_called_once()
    
    # Check response status code and content
    assert response.status_code == 404
    data = response.json()
    assert data["status"] == "error"
    assert data["message"] == "Invalid vertical label"


def test_get_course_level_error(mock_get_course_level_error_response):
    """Test with server error"""
    # Make API request
    response = requests.post(
        f"{BASE_URL}/api/method/tap_lms.api.get_course_level_api",
        data={
            "api_key": TEST_API_KEY,
            "grade": TEST_GRADE,
            "vertical": TEST_VERTICAL,
            "batch_skeyword": TEST_BATCH_KEYWORD
        }
    )
    
    # Assert that the API was called
    mock_get_course_level_error_response.assert_called_once()
    
    # Check response status code and content
    assert response.status_code == 500
    data = response.json()
    assert data["status"] == "error"
    assert data["message"] == "Something went wrong"