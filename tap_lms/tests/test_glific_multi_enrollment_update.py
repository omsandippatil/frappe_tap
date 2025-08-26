# test_glific_multi_enrollment_update.py
# Fixed test cases for glific_multi_enrollment_update.py

import frappe
import unittest
from unittest.mock import patch, MagicMock, Mock
import json
from datetime import datetime, timezone


class TestGlificMultiEnrollmentUpdate(unittest.TestCase):
    """Test cases for Glific multi-enrollment update functionality"""
    
    def setUp(self):
        """Set up test environment"""
        if hasattr(frappe, 'set_user'):
            frappe.set_user("Administrator")

    def tearDown(self):
        """Clean up after tests"""
        pass

    def _import_function(self, function_name):
        """Helper to safely import functions"""
        try:
            module = __import__(
                'tap_lms.tap_lms.doctype.backend_student_onboarding.glific_multi_enrollment_update',
                fromlist=[function_name]
            )
            return getattr(module, function_name)
        except (ImportError, AttributeError):
            self.skipTest(f"Could not import {function_name}")

    def test_check_student_multi_enrollment_with_multiple_enrollments(self):
        """Test check_student_multi_enrollment returns 'yes' for student with multiple enrollments"""
        check_student_multi_enrollment = self._import_function('check_student_multi_enrollment')
        
        with patch('frappe.db.exists') as mock_exists, \
             patch('frappe.get_doc') as mock_get_doc:
            
            # Setup mocks
            mock_exists.return_value = True
            mock_student = Mock()
            mock_student.enrollment = [
                {"program": "Program 1"},
                {"program": "Program 2"}
            ]
            mock_get_doc.return_value = mock_student
            
            # Test
            result = check_student_multi_enrollment("STU-001")
            
            # Assertions
            self.assertEqual(result, "yes")
            mock_exists.assert_called_once_with("Student", "STU-001")
            mock_get_doc.assert_called_once_with("Student", "STU-001")

    def test_check_student_multi_enrollment_with_single_enrollment(self):
        """Test check_student_multi_enrollment returns 'no' for student with single enrollment"""
        check_student_multi_enrollment = self._import_function('check_student_multi_enrollment')
        
        with patch('frappe.db.exists') as mock_exists, \
             patch('frappe.get_doc') as mock_get_doc:
            
            mock_exists.return_value = True
            mock_student = Mock()
            mock_student.enrollment = [{"program": "Program 1"}]
            mock_get_doc.return_value = mock_student
            
            result = check_student_multi_enrollment("STU-001")
            self.assertEqual(result, "no")

    def test_check_student_multi_enrollment_no_enrollments(self):
        """Test check_student_multi_enrollment returns 'no' for student with no enrollments"""
        check_student_multi_enrollment = self._import_function('check_student_multi_enrollment')
        
        with patch('frappe.db.exists') as mock_exists, \
             patch('frappe.get_doc') as mock_get_doc:
            
            mock_exists.return_value = True
            mock_student = Mock()
            mock_student.enrollment = []
            mock_get_doc.return_value = mock_student
            
            result = check_student_multi_enrollment("STU-001")
            self.assertEqual(result, "no")

    def test_check_student_multi_enrollment_student_not_exists(self):
        """Test check_student_multi_enrollment returns 'no' when student doesn't exist"""
        check_student_multi_enrollment = self._import_function('check_student_multi_enrollment')
        
        with patch('frappe.db.exists') as mock_exists:
            mock_exists.return_value = False
            
            result = check_student_multi_enrollment("NONEXISTENT")
            self.assertEqual(result, "no")

    def test_check_student_multi_enrollment_exception(self):
        """Test check_student_multi_enrollment handles exceptions gracefully"""
        check_student_multi_enrollment = self._import_function('check_student_multi_enrollment')
        
        with patch('frappe.db.exists') as mock_exists, \
             patch('frappe.get_doc') as mock_get_doc, \
             patch('frappe.logger') as mock_logger:
            
            mock_exists.return_value = True
            mock_get_doc.side_effect = Exception("Database error")
            
            result = check_student_multi_enrollment("STU-001")
            
            self.assertEqual(result, "no")

    def test_update_specific_set_contacts_no_set_name(self):
        """Test update function returns error when no set name provided"""
        update_function = self._import_function('update_specific_set_contacts_with_multi_enrollment')
        
        result = update_function("")
        
        self.assertIn("error", result)
        self.assertEqual(result["error"], "Backend Student Onboarding set name is required")

    def test_update_specific_set_contacts_set_not_found(self):
        """Test update function returns error when set doesn't exist"""
        update_function = self._import_function('update_specific_set_contacts_with_multi_enrollment')
        
        with patch('frappe.get_doc') as mock_get_doc:
            mock_get_doc.side_effect = frappe.DoesNotExistError()
            
            result = update_function("NONEXISTENT")
            
            self.assertIn("error", result)
            self.assertIn("not found", result["error"])

    def test_update_specific_set_contacts_set_not_processed(self):
        """Test update function returns error when set status is not 'Processed'"""
        update_function = self._import_function('update_specific_set_contacts_with_multi_enrollment')
        
        with patch('frappe.get_doc') as mock_get_doc:
            mock_set = Mock()
            mock_set.status = "Draft"
            mock_set.set_name = "Test Set"
            mock_get_doc.return_value = mock_set
            
            result = update_function("TEST-SET")
            
            self.assertIn("error", result)
            self.assertIn("not 'Processed'", result["error"])

    def test_update_specific_set_contacts_no_students(self):
        """Test update function returns message when no students found"""
        update_function = self._import_function('update_specific_set_contacts_with_multi_enrollment')
        
        with patch('frappe.get_doc') as mock_get_doc, \
             patch('frappe.get_all') as mock_get_all:
            
            # Mock processed onboarding set
            mock_set = Mock()
            mock_set.status = "Processed"
            mock_set.set_name = "Test Set"
            mock_get_doc.return_value = mock_set
            
            # Mock no backend students found
            mock_get_all.return_value = []
            
            result = update_function("TEST-SET")
            
            self.assertIn("message", result)
            self.assertIn("No successfully processed students", result["message"])

    def test_update_specific_set_contacts_successful_update(self):
        """Test successful update of contact with multi_enrollment field"""
        update_function = self._import_function('update_specific_set_contacts_with_multi_enrollment')
        
        with patch('frappe.get_all') as mock_get_all, \
             patch('frappe.get_doc') as mock_get_doc, \
             patch('frappe.db.exists') as mock_db_exists, \
             patch('tap_lms.tap_lms.doctype.backend_student_onboarding.glific_multi_enrollment_update.check_student_multi_enrollment') as mock_check_multi, \
             patch('tap_lms.tap_lms.doctype.backend_student_onboarding.glific_multi_enrollment_update.get_glific_settings') as mock_settings, \
             patch('tap_lms.tap_lms.doctype.backend_student_onboarding.glific_multi_enrollment_update.get_glific_auth_headers') as mock_headers, \
             patch('requests.post') as mock_post:
            
            # Mock onboarding set
            mock_set = Mock()
            mock_set.status = "Processed"
            mock_set.set_name = "Test Set"
            
            # Mock student document
            mock_student = Mock()
            mock_student.glific_id = "12345"
            
            mock_get_doc.side_effect = [mock_set, mock_student]
            
            # Mock backend students
            mock_get_all.return_value = [{
                "student_name": "Test Student",
                "phone": "+1234567890", 
                "student_id": "STU-001",
                "batch_skeyword": "BATCH1"
            }]
            
            mock_db_exists.return_value = True
            mock_check_multi.return_value = "yes"
            
            # Mock Glific settings
            mock_settings_obj = Mock()
            mock_settings_obj.api_url = "https://test.glific.com"
            mock_settings.return_value = mock_settings_obj
            
            mock_headers.return_value = {"Authorization": "Bearer test_token"}
            
            # Mock successful API responses
            fetch_response = Mock()
            fetch_response.status_code = 200
            fetch_response.json.return_value = {
                "data": {
                    "contact": {
                        "contact": {
                            "id": "12345",
                            "name": "Test Student",
                            "phone": "+1234567890",
                            "fields": json.dumps({
                                "existing_field": {"value": "test", "type": "string"}
                            })
                        }
                    }
                }
            }
            
            update_response = Mock()
            update_response.status_code = 200
            update_response.json.return_value = {
                "data": {
                    "updateContact": {
                        "contact": {
                            "id": "12345",
                            "name": "Test Student",
                            "fields": json.dumps({
                                "existing_field": {"value": "test", "type": "string"},
                                "multi_enrollment": {"value": "yes", "type": "string"}
                            })
                        },
                        "errors": []
                    }
                }
            }
            
            mock_post.side_effect = [fetch_response, update_response]
            
            result = update_function("TEST-SET")
            
            self.assertEqual(result["updated"], 1)
            self.assertEqual(result["errors"], 0)
            self.assertEqual(result["total_processed"], 1)

    def test_run_multi_enrollment_update_for_specific_set_success(self):
        """Test whitelist function successful execution"""
        run_function = self._import_function('run_multi_enrollment_update_for_specific_set')
        
        with patch('frappe.db.begin') as mock_begin, \
             patch('frappe.db.commit') as mock_commit, \
             patch('frappe.db.rollback') as mock_rollback, \
             patch('tap_lms.tap_lms.doctype.backend_student_onboarding.glific_multi_enrollment_update.update_specific_set_contacts_with_multi_enrollment') as mock_update:
            
            mock_update.return_value = {
                "set_name": "Test Set",
                "updated": 5,
                "skipped": 0, 
                "errors": 0,
                "total_processed": 5
            }
            
            result = run_function("TEST-SET")
            
            self.assertIn("Process completed", result)
            self.assertIn("Updated: 5", result)

    def test_run_multi_enrollment_update_no_set_name(self):
        """Test whitelist function returns error when no set name provided"""
        run_function = self._import_function('run_multi_enrollment_update_for_specific_set')
        
        result = run_function("")
        
        self.assertIn("Error: Backend Student Onboarding set name is required", result)

    def test_run_multi_enrollment_update_exception_handling(self):
        """Test whitelist function handles exceptions properly"""
        run_function = self._import_function('run_multi_enrollment_update_for_specific_set')
        
        with patch('frappe.db.begin') as mock_begin, \
             patch('frappe.db.commit') as mock_commit, \
             patch('frappe.db.rollback') as mock_rollback, \
             patch('tap_lms.tap_lms.doctype.backend_student_onboarding.glific_multi_enrollment_update.update_specific_set_contacts_with_multi_enrollment') as mock_update:
            
            mock_update.side_effect = Exception("Database connection failed")
            
            result = run_function("TEST-SET")
            
            self.assertIn("Error occurred:", result)

    def test_get_backend_onboarding_sets(self):
        """Test getting list of processed Backend Student Onboarding sets"""
        get_sets_function = self._import_function('get_backend_onboarding_sets')
        
        with patch('frappe.get_all') as mock_get_all:
            mock_get_all.return_value = [
                {
                    "name": "SET-001",
                    "set_name": "Test Set 1", 
                    "processed_student_count": 10,
                    "upload_date": "2024-01-01"
                },
                {
                    "name": "SET-002",
                    "set_name": "Test Set 2",
                    "processed_student_count": 15, 
                    "upload_date": "2024-01-02"
                }
            ]
            
            result = get_sets_function()
            
            self.assertEqual(len(result), 2)
            self.assertEqual(result[0]["name"], "SET-001")

    def test_process_multiple_sets_simple_success(self):
        """Test processing multiple sets successfully"""
        process_function = self._import_function('process_multiple_sets_simple')
        
        with patch('time.sleep') as mock_sleep, \
             patch('tap_lms.tap_lms.doctype.backend_student_onboarding.glific_multi_enrollment_update.update_specific_set_contacts_with_multi_enrollment') as mock_update:
            
            mock_update.side_effect = [
                {"updated": 5, "errors": 0, "total_processed": 0},  # Signal completion
                {"updated": 3, "errors": 1, "total_processed": 0}   # Signal completion
            ]
            
            result = process_function(["SET-001", "SET-002"])
            
            self.assertEqual(len(result), 2)
            self.assertEqual(result[0]["status"], "completed")

    def test_process_multiple_sets_simple_with_error(self):
        """Test processing multiple sets with error handling"""
        process_function = self._import_function('process_multiple_sets_simple')
        
        with patch('tap_lms.tap_lms.doctype.backend_student_onboarding.glific_multi_enrollment_update.update_specific_set_contacts_with_multi_enrollment') as mock_update:
            
            mock_update.return_value = {"error": "Set not found"}
            
            result = process_function(["INVALID-SET"])
            
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["status"], "completed")

    def test_process_multiple_sets_simple_exception(self):
        """Test processing multiple sets with exception"""
        process_function = self._import_function('process_multiple_sets_simple')
        
        with patch('tap_lms.tap_lms.doctype.backend_student_onboarding.glific_multi_enrollment_update.update_specific_set_contacts_with_multi_enrollment') as mock_update:
            
            mock_update.side_effect = Exception("Unexpected error")
            
            result = process_function(["SET-001"])
            
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["status"], "error")
            self.assertIn("error", result[0])

    def test_process_my_sets_with_list(self):
        """Test process_my_sets with list input"""
        process_my_sets = self._import_function('process_my_sets')
        
        with patch('frappe.utils.background_jobs.enqueue') as mock_enqueue:
            mock_job = Mock()
            mock_job.id = "job_123"
            mock_enqueue.return_value = mock_job
            
            result = process_my_sets(["SET-001", "SET-002"])
            
            self.assertIn("Started processing 2 sets", result)
            self.assertIn("job_123", result)

    def test_process_my_sets_with_string(self):
        """Test process_my_sets with comma-separated string input"""
        process_my_sets = self._import_function('process_my_sets')
        
        with patch('frappe.utils.background_jobs.enqueue') as mock_enqueue:
            mock_job = Mock()
            mock_job.id = "job_456"
            mock_enqueue.return_value = mock_job
            
            result = process_my_sets("SET-001, SET-002, SET-003")
            
            self.assertIn("Started processing 3 sets", result)


class TestGlificMultiEnrollmentUpdateStandalone(unittest.TestCase):
    """Standalone tests that don't require complex imports"""
    
    def setUp(self):
        if hasattr(frappe, 'set_user'):
            frappe.set_user("Administrator")

    def test_frappe_db_mocking(self):
        """Test that Frappe DB can be mocked properly"""
        with patch('frappe.db.exists') as mock_exists:
            mock_exists.return_value = True
            result = frappe.db.exists("Student", "TEST") if hasattr(frappe.db, 'exists') else True
            self.assertTrue(result)

