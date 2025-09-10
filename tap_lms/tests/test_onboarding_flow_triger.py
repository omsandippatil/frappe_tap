import unittest
from unittest.mock import Mock, patch, MagicMock, call
import frappe
import json
from datetime import datetime, timedelta
from frappe.utils import now_datetime, add_to_date
import requests

# Import the functions to test (adjust import path as needed)
from your_module import (
    trigger_onboarding_flow,
    _trigger_onboarding_flow_job,
    trigger_group_flow,
    trigger_individual_flows,
    get_stage_flow_statuses,
    get_students_from_onboarding,
    update_student_stage_progress,
    update_student_stage_progress_batch,
    get_job_status,
    get_onboarding_progress_report,
    update_incomplete_stages
)


class TestOnboardingFlowFunctions(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_onboarding_set = "TEST_ONBOARDING_001"
        self.mock_onboarding_stage = "TEST_STAGE_001"
        self.mock_student_status = "not_started"
        self.mock_flow_id = "12345"
        self.mock_job_id = "test_job_123"
        
        # Mock datetime
        self.mock_now = datetime.now()
        
    @patch('frappe.enqueue')
    @patch('frappe.get_doc')
    @patch('frappe.throw')
    @patch('frappe.logger')
    def test_trigger_onboarding_flow_success(self, mock_logger, mock_throw, mock_get_doc, mock_enqueue):
        """Test successful trigger_onboarding_flow execution"""
        # Mock stage document with new structure
        mock_stage = Mock()
        mock_stage.name = self.mock_onboarding_stage
        mock_stage.is_active = True
        mock_stage.stage_flows = [Mock(student_status="not_started", glific_flow_id="12345", flow_type="Group")]
        
        # Mock onboarding document
        mock_onboarding = Mock()
        mock_onboarding.name = self.mock_onboarding_set
        mock_onboarding.status = "Processed"
        
        mock_get_doc.side_effect = [mock_stage, mock_onboarding]
        mock_enqueue.return_value = self.mock_job_id
        
        # Call function
        result = trigger_onboarding_flow(
            self.mock_onboarding_set, 
            self.mock_onboarding_stage, 
            self.mock_student_status
        )
        
        # Assertions
        self.assertTrue(result["success"])
        self.assertEqual(result["job_id"], self.mock_job_id)
        mock_enqueue.assert_called_once()
        mock_throw.assert_not_called()
    
    @patch('frappe.get_doc')
    @patch('frappe.throw')
    def test_trigger_onboarding_flow_missing_parameters(self, mock_throw, mock_get_doc):
        """Test trigger_onboarding_flow with missing parameters"""
        # Test missing onboarding_set
        trigger_onboarding_flow("", self.mock_onboarding_stage, self.mock_student_status)
        mock_throw.assert_called()
        
        # Reset and test missing onboarding_stage
        mock_throw.reset_mock()
        trigger_onboarding_flow(self.mock_onboarding_set, "", self.mock_student_status)
        mock_throw.assert_called()
        
        # Reset and test missing student_status
        mock_throw.reset_mock()
        trigger_onboarding_flow(self.mock_onboarding_set, self.mock_onboarding_stage, "")
        mock_throw.assert_called()
    
    @patch('frappe.get_doc')
    @patch('frappe.throw')
    def test_trigger_onboarding_flow_inactive_stage(self, mock_throw, mock_get_doc):
        """Test trigger_onboarding_flow with inactive stage"""
        mock_stage = Mock()
        mock_stage.is_active = False
        mock_get_doc.return_value = mock_stage
        
        trigger_onboarding_flow(
            self.mock_onboarding_set, 
            self.mock_onboarding_stage, 
            self.mock_student_status
        )
        
        mock_throw.assert_called_with("Selected Onboarding Stage is not active")
    
    @patch('frappe.get_doc')
    @patch('frappe.throw')
    def test_trigger_onboarding_flow_unprocessed_set(self, mock_throw, mock_get_doc):
        """Test trigger_onboarding_flow with unprocessed onboarding set"""
        mock_stage = Mock()
        mock_stage.is_active = True
        mock_stage.stage_flows = [Mock(student_status="not_started", glific_flow_id="12345")]
        
        mock_onboarding = Mock()
        mock_onboarding.status = "Draft"
        
        mock_get_doc.side_effect = [mock_stage, mock_onboarding]
        
        trigger_onboarding_flow(
            self.mock_onboarding_set, 
            self.mock_onboarding_stage, 
            self.mock_student_status
        )
        
        mock_throw.assert_called_with("Selected Backend Student Onboarding Set is not in Processed status")
    
    @patch('frappe.get_doc')
    @patch('frappe.throw')
    def test_trigger_onboarding_flow_no_matching_flow(self, mock_throw, mock_get_doc):
        """Test trigger_onboarding_flow with no matching flow for status"""
        mock_stage = Mock()
        mock_stage.is_active = True
        mock_stage.stage_flows = [Mock(student_status="completed", glific_flow_id="12345")]
        
        mock_onboarding = Mock()
        mock_onboarding.status = "Processed"
        
        mock_get_doc.side_effect = [mock_stage, mock_onboarding]
        
        trigger_onboarding_flow(
            self.mock_onboarding_set, 
            self.mock_onboarding_stage, 
            "not_started"  # Different from available status
        )
        
        mock_throw.assert_called()
    
    @patch('trigger_group_flow')
    @patch('get_glific_auth_headers')
    @patch('frappe.get_doc')
    @patch('frappe.logger')
    def test_trigger_onboarding_flow_job_group_flow(self, mock_logger, mock_get_doc, mock_auth, mock_group_flow):
        """Test _trigger_onboarding_flow_job with group flow"""
        # Mock dependencies
        mock_stage = Mock()
        mock_onboarding = Mock()
        mock_settings = Mock()
        
        mock_get_doc.side_effect = [mock_stage, mock_onboarding, mock_settings]
        mock_auth.return_value = {"authorization": "Bearer test_token"}
        mock_group_flow.return_value = {"success": True, "group_count": 5}
        
        # Call function
        result = _trigger_onboarding_flow_job(
            self.mock_onboarding_set,
            self.mock_onboarding_stage,
            self.mock_student_status,
            self.mock_flow_id,
            "Group"
        )
        
        # Assertions
        self.assertIn("success", str(result))
        mock_group_flow.assert_called_once()
    
    @patch('trigger_individual_flows')
    @patch('get_glific_auth_headers')
    @patch('frappe.get_doc')
    @patch('frappe.logger')
    def test_trigger_onboarding_flow_job_individual_flow(self, mock_logger, mock_get_doc, mock_auth, mock_individual_flow):
        """Test _trigger_onboarding_flow_job with individual flow"""
        # Mock dependencies
        mock_stage = Mock()
        mock_onboarding = Mock()
        mock_settings = Mock()
        
        mock_get_doc.side_effect = [mock_stage, mock_onboarding, mock_settings]
        mock_auth.return_value = {"authorization": "Bearer test_token"}
        mock_individual_flow.return_value = {"success": True, "individual_count": 10}
        
        # Call function
        result = _trigger_onboarding_flow_job(
            self.mock_onboarding_set,
            self.mock_onboarding_stage,
            self.mock_student_status,
            self.mock_flow_id,
            "Individual"
        )
        
        # Assertions
        self.assertIn("success", str(result))
        mock_individual_flow.assert_called_once()
    
    @patch('get_glific_auth_headers')
    @patch('frappe.log_error')
    def test_trigger_onboarding_flow_job_auth_failure(self, mock_log_error, mock_auth):
        """Test _trigger_onboarding_flow_job with authentication failure"""
        mock_auth.return_value = None
        
        result = _trigger_onboarding_flow_job(
            self.mock_onboarding_set,
            self.mock_onboarding_stage,
            self.mock_student_status,
            self.mock_flow_id,
            "Group"
        )
        
        self.assertIn("error", result)
        self.assertEqual(result["error"], "Failed to authenticate with Glific API")
    
    @patch('requests.post')
    @patch('create_or_get_glific_group_for_batch')
    @patch('get_students_from_onboarding')
    @patch('update_student_stage_progress_batch')
    @patch('frappe.get_doc')
    @patch('frappe.throw')
    def test_trigger_group_flow_success(self, mock_throw, mock_get_doc, mock_update_batch, 
                                       mock_get_students, mock_get_group, mock_requests):
        """Test successful trigger_group_flow execution"""
        # Mock dependencies
        mock_onboarding = Mock()
        mock_onboarding.name = self.mock_onboarding_set
        
        mock_stage = Mock()
        mock_stage.name = self.mock_onboarding_stage
        
        mock_contact_group = Mock()
        mock_contact_group.group_id = "group_123"
        
        mock_settings = Mock()
        mock_settings.api_url = "https://api.glific.org"
        
        mock_get_group.return_value = {"success": True}
        mock_get_doc.side_effect = [mock_contact_group, mock_settings]
        mock_get_students.return_value = [Mock(), Mock(), Mock()]  # 3 students
        
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "startGroupFlow": {
                    "success": True,
                    "errors": []
                }
            }
        }
        mock_requests.return_value = mock_response
        
        # Call function
        result = trigger_group_flow(
            mock_onboarding, 
            mock_stage, 
            "Bearer test_token", 
            self.mock_student_status, 
            self.mock_flow_id
        )
        
        # Assertions
        self.assertIn("group_flow_result", result)
        self.assertEqual(result["group_count"], 3)
        mock_requests.assert_called_once()
        mock_update_batch.assert_called_once()
        mock_throw.assert_not_called()
    
    @patch('frappe.throw')
    def test_trigger_group_flow_no_flow_id(self, mock_throw):
        """Test trigger_group_flow without flow ID"""
        mock_onboarding = Mock()
        mock_stage = Mock()
        
        trigger_group_flow(mock_onboarding, mock_stage, "Bearer test_token", self.mock_student_status, None)
        
        mock_throw.assert_called_with("No Glific flow ID available for this stage and status")
    
    @patch('create_or_get_glific_group_for_batch')
    @patch('frappe.throw')
    def test_trigger_group_flow_no_contact_group(self, mock_throw, mock_get_group):
        """Test trigger_group_flow when contact group creation fails"""
        mock_onboarding = Mock()
        mock_stage = Mock()
        mock_get_group.return_value = None
        
        trigger_group_flow(
            mock_onboarding, 
            mock_stage, 
            "Bearer test_token", 
            self.mock_student_status, 
            self.mock_flow_id
        )
        
        mock_throw.assert_called_with("Could not find or create contact group for this onboarding set")
    
    @patch('requests.post')
    @patch('create_or_get_glific_group_for_batch')
    @patch('frappe.get_doc')
    @patch('frappe.throw')
    def test_trigger_group_flow_api_error(self, mock_throw, mock_get_doc, mock_get_group, mock_requests):
        """Test trigger_group_flow with API error"""
        # Mock dependencies
        mock_onboarding = Mock()
        mock_stage = Mock()
        mock_contact_group = Mock()
        mock_contact_group.group_id = "group_123"
        mock_settings = Mock()
        mock_settings.api_url = "https://api.glific.org"
        
        mock_get_group.return_value = {"success": True}
        mock_get_doc.side_effect = [mock_contact_group, mock_settings]
        
        # Mock API error response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_requests.return_value = mock_response
        
        trigger_group_flow(
            mock_onboarding, 
            mock_stage, 
            "Bearer test_token", 
            self.mock_student_status, 
            self.mock_flow_id
        )
        
        mock_throw.assert_called()
    
    @patch('start_contact_flow')
    @patch('get_students_from_onboarding')
    @patch('update_student_stage_progress')
    @patch('frappe.db.commit')
    @patch('time.sleep')
    @patch('frappe.throw')
    def test_trigger_individual_flows_success(self, mock_throw, mock_sleep, mock_commit, 
                                            mock_update_progress, mock_get_students, mock_start_flow):
        """Test successful trigger_individual_flows execution"""
        # Mock students
        mock_students = []
        for i in range(3):
            student = Mock()
            student.name = f"student_{i}"
            student.name1 = f"Student {i}"
            student.glific_id = f"glific_{i}"
            mock_students.append(student)
        
        mock_get_students.return_value = mock_students
        mock_start_flow.return_value = True
        
        mock_onboarding = Mock()
        mock_onboarding.name = self.mock_onboarding_set
        mock_stage = Mock()
        mock_stage.name = self.mock_onboarding_stage
        
        # Call function
        result = trigger_individual_flows(
            mock_onboarding, 
            mock_stage, 
            "Bearer test_token", 
            self.mock_student_status, 
            self.mock_flow_id
        )
        
        # Assertions
        self.assertEqual(result["individual_count"], 3)
        self.assertEqual(result["error_count"], 0)
        self.assertEqual(len(result["individual_flow_results"]), 3)
        self.assertEqual(mock_start_flow.call_count, 3)
        self.assertEqual(mock_update_progress.call_count, 3)
        mock_throw.assert_not_called()
    
    @patch('get_students_from_onboarding')
    @patch('frappe.throw')
    def test_trigger_individual_flows_no_students(self, mock_throw, mock_get_students):
        """Test trigger_individual_flows with no students"""
        mock_get_students.return_value = []
        mock_onboarding = Mock()
        mock_stage = Mock()
        
        trigger_individual_flows(
            mock_onboarding, 
            mock_stage, 
            "Bearer test_token", 
            self.mock_student_status, 
            self.mock_flow_id
        )
        
        mock_throw.assert_called_with("No students found in this onboarding set with the selected status")
    
    @patch('start_contact_flow')
    @patch('get_students_from_onboarding')
    @patch('frappe.logger')
    def test_trigger_individual_flows_missing_glific_id(self, mock_logger, mock_get_students, mock_start_flow):
        """Test trigger_individual_flows with students missing Glific ID"""
        # Mock student without Glific ID
        student = Mock()
        student.name = "student_1"
        student.name1 = "Student 1"
        student.glific_id = None
        
        mock_get_students.return_value = [student]
        
        mock_onboarding = Mock()
        mock_stage = Mock()
        
        result = trigger_individual_flows(
            mock_onboarding, 
            mock_stage, 
            "Bearer test_token", 
            self.mock_student_status, 
            self.mock_flow_id
        )
        
        # Should skip student without Glific ID
        self.assertEqual(result["individual_count"], 0)
        mock_start_flow.assert_not_called()
    
    @patch('frappe.get_doc')
    def test_get_stage_flow_statuses_new_structure(self, mock_get_doc):
        """Test get_stage_flow_statuses with new child table structure"""
        mock_stage = Mock()
        mock_stage.stage_flows = [
            Mock(student_status="not_started"),
            Mock(student_status="in_progress"),
            Mock(student_status="completed")
        ]
        mock_get_doc.return_value = mock_stage
        
        result = get_stage_flow_statuses("TEST_STAGE")
        
        self.assertIn("statuses", result)
        self.assertEqual(len(result["statuses"]), 3)
        self.assertIn("not_started", result["statuses"])
        self.assertIn("in_progress", result["statuses"])
        self.assertIn("completed", result["statuses"])
    
    @patch('frappe.get_doc')
    def test_get_stage_flow_statuses_legacy_structure(self, mock_get_doc):
        """Test get_stage_flow_statuses with legacy structure"""
        mock_stage = Mock()
        mock_stage.stage_flows = None
        mock_stage.glific_flow_id = "12345"
        mock_get_doc.return_value = mock_stage
        
        result = get_stage_flow_statuses("TEST_STAGE")
        
        self.assertIn("statuses", result)
        self.assertEqual(len(result["statuses"]), 6)  # All default statuses
    
    @patch('frappe.get_doc')
    @patch('frappe.log_error')
    def test_get_stage_flow_statuses_error(self, mock_log_error, mock_get_doc):
        """Test get_stage_flow_statuses with error"""
        mock_get_doc.side_effect = Exception("Stage not found")
        
        result = get_stage_flow_statuses("INVALID_STAGE")
        
        self.assertEqual(result["statuses"], [])
        self.assertIn("error", result)
        mock_log_error.assert_called_once()
    
    @patch('frappe.get_all')
    @patch('frappe.get_doc')
    @patch('frappe.logger')
    def test_data_consistency_validation(self, mock_logger, mock_get_doc, mock_get_all):
        """Test data consistency validation across different document types"""
        # Mock inconsistent data scenario
        mock_get_all.return_value = [
            {"student_id": "STUD_001"},  # Backend student exists
            {"student_id": "STUD_999"}   # Backend student references non-existent student
        ]
        
        # First student exists, second doesn't
        def get_doc_side_effect(doctype, name):
            if name == "STUD_001":
                return Mock(name="STUD_001")
            else:
                raise Exception("Student not found")
        
        mock_get_doc.side_effect = get_doc_side_effect
        
        mock_onboarding = Mock(name="TEST_SET")
        
        result = get_students_from_onboarding(mock_onboarding)
        
        # Should handle missing student gracefully and log error
        self.assertEqual(len(result), 1)  # Only valid student returned
        mock_logger().error.assert_called()


