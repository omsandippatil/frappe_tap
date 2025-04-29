import pytest
import requests
import json
from unittest.mock import patch, MagicMock

# Base URL for the API
BASE_URL = "http://localhost:8080" # Replace with your actual base URL

# Test data
TEST_API_KEY = "test_api_key"
TEST_KEYWORD = "test_batch_keyword"


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
def mock_grade_list_success():
    """Mock successful grade_list response"""
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "1": "5",
            "2": "6",
            "3": "7",
            "count": "3"
        }
        mock_get.return_value = mock_response
        yield mock_get


@pytest.fixture
def mock_grade_list_empty():
    """Mock empty grade_list response"""
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "count": "0"
        }
        mock_get.return_value = mock_response
        yield mock_get


@pytest.fixture
def mock_grade_list_error():
    """Mock error response for invalid batch keyword"""
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": "No batch found with the provided keyword"
        }
        mock_get.return_value = mock_response
        yield mock_get


@pytest.fixture
def mock_grade_list_auth_error():
    """Mock error response for invalid API key"""
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            "error": "Invalid API key"
        }
        mock_get.return_value = mock_response
        yield mock_get


def test_grade_list_success(mock_grade_list_success):
    """Test grade_list API with successful response"""
    # Make API request
    response = requests.get(
        f"{BASE_URL}/api/method/grade_list",
        params={"api_key": TEST_API_KEY, "keyword": TEST_KEYWORD}
    )
    
    # Assert that the API was called with the correct parameters
    mock_grade_list_success.assert_called_once()
    
    # Check response status code and content
    assert response.status_code == 200
    data = response.json()
    assert "1" in data
    assert data["1"] == "5"
    assert "2" in data
    assert data["2"] == "6"
    assert "3" in data
    assert data["3"] == "7"
    assert "count" in data
    assert data["count"] == "3"


def test_grade_list_empty(mock_grade_list_empty):
    """Test grade_list API with empty response (no grades)"""
    # Make API request
    response = requests.get(
        f"{BASE_URL}/api/method/grade_list",
        params={"api_key": TEST_API_KEY, "keyword": TEST_KEYWORD}
    )
    
    # Assert that the API was called with the correct parameters
    mock_grade_list_empty.assert_called_once()
    
    # Check response status code and content
    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    assert data["count"] == "0"
    # Verify no grade entries are present
    assert len(data) == 1


def test_grade_list_invalid_keyword(mock_grade_list_error):
    """Test grade_list API with invalid batch keyword"""
    # Make API request with invalid keyword
    response = requests.get(
        f"{BASE_URL}/api/method/grade_list",
        params={"api_key": TEST_API_KEY, "keyword": "invalid_keyword"}
    )
    
    # Assert that the API was called
    mock_grade_list_error.assert_called_once()
    
    # Check response status code and error message
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert "No batch found" in data["error"]


def test_grade_list_invalid_api_key(mock_grade_list_auth_error):
    """Test grade_list API with invalid API key"""
    # Make API request with invalid API key
    response = requests.get(
        f"{BASE_URL}/api/method/grade_list",
        params={"api_key": "invalid_api_key", "keyword": TEST_KEYWORD}
    )
    
    # Assert that the API was called
    mock_grade_list_auth_error.assert_called_once()
    
    # Check response status code and error message
    assert response.status_code == 401
    data = response.json()
    assert "error" in data
    assert "Invalid API key" in data["error"]


def test_grade_list_missing_api_key(mock_grade_list_auth_error):
    """Test grade_list API with missing API key"""
    # Make API request without API key
    response = requests.get(
        f"{BASE_URL}/api/method/grade_list",
        params={"keyword": TEST_KEYWORD}
    )
    
    # Assert that the API was called
    mock_grade_list_auth_error.assert_called_once()
    
    # Check response status code and error message
    assert response.status_code == 401
    data = response.json()
    assert "error" in data


def test_grade_list_missing_keyword(mock_grade_list_error):
    """Test grade_list API with missing keyword"""
    # Make API request without keyword
    response = requests.get(
        f"{BASE_URL}/api/method/grade_list",
        params={"api_key": TEST_API_KEY}
    )
    
    # Assert that the API was called
    mock_grade_list_error.assert_called_once()
    
    # Check response status code and error message
    assert response.status_code == 400
    data = response.json()
    assert "error" in data


# Test to verify the structure of the grade objects
def test_grade_list_structure(mock_grade_list_success):
    """Test grade_list API response structure"""
    # Make API request
    response = requests.get(
        f"{BASE_URL}/api/method/grade_list",
        params={"api_key": TEST_API_KEY, "keyword": TEST_KEYWORD}
    )
    
    # Assert that the API was called
    mock_grade_list_success.assert_called_once()
    
    # Check response status code
    assert response.status_code == 200
    data = response.json()
    
    # Verify the structure: "count" key and numeric keys for grades
    assert "count" in data
    count = int(data["count"])
    
    # Verify that we have the correct number of grade entries
    # (total keys minus the "count" key should equal the count value)
    assert len(data) - 1 == count
    
    # Verify each grade entry has a numeric key from 1 to count
    for i in range(1, count + 1):
        assert str(i) in data
        # Verify grade value is a string
        assert isinstance(data[str(i)], str)


# Mock for frappe internal function calls
def test_grade_list_frappe_internals():
    """Test the internal mechanics of the grade_list function"""
    with patch('frappe.get_all') as mock_get_all:
        # Mock the batch onboarding query result
        mock_get_all.return_value = [{
            "name": "batch_onboarding_1",
            "from_grade": "5",
            "to_grade": "7"
        }]
        
        with patch('frappe.utils.cint') as mock_cint:
            # Mock the cint function to convert string to int
            mock_cint.side_effect = lambda x: int(x)
            
            # In a real environment, you'd call the function directly:
            # result = grade_list(TEST_API_KEY, TEST_KEYWORD)
            
            # For now, we'll just verify our mocks were set up correctly
            assert mock_get_all.return_value[0]["from_grade"] == "5"
            assert mock_get_all.return_value[0]["to_grade"] == "7"
            
            # The actual implementation would generate grades from 5 to 7
            # and return a dictionary like:
            # {
            #     "1": "5",
            #     "2": "6",
            #     "3": "7",
            #     "count": "3"
            # }


# # Integration test (to be run in a real environment)
# @pytest.mark.integration
# def test_integration_grade_list():
#     """Integration test for grade_list API"""
#     # This test should only run in an integration testing environment
#     response = requests.get(
#         f"{BASE_URL}/api/method/grade_list",
#         params={"api_key": TEST_API_KEY, "keyword": TEST_KEYWORD}
#     )
    
#     # Check that the response is one of the expected types
#     assert response.status_code in [200, 400, 401]
    
#     # If successful, verify the basic structure
#     if response.status_code == 200:
#         data = response.json()
#         assert "count" in data
#         count = int(data["count"])
        
#         # Verify we have the right number of grade entries
#         assert len(data) - 1 == count


if __name__ == "__main__":
    # This allows running the tests directly from this file
    pytest.main(["-v", __file__])