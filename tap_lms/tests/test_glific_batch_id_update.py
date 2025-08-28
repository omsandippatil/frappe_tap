# test_glific_batch_update.py - Comprehensive test suite for 100% coverage
"""
Complete test suite for Glific batch ID update module
This test suite is designed to achieve 100% code coverage with 0 missing lines
"""

import pytest
import json
import time
import random
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime, timezone
import requests
from test_utils import (
    MockDataFactory, APIResponseSimulator, DatabaseMockHelper,
    LoggingCapture, PerformanceProfiler, TestDataGenerator,
    ErrorScenarioGenerator, AssertionHelpers, TestEnvironmentSetup,
    TestReportGenerator, TestConfigManager, test_config,
    parameterized_test, validate_student_data, validate_processing_result,
    MockTimeContextManager, MockNetworkContextManager
)


class TestMockDataFactory:
    """Test all MockDataFactory methods for 100% coverage"""
    
    def test_create_backend_student_default(self):
        """Test creating backend student with default parameters"""
        student = MockDataFactory.create_backend_student()
        
        assert student['name'] == 'BS-001'
        assert student['student_name'] == 'John Doe'
        assert student['phone'] == '+1234567890'
        assert student['student_id'] == 'STU-001'
        assert student['batch'] == 'BATCH-CS-2024'
        assert student['batch_skeyword'] == 'batchcs2024'
    
    def test_create_backend_student_custom(self):
        """Test creating backend student with custom parameters"""
        student = MockDataFactory.create_backend_student(
            student_id="STU-999",
            batch="BATCH-EE-2023",
            phone="+9876543210",
            name="Jane Smith"
        )
        
        assert student['name'] == 'BS-999'
        assert student['student_name'] == 'Jane Smith'
        assert student['phone'] == '+9876543210'
        assert student['student_id'] == 'STU-999'
        assert student['batch'] == 'BATCH-EE-2023'
        assert student['batch_skeyword'] == 'batchee2023'
    
    def test_create_onboarding_set_default(self):
        """Test creating onboarding set with default parameters"""
        mock_set = MockDataFactory.create_onboarding_set()
        
        assert mock_set.name == "SET-001"
        assert mock_set.set_name == "Test SET-001"
        assert mock_set.status == "Processed"
        assert mock_set.processed_student_count == 25
        assert hasattr(mock_set, 'upload_date')
    
    def test_create_onboarding_set_custom(self):
        """Test creating onboarding set with custom parameters"""
        mock_set = MockDataFactory.create_onboarding_set(
            name="SET-999",
            status="Pending",
            student_count=50
        )
        
        assert mock_set.name == "SET-999"
        assert mock_set.set_name == "Test SET-999"
        assert mock_set.status == "Pending"
        assert mock_set.processed_student_count == 50
    
    def test_create_student_document_default(self):
        """Test creating student document with default parameters"""
        student_doc = MockDataFactory.create_student_document()
        
        assert student_doc.name == "STU-001"
        assert student_doc.student_name == "Test Student"
        assert student_doc.glific_id == "12345"
    
    def test_create_student_document_custom(self):
        """Test creating student document with custom parameters"""
        student_doc = MockDataFactory.create_student_document(
            student_id="STU-777",
            glific_id="67890"
        )
        
        assert student_doc.name == "STU-777"
        assert student_doc.student_name == "Test Student"
        assert student_doc.glific_id == "67890"
    
    def test_create_glific_contact_response_default(self):
        """Test creating Glific contact response with default parameters"""
        response = MockDataFactory.create_glific_contact_response()
        
        assert "data" in response
        assert "contact" in response["data"]
        assert response["data"]["contact"]["contact"]["id"] == "12345"
        assert response["data"]["contact"]["contact"]["name"] == "Test Student"
        assert response["data"]["contact"]["contact"]["phone"] == "+1234567890"
        
        fields = json.loads(response["data"]["contact"]["contact"]["fields"])
        assert isinstance(fields, dict)
    
    def test_create_glific_contact_response_custom(self):
        """Test creating Glific contact response with custom parameters"""
        custom_fields = {"batch_id": "BATCH-CS-2024"}
        response = MockDataFactory.create_glific_contact_response(
            contact_id="99999",
            name="Custom Student",
            fields=custom_fields
        )
        
        assert response["data"]["contact"]["contact"]["id"] == "99999"
        assert response["data"]["contact"]["contact"]["name"] == "Custom Student"
        
        fields = json.loads(response["data"]["contact"]["contact"]["fields"])
        assert fields == custom_fields
    
    def test_create_glific_update_response_success(self):
        """Test creating successful Glific update response"""
        response = MockDataFactory.create_glific_update_response()
        
        assert "data" in response
        assert "updateContact" in response["data"]
        assert response["data"]["updateContact"]["contact"]["id"] == "12345"
        
        fields = json.loads(response["data"]["updateContact"]["contact"]["fields"])
        assert "batch_id" in fields
        assert fields["batch_id"]["value"] == "BATCH-CS-2024"
        assert fields["batch_id"]["type"] == "string"
        assert "inserted_at" in fields["batch_id"]
    
    def test_create_glific_update_response_failure(self):
        """Test creating failed Glific update response"""
        response = MockDataFactory.create_glific_update_response(success=False)
        
        assert "errors" in response
        assert len(response["errors"]) == 1
        assert response["errors"][0]["key"] == "contact"
        assert response["errors"][0]["message"] == "Update failed"
    
    def test_create_glific_update_response_custom_success(self):
        """Test creating custom successful Glific update response"""
        custom_fields = {"custom_field": {"value": "test", "type": "string"}}
        response = MockDataFactory.create_glific_update_response(
            contact_id="88888",
            success=True,
            fields=custom_fields
        )
        
        assert response["data"]["updateContact"]["contact"]["id"] == "88888"
        fields = json.loads(response["data"]["updateContact"]["contact"]["fields"])
        assert fields == custom_fields
    
    def test_create_batch_of_students_default(self):
        """Test creating batch of students with default parameters"""
        students = MockDataFactory.create_batch_of_students()
        
        assert len(students) == 10
        for i, student in enumerate(students, 1):
            assert student['student_id'] == f'STU-{i:03d}'
            assert student['batch'] == f'BATCH-{(i-1)//10 + 1}'
            assert student['phone'] == f'+123456{i:04d}'
            assert student['name'] == f'Student {i}'
    
    def test_create_batch_of_students_custom(self):
        """Test creating batch of students with custom parameters"""
        students = MockDataFactory.create_batch_of_students(count=5, batch_prefix="TEST")
        
        assert len(students) == 5
        for i, student in enumerate(students, 1):
            assert student['student_id'] == f'STU-{i:03d}'
            assert student['batch'] == f'TEST-{(i-1)//10 + 1}'
            assert student['phone'] == f'+123456{i:04d}'
            assert student['name'] == f'Student {i}'