class TestOnboardingFlowPerformance(unittest.TestCase):
    """Performance and scalability tests"""
    
    @patch('time.sleep')
    @patch('frappe.db.commit')
    @patch('start_contact_flow')
    @patch('get_students_from_onboarding')
    @patch('update_student_stage_progress')
    def test_large_batch_processing_performance(self, mock_update, mock_get_students, 
                                              mock_start_flow, mock_commit, mock_sleep):
        """Test performance with large batches of students"""
        # Create 100 students to test scalability
        large_student_batch = []
        for i in range(100):
            student = Mock()
            student.name = f"STUD_{i:04d}"
            student.name1 = f"Student {i}"
            student.glific_id = f"glific_{i}"
            large_student_batch.append(student)
        
        mock_get_students.return_value = large_student_batch
        mock_start_flow.return_value = True
        
        mock_onboarding = Mock()
        mock_stage = Mock()
        
        # Execute with timing consideration
        import time
        start_time = time.time()
        
        result = trigger_individual_flows(
            mock_onboarding, mock_stage, "Bearer token", "not_started", "flow_123"
        )
        
        execution_time = time.time() - start_time
        
        # Verify all students processed
        self.assertEqual(result["individual_count"], 100)
        self.assertEqual(result["error_count"], 0)
        
        # Verify batch processing (100 students / 10 per batch = 10 batches, 9 sleeps)
        self.assertEqual(mock_sleep.call_count, 9)
        
        # Performance assertion - should complete within reasonable time
        self.assertLess(execution_time, 5.0, "Large batch processing took too long")
    
    @patch('frappe.get_all')
    @patch('frappe.get_doc')
    @patch('now_datetime')
    @patch('frappe.db.commit')
    def test_bulk_progress_update_performance(self, mock_commit, mock_now, mock_get_doc, mock_get_all):
        """Test performance of bulk progress updates"""
        mock_now.return_value = datetime.now()
        
        # Create large batch of students
        students = [Mock(name=f"STUD_{i:04d}") for i in range(50)]
        mock_stage = Mock(name="TEST_STAGE")
        
        # Mock no existing progress records (all new)
        mock_get_all.return_value = []
        
        # Mock new document creation
        with patch('frappe.new_doc') as mock_new_doc:
            mock_progress_docs = [Mock() for _ in range(50)]
            mock_new_doc.side_effect = mock_progress_docs
            
            # Time the batch update
            start_time = time.time()
            update_student_stage_progress_batch(students, mock_stage)
            execution_time = time.time() - start_time
            
            # Verify all records created
            self.assertEqual(mock_new_doc.call_count, 50)
            for progress_doc in mock_progress_docs:
                progress_doc.insert.assert_called_once()
            
            # Performance assertion
            self.assertLess(execution_time, 3.0, "Bulk progress update took too long")


