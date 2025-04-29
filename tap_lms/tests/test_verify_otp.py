import pytest
import requests
import json
from unittest.mock import patch, MagicMock

# Base URL for the API
BASE_URL = "http://localhost:8080" 

# Test data
TEST_API_KEY = "test_api_key"
TEST_PHONE = "1234567890"
TEST_OTP = "123456"

#! -------------------------------------- START OF FIXTURES -------------------------------------------------------
@pytest.fixture
def mock_verify_otp_success_response():
    """Mock a successful OTP verification response"""
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "message": "Phone number verified successfully"
        }
        mock_post.return_value = mock_response
        yield mock_post


@pytest.fixture
def mock_verify_otp_invalid_api_key_response():
    """Mock an invalid API key response"""
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
def mock_verify_otp_missing_params_response():
    """Mock a missing parameters response"""
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "status": "failure",
            "message": "Phone number and OTP are required"
        }
        mock_post.return_value = mock_response
        yield mock_post


@pytest.fixture
def mock_verify_otp_invalid_otp_response():
    """Mock an invalid OTP response"""
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "status": "failure",
            "message": "Invalid OTP"
        }
        mock_post.return_value = mock_response
        yield mock_post


@pytest.fixture
def mock_verify_otp_expired_response():
    """Mock an expired OTP response"""
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "status": "failure",
            "message": "OTP has expired"
        }
        mock_post.return_value = mock_response
        yield mock_post


@pytest.fixture
def mock_verify_otp_error_response():
    """Mock a server error response"""
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {
            "status": "failure",
            "message": "An error occurred during OTP verification"
        }
        mock_post.return_value = mock_response
        yield mock_post

#! ----------------------------------- END OF FIXTURES ----------------------------------------------------------


# ---------------------------------- START OF TEST CASES --------------------------------------------------------------
def test_verify_otp_success(mock_verify_otp_success_response):
    """Test successful OTP verification"""
    # Make API request
    response = requests.post(
        f"{BASE_URL}/api/method/tap_lms.api.verify_otp",
        data={
            "api_key": TEST_API_KEY,
            "phone": TEST_PHONE,
            "otp": TEST_OTP
        }
    )
    
    # Assert that the API was called
    mock_verify_otp_success_response.assert_called_once()
    
    # Check response status code and content
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "Phone number verified successfully" in data["message"]


def test_verify_otp_invalid_api_key(mock_verify_otp_invalid_api_key_response):
    """Test OTP verification with invalid API key"""
    # Make API request
    response = requests.post(
        f"{BASE_URL}/api/method/tap_lms.api.verify_otp",
        data={
            "api_key": "invalid_key",
            "phone": TEST_PHONE,
            "otp": TEST_OTP
        }
    )
    
    # Assert that the API was called
    mock_verify_otp_invalid_api_key_response.assert_called_once()
    
    # Check response status code and content
    assert response.status_code == 401
    data = response.json()
    assert data["status"] == "failure"
    assert "Invalid API key" in data["message"]


def test_verify_otp_missing_phone(mock_verify_otp_missing_params_response):
    """Test OTP verification with missing phone number"""
    # Make API request without phone
    response = requests.post(
        f"{BASE_URL}/api/method/tap_lms.api.verify_otp",
        data={
            "api_key": TEST_API_KEY,
            "otp": TEST_OTP
            # Missing phone
        }
    )
    
    # Assert that the API was called
    mock_verify_otp_missing_params_response.assert_called_once()
    
    # Check response status code and content
    assert response.status_code == 400
    data = response.json()
    assert data["status"] == "failure"
    assert "Phone number and OTP are required" in data["message"]


def test_verify_otp_missing_otp(mock_verify_otp_missing_params_response):
    """Test OTP verification with missing OTP"""
    # Make API request without OTP
    response = requests.post(
        f"{BASE_URL}/api/method/tap_lms.api.verify_otp",
        data={
            "api_key": TEST_API_KEY,
            "phone": TEST_PHONE
            # Missing OTP
        }
    )
    
    # Assert that the API was called
    mock_verify_otp_missing_params_response.assert_called_once()
    
    # Check response status code and content
    assert response.status_code == 400
    data = response.json()
    assert data["status"] == "failure"
    assert "Phone number and OTP are required" in data["message"]


def test_verify_otp_invalid_otp(mock_verify_otp_invalid_otp_response):
    """Test OTP verification with invalid OTP"""
    # Make API request with invalid OTP
    response = requests.post(
        f"{BASE_URL}/api/method/tap_lms.api.verify_otp",
        data={
            "api_key": TEST_API_KEY,
            "phone": TEST_PHONE,
            "otp": "999999"  # Invalid OTP
        }
    )
    
    # Assert that the API was called
    mock_verify_otp_invalid_otp_response.assert_called_once()
    
    # Check response status code and content
    assert response.status_code == 400
    data = response.json()
    assert data["status"] == "failure"
    assert "Invalid OTP" in data["message"]


def test_verify_otp_expired(mock_verify_otp_expired_response):
    """Test OTP verification with expired OTP"""
    # Make API request with expired OTP
    response = requests.post(
        f"{BASE_URL}/api/method/tap_lms.api.verify_otp",
        data={
            "api_key": TEST_API_KEY,
            "phone": TEST_PHONE,
            "otp": TEST_OTP  # Expired OTP
        }
    )
    
    # Assert that the API was called
    mock_verify_otp_expired_response.assert_called_once()
    
    # Check response status code and content
    assert response.status_code == 400
    data = response.json()
    assert data["status"] == "failure"
    assert "OTP has expired" in data["message"]


def test_verify_otp_server_error(mock_verify_otp_error_response):
    """Test OTP verification with server error"""
    # Make API request
    response = requests.post(
        f"{BASE_URL}/api/method/tap_lms.api.verify_otp",
        data={
            "api_key": TEST_API_KEY,
            "phone": TEST_PHONE,
            "otp": TEST_OTP
        }
    )
    
    # Assert that the API was called
    mock_verify_otp_error_response.assert_called_once()
    
    # Check response status code and content
    assert response.status_code == 500
    data = response.json()
    assert data["status"] == "failure"
    assert "An error occurred during OTP verification" in data["message"]