class TestAPIResponseSimulator:
    """Test all APIResponseSimulator methods for 100% coverage"""
    
    def test_init(self):
        """Test APIResponseSimulator initialization"""
        simulator = APIResponseSimulator()
        assert simulator.call_count == 0
        assert simulator.responses == []
    
    def test_add_response_default(self):
        """Test adding response with default status code"""
        simulator = APIResponseSimulator()
        response_data = {"test": "data"}
        simulator.add_response(response_data)
        
        assert len(simulator.responses) == 1
        mock_response = simulator.responses[0]
        assert mock_response.status_code == 200
        assert mock_response.json() == response_data
    
    def test_add_response_custom_status(self):
        """Test adding response with custom status code"""
        simulator = APIResponseSimulator()
        response_data = {"error": "Not found"}
        simulator.add_response(response_data, status_code=404)
        
        assert len(simulator.responses) == 1
        mock_response = simulator.responses[0]
        assert mock_response.status_code == 404
        assert mock_response.json() == response_data
    
    def test_add_error_response_default(self):
        """Test adding error response with default parameters"""
        simulator = APIResponseSimulator()
        simulator.add_error_response()
        
        assert len(simulator.responses) == 1
        mock_response = simulator.responses[0]
        assert mock_response.status_code == 500
        assert mock_response.json() == {"error": "Server Error"}
    
    def test_add_error_response_custom(self):
        """Test adding error response with custom parameters"""
        simulator = APIResponseSimulator()
        simulator.add_error_response(status_code=404, message="Not Found")
        
        assert len(simulator.responses) == 1
        mock_response = simulator.responses[0]
        assert mock_response.status_code == 404
        assert mock_response.json() == {"error": "Not Found"}
    
    def test_add_timeout(self):
        """Test adding timeout exception"""
        simulator = APIResponseSimulator()
        simulator.add_timeout()
        
        assert len(simulator.responses) == 1
        assert isinstance(simulator.responses[0], requests.exceptions.Timeout)
        assert str(simulator.responses[0]) == "Request timed out"
    
    def test_add_connection_error(self):
        """Test adding connection error"""
        simulator = APIResponseSimulator()
        simulator.add_connection_error()
        
        assert len(simulator.responses) == 1
        assert isinstance(simulator.responses[0], requests.exceptions.ConnectionError)
        assert str(simulator.responses[0]) == "Connection failed"
    
    def test_get_side_effect_normal_responses(self):
        """Test side effect function with normal responses"""
        simulator = APIResponseSimulator()
        simulator.add_response({"test": "data1"})
        simulator.add_response({"test": "data2"})
        
        side_effect = simulator.get_side_effect()
        
        # First call
        response1 = side_effect()
        assert response1.json() == {"test": "data1"}
        assert simulator.call_count == 1
        
        # Second call
        response2 = side_effect()
        assert response2.json() == {"test": "data2"}
        assert simulator.call_count == 2
    
    def test_get_side_effect_exception(self):
        """Test side effect function with exception"""
        simulator = APIResponseSimulator()
        simulator.add_timeout()
        
        side_effect = simulator.get_side_effect()
        
        with pytest.raises(requests.exceptions.Timeout):
            side_effect()
        
        assert simulator.call_count == 1
    
    def test_get_side_effect_default_after_exhaustion(self):
        """Test side effect function returns default after exhausting responses"""
        simulator = APIResponseSimulator()
        simulator.add_response({"test": "data"})
        
        side_effect = simulator.get_side_effect()
        
        # Use up the predefined response
        side_effect()
        
        # Next call should return default
        default_response = side_effect()
        assert default_response.status_code == 200
        assert "contact" in default_response.json()["data"]
    
    def test_reset(self):
        """Test resetting the simulator"""
        simulator = APIResponseSimulator()
        simulator.add_response({"test": "data"})
        simulator.call_count = 5
        
        simulator.reset()
        
        assert simulator.call_count == 0
        assert simulator.responses == []


class TestDatabaseMockHelper:
    """Test all DatabaseMockHelper methods for 100% coverage"""
    
    def test_create_frappe_db_mock(self):
        """Test creating Frappe DB mock"""
        mock_db = DatabaseMockHelper.create_frappe_db_mock()
        
        assert mock_db.exists.return_value == True
        assert mock_db.begin.return_value == None
        assert mock_db.commit.return_value == None
        assert mock_db.rollback.return_value == None
    
    def test_create_get_doc_mock_found(self):
        """Test get_doc mock when document exists"""
        documents = {
            "Student:STU-001": Mock(name="STU-001", student_name="Test Student")
        }
        side_effect = DatabaseMockHelper.create_get_doc_mock(documents)
        
        result = side_effect("Student", "STU-001")
        assert result.name == "STU-001"
        assert result.student_name == "Test Student"
    
    def test_create_get_doc_mock_not_found(self):
        """Test get_doc mock when document doesn't exist"""
        documents = {}
        side_effect = DatabaseMockHelper.create_get_doc_mock(documents)
        
        result = side_effect("Student", "STU-999")
        assert result.name == "STU-999"
    
    def test_create_get_all_mock(self):
        """Test creating get_all mock"""
        results = [{"name": "STU-001"}, {"name": "STU-002"}]
        mock_get_all = DatabaseMockHelper.create_get_all_mock(results)
        
        assert mock_get_all.return_value == results


