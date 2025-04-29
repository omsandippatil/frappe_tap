import pytest
import requests
import json
from unittest.mock import patch, MagicMock

# Base URL for the API
BASE_URL = "http://localhost:8080" 

# Test data
TEST_API_KEY = "test_api_key"
TEST_KEYWORD = "test_keyword"

#- Fixture - these are kind of preperation steps that run before a test
#! -------------------------------------- START OF FIXTURES -------------------------------------------------------
@pytest.fixture
def mock_authenticate_api_key():
    """Mock the authenticate_api_key function to return True for test_api_key"""
    with patch('frappe.whitelist') as mock_whitelist:
        # Configure the mock decorator to pass through the decorated function
        mock_whitelist.return_value = lambda func: func
        
        with patch('frappe.utils.cint', return_value=0):
            with patch('frappe.utils.today', return_value='2023-01-01'):
                with patch('frappe.utils.get_url', return_value='http://test.com'):
                    with patch('frappe.utils.now_datetime') as mock_now:
                        mock_now.return_value = '2023-01-01 12:00:00'
                        
                        # Mock the authentication function
                        with patch('frappe.get_doc') as mock_get_doc:
                            mock_api_key_doc = MagicMock()
                            mock_api_key_doc.name = "test_api_key_doc"
                            mock_get_doc.return_value = mock_api_key_doc
                            yield


@pytest.fixture
def mock_course_vertical_list_response():
    """Mock the course_vertical_list API response"""
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "vertical_id1": "Math",
            "vertical_id2": "Science",
            "vertical_id3": "English"
        }
        mock_post.return_value = mock_response
        yield mock_post


@pytest.fixture
def mock_course_vertical_list_count_response():
    """Mock the course_vertical_list_count API response"""
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "1": "Math",
            "2": "Science",
            "3": "English",
            "count": "3"
        }
        mock_post.return_value = mock_response
        yield mock_post


@pytest.fixture
def mock_batch_onboarding_not_found():
    """Mock batch onboarding not found response"""
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {
            "error": "Invalid batch keyword"
        }
        mock_post.return_value = mock_response
        yield mock_post

#! ----------------------------------- END OF FIXTURES ----------------------------------------------------------


# ---------------------------------- START OF TEST CASES --------------------------------------------------------------
#? VERTICAL LIST API
def test_course_vertical_list_success(mock_course_vertical_list_response):
    """1. Test course_vertical_list API with successful response"""
    # Make API request
    response = requests.post(
        f"{BASE_URL}/api/method/course_vertical_list",
        data={"api_key": TEST_API_KEY, "keyword": TEST_KEYWORD}
    )
    
    # Assert that the API was called with the correct parameters
    mock_course_vertical_list_response.assert_called_once()
    
    # Check response status code and content
    assert response.status_code == 200
    data = response.json()
    assert "vertical_id1" in data #! check thesee vertical id by sending a sample request
    assert data["vertical_id1"] == "Math"
    assert "vertical_id2" in data
    assert data["vertical_id2"] == "Science"
    assert "vertical_id3" in data
    assert data["vertical_id3"] == "English"


def test_course_vertical_list_missing_api_key(mock_batch_onboarding_not_found):
    """2. Test course_vertical_list API with missing API key"""
    # Make API request without API key
    response = requests.post(
        f"{BASE_URL}/api/method/course_vertical_list",
        data={"keyword": TEST_KEYWORD}
    )
    
    # Assert that the API was called
    mock_batch_onboarding_not_found.assert_called_once()
    
    # Check response status code and error message
    assert response.status_code == 404
    data = response.json()
    assert "error" in data


def test_course_vertical_list_missing_keyword(mock_batch_onboarding_not_found):
    """3. Test course_vertical_list API with missing keyword"""
    # Make API request without keyword
    response = requests.post(
        f"{BASE_URL}/api/method/course_vertical_list",
        data={"api_key": TEST_API_KEY}
    )
    
    # Assert that the API was called
    mock_batch_onboarding_not_found.assert_called_once()
    
    # Check response status code and error message
    assert response.status_code == 404
    data = response.json()
    assert "error" in data


def test_course_vertical_list_invalid_api_key(mock_batch_onboarding_not_found):
    """4. Test course_vertical_list API with invalid API key"""
    # Make API request with invalid API key
    response = requests.post(
        f"{BASE_URL}/api/method/course_vertical_list",
        data={"api_key": "invalid_key", "keyword": TEST_KEYWORD}
    )
    
    # Assert that the API was called
    mock_batch_onboarding_not_found.assert_called_once()
    
    # Check response status code and error message
    assert response.status_code == 404
    data = response.json()
    assert "error" in data