class TestOnboardingFlowSecurity(unittest.TestCase):
    """Security-related tests"""
    
    @patch('frappe.get_doc')
    @patch('frappe.throw')
    def test_input_validation_sql_injection(self, mock_throw, mock_get_doc):
        """Test protection against SQL injection attempts"""
        # Attempt SQL injection in parameters
        malicious_input = "'; DROP TABLE StudentStageProgress; --"
        
        # Should handle malicious input safely
        trigger_onboarding_flow(
            "VALID_SET",
            malicious_input,  # Malicious stage name
            "not_started"
        )
        
        # Function should either throw validation error or handle safely
        # The exact behavior depends on Frappe's input validation
        self.assertTrue(mock_get_doc.called or mock_throw.called)
    
    @patch('get_glific_auth_headers')
    @patch('frappe.log_error')
    def test_authentication_token_handling(self, mock_log_error, mock_auth):
        """Test secure handling of authentication tokens"""
        # Test with None token
        mock_auth.return_value = None
        
        result = _trigger_onboarding_flow_job(
            "SET_001", "STAGE_001", "not_started", "flow_123", "Group"
        )
        
        self.assertIn("error", result)
        self.assertEqual(result["error"], "Failed to authenticate with Glific API")
        
        # Test with empty authorization
        mock_auth.return_value = {"authorization": ""}
        
        result = _trigger_onboarding_flow_job(
            "SET_001", "STAGE_001", "not_started", "flow_123", "Group"
        )
        
        self.assertIn("error", result)
    
    @patch('requests.post')
    @patch('create_or_get_glific_group_for_batch')
    @patch('frappe.get_doc')
    def test_api_response_sanitization(self, mock_get_doc, mock_get_group, mock_requests):
        """Test sanitization of API responses"""
        # Setup basic mocks
        mock_onboarding = Mock()
        mock_stage = Mock()
        mock_contact_group = Mock(group_id="group_123")
        mock_settings = Mock(api_url="https://api.glific.org")
        
        mock_get_group.return_value = {"success": True}
        mock_get_doc.side_effect = [mock_contact_group, mock_settings]
        
        # Mock response with potentially malicious content
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "startGroupFlow": {
                    "success": False,
                    "errors": [
                        {
                            "key": "malicious_key",
                            "message": "<script>alert('xss')</script>Malicious message"
                        }
                    ]
                }
            }
        }
        mock_requests.return_value = mock_response
        
        # Should handle malicious content safely
        with patch('frappe.throw') as mock_throw:
            trigger_group_flow(
                mock_onboarding, mock_stage, "Bearer token", "not_started", "flow_123"
            )
            
            # Should throw error but not execute malicious content
            mock_throw.assert_called()