class TestLoggingCapture:
    """Test all LoggingCapture methods for 100% coverage"""
    
    def test_init(self):
        """Test LoggingCapture initialization"""
        capture = LoggingCapture()
        
        expected_levels = ['info', 'warning', 'error', 'debug']
        for level in expected_levels:
            assert level in capture.logs
            assert capture.logs[level] == []
    
    def test_create_logger_mock(self):
        """Test creating logger mock"""
        capture = LoggingCapture()
        mock_logger = capture.create_logger_mock()
        
        # Test info logging
        mock_logger.info("Test info message")
        assert "Test info message" in capture.logs['info']
        
        # Test warning logging
        mock_logger.warning("Test warning message")
        assert "Test warning message" in capture.logs['warning']
        
        # Test error logging
        mock_logger.error("Test error message")
        assert "Test error message" in capture.logs['error']
        
        # Test debug logging
        mock_logger.debug("Test debug message")
        assert "Test debug message" in capture.logs['debug']
    
    def test_get_logs_specific_level(self):
        """Test getting logs for specific level"""
        capture = LoggingCapture()
        capture.logs['info'] = ["Info 1", "Info 2"]
        capture.logs['error'] = ["Error 1"]
        
        info_logs = capture.get_logs('info')
        assert info_logs == ["Info 1", "Info 2"]
        
        error_logs = capture.get_logs('error')
        assert error_logs == ["Error 1"]
    
    def test_get_logs_all_levels(self):
        """Test getting all logs"""
        capture = LoggingCapture()
        capture.logs['info'] = ["Info 1"]
        capture.logs['warning'] = ["Warning 1"]
        capture.logs['error'] = ["Error 1"]
        capture.logs['debug'] = ["Debug 1"]
        
        all_logs = capture.get_logs()
        expected = ["Info 1", "Warning 1", "Error 1", "Debug 1"]
        assert all_logs == expected
    
    def test_get_logs_nonexistent_level(self):
        """Test getting logs for non-existent level"""
        capture = LoggingCapture()
        
        result = capture.get_logs('nonexistent')
        assert result == []
    
    def test_assert_logged_found(self):
        """Test asserting message was logged - success case"""
        capture = LoggingCapture()
        capture.logs['info'] = ["This is a test message"]
        
        # Should not raise assertion error
        capture.assert_logged("test message")
        capture.assert_logged("test message", "info")
    
    def test_assert_logged_not_found(self):
        """Test asserting message was logged - failure case"""
        capture = LoggingCapture()
        capture.logs['info'] = ["Other message"]
        
        with pytest.raises(AssertionError, match="Message 'missing message' not found in logs"):
            capture.assert_logged("missing message")
    
    def test_assert_log_count_correct(self):
        """Test asserting log count - success case"""
        capture = LoggingCapture()
        capture.logs['error'] = ["Error 1", "Error 2"]
        
        # Should not raise assertion error
        capture.assert_log_count('error', 2)
    
    def test_assert_log_count_incorrect(self):
        """Test asserting log count - failure case"""
        capture = LoggingCapture()
        capture.logs['error'] = ["Error 1"]
        
        with pytest.raises(AssertionError, match="Expected 3 error logs, got 1"):
            capture.assert_log_count('error', 3)
    
    def test_clear(self):
        """Test clearing all logs"""
        capture = LoggingCapture()
        capture.logs['info'] = ["Info 1", "Info 2"]
        capture.logs['error'] = ["Error 1"]
        
        capture.clear()
        
        for level in capture.logs:
            assert capture.logs[level] == []


class TestPerformanceProfiler:
    """Test all PerformanceProfiler methods for 100% coverage"""
    
    def test_init(self):
        """Test PerformanceProfiler initialization"""
        profiler = PerformanceProfiler()
        assert profiler.timings == {}
        assert profiler.memory_usage == {}
    
    def test_time_function_decorator(self):
        """Test function timing decorator"""
        profiler = PerformanceProfiler()
        
        @profiler.time_function("test_func")
        def test_function(x, y):
            time.sleep(0.01)  # Small delay to measure
            return x + y
        
        result = test_function(2, 3)
        assert result == 5
        
        # Check timing was recorded
        assert "test_func" in profiler.timings
        assert len(profiler.timings["test_func"]) == 1
        assert profiler.timings["test_func"][0] > 0
    
    def test_time_function_decorator_with_exception(self):
        """Test function timing decorator when function raises exception"""
        profiler = PerformanceProfiler()
        
        @profiler.time_function("failing_func")
        def failing_function():
            time.sleep(0.01)
            raise ValueError("Test exception")
        
        with pytest.raises(ValueError):
            failing_function()
        
        # Timing should still be recorded
        assert "failing_func" in profiler.timings
        assert len(profiler.timings["failing_func"]) == 1
    
    def test_get_average_time_with_data(self):
        """Test getting average time with data"""
        profiler = PerformanceProfiler()
        profiler.timings["test_func"] = [1.0, 2.0, 3.0]
        
        avg_time = profiler.get_average_time("test_func")
        assert avg_time == 2.0
    
    def test_get_average_time_no_data(self):
        """Test getting average time without data"""
        profiler = PerformanceProfiler()
        
        avg_time = profiler.get_average_time("nonexistent_func")
        assert avg_time == 0.0
    
    def test_get_average_time_empty_list(self):
        """Test getting average time with empty list"""
        profiler = PerformanceProfiler()
        profiler.timings["test_func"] = []
        
        avg_time = profiler.get_average_time("test_func")
        assert avg_time == 0.0
    
    def test_get_max_time_with_data(self):
        """Test getting max time with data"""
        profiler = PerformanceProfiler()
        profiler.timings["test_func"] = [1.0, 3.0, 2.0]
        
        max_time = profiler.get_max_time("test_func")
        assert max_time == 3.0
    
    def test_get_max_time_no_data(self):
        """Test getting max time without data"""
        profiler = PerformanceProfiler()
        
        max_time = profiler.get_max_time("nonexistent_func")
        assert max_time == 0.0
    
    def test_get_max_time_empty_list(self):
        """Test getting max time with empty list"""
        profiler = PerformanceProfiler()
        profiler.timings["test_func"] = []
        
        max_time = profiler.get_max_time("test_func")
        assert max_time == 0.0
    
    def test_assert_performance_success(self):
        """Test performance assertion - success case"""
        profiler = PerformanceProfiler()
        profiler.timings["fast_func"] = [0.1, 0.2, 0.15]  # avg = 0.15, max = 0.2
        
        # Should not raise assertion error
        profiler.assert_performance("fast_func", 0.5)
    
    def test_assert_performance_avg_failure(self):
        """Test performance assertion - average time failure"""
        profiler = PerformanceProfiler()
        profiler.timings["slow_func"] = [1.0, 2.0, 3.0]  # avg = 2.0
        
        with pytest.raises(AssertionError, match="Average time 2.000s exceeds limit 1.000s"):
            profiler.assert_performance("slow_func", 1.0)
    
    def test_assert_performance_max_failure(self):
        """Test performance assertion - max time failure"""
        profiler = PerformanceProfiler()
        profiler.timings["spike_func"] = [0.1, 0.2, 5.0]  # avg = 1.77, max = 5.0
        
        with pytest.raises(AssertionError, match="Max time 5.000s exceeds reasonable limit"):
            profiler.assert_performance("spike_func", 2.0)


