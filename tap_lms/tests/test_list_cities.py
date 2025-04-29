import pytest
import requests
import json
from unittest.mock import patch, MagicMock

# Base URL for the API
BASE_URL = "http://localhost:8080" 

# Test data
TEST_API_KEY = "testapikey456"
TEST_DISTRICT = "Thrissur"
TEST_CITY_ID = "CITY001"
TEST_CITY_NAME = "Irinjalakuda"

#! -------------------------------------- START OF FIXTURES -------------------------------------------------------
@pytest.fixture
def mock_list_cities_success_response():
    """Mock a successful cities list response"""
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                TEST_CITY_ID: TEST_CITY_NAME
            },
            "message": "Cities retrieved successfully"
        }
        mock_post.return_value = mock_response
        yield mock_post


@pytest.fixture
def mock_list_cities_invalid_api_key_response():
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
def mock_list_cities_missing_fields_response():
    """Mock a response for missing required fields"""
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "status": "error",
            "message": "API key and district are required"
        }
        mock_post.return_value = mock_response
        yield mock_post


@pytest.fixture
def mock_list_cities_district_not_found_response():
    """Mock a response for district not found"""
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {
            "status": "error",
            "message": "District not found"
        }
        mock_post.return_value = mock_response
        yield mock_post

#! ----------------------------------- END OF FIXTURES ----------------------------------------------------------


# ---------------------------------- START OF TEST CASES --------------------------------------------------------------
def test_list_cities_success(mock_list_cities_success_response):
    """Test successful fetch of cities"""
    # Make API request with valid parameters
    response = requests.post(
        f"{BASE_URL}/api/method/tap_lms.api.list_cities",
        data={
            "api_key": TEST_API_KEY,
            "district": TEST_DISTRICT
        }
    )
    
    # Assert that the API was called with the correct parameters
    mock_list_cities_success_response.assert_called_once()
    
    # Check response status code and content
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert TEST_CITY_ID in data["data"]
    assert data["data"][TEST_CITY_ID] == TEST_CITY_NAME


def test_list_cities_invalid_api_key(mock_list_cities_invalid_api_key_response):
    """Test with invalid API Key"""
    # Make API request with invalid API key
    response = requests.post(
        f"{BASE_URL}/api/method/tap_lms.api.list_cities",
        data={
            "api_key": "wrongapikey",
            "district": TEST_DISTRICT
        }
    )
    
    # Assert that the API was called
    mock_list_cities_invalid_api_key_response.assert_called_once()
    
    # Check response status code and content
    assert response.status_code == 401
    data = response.json()
    assert data["status"] == "error"
    assert data["message"] == "Invalid API key"


def test_list_cities_missing_fields(mock_list_cities_missing_fields_response):
    """Test missing API Key or District"""
    # Make API request without district
    response = requests.post(
        f"{BASE_URL}/api/method/tap_lms.api.list_cities",
        data={
            "api_key": TEST_API_KEY
            # district is missing
        }
    )
    
    # Assert that the API was called
    mock_list_cities_missing_fields_response.assert_called_once()
    
    # Check response status code and content
    assert response.status_code == 400
    data = response.json()
    assert data["status"] == "error"
    assert data["message"] == "API key and district are required"


def test_list_cities_district_not_found(mock_list_cities_district_not_found_response):
    """Test with non-existent district"""
    # Make API request with non-existent district
    response = requests.post(
        f"{BASE_URL}/api/method/tap_lms.api.list_cities",
        data={
            "api_key": TEST_API_KEY,
            "district": "NonExistentDistrict"
        }
    )
    
    # Assert that the API was called
    mock_list_cities_district_not_found_response.assert_called_once()
    
    # Check response status code and content
    assert response.status_code == 404
    data = response.json()
    assert data["status"] == "error"
    assert data["message"] == "District not found"