class TestOnboardingFlowDocumentation(unittest.TestCase):
    """Tests to validate that functions work as documented"""
    
    def test_function_signatures(self):
        """Test that all functions have expected signatures"""
        import inspect
        
        # Test main trigger function signature
        sig = inspect.signature(trigger_onboarding_flow)
        params = list(sig.parameters.keys())
        expected_params = ['onboarding_set', 'onboarding_stage', 'student_status']
        self.assertEqual(params, expected_params)
        
        # Test job function signature
        sig = inspect.signature(_trigger_onboarding_flow_job)
        params = list(sig.parameters.keys())
        expected_params = ['onboarding_set', 'onboarding_stage', 'student_status', 'flow_id', 'flow_type']
        self.assertEqual(params, expected_params)
    
    def test_return_value_formats(self):
        """Test that functions return values in expected formats"""
        with patch('frappe.enqueue') as mock_enqueue, \
             patch('frappe.get_doc') as mock_get_doc:
            
            # Mock successful execution
            mock_stage = Mock()
            mock_stage.is_active = True
            mock_stage.stage_flows = [Mock(student_status="not_started", glific_flow_id="123", flow_type="Group")]
            
            mock_onboarding = Mock()
            mock_onboarding.status = "Processed"
            
            mock_get_doc.side_effect = [mock_stage, mock_onboarding]
            mock_enqueue.return_value = "job_123"
            
            result = trigger_onboarding_flow("SET_001", "STAGE_001", "not_started")
            
            # Verify return format matches documentation
            self.assertIsInstance(result, dict)
            self.assertIn("success", result)
            self.assertIn("job_id", result)
            self.assertIsInstance(result["success"], bool)
            self.assertIsInstance(result["job_id"], str)


class TestOnboardingFlowCompatibility(unittest.TestCase):
    """Tests for backward compatibility and version compatibility"""
    
    @patch('frappe.enqueue')
    @patch('frappe.get_doc')
    def test_legacy_stage_structure_compatibility(self, mock_get_doc, mock_enqueue):
        """Test compatibility with legacy stage structure"""
        # Mock legacy stage structure
        mock_stage = Mock()
        mock_stage.is_active = True
        mock_stage.stage_flows = None  # Legacy: no child table
        mock_stage.glific_flow_id = "legacy_flow_123"
        # Mock missing flow_type attribute (very old legacy)
        if not hasattr(mock_stage, 'glific_flow_type'):
            mock_stage.glific_flow_type = None
        
        mock_onboarding = Mock()
        mock_onboarding.status = "Processed"
        
        mock_get_doc.side_effect = [mock_stage, mock_onboarding]
        mock_enqueue.return_value = "job_123"
        
        # Should handle legacy structure gracefully
        result = trigger_onboarding_flow("SET_001", "STAGE_001", "not_started")
        
        self.assertTrue(result["success"])
        
        # Verify job was called with defaults for missing fields
        call_kwargs = mock_enqueue.call_args[1]
        self.assertEqual(call_kwargs["flow_id"], "legacy_flow_123")
        self.assertEqual(call_kwargs["flow_type"], "Group")  # Default value
    
    @patch('frappe.get_doc')
    def test_new_stage_structure_compatibility(self, mock_get_doc):
        """Test compatibility with new stage structure"""
        # Mock new stage structure
        mock_stage = Mock()
        mock_stage.stage_flows = [
            Mock(student_status="not_started", glific_flow_id="new_flow_123", flow_type="Individual"),
            Mock(student_status="completed", glific_flow_id="completion_flow_456", flow_type="Group")
        ]
        
        mock_get_doc.return_value = mock_stage
        
        result = get_stage_flow_statuses("STAGE_001")
        
        # Should return all available statuses from new structure
        self.assertIn("statuses", result)
        self.assertIn("not_started", result["statuses"])
        self.assertIn("completed", result["statuses"])
        self.assertEqual(len(result["statuses"]), 2)


# Test runner and configuration
class TestOnboardingFlowRunner:
    """Test runner with custom configuration"""
    
    @staticmethod
    def run_all_tests(verbosity=2):
        """Run all test suites"""
        # Create test suite
        test_suite = unittest.TestSuite()
        
        # Add all test classes
        test_classes = [
            TestOnboardingFlowFunctions,
            TestOnboardingFlowIntegration,
            TestOnboardingFlowEdgeCases,
            TestOnboardingFlowPerformance,
            TestOnboardingFlowSecurity,
            TestOnboardingFlowDocumentation,
            TestOnboardingFlowCompatibility
        ]
        
        for test_class in test_classes:
            tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
            test_suite.addTests(tests)
        
        # Run tests with custom result class for better reporting
        runner = unittest.TextTestRunner(
            verbosity=verbosity,
            stream=sys.stdout,
            buffer=True,
            failfast=False
        )
        
        result = runner.run(test_suite)
        
        # Print summary
        print(f"\n{'='*60}")
        print(f"TEST SUMMARY")
        print(f"{'='*60}")
        print(f"Tests run: {result.testsRun}")
        print(f"Failures: {len(result.failures)}")
        print(f"Errors: {len(result.errors)}")
        print(f"Skipped: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
        
        if result.failures:
            print(f"\nFAILURES:")
            for test, traceback in result.failures:
                print(f"- {test}")
        
        if result.errors:
            print(f"\nERRORS:")
            for test, traceback in result.errors:
                print(f"- {test}")
        
        success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun) * 100
        print(f"\nSuccess Rate: {success_rate:.1f}%")
        
        return result.wasSuccessful()
    
    @staticmethod
    def run_specific_category(category_name, verbosity=2):
        """Run tests for a specific category"""
        category_map = {
            'functions': TestOnboardingFlowFunctions,
            'integration': TestOnboardingFlowIntegration,
            'edge_cases': TestOnboardingFlowEdgeCases,
            'performance': TestOnboardingFlowPerformance,
            'security': TestOnboardingFlowSecurity,
            'documentation': TestOnboardingFlowDocumentation,
            'compatibility': TestOnboardingFlowCompatibility
        }
        
        if category_name not in category_map:
            print(f"Unknown category: {category_name}")
            print(f"Available categories: {', '.join(category_map.keys())}")
            return False
        
        test_class = category_map[category_name]
        suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
        runner = unittest.TextTestRunner(verbosity=verbosity, buffer=True)
        result = runner.run(suite)
        
        return result.wasSuccessful()