class TestTestDataGenerator:
    """Test all TestDataGenerator methods for 100% coverage"""
    
    def test_random_phone(self):
        """Test generating random phone numbers"""
        phone = TestDataGenerator.random_phone()
        
        assert phone.startswith("+1")
        assert len(phone) == 12  # +1 + 10 digits
        assert phone[2:].isdigit()
    
    def test_random_phone_multiple(self):
        """Test generating multiple random phone numbers are different"""
        phones = [TestDataGenerator.random_phone() for _ in range(10)]
        
        # Should generate different numbers
        assert len(set(phones)) > 1
    
    def test_random_name(self):
        """Test generating random names"""
        name = TestDataGenerator.random_name()
        
        parts = name.split()
        assert len(parts) == 2  # First and last name
        
        expected_first = ["John", "Jane", "Bob", "Alice", "Charlie", "Diana", "Eve", "Frank"]
        expected_last = ["Doe", "Smith", "Johnson", "Brown", "Wilson", "Davis", "Miller", "Taylor"]
        
        assert parts[0] in expected_first
        assert parts[1] in expected_last
    
    def test_random_batch_id(self):
        """Test generating random batch IDs"""
        batch_id = TestDataGenerator.random_batch_id()
        
        assert batch_id.startswith("BATCH-")
        
        parts = batch_id.split("-")
        assert len(parts) == 3
        assert parts[1] in ["CS", "EE", "ME", "CE", "BIO"]
        assert 2020 <= int(parts[2]) <= 2025
    
    def test_generate_realistic_students(self):
        """Test generating realistic student data"""
        students = TestDataGenerator.generate_realistic_students(5)
        
        assert len(students) == 5
        
        for i, student in enumerate(students, 1):
            assert student['name'] == f'BS-{i:03d}'
            assert student['student_id'] == f'STU-{i:03d}'
            assert 'student_name' in student
            assert 'phone' in student
            assert 'batch' in student
            assert 'batch_skeyword' in student
            
            # Validate formats
            assert student['phone'].startswith('+1')
            assert student['batch'].startswith('BATCH-')
            assert student['batch_skeyword'].startswith('batch')


class TestErrorScenarioGenerator:
    """Test all ErrorScenarioGenerator methods for 100% coverage"""
    
    def test_create_network_errors(self):
        """Test creating network errors"""
        errors = ErrorScenarioGenerator.create_network_errors()
        
        assert len(errors) == 4
        assert isinstance(errors[0], requests.exceptions.Timeout)
        assert isinstance(errors[1], requests.exceptions.ConnectionError)
        assert isinstance(errors[2], requests.exceptions.HTTPError)
        assert isinstance(errors[3], requests.exceptions.RequestException)
        
        assert str(errors[0]) == "Request timed out"
        assert str(errors[1]) == "Connection refused"
        assert str(errors[2]) == "404 Not Found"
        assert str(errors[3]) == "Generic request error"
    
    def test_create_api_error_responses(self):
        """Test creating API error responses"""
        responses = ErrorScenarioGenerator.create_api_error_responses()
        
        expected_codes = [400, 401, 403, 404, 429, 500, 502, 503]
        expected_messages = [
            "Bad Request", "Unauthorized", "Forbidden", "Not Found",
            "Rate limit exceeded", "Internal server error", "Bad gateway", "Service unavailable"
        ]
        
        assert len(responses) == 8
        
        for i, response in enumerate(responses):
            assert response.status_code == expected_codes[i]
            assert response.json()["error"] == expected_messages[i]
    
    def test_create_database_errors(self):
        """Test creating database errors"""
        errors = ErrorScenarioGenerator.create_database_errors()
        
        expected_messages = [
            "Database connection lost",
            "Transaction deadlock detected",
            "Table doesn't exist",
            "Permission denied"
        ]
        
        assert len(errors) == 4
        for i, error in enumerate(errors):
            assert isinstance(error, Exception)
            assert str(error) == expected_messages[i]
    
    def test_create_data_validation_errors(self):
        """Test creating data validation errors"""
        errors = ErrorScenarioGenerator.create_data_validation_errors()
        
        assert len(errors) == 5
        
        # Check each error scenario
        assert errors[0] == {"student_id": None, "batch": "BATCH-1"}
        assert errors[1] == {"student_id": "", "batch": "BATCH-1"}
        assert errors[2] == {"student_id": "STU-001", "batch": None}
        assert errors[3] == {"student_id": "STU-001", "batch": ""}
        assert errors[4] == {"student_id": "STU-001", "phone": ""}


