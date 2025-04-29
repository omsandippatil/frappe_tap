import pytest
import requests
from unittest.mock import patch, MagicMock

# Base URL for the API
BASE_URL = "http://localhost:8080"

# Test data
TEST_API_KEY = "valid_api_key"
TEST_KEYWORD = "teacher_registered_successfully"
TEST_FIRST_NAME = "Allu"
TEST_LAST_NAME = "Arjun"
TEST_PHONE_NUMBER = "1234567890"
TEST_GLIFIC_ID = "glific_001"

# -------------------------------------- START OF FIXTURES -------------------------------------------------------

@pytest.fixture
def mock_create_teacher_success():
    """Mock a successful teacher creation response"""
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "message": "Teacher created successfully",
            "teacher_id": "TEA-0001"
        }
        mock_post.return_value = mock_response
        yield mock_post

@pytest.fixture
def mock_create_teacher_invalid_api_key():
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
def mock_create_teacher_missing_fields():
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
def mock_create_teacher_school_not_found():
    """Mock a response when school is not found"""
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {
            "status": "error",
            "message": "School not found"
        }
        mock_post.return_value = mock_response
        yield mock_post

@pytest.fixture
def mock_create_teacher_server_error():
    """Mock a response for server error"""
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {
            "status": "error",
            "message": "Something went wrong"
        }
        mock_post.return_value = mock_response
        yield mock_post

# -------------------------------------- END OF FIXTURES -------------------------------------------------------

# -------------------------------------- START OF TEST CASES -------------------------------------------------------

def test_create_teacher_success(mock_create_teacher_success):
    """Test creating a teacher with valid data"""
    response = requests.post(
        f"{BASE_URL}/api/method/tap_lms.api.create_teacher_web",
        data={
            "api_key": TEST_API_KEY,
            "keyword": TEST_KEYWORD,
            "first_name": TEST_FIRST_NAME,
            "last_name": TEST_LAST_NAME,
            "phone_number": TEST_PHONE_NUMBER,
            "glific_id": TEST_GLIFIC_ID
        }
    )
    mock_create_teacher_success.assert_called_once()
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["message"] == "Teacher created successfully"
    assert data["teacher_id"] == "TEA-0001"

def test_create_teacher_invalid_api_key(mock_create_teacher_invalid_api_key):
    """Test creating a teacher with invalid API key"""
    response = requests.post(
        f"{BASE_URL}/api/method/tap_lms.api.create_teacher_web",
        data={
            "api_key": "invalid_key",
            "keyword": TEST_KEYWORD,
            "first_name": TEST_FIRST_NAME,
            "last_name": TEST_LAST_NAME,
            "phone_number": TEST_PHONE_NUMBER,
            "glific_id": TEST_GLIFIC_ID
        }
    )
    mock_create_teacher_invalid_api_key.assert_called_once()
    assert response.status_code == 401
    data = response.json()
    assert data["status"] == "error"
    assert data["message"] == "Invalid API key"

def test_create_teacher_missing_fields(mock_create_teacher_missing_fields):
    """Test creating a teacher with missing required fields"""
    response = requests.post(
        f"{BASE_URL}/api/method/tap_lms.api.create_teacher_web",
        data={
            "api_key": TEST_API_KEY,
            "keyword": TEST_KEYWORD,
            # Missing first_name, last_name, phone_number, glific_id
        }
    )
    mock_create_teacher_missing_fields.assert_called_once()
    assert response.status_code == 400
    data = response.json()
    assert data["status"] == "error"
    assert data["message"] == "All fields are required"

def test_create_teacher_school_not_found(mock_create_teacher_school_not_found):
    """Test creating a teacher when school is not found"""
    response = requests.post(
        f"{BASE_URL}/api/method/tap_lms.api.create_teacher_web",
        data={
            "api_key": TEST_API_KEY,
            "keyword": "invalid_keyword",
            "first_name": TEST_FIRST_NAME,
            "last_name": TEST_LAST_NAME,
            "phone_number": TEST_PHONE_NUMBER,
            "glific_id": TEST_GLIFIC_ID
        }
    )
    mock_create_teacher_school_not_found.assert_called_once()
    assert response.status_code == 404
    data = response.json()
    assert data["status"] == "error"
    assert data["message"] == "School not found"

def test_create_teacher_server_error(mock_create_teacher_server_error):
    """Test creating a teacher when server error occurs"""
    response = requests.post(
        f"{BASE_URL}/api/method/tap_lms.api.create_teacher_web",
        data={
            "api_key": TEST_API_KEY,
            "keyword": TEST_KEYWORD,
            "first_name": TEST_FIRST_NAME,
            "last_name": TEST_LAST_NAME,
            "phone_number": TEST_PHONE_NUMBER,
            "glific_id": TEST_GLIFIC_ID
        }
    )
    mock_create_teacher_server_error.assert_called_once()
    assert response.status_code == 500
    data = response.json()
    assert data["status"] == "error"
    assert data["message"] == "Something went wrong"

# -------------------------------------- END OF TEST CASES -------------------------------------------------------