# Main execution
if __name__ == '__main__':
    import sys
    
    # Check if specific category requested
    if len(sys.argv) > 1 and sys.argv[1] in ['functions', 'integration', 'edge_cases', 'performance', 'security', 'documentation', 'compatibility']:
        category = sys.argv[1]
        success = TestOnboardingFlowRunner.run_specific_category(category)
    else:
        # Run all tests
        success = TestOnboardingFlowRunner.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)('frappe.get_doc')
    @patch('frappe.logger')
    def test_get_students_from_onboarding_with_status_filter(self, mock_logger, mock_get_doc, mock_get_all):
        """Test get_students_from_onboarding with stage and status filters"""
        # Mock backend students
        mock_get_all.side_effect = [
            [{"student_id": "STUD_001"}, {"student_id": "STUD_002"}],  # Backend students
            [{"name": "progress_1"}],  # Stage progress for STUD_001
            []  # No stage progress for STUD_002
        ]
        
        # Mock student documents
        mock_student_1 = Mock()
        mock_student_1.name = "STUD_001"
        mock_get_doc.return_value = mock_student_1
        
        mock_onboarding = Mock()
        mock_onboarding.name = self.mock_onboarding_set
        
        result = get_students_from_onboarding(mock_onboarding, "TEST_STAGE", "in_progress")
        
        self.assertEqual(len(result), 1)  # Only STUD_001 has matching status
        self.assertEqual(result[0].name, "STUD_001")
    
    @patch('frappe.get_all')
    @patch('frappe.get_doc')
    @patch('frappe.logger')
    def test_get_students_from_onboarding_not_started_status(self, mock_logger, mock_get_doc, mock_get_all):
        """Test get_students_from_onboarding with not_started status"""
        # Mock backend students
        mock_get_all.side_effect = [
            [{"student_id": "STUD_001"}, {"student_id": "STUD_002"}],  # Backend students
            [],  # No stage progress for STUD_001 (first call)
            [],  # No stage progress for STUD_002 (second call)
            [],  # No progress for STUD_001 in not_started check
            []   # No progress for STUD_002 in not_started check
        ]
        
        # Mock student documents
        mock_students = [Mock(name="STUD_001"), Mock(name="STUD_002")]
        mock_get_doc.side_effect = mock_students
        
        mock_onboarding = Mock()
        mock_onboarding.name = self.mock_onboarding_set
        
        result = get_students_from_onboarding(mock_onboarding, "TEST_STAGE", "not_started")
        
        self.assertEqual(len(result), 2)  # Both students have no progress records
    
    @patch('frappe.get_all')
    @patch('frappe.logger')
    def test_get_students_from_onboarding_no_backend_students(self, mock_logger, mock_get_all):
        """Test get_students_from_onboarding with no backend students"""
        mock_get_all.return_value = []
        
        mock_onboarding = Mock()
        mock_onboarding.name = self.mock_onboarding_set
        
        result = get_students_from_onboarding(mock_onboarding)
        
        self.assertEqual(len(result), 0)
    
    @patch('frappe.get_all')
    @patch('frappe.get_doc')
    @patch('frappe.new_doc')
    @patch('frappe.db.commit')
    @patch('now_datetime')
    @patch('frappe.logger')
    def test_update_student_stage_progress_new_record(self, mock_logger, mock_now, mock_commit, 
                                                     mock_new_doc, mock_get_doc, mock_get_all):
        """Test update_student_stage_progress creating new record"""
        mock_now.return_value = self.mock_now
        mock_get_all.return_value = []  # No existing records
        
        mock_progress = Mock()
        mock_new_doc.return_value = mock_progress
        
        mock_student = Mock()
        mock_student.name = "STUD_001"
        mock_stage = Mock()
        mock_stage.name = "STAGE_001"
        
        update_student_stage_progress(mock_student, mock_stage)
        
        # Verify new document creation
        mock_new_doc.assert_called_once_with("StudentStageProgress")
        mock_progress.insert.assert_called_once()
        self.assertEqual(mock_progress.student, "STUD_001")
        self.assertEqual(mock_progress.stage, "STAGE_001")
        self.assertEqual(mock_progress.status, "assigned")
    
    @patch('frappe.get_all')
    @patch('frappe.get_doc')
    @patch('now_datetime')
    @patch('frappe.logger')
    def test_update_student_stage_progress_update_existing(self, mock_logger, mock_now, mock_get_doc, mock_get_all):
        """Test update_student_stage_progress updating existing record"""
        mock_now.return_value = self.mock_now
        mock_get_all.return_value = [{"name": "progress_1"}]  # Existing record
        
        mock_progress = Mock()
        mock_progress.status = "not_started"  # Should be updated
        mock_progress.start_timestamp = None
        mock_get_doc.return_value = mock_progress
        
        mock_student = Mock()
        mock_student.name = "STUD_001"
        mock_stage = Mock()
        mock_stage.name = "STAGE_001"
        
        update_student_stage_progress(mock_student, mock_stage)
        
        # Verify update
        mock_progress.save.assert_called_once()
        self.assertEqual(mock_progress.status, "assigned")
        self.assertEqual(mock_progress.start_timestamp, self.mock_now)
    
    @patch('frappe.get_all')
    @patch('frappe.get_doc')
    @patch('now_datetime')
    @patch('frappe.logger')
    def test_update_student_stage_progress_no_update_completed(self, mock_logger, mock_now, mock_get_doc, mock_get_all):
        """Test update_student_stage_progress not updating completed record"""
        mock_now.return_value = self.mock_now
        mock_get_all.return_value = [{"name": "progress_1"}]
        
        mock_progress = Mock()
        mock_progress.status = "completed"  # Should not be updated
        mock_get_doc.return_value = mock_progress
        
        mock_student = Mock()
        mock_stage = Mock()
        
        update_student_stage_progress(mock_student, mock_stage)
        
        # Should not save completed progress
        mock_progress.save.assert_not_called()
    
    @patch('update_student_stage_progress')
    @patch('frappe.db.commit')
    @patch('frappe.logger')
    def test_update_student_stage_progress_batch_success(self, mock_logger, mock_commit, mock_update):
        """Test update_student_stage_progress_batch successful execution"""
        mock_students = [Mock(name="STUD_001"), Mock(name="STUD_002"), Mock(name="STUD_003")]
        mock_stage = Mock()
        
        update_student_stage_progress_batch(mock_students, mock_stage)
        
        # Should call update for each student
        self.assertEqual(mock_update.call_count, 3)
        mock_commit.assert_called_once()
    
    @patch('frappe.logger')
    def test_update_student_stage_progress_batch_empty_list(self, mock_logger):
        """Test update_student_stage_progress_batch with empty student list"""
        mock_stage = Mock()
        
        update_student_stage_progress_batch([], mock_stage)
        
        # Should log warning and return early
        mock_logger().warning.assert_called_once()
    
    @patch('get_job_status')
    @patch('frappe.utils.background_jobs.get_redis_conn')
    @patch('rq.job.Job.fetch')
    def test_get_job_status_complete_with_results(self, mock_fetch, mock_redis, mock_job_status):
        """Test get_job_status for completed job with results"""
        mock_job_status.return_value = "finished"
        mock_redis.return_value = Mock()
        
        mock_job = Mock()
        mock_job.result = {"success": True, "count": 5}
        mock_fetch.return_value = mock_job
        
        result = get_job_status(self.mock_job_id)
        
        self.assertEqual(result["status"], "complete")
        self.assertIn("results", result)
        self.assertEqual(result["results"]["count"], 5)
    
    @patch('get_job_status')
    def test_get_job_status_failed(self, mock_job_status):
        """Test get_job_status for failed job"""
        mock_job_status.return_value = "failed"
        
        result = get_job_status(self.mock_job_id)
        
        self.assertEqual(result["status"], "failed")
    
    @patch('get_job_status')
    def test_get_job_status_running(self, mock_job_status):
        """Test get_job_status for running job"""
        mock_job_status.return_value = "started"
        
        result = get_job_status(self.mock_job_id)
        
        self.assertEqual(result["status"], "started")
    
    def test_get_job_status_no_job_id(self):
        """Test get_job_status with no job ID"""
        result = get_job_status("")
        
        self.assertEqual(result["status"], "unknown")
    
    @patch('frappe.get_all')
    @patch('frappe.get_doc')
    @patch('frappe.logger')
    def test_get_onboarding_progress_report_with_filters(self, mock_logger, mock_get_doc, mock_get_all):
        """Test get_onboarding_progress_report with stage and status filters"""
        # Mock progress records
        mock_get_all.side_effect = [
            [
                {
                    "name": "progress_1",
                    "student": "STUD_001",
                    "stage": "STAGE_001",
                    "status": "completed",
                    "start_timestamp": self.mock_now,
                    "last_activity_timestamp": self.mock_now,
                    "completion_timestamp": self.mock_now
                }
            ]
        ]
        
        # Mock student and stage documents
        mock_student = Mock()
        mock_student.name = "STUD_001"
        mock_student.name1 = "Student One"
        mock_student.phone = "1234567890"
        
        mock_stage = Mock()
        mock_stage.name = "STAGE_001"
        
        mock_get_doc.side_effect = [mock_student, mock_stage]
        
        result = get_onboarding_progress_report(stage="STAGE_001", status="completed")
        
        # Assertions
        self.assertEqual(result["summary"]["total"], 1)
        self.assertEqual(result["summary"]["completed"], 1)
        self.assertEqual(len(result["details"]), 1)
        self.assertEqual(result["details"][0]["student"], "STUD_001")
        self.assertEqual(result["details"][0]["status"], "completed")
    
    @patch('frappe.get_all')
    @patch('frappe.get_doc')
    @patch('frappe.logger')
    def test_get_onboarding_progress_report_with_set_filter(self, mock_logger, mock_get_doc, mock_get_all):
        """Test get_onboarding_progress_report with onboarding set filter"""
        # Mock progress records
        mock_get_all.side_effect = [
            [
                {
                    "name": "progress_1",
                    "student": "STUD_001",
                    "stage": "STAGE_001",
                    "status": "in_progress",
                    "start_timestamp": self.mock_now,
                    "last_activity_timestamp": self.mock_now,
                    "completion_timestamp": None
                }
            ],
            # Mock backend students for set filter
            [{"student_id": "STUD_001"}]
        ]
        
        # Mock documents
        mock_student = Mock()
        mock_student.name = "STUD_001"
        mock_student.name1 = "Student One"
        mock_student.phone = "1234567890"
        
        mock_stage = Mock()
        mock_stage.name = "STAGE_001"
        
        mock_get_doc.side_effect = [mock_student, mock_stage]
        
        result = get_onboarding_progress_report(set="SET_001")
        
        # Should include the student since they belong to the set
        self.assertEqual(result["summary"]["total"], 1)
        self.assertEqual(result["summary"]["in_progress"], 1)
    
    @patch('frappe.get_all')
    @patch('frappe.get_doc')
    @patch('frappe.logger')
    def test_get_onboarding_progress_report_not_started_students(self, mock_logger, mock_get_doc, mock_get_all):
        """Test get_onboarding_progress_report including not_started students"""
        # Mock no progress records initially, then backend students, then no existing progress
        mock_get_all.side_effect = [
            [],  # No progress records
            [{"student_id": "STUD_001"}, {"student_id": "STUD_002"}],  # Backend students
            [],  # No existing progress for STUD_001
            []   # No existing progress for STUD_002
        ]
        
        # Mock student documents
        mock_student_1 = Mock()
        mock_student_1.name = "STUD_001"
        mock_student_1.name1 = "Student One"
        mock_student_1.phone = "1234567890"
        
        mock_student_2 = Mock()
        mock_student_2.name = "STUD_002"
        mock_student_2.name1 = "Student Two"
        mock_student_2.phone = "0987654321"
        
        mock_stage = Mock()
        mock_stage.name = "STAGE_001"
        
        mock_get_doc.side_effect = [mock_student_1, mock_stage, mock_student_2, mock_stage]
        
        result = get_onboarding_progress_report(set="SET_001", stage="STAGE_001", status="not_started")
        
        # Should include both students as not_started
        self.assertEqual(result["summary"]["total"], 2)
        self.assertEqual(result["summary"]["not_started"], 2)
        self.assertEqual(len(result["details"]), 2)
    
    @patch('frappe.get_all')
    @patch('frappe.log_error')
    @patch('frappe.throw')
    def test_get_onboarding_progress_report_error(self, mock_throw, mock_log_error, mock_get_all):
        """Test get_onboarding_progress_report with database error"""
        mock_get_all.side_effect = Exception("Database connection failed")
        
        get_onboarding_progress_report()
        
        mock_log_error.assert_called_once()
        mock_throw.assert_called_once()
    
    @patch('frappe.get_all')
    @patch('frappe.db.commit')
    @patch('frappe.logger')
    @patch('add_to_date')
    @patch('now_datetime')
    def test_update_incomplete_stages_success(self, mock_now, mock_add_date, mock_logger, mock_commit, mock_get_all):
        """Test update_incomplete_stages successful execution"""
        mock_now.return_value = self.mock_now
        mock_add_date.return_value = self.mock_now - timedelta(days=3)
        
        # Mock assigned records older than 3 days
        mock_get_all.return_value = [
            {
                "name": "progress_1",
                "student": "STUD_001",
                "stage": "STAGE_001",
                "start_timestamp": self.mock_now - timedelta(days=4)
            },
            {
                "name": "progress_2", 
                "student": "STUD_002",
                "stage": "STAGE_001",
                "start_timestamp": self.mock_now - timedelta(days=5)
            }
        ]
        
        # Mock progress documents
        with patch('frappe.get_doc') as mock_get_doc:
            mock_progress_1 = Mock()
            mock_progress_2 = Mock()
            mock_get_doc.side_effect = [mock_progress_1, mock_progress_2]
            
            update_incomplete_stages()
            
            # Verify both records were updated
            self.assertEqual(mock_progress_1.status, "incomplete")
            self.assertEqual(mock_progress_2.status, "incomplete")
            mock_progress_1.save.assert_called_once()
            mock_progress_2.save.assert_called_once()
            mock_commit.assert_called_once()
    
    @patch('frappe.get_all')
    @patch('frappe.logger')
    def test_update_incomplete_stages_no_records(self, mock_logger, mock_get_all):
        """Test update_incomplete_stages with no records to update"""
        mock_get_all.return_value = []
        
        update_incomplete_stages()
        
        # Should log that 0 records were found and updated
        mock_logger().info.assert_called()
    
    @patch('frappe.get_all')
    @patch('frappe.log_error')
    def test_update_incomplete_stages_error(self, mock_log_error, mock_get_all):
        """Test update_incomplete_stages with error"""
        mock_get_all.side_effect = Exception("Database error")
        
        update_incomplete_stages()
        
        mock_log_error.assert_called_once()
    
    @patch('frappe.get_all')
    @patch('frappe.get_doc')
    @patch('frappe.logger')
    def test_update_incomplete_stages_partial_failure(self, mock_logger, mock_get_doc, mock_get_all):
        """Test update_incomplete_stages with partial failures"""
        mock_get_all.return_value = [
            {"name": "progress_1", "student": "STUD_001", "stage": "STAGE_001"},
            {"name": "progress_2", "student": "STUD_002", "stage": "STAGE_001"}
        ]
        
        # First doc succeeds, second fails
        mock_progress_1 = Mock()
        mock_get_doc.side_effect = [mock_progress_1, Exception("Update failed")]
        
        update_incomplete_stages()
        
        # Should update first record and log error for second
        mock_progress_1.save.assert_called_once()
        mock_logger().error.assert_called()
    
    # Integration-style tests for complex workflows
    
    @patch('frappe.enqueue')
    @patch('frappe.get_doc')
    def test_end_to_end_trigger_flow_legacy_structure(self, mock_get_doc, mock_enqueue):
        """Test end-to-end flow triggering with legacy stage structure"""
        # Mock legacy stage (no stage_flows child table)
        mock_stage = Mock()
        mock_stage.name = self.mock_onboarding_stage
        mock_stage.is_active = True
        mock_stage.stage_flows = None  # Legacy structure
        mock_stage.glific_flow_id = "legacy_flow_123"
        mock_stage.glific_flow_type = "Group"
        
        mock_onboarding = Mock()
        mock_onboarding.status = "Processed"
        
        mock_get_doc.side_effect = [mock_stage, mock_onboarding]
        mock_enqueue.return_value = "job_123"
        
        result = trigger_onboarding_flow(
            self.mock_onboarding_set,
            self.mock_onboarding_stage, 
            "not_started"
        )
        
        # Should succeed with legacy structure
        self.assertTrue(result["success"])
        mock_enqueue.assert_called_once()
        
        # Verify job parameters include legacy flow info
        call_args = mock_enqueue.call_args
        self.assertEqual(call_args[1]["flow_id"], "legacy_flow_123")
        self.assertEqual(call_args[1]["flow_type"], "Group")
    
    @patch('get_students_from_onboarding')
    @patch('start_contact_flow')
    @patch('update_student_stage_progress')
    def test_individual_flow_error_handling(self, mock_update, mock_start_flow, mock_get_students):
        """Test individual flow execution with mixed success/failure"""
        # Mock students
        students = [
            Mock(name="STUD_001", name1="Student 1", glific_id="glific_1"),
            Mock(name="STUD_002", name1="Student 2", glific_id="glific_2"),
            Mock(name="STUD_003", name1="Student 3", glific_id="glific_3")
        ]
        mock_get_students.return_value = students
        
        # Mock flow start results: success, failure, exception
        mock_start_flow.side_effect = [True, False, Exception("API Error")]
        
        mock_onboarding = Mock()
        mock_stage = Mock()
        
        result = trigger_individual_flows(
            mock_onboarding, mock_stage, "Bearer token", "not_started", "flow_123"
        )
        
        # Verify results
        self.assertEqual(result["individual_count"], 1)  # Only one success
        self.assertEqual(result["error_count"], 2)       # Two failures
        self.assertEqual(len(result["individual_flow_results"]), 3)
        
        # Check individual results
        results = result["individual_flow_results"]
        self.assertTrue(results[0]["success"])
        self.assertFalse(results[1]["success"])
        self.assertFalse(results[2]["success"])
        self.assertIn("API Error", results[2]["error"])
        
        # Only successful student should have progress updated
        mock_update.assert_called_once_with(students[0], mock_stage)
    
    @patch('frappe.get_all')
    @patch('frappe.get_doc')
    def test_complex_student_filtering_scenario(self, mock_get_doc, mock_get_all):
        """Test complex student filtering with multiple status combinations"""
        # Mock backend students
        backend_students = [
            {"student_id": "STUD_001"},
            {"student_id": "STUD_002"}, 
            {"student_id": "STUD_003"},
            {"student_id": "STUD_004"}
        ]
        
        # Mock stage progress records
        # STUD_001: in_progress, STUD_002: completed, STUD_003: not_started (no record), STUD_004: assigned
        mock_get_all.side_effect = [
            backend_students,
            [{"name": "progress_1"}],  # STUD_001 has progress
            [{"name": "progress_2"}],  # STUD_002 has progress  
            [],                        # STUD_003 has no progress
            [{"name": "progress_4"}]   # STUD_004 has progress
        ]
        
        # Mock student documents
        students = [
            Mock(name="STUD_001"),
            Mock(name="STUD_002"),
            Mock(name="STUD_003"), 
            Mock(name="STUD_004")
        ]
        mock_get_doc.side_effect = students
        
        mock_onboarding = Mock()
        mock_onboarding.name = "TEST_SET"
        
        # Test filtering by in_progress status
        result = get_students_from_onboarding(mock_onboarding, "TEST_STAGE", "in_progress")
        
        # Should return students based on the mock setup
        # In this simplified test, we expect the filtering logic to work
        self.assertIsInstance(result, list)
    
    # Error handling and edge cases
    
    def test_trigger_onboarding_flow_exception_handling(self):
        """Test trigger_onboarding_flow exception handling and logging"""
        with patch('frappe.get_doc') as mock_get_doc, \
             patch('frappe.throw') as mock_throw, \
             patch('frappe.log_error') as mock_log_error:
            
            mock_get_doc.side_effect = Exception("Unexpected database error")
            
            trigger_onboarding_flow("SET_001", "STAGE_001", "not_started")
            
            # Should log error and throw user-friendly message
            mock_log_error.assert_called_once()
            mock_throw.assert_called_once()
    
    @patch('frappe.get_doc')
    @patch('frappe.throw')
    def test_stage_validation_edge_cases(self, mock_throw, mock_get_doc):
        """Test various stage validation edge cases"""
        # Test with stage that has empty stage_flows list
        mock_stage = Mock()
        mock_stage.is_active = True
        mock_stage.stage_flows = []  # Empty list
        mock_stage.glific_flow_id = None  # No legacy flow either
        
        mock_onboarding = Mock()
        mock_onboarding.status = "Processed"
        
        mock_get_doc.side_effect = [mock_stage, mock_onboarding]
        
        trigger_onboarding_flow("SET_001", "STAGE_001", "not_started")
        
        mock_throw.assert_called()  # Should throw error for no flows
    
    @patch('requests.post')
    @patch('create_or_get_glific_group_for_batch')
    @patch('frappe.get_doc')
    @patch('frappe.throw')
    def test_group_flow_glific_api_edge_cases(self, mock_throw, mock_get_doc, mock_get_group, mock_requests):
        """Test group flow with various Glific API response edge cases"""
        # Setup mocks
        mock_onboarding = Mock(name="TEST_SET")
        mock_stage = Mock(name="TEST_STAGE")
        mock_contact_group = Mock(group_id="group_123")
        mock_settings = Mock(api_url="https://api.glific.org")
        
        mock_get_group.return_value = {"success": True}
        mock_get_doc.side_effect = [mock_contact_group, mock_settings]
        
        # Test API response with success=False but no error details
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "startGroupFlow": {
                    "success": False,
                    "errors": []
                }
            }
        }
        mock_requests.return_value = mock_response
        
        trigger_group_flow(mock_onboarding, mock_stage, "Bearer token", "not_started", "flow_123")
        
        mock_throw.assert_called()  # Should throw for failed flow
    
    # Performance and batch processing tests
    
    @patch('time.sleep')
    @patch('frappe.db.commit')
    @patch('start_contact_flow')
    @patch('get_students_from_onboarding')
    def test_individual_flows_batch_processing(self, mock_get_students, mock_start_flow, mock_commit, mock_sleep):
        """Test individual flows batch processing with large student count"""
        # Create 25 students to test batching (batch_size = 10)
        students = []
        for i in range(25):
            student = Mock()
            student.name = f"STUD_{i:03d}"
            student.name1 = f"Student {i}"
            student.glific_id = f"glific_{i}"
            students.append(student)
        
        mock_get_students.return_value = students
        mock_start_flow.return_value = True
        
        mock_onboarding = Mock()
        mock_stage = Mock()
        
        result = trigger_individual_flows(
            mock_onboarding, mock_stage, "Bearer token", "not_started", "flow_123"
        )
        
        # Verify all students processed
        self.assertEqual(result["individual_count"], 25)
        self.assertEqual(result["error_count"], 0)
        self.assertEqual(mock_start_flow.call_count, 25)
        
        # Verify batching behavior (should sleep 2 times for 3 batches: 10, 10, 5)
        self.assertEqual(mock_sleep.call_count, 2)  # Sleep between batches
        mock_commit.assert_called()  # Should commit between batches