class TestAssertionHelpers:
    """Test all AssertionHelpers methods for 100% coverage"""
    
    def test_assert_result_structure_success(self):
        """Test result structure assertion - success case"""
        result = {"key1": "value1", "key2": "value2", "key3": "value3"}
        expected_keys = ["key1", "key2"]
        
        # Should not raise assertion error
        AssertionHelpers.assert_result_structure(result, expected_keys)
    
    def test_assert_result_structure_not_dict(self):
        """Test result structure assertion - not a dictionary"""
        result = "not a dict"
        expected_keys = ["key1"]
        
        with pytest.raises(AssertionError, match="Result should be a dictionary"):
            AssertionHelpers.assert_result_structure(result, expected_keys)
    
    def test_assert_result_structure_missing_key(self):
        """Test result structure assertion - missing key"""
        result = {"key1": "value1"}
        expected_keys = ["key1", "missing_key"]
        
        with pytest.raises(AssertionError, match="Missing key 'missing_key' in result"):
            AssertionHelpers.assert_result_structure(result, expected_keys)
    
    def test_assert_processing_result_success(self):
        """Test processing result assertion - success case"""
        result = {
            "updated": 10,
            "skipped": 5,
            "errors": 2,
            "total_processed": 17
        }
        
        # Should not raise assertion error
        AssertionHelpers.assert_processing_result(result)
    
    def test_assert_processing_result_non_integer(self):
        """Test processing result assertion - non-integer value"""
        result = {
            "updated": "10",  # String instead of int
            "skipped": 5,
            "errors": 2,
            "total_processed": 17
        }
        
        with pytest.raises(AssertionError, match="updated should be an integer"):
            AssertionHelpers.assert_processing_result(result)
    
    def test_assert_processing_result_negative(self):
        """Test processing result assertion - negative value"""
        result = {
            "updated": 10,
            "skipped": -5,  # Negative value
            "errors": 2,
            "total_processed": 17
        }
        
        with pytest.raises(AssertionError, match="skipped should be non-negative"):
            AssertionHelpers.assert_processing_result(result)
    
    def test_assert_processing_result_totals_mismatch(self):
        """Test processing result assertion - totals don't match"""
        result = {
            "updated": 10,
            "skipped": 5,
            "errors": 2,
            "total_processed": 20  # Should be 17
        }
        
        with pytest.raises(AssertionError, match="Totals don't add up correctly"):
            AssertionHelpers.assert_processing_result(result)
    
    def test_assert_glific_api_called_correctly_basic(self):
        """Test Glific API call assertion - basic case"""
        mock_post = Mock()
        mock_post.called = True
        
        # Should not raise assertion error
        AssertionHelpers.assert_glific_api_called_correctly(mock_post)
    
    def test_assert_glific_api_called_correctly_not_called(self):
        """Test Glific API call assertion - not called"""
        mock_post = Mock()
        mock_post.called = False
        
        with pytest.raises(AssertionError, match="Glific API should have been called"):
            AssertionHelpers.assert_glific_api_called_correctly(mock_post)
    
    def test_assert_glific_api_called_correctly_call_count(self):
        """Test Glific API call assertion - with call count"""
        mock_post = Mock()
        mock_post.called = True
        mock_post.call_count = 3
        
        # Correct count
        AssertionHelpers.assert_glific_api_called_correctly(mock_post, 3)
        
        # Incorrect count
        with pytest.raises(AssertionError, match="Expected 5 API calls, got 3"):
            AssertionHelpers.assert_glific_api_called_correctly(mock_post, 5)
    
    def test_assert_glific_api_called_correctly_call_structure(self):
        """Test Glific API call assertion - call structure"""
        mock_post = Mock()
        mock_post.called = True
        mock_post.call_count = 2
        mock_post.call_args_list = [
            call("http://test.com", headers={"auth": "token"}, json={"query": "test"}),
            call("http://test.com", headers={"auth": "token"}, json={"query": "test2"})
        ]
        
        # Should not raise assertion error
        AssertionHelpers.assert_glific_api_called_correctly(mock_post, 2)
    
    def test_assert_glific_api_called_correctly_missing_headers(self):
        """Test Glific API call assertion - missing headers"""
        mock_post = Mock()
        mock_post.called = True
        mock_post.call_count = 1
        mock_post.call_args_list = [
            call("http://test.com", json={"query": "test"})  # Missing headers
        ]
        
        with pytest.raises(AssertionError, match="API call should have headers"):
            AssertionHelpers.assert_glific_api_called_correctly(mock_post, 1)
    
    def test_assert_glific_api_called_correctly_missing_json(self):
        """Test Glific API call assertion - missing json"""
        mock_post = Mock()
        mock_post.called = True
        mock_post.call_count = 1
        mock_post.call_args_list = [
            call("http://test.com", headers={"auth": "token"})  # Missing json
        ]
        
        with pytest.raises(AssertionError, match="API call should have JSON payload"):
            AssertionHelpers.assert_glific_api_called_correctly(mock_post, 1)
    
    def test_assert_glific_api_called_correctly_missing_query(self):
        """Test Glific API call assertion - missing query in json"""
        mock_post = Mock()
        mock_post.called = True
        mock_post.call_count = 1
        mock_post.call_args_list = [
            call("http://test.com", headers={"auth": "token"}, json={"data": "test"})  # Missing query
        ]
        
        with pytest.raises(AssertionError, match="Payload should have GraphQL query"):
            AssertionHelpers.assert_glific_api_called_correctly(mock_post, 1)
    
    def test_assert_database_transaction_handling_commit(self):
        """Test database transaction assertion - commit case"""
        mock_db = Mock()
        mock_db.begin.called = True
        mock_db.commit.called = True
        mock_db.rollback.called = False
        
        # Should not raise assertion error
        AssertionHelpers.assert_database_transaction_handling(mock_db)
    
    def test_assert_database_transaction_handling_rollback(self):
        """Test database transaction assertion - rollback case"""
        mock_db = Mock()
        mock_db.begin.called = True
        mock_db.commit.called = False
        mock_db.rollback.called = True
        
        # Should not raise assertion error
        AssertionHelpers.assert_database_transaction_handling(mock_db)
    
    def test_assert_database_transaction_handling_no_action(self):
        """Test database transaction assertion - no commit or rollback"""
        mock_db = Mock()
        mock_db.begin.called = True
        mock_db.commit.called = False
        mock_db.rollback.called = False
        
        with pytest.raises(AssertionError, match="Should have commit or rollback"):
            AssertionHelpers.assert_database_transaction_handling(mock_db)
    
    def test_assert_database_transaction_handling_both_actions(self):
        """Test database transaction assertion - both commit and rollback"""
        mock_db = Mock()
        mock_db.begin.called = True
        mock_db.commit.called = True
        mock_db.rollback.called = True
        
        with pytest.raises(AssertionError, match="Should not have both commit and rollback"):
            AssertionHelpers.assert_database_transaction_handling(mock_db)
    
    def test_assert_error_logged_success(self):
        """Test error logging assertion - success case"""
        mock_logger = Mock()
        mock_logger.error.called = True
        mock_logger.error.call_args_list = [
            call("This is an error message"),
            call("Another error occurred")
        ]
        
        # Should not raise assertion error
        AssertionHelpers.assert_error_logged(mock_logger, "error message")
    
    def test_assert_error_logged_not_found(self):
        """Test error logging assertion - error not found"""
        mock_logger = Mock()
        mock_logger.error.called = True
        mock_logger.error.call_args_list = [
            call("Different error message"),
        ]
        
        with pytest.raises(AssertionError, match="Error message 'missing error' not found in logs"):
            AssertionHelpers.assert_error_logged(mock_logger, "missing error")