#!=============================================================================================

#? VERTICAL LIST COUNT API
def test_course_vertical_list_count_success(mock_course_vertical_list_count_response):
    """5. Test course_vertical_list_count API with successful response"""
    # Make API request
    response = requests.post(
        f"{BASE_URL}/api/method/course_vertical_list_count",
        data={"api_key": TEST_API_KEY, "keyword": TEST_KEYWORD}
    )
    
    # Assert that the API was called with the correct parameters
    mock_course_vertical_list_count_response.assert_called_once()
    
    # Check response status code and content
    assert response.status_code == 200
    data = response.json()
    assert "1" in data
    assert data["1"] == "Math"
    assert "2" in data
    assert data["2"] == "Science"
    assert "3" in data
    assert data["3"] == "English"
    assert "count" in data
    assert data["count"] == "3"


def test_course_vertical_list_count_missing_api_key(mock_batch_onboarding_not_found):
    """6. Test course_vertical_list_count API with missing API key"""
    # Make API request without API key
    response = requests.post(
        f"{BASE_URL}/api/method/course_vertical_list_count",
        data={"keyword": TEST_KEYWORD}
    )
    
    # Assert that the API was called
    mock_batch_onboarding_not_found.assert_called_once()
    
    # Check response status code and error message
    assert response.status_code == 404
    data = response.json()
    assert "error" in data


def test_course_vertical_list_count_missing_keyword(mock_batch_onboarding_not_found):
    """7. Test course_vertical_list_count API with missing keyword"""
    # Make API request without keyword
    response = requests.post(
        f"{BASE_URL}/api/method/course_vertical_list_count",
        data={"api_key": TEST_API_KEY}
    )
    
    # Assert that the API was called
    mock_batch_onboarding_not_found.assert_called_once()
    
    # Check response status code and error message
    assert response.status_code == 404
    data = response.json()
    assert "error" in data


def test_course_vertical_list_count_invalid_api_key(mock_batch_onboarding_not_found):
    """8. Test course_vertical_list_count API with invalid API key"""
    # Make API request with invalid API key
    response = requests.post(
        f"{BASE_URL}/api/method/course_vertical_list_count",
        data={"api_key": "invalid_key", "keyword": TEST_KEYWORD}
    )
    
    # Assert that the API was called
    mock_batch_onboarding_not_found.assert_called_once()
    
    # Check response status code and error message
    assert response.status_code == 404
    data = response.json()
    assert "error" in data

#!=============================================================================================

#? Integration tests (These would be run in a real environment)
# @pytest.mark.integration
# def test_integration_course_vertical_list():
#     """Integration test for course_vertical_list API"""
#     # This test should only run in integration testing environment
#     response = requests.post(
#         f"{BASE_URL}/api/method/course_vertical_list",
#         data={"api_key": TEST_API_KEY, "keyword": TEST_KEYWORD}
#     )
    
#     # Check response status code
#     assert response.status_code in [200, 404, 401]  # Accept various status codes in integration test


# @pytest.mark.integration
# def test_integration_course_vertical_list_count():
#     """Integration test for course_vertical_list_count API"""
#     # This test should only run in integration testing environment
#     response = requests.post(
#         f"{BASE_URL}/api/method/course_vertical_list_count",
#         data={"api_key": TEST_API_KEY, "keyword": TEST_KEYWORD}
#     )
    
#     # Check response status code
#     assert response.status_code in [200, 404, 401]  # Accept various status codes in integration test



######################################################################################################################

"""

Type	                          Meaning	                                          Example in code
Unit Test	            Test one small isolated part	                         Mock responses of API call
Integration Test	    Test how parts work together in a real setup	         Actually calling localhost APIs

"""

"""
#! Unit Test with Mock (The uncommented Code)
- No real server involved.
- Fake (mocked) the server response.
- Only checking:Did we send the right request?
- If server sends this (fake) response, does our code behave correctly?
- Very fast and isolated.


#! Integration Test (marked with decorator pytest.mark.integration) (The Commented Code)
- Real HTTP call.
- No mocking.
- Server must be running.
- Good to catch issues like: wrong URL, server crashes, missing API methods, etc.
"""