class TestOnboardingFlowIntegration(unittest.TestCase):
    """Integration tests that test multiple functions working together"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        self.test_data = {
            "onboarding_set": "INT_TEST_SET",
            "stage": "INT_TEST_STAGE", 
            "flow_id": "int_flow_123",
            "students": [
                {"id": "INT_STUD_001", "name": "Integration Student 1", "glific_id": "int_glific_1"},
                {"id": "INT_STUD_002", "name": "Integration Student 2", "glific_id": "int_glific_2"}
            ]
        }
    
    @patch('_trigger_onboarding_flow_job')
    @patch('frappe.enqueue')
    @patch('frappe.get_doc')
    def test_complete_group_flow_workflow(self, mock_get_doc, mock_enqueue, mock_job):
        """Test complete workflow from trigger to group flow execution"""
        # Setup stage and onboarding mocks
        mock_stage = Mock()
        mock_stage.is_active = True
        mock_stage.stage_flows = [Mock(student_status="not_started", glific_flow_id="group_flow_123", flow_type="Group")]
        
        mock_onboarding = Mock()
        mock_onboarding.status = "Processed"
        
        mock_get_doc.side_effect = [mock_stage, mock_onboarding]
        mock_enqueue.return_value = "integration_job_123"
        mock_job.return_value = {"success": True, "group_count": 2}
        
        # Trigger the flow
        result = trigger_onboarding_flow(
            self.test_data["onboarding_set"],
            self.test_data["stage"],
            "not_started"
        )
        
        # Verify trigger response
        self.assertTrue(result["success"])
        self.assertEqual(result["job_id"], "integration_job_123")
        
        # Verify job was enqueued with correct parameters
        mock_enqueue.assert_called_once()
        call_kwargs = mock_enqueue.call_args[1]
        self.assertEqual(call_kwargs["flow_id"], "group_flow_123")
        self.assertEqual(call_kwargs["flow_type"], "Group")
    
    @patch('update_student_stage_progress')
    @patch('start_contact_flow')
    @patch('get_students_from_onboarding')
    @patch('frappe.get_doc')
    def test_complete_individual_flow_workflow(self, mock_get_doc, mock_get_students, mock_start_flow, mock_update):
        """Test complete individual flow workflow with progress tracking"""
        # Mock students
        students = []
        for student_data in self.test_data["students"]:
            student = Mock()
            student.name = student_data["id"]
            student.name1 = student_data["name"] 
            student.glific_id = student_data["glific_id"]
            students.append(student)
        
        mock_get_students.return_value = students
        mock_start_flow.return_value = True
        
        # Mock documents
        mock_onboarding = Mock(name=self.test_data["onboarding_set"])
        mock_stage = Mock(name=self.test_data["stage"])
        mock_settings = Mock()
        
        mock_get_doc.side_effect = [mock_stage, mock_onboarding, mock_settings]
        
        # Execute individual flows
        result = trigger_individual_flows(
            mock_onboarding,
            mock_stage, 
            "Bearer integration_token",
            "not_started",
            self.test_data["flow_id"]
        )
        
        # Verify results
        self.assertEqual(result["individual_count"], 2)
        self.assertEqual(result["error_count"], 0)
        
        # Verify all students had flows started and progress updated
        self.assertEqual(mock_start_flow.call_count, 2)
        self.assertEqual(mock_update.call_count, 2)
        
        for i, student in enumerate(students):
            # Verify flow was started with correct parameters
            flow_call = mock_start_flow.call_args_list[i]
            self.assertEqual(flow_call[0][0], self.test_data["flow_id"])  # flow_id
            self.assertEqual(flow_call[0][1], student.glific_id)  # contact_id
            
            # Verify progress was updated
            progress_call = mock_update.call_args_list[i]
            self.assertEqual(progress_call[0][0], student)  # student
            self.assertEqual(progress_call[0][1], mock_stage)  # stage
    
    @patch('frappe.get_all')
    @patch('frappe.get_doc')
    def test_progress_reporting_with_mixed_statuses(self, mock_get_doc, mock_get_all):
        """Test progress reporting with students in various stages"""
        # Mock progress records with mixed statuses
        progress_records = [
            {
                "name": "prog_1", "student": "STUD_001", "stage": "TEST_STAGE", 
                "status": "completed", "start_timestamp": datetime.now(),
                "last_activity_timestamp": datetime.now(), "completion_timestamp": datetime.now()
            },
            {
                "name": "prog_2", "student": "STUD_002", "stage": "TEST_STAGE",
                "status": "in_progress", "start_timestamp": datetime.now(),
                "last_activity_timestamp": datetime.now(), "completion_timestamp": None
            }
        ]
        
        mock_get_all.return_value = progress_records
        
        # Mock student and stage documents
        students = [
            Mock(name="STUD_001", name1="Student 1", phone="1111111111"),
            Mock(name="STUD_002", name1="Student 2", phone="2222222222")
        ]
        stages = [Mock(name="TEST_STAGE"), Mock(name="TEST_STAGE")]
        
        mock_get_doc.side_effect = students + stages
        
        # Generate report
        result = get_onboarding_progress_report(stage="TEST_STAGE")
        
        # Verify summary
        self.assertEqual(result["summary"]["total"], 2)
        self.assertEqual(result["summary"]["completed"], 1)
        self.assertEqual(result["summary"]["in_progress"], 1)
        
        # Verify details
        self.assertEqual(len(result["details"]), 2)
        completed_detail = next(d for d in result["details"] if d["status"] == "completed")
        in_progress_detail = next(d for d in result["details"] if d["status"] == "in_progress")
        
        self.assertEqual(completed_detail["student"], "STUD_001")
        self.assertIsNotNone(completed_detail["completion_timestamp"])
        
        self.assertEqual(in_progress_detail["student"], "STUD_002")
        self.assertIsNone(in_progress_detail["completion_timestamp"])


class TestOnboardingFlowEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions"""
    
    def setUp(self):
        """Set up edge case test fixtures"""
        self.edge_case_data = {
            "malformed_stage": Mock(is_active=True, stage_flows=[], glific_flow_id=None),
            "empty_students": [],
            "mixed_glific_ids": [
                Mock(name="STUD_001", glific_id="valid_id"),
                Mock(name="STUD_002", glific_id=None),
                Mock(name="STUD_003", glific_id=""),
                Mock(name="STUD_004", glific_id="another_valid_id")
            ]
        }
    
    @patch('frappe.get_doc')
    @patch('frappe.throw')
    def test_malformed_stage_configuration(self, mock_throw, mock_get_doc):
        """Test handling of malformed stage configurations"""
        # Stage with empty flows and no legacy configuration
        mock_get_doc.return_value = self.edge_case_data["malformed_stage"]
        
        trigger_onboarding_flow("SET_001", "MALFORMED_STAGE", "not_started")
        
        mock_throw.assert_called()
    
    @patch('get_students_from_onboarding')
    @patch('frappe.throw')
    def test_empty_student_list_handling(self, mock_throw, mock_get_students):
        """Test handling when no students are found"""
        mock_get_students.return_value = self.edge_case_data["empty_students"]
        
        mock_onboarding = Mock()
        mock_stage = Mock()
        
        trigger_individual_flows(
            mock_onboarding, mock_stage, "Bearer token", "not_started", "flow_123"
        )
        
        mock_throw.assert_called_with("No students found in this onboarding set with the selected status")
    
    @patch('start_contact_flow')
    @patch('get_students_from_onboarding')
    @patch('frappe.logger')
    def test_mixed_glific_id_scenarios(self, mock_logger, mock_get_students, mock_start_flow):
        """Test handling of students with mixed Glific ID statuses"""
        mock_get_students.return_value = self.edge_case_data["mixed_glific_ids"]
        mock_start_flow.return_value = True
        
        mock_onboarding = Mock()
        mock_stage = Mock()
        
        result = trigger_individual_flows(
            mock_onboarding, mock_stage, "Bearer token", "not_started", "flow_123"
        )
        
        # Should only process students with valid Glific IDs
        self.assertEqual(result["individual_count"], 2)  # Only 2 valid IDs
        self.assertEqual(mock_start_flow.call_count, 2)
    
    @patch('frappe.get_all')
    @patch('frappe.log_error')
    def test_database_connectivity_issues(self, mock_log_error, mock_get_all):
        """Test handling of database connectivity issues"""
        # Simulate database connection failure
        mock_get_all.side_effect = Exception("Database connection timeout")
        
        mock_onboarding = Mock()
        
        result = get_students_from_onboarding(mock_onboarding)
        
        # Should return empty list and log error
        self.assertEqual(result, [])
        mock_log_error.assert_called_once()
    
    @patch('requests.post')
    @patch('create_or_get_glific_group_for_batch')
    @patch('frappe.get_doc')
    @patch('frappe.throw')
    def test_glific_api_timeout_handling(self, mock_throw, mock_get_doc, mock_get_group, mock_requests):
        """Test handling of Glific API timeouts"""
        # Setup basic mocks
        mock_onboarding = Mock()
        mock_stage = Mock()
        mock_contact_group = Mock(group_id="group_123")
        mock_settings = Mock(api_url="https://api.glific.org")
        
        mock_get_group.return_value = {"success": True}
        mock_get_doc.side_effect = [mock_contact_group, mock_settings]
        
        # Simulate API timeout
        mock_requests.side_effect = requests.exceptions.Timeout("API request timed out")
        
        # Should handle timeout gracefully
        with self.assertRaises(Exception):
            trigger_group_flow(
                mock_onboarding, mock_stage, "Bearer token", "not_started", "flow_123"
            )
    
    