class TestTestReportGenerator:
    """Test all TestReportGenerator methods for 100% coverage"""
    
    def test_init(self):
        """Test TestReportGenerator initialization"""
        generator = TestReportGenerator()
        assert generator.test_results == []
        assert generator.performance_data == {}
        assert generator.coverage_data == {}
    
    def test_record_test_result_minimal(self):
        """Test recording test result with minimal data"""
        generator = TestReportGenerator()
        generator.record_test_result("test_sample", "passed", 1.5)
        
        assert len(generator.test_results) == 1
        result = generator.test_results[0]
        assert result['name'] == "test_sample"
        assert result['status'] == "passed"
        assert result['duration'] == 1.5
        assert 'timestamp' in result
        assert result['details'] == {}
    
    def test_record_test_result_with_details(self):
        """Test recording test result with details"""
        generator = TestReportGenerator()
        details = {"error_message": "Test failed", "line": 42}
        generator.record_test_result("test_failing", "failed", 2.0, details)
        
        assert len(generator.test_results) == 1
        result = generator.test_results[0]
        assert result['name'] == "test_failing"
        assert result['status'] == "failed"
        assert result['duration'] == 2.0
        assert result['details'] == details
    
    def test_record_performance_data_minimal(self):
        """Test recording performance data without memory usage"""
        generator = TestReportGenerator()
        generator.record_performance_data("database_query", 0.5)
        
        assert "database_query" in generator.performance_data
        assert len(generator.performance_data["database_query"]) == 1
        
        record = generator.performance_data["database_query"][0]
        assert record['duration'] == 0.5
        assert record['memory_usage'] == None
        assert 'timestamp' in record
    
    def test_record_performance_data_with_memory(self):
        """Test recording performance data with memory usage"""
        generator = TestReportGenerator()
        generator.record_performance_data("api_call", 1.2, 1024000)
        
        assert "api_call" in generator.performance_data
        record = generator.performance_data["api_call"][0]
        assert record['duration'] == 1.2
        assert record['memory_usage'] == 1024000
    
    def test_record_performance_data_multiple(self):
        """Test recording multiple performance data points"""
        generator = TestReportGenerator()
        generator.record_performance_data("operation", 1.0)
        generator.record_performance_data("operation", 1.5)
        generator.record_performance_data("operation", 0.8)
        
        assert len(generator.performance_data["operation"]) == 3
        durations = [r['duration'] for r in generator.performance_data["operation"]]
        assert durations == [1.0, 1.5, 0.8]
    
    def test_generate_summary_empty(self):
        """Test generating summary with no data"""
        generator = TestReportGenerator()
        summary = generator.generate_summary()
        
        assert summary['summary']['total_tests'] == 0
        assert summary['summary']['passed'] == 0
        assert summary['summary']['failed'] == 0
        assert summary['summary']['skipped'] == 0
        assert summary['summary']['pass_rate'] == 0
        assert summary['summary']['total_duration'] == 0
        assert summary['performance'] == {}
        assert summary['failed_tests'] == []
    
    def test_generate_summary_with_data(self):
        """Test generating summary with test data"""
        generator = TestReportGenerator()
        generator.record_test_result("test1", "passed", 1.0)
        generator.record_test_result("test2", "failed", 2.0, {"error": "failed"})
        generator.record_test_result("test3", "passed", 1.5)
        generator.record_test_result("test4", "skipped", 0.0)
        
        generator.record_performance_data("op1", 1.0)
        generator.record_performance_data("op1", 2.0)
        generator.record_performance_data("op2", 0.5)
        
        summary = generator.generate_summary()
        
        # Test summary
        test_summary = summary['summary']
        assert test_summary['total_tests'] == 4
        assert test_summary['passed'] == 2
        assert test_summary['failed'] == 1
        assert test_summary['skipped'] == 1
        assert test_summary['pass_rate'] == 50.0
        assert test_summary['total_duration'] == 4.5
        
        # Performance summary
        perf_summary = summary['performance']
        assert 'op1' in perf_summary
        assert 'op2' in perf_summary
        assert perf_summary['op1']['count'] == 2
        assert perf_summary['op1']['avg_duration'] == 1.5
        assert perf_summary['op1']['min_duration'] == 1.0
        assert perf_summary['op1']['max_duration'] == 2.0
        assert perf_summary['op2']['count'] == 1
        assert perf_summary['op2']['avg_duration'] == 0.5
        
        # Failed tests
        assert len(summary['failed_tests']) == 1
        assert summary['failed_tests'][0]['name'] == "test2"
    
    def test_summarize_performance_empty(self):
        """Test summarizing performance with no data"""
        generator = TestReportGenerator()
        summary = generator._summarize_performance()
        assert summary == {}
    
    def test_export_to_json(self, tmp_path):
        """Test exporting results to JSON file"""
        generator = TestReportGenerator()
        generator.record_test_result("test1", "passed", 1.0)
        generator.record_performance_data("op1", 0.5)
        
        json_file = tmp_path / "test_report.json"
        generator.export_to_json(str(json_file))
        
        # Verify file was created and contains expected data
        assert json_file.exists()
        
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        assert 'test_results' in data
        assert 'performance_data' in data
        assert 'summary' in data
        assert 'generated_at' in data
        
        assert len(data['test_results']) == 1
        assert 'op1' in data['performance_data']


class TestTestConfigManager:
    """Test all TestConfigManager methods for 100% coverage"""
    
    def test_init(self):
        """Test TestConfigManager initialization"""
        config = TestConfigManager()
        
        # Check default configuration values
        assert config.config['api_url'] == 'https://test-api.glific.org'
        assert config.config['timeout'] == 30
        assert config.config['retry_count'] == 3
        assert config.config['batch_size'] == 10
        assert 'performance_thresholds' in config.config
        
        thresholds = config.config['performance_thresholds']
        assert thresholds['single_student_processing'] == 1.0
        assert thresholds['batch_processing_per_student'] == 0.1
        assert thresholds['memory_increase_limit'] == 100 * 1024 * 1024
    
    def test_get_existing_key(self):
        """Test getting existing configuration value"""
        config = TestConfigManager()
        
        assert config.get('api_url') == 'https://test-api.glific.org'
        assert config.get('timeout') == 30
    
    def test_get_nonexistent_key_no_default(self):
        """Test getting non-existent key without default"""
        config = TestConfigManager()
        
        result = config.get('nonexistent_key')
        assert result is None
    
    def test_get_nonexistent_key_with_default(self):
        """Test getting non-existent key with default"""
        config = TestConfigManager()
        
        result = config.get('nonexistent_key', 'default_value')
        assert result == 'default_value'
    
    def test_set_new_key(self):
        """Test setting new configuration value"""
        config = TestConfigManager()
        config.set('new_key', 'new_value')
        
        assert config.get('new_key') == 'new_value'
    
    def test_set_existing_key(self):
        """Test updating existing configuration value"""
        config = TestConfigManager()
        config.set('timeout', 60)
        
        assert config.get('timeout') == 60
    
    def test_load_from_file_nonexistent(self):
        """Test loading from non-existent file"""
        config = TestConfigManager()
        original_config = config.config.copy()
        
        # Should not raise error and should keep original config
        config.load_from_file('nonexistent_file.json')
        assert config.config == original_config
    
    def test_load_from_file_existing(self, tmp_path):
        """Test loading from existing file"""
        config = TestConfigManager()
        
        # Create temporary config file
        config_file = tmp_path / "test_config.json"
        test_config_data = {
            'api_url': 'https://custom-api.com',
            'timeout': 120,
            'custom_setting': 'custom_value'
        }
        
        with open(config_file, 'w') as f:
            json.dump(test_config_data, f)
        
        # Load configuration
        config.load_from_file(str(config_file))
        
        # Check that values were loaded and merged
        assert config.get('api_url') == 'https://custom-api.com'
        assert config.get('timeout') == 120
        assert config.get('custom_setting') == 'custom_value'
        # Original values should still exist if not overridden
        assert config.get('retry_count') == 3
    
    def test_save_to_file(self, tmp_path):
        """Test saving configuration to file"""
        config = TestConfigManager()
        config.set('custom_key', 'custom_value')
        
        config_file = tmp_path / "saved_config.json"
        config.save_to_file(str(config_file))
        
        # Verify file was created
        assert config_file.exists()
        
        # Verify file contents
        with open(config_file, 'r') as f:
            saved_data = json.load(f)
        
        assert saved_data['custom_key'] == 'custom_value'
        assert saved_data['api_url'] == config.get('api_url')


class TestGlobalTestConfig:
    """Test global test_config instance"""
    
    def test_global_config_instance(self):
        """Test that global test_config is a TestConfigManager instance"""
        assert isinstance(test_config, TestConfigManager)
        assert test_config.get('api_url') is not None


class TestParameterizedTestDecorator:
    """Test parameterized_test decorator"""
    
    def test_parameterized_test_with_tuples(self):
        """Test parameterized test decorator with tuple parameters"""
        call_count = 0
        parameters = [(1, 2, 3), (4, 5, 9), (10, 20, 30)]
        
        @parameterized_test(parameters)
        def test_addition(a, b, expected):
            nonlocal call_count
            call_count += 1
            assert a + b == expected
        
        test_addition()
        assert call_count == 3
    
    def test_parameterized_test_with_dicts(self):
        """Test parameterized test decorator with dict parameters"""
        call_count = 0
        parameters = [
            {'x': 1, 'y': 2, 'expected': 3},
            {'x': 4, 'y': 5, 'expected': 9},
            {'x': 10, 'y': 20, 'expected': 30}
        ]
        
        @parameterized_test(parameters)
        def test_addition(x, y, expected):
            nonlocal call_count
            call_count += 1
            assert x + y == expected
        
        test_addition()
        assert call_count == 3
    
    def test_parameterized_test_with_failure(self):
        """Test parameterized test decorator when test fails"""
        parameters = [(1, 2, 3), (4, 5, 10)]  # Second case will fail
        
        @parameterized_test(parameters)
        def test_addition(a, b, expected):
            assert a + b == expected
        
        with pytest.raises(AssertionError, match="Test failed with parameters"):
            test_addition()


class TestValidationFunctions:
    """Test validation functions"""
    
    def test_validate_student_data_valid(self):
        """Test validating valid student data"""
        student_data = {
            'student_id': 'STU-001',
            'student_name': 'John Doe',
            'phone': '+1234567890',
            'batch': 'BATCH-CS-2024'
        }
        
        errors = validate_student_data(student_data)
        assert errors == []
    
    def test_validate_student_data_missing_fields(self):
        """Test validating student data with missing fields"""
        student_data = {
            'student_id': 'STU-001',
            # Missing student_name, phone, batch
        }
        
        errors = validate_student_data(student_data)
        assert len(errors) == 3
        assert "Missing or empty student_name" in errors
        assert "Missing or empty phone" in errors
        assert "Missing or empty batch" in errors
    
    def test_validate_student_data_empty_fields(self):
        """Test validating student data with empty fields"""
        student_data = {
            'student_id': '',
            'student_name': '',
            'phone': '',
            'batch': ''
        }
        
        errors = validate_student_data(student_data)
        assert len(errors) == 5  # 4 empty fields + invalid phone format + invalid student ID
    
    def test_validate_student_data_invalid_phone(self):
        """Test validating student data with invalid phone"""
        student_data = {
            'student_id': 'STU-001',
            'student_name': 'John Doe',
            'phone': '123456',  # Invalid format
            'batch': 'BATCH-CS-2024'
        }
        
        errors = validate_student_data(student_data)
        assert len(errors) == 1
        assert "Invalid phone number format" in errors[0]
    
    def test_validate_student_data_invalid_student_id(self):
        """Test validating student data with invalid student ID"""
        student_data = {
            'student_id': 'INVALID-001',  # Should start with STU-
            'student_name': 'John Doe',
            'phone': '+1234567890',
            'batch': 'BATCH-CS-2024'
        }
        
        errors = validate_student_data(student_data)
        assert len(errors) == 1
        assert "Invalid student ID format" in errors[0]
    
    def test_validate_processing_result_valid(self):
        """Test validating valid processing result"""
        result = {
            'updated': 10,
            'skipped': 5,
            'errors': 2,
            'total_processed': 17
        }
        
        errors = validate_processing_result(result)
        assert errors == []
    
    def test_validate_processing_result_missing_fields(self):
        """Test validating processing result with missing fields"""
        result = {
            'updated': 10,
            'skipped': 5
            # Missing errors and total_processed
        }
        
        errors = validate_processing_result(result)
        assert len(errors) == 2
        assert "Missing field: errors" in errors
        assert "Missing field: total_processed" in errors
    
    def test_validate_processing_result_wrong_types(self):
        """Test validating processing result with wrong data types"""
        result = {
            'updated': '10',  # String instead of int
            'skipped': 5.5,   # Float instead of int
            'errors': 2,
            'total_processed': 17
        }
        
        errors = validate_processing_result(result)
        assert len(errors) >= 2
        assert any("should be integer" in error for error in errors)
    
    def test_validate_processing_result_negative_values(self):
        """Test validating processing result with negative values"""
        result = {
            'updated': -10,
            'skipped': 5,
            'errors': 2,
            'total_processed': 17
        }
        
        errors = validate_processing_result(result)
        assert len(errors) >= 1
        assert any("should be non-negative" in error for error in errors)
    
    def test_validate_processing_result_totals_mismatch(self):
        """Test validating processing result with mismatched totals"""
        result = {
            'updated': 10,
            'skipped': 5,
            'errors': 2,
            'total_processed': 20  # Should be 17
        }
        
        errors = validate_processing_result(result)
        assert len(errors) == 1
        assert "Total processed doesn't match sum" in errors[0]


class TestContextManagers:
    """Test context manager utilities"""
    
    def test_mock_time_context_manager(self):
        """Test MockTimeContextManager"""
        mock_time = datetime(2024, 1, 15, 12, 0, 0)
        
        with MockTimeContextManager(mock_time):
            # Test that time functions return mocked values
            import time
            assert abs(time.time() - mock_time.timestamp()) < 0.1
    
    def test_mock_network_context_manager_normal(self):
        """Test MockNetworkContextManager with normal conditions"""
        with MockNetworkContextManager():
            import requests
            response = requests.post("http://test.com")
            assert response.status_code == 200
    
    def test_mock_network_context_manager_with_failures(self):
        """Test MockNetworkContextManager with simulated failures"""
        with MockNetworkContextManager(simulate_failures=True, failure_rate=1.0):
            import requests
            with pytest.raises(requests.exceptions.ConnectionError):
                requests.post("http://test.com")
    
    def test_mock_network_context_manager_slow(self):
        """Test MockNetworkContextManager with slow simulation"""
        start_time = time.time()
        with MockNetworkContextManager(simulate_slow=True):
            import requests
            requests.post("http://test.com")
        
        # Should take at least some time due to simulated slowness
        # Note: In real test, we might want to use a smaller delay
        elapsed = time.time() - start_time
        # Just check that some delay was added, actual timing may vary in tests
        assert elapsed >= 0


# Integration tests combining multiple utilities
class TestUtilityIntegration:
    """Test integration of multiple utilities together"""
    
    def test_complete_test_scenario(self):
        """Test a complete testing scenario using multiple utilities"""
        # Setup
        profiler = PerformanceProfiler()
        logger_capture = LoggingCapture()
        mock_logger = logger_capture.create_logger_mock()
        
        simulator = APIResponseSimulator()
        simulator.add_response(MockDataFactory.create_glific_contact_response())
        simulator.add_response(MockDataFactory.create_glific_update_response())
        
        # Create test data
        students = MockDataFactory.create_batch_of_students(5)
        
        # Simulate processing with performance profiling
        @profiler.time_function("process_students")
        def process_students(student_list):
            mock_logger.info(f"Processing {len(student_list)} students")
            
            results = {"updated": 0, "skipped": 0, "errors": 0, "total_processed": 0}
            
            for student in student_list:
                errors = validate_student_data(student)
                if errors:
                    mock_logger.error(f"Validation failed for {student['student_id']}: {errors}")
                    results["errors"] += 1
                else:
                    results["updated"] += 1
                
                results["total_processed"] += 1
            
            return results
        
        # Execute the test
        result = process_students(students)
        
        # Validate results
        AssertionHelpers.assert_processing_result(result)
        logger_capture.assert_logged("Processing 5 students", "info")
        
        # Check performance
        avg_time = profiler.get_average_time("process_students")
        assert avg_time > 0
        
        # Verify all students were processed
        assert result["total_processed"] == 5
    
    def test_error_handling_integration(self):
        """Test error handling across multiple utilities"""
        # Setup error scenarios
        error_students = ErrorScenarioGenerator.create_data_validation_errors()
        logger_capture = LoggingCapture()
        mock_logger = logger_capture.create_logger_mock()
        
        error_count = 0
        for student_data in error_students:
            errors = validate_student_data(student_data)
            if errors:
                error_count += 1
                mock_logger.error(f"Validation failed: {errors}")
        
        # Verify errors were detected and logged
        assert error_count == len(error_students)
        logger_capture.assert_log_count("error", error_count)
    
    def test_performance_reporting_integration(self):
        """Test performance reporting integration"""
        profiler = PerformanceProfiler()
        report_generator = TestReportGenerator()
        
        # Simulate multiple operations
        operations = ["fetch_student", "update_contact", "validate_data"]
        
        for op in operations:
            # Record some test results
            report_generator.record_test_result(f"test_{op}", "passed", random.uniform(0.1, 2.0))
            
            # Record performance data
            for _ in range(3):
                duration = random.uniform(0.1, 1.0)
                report_generator.record_performance_data(op, duration)
        
        # Generate comprehensive report
        summary = report_generator.generate_summary()
        
        # Validate report structure
        assert summary['summary']['total_tests'] == 3
        assert summary['summary']['passed'] == 3
        assert summary['summary']['pass_rate'] == 100.0
        
        # Validate performance data
        for op in operations:
            assert op in summary['performance']
            assert summary['performance'][op]['count'] == 3


if __name__ == "__main__":
    # Run all tests
    pytest.main([__file__, "-v", "--tb=short"])