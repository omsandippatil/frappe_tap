# import unittest
# from tap_lms.page.backend_onboarding_process import backend_onboarding_process


# class TestBackendOnboardingProcess(unittest.TestCase):

#     def test_normalize_phone_number_valid_10_digit(self):
#         phone_12, phone_10 = backend_onboarding_process.normalize_phone_number("9876543210")
#         self.assertEqual(phone_12, "919876543210")
#         self.assertEqual(phone_10, "9876543210")

#     def test_normalize_phone_number_valid_12_digit(self):
#         phone_12, phone_10 = backend_onboarding_process.normalize_phone_number("919876543210")
#         self.assertEqual(phone_12, "919876543210")
#         self.assertEqual(phone_10, "9876543210")

#     def test_normalize_phone_number_invalid(self):
#         phone_12, phone_10 = backend_onboarding_process.normalize_phone_number("123")
#         self.assertIsNone(phone_12)
#         self.assertIsNone(phone_10)

#     def test_find_existing_student_by_phone_and_name_none(self):
#         result = backend_onboarding_process.find_existing_student_by_phone_and_name(None, None)
#         self.assertIsNone(result)


# if __name__ == "__main__":
#     unittest.main()



import unittest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timedelta
import sys
import os

# Instructions for running this test:
# 1. Update the BACKEND_MODULE_PATH below to match your actual file location
# 2. The backend_student_onboarding.py file should be in your app's directory structure

# Based on your file structure: tap_lms/tap_lms/page/backend_onboarding_process/
BACKEND_MODULE_PATH = 'tap_lms.tap_lms.page.backend_onboarding_process.backend_onboarding_process'

class TestBackendStudentOnboarding(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.mock_batch_id = "BSO_001"
        self.mock_student_name = "Test Student"
        self.mock_phone_10 = "9876543210"
        self.mock_phone_12 = "919876543210"
        self.mock_course_vertical = "Math"
        self.mock_grade = "5"
        self.current_time = datetime(2025, 9, 11, 16, 3)

        # Mock frappe module at module level
        self.frappe_patcher = patch.dict('sys.modules', {
            'frappe': MagicMock(),
            'frappe.utils': MagicMock(),
            'tap_lms.glific_integration': MagicMock(),
            'tap_lms.api': MagicMock()
        })
        self.frappe_patcher.start()

        # Import the module - this will need to be updated based on your file structure
        try:
            self.backend_module = __import__(BACKEND_MODULE_PATH, fromlist=[''])
        except ImportError as e:
            self.skipTest(f"Could not import backend module at {BACKEND_MODULE_PATH}. Error: {e}")

    def tearDown(self):
        """Clean up after each test."""
        self.frappe_patcher.stop()

    # ============= Phone Number Normalization Tests =============

    def test_normalize_phone_number_10_digit(self):
        """Test normalize_phone_number with 10-digit number"""
        result = self.backend_module.normalize_phone_number("9876543210")
        self.assertEqual(result, ("919876543210", "9876543210"))

    def test_normalize_phone_number_12_digit(self):
        """Test normalize_phone_number with 12-digit number"""
        result = self.backend_module.normalize_phone_number("919876543210")
        self.assertEqual(result, ("919876543210", "9876543210"))

    def test_normalize_phone_number_11_digit_with_1_prefix(self):
        """Test normalize_phone_number with 11-digit number starting with 1"""
        result = self.backend_module.normalize_phone_number("19876543210")
        self.assertEqual(result, ("919876543210", "9876543210"))

    def test_normalize_phone_number_with_formatting(self):
        """Test normalize_phone_number with formatted input"""
        result = self.backend_module.normalize_phone_number("(987) 654-3210")
        self.assertEqual(result, ("919876543210", "9876543210"))

    def test_normalize_phone_number_invalid_length(self):
        """Test normalize_phone_number with invalid length"""
        result = self.backend_module.normalize_phone_number("123456")
        self.assertEqual(result, (None, None))

    def test_normalize_phone_number_empty_input(self):
        """Test normalize_phone_number with empty input"""
        result = self.backend_module.normalize_phone_number("")
        self.assertEqual(result, (None, None))

    def test_normalize_phone_number_none_input(self):
        """Test normalize_phone_number with None input"""
        result = self.backend_module.normalize_phone_number(None)
        self.assertEqual(result, (None, None))

    # ============= Student Finding Tests =============

    @patch(f'{BACKEND_MODULE_PATH}.frappe')
    def test_find_existing_student_by_phone_and_name_found(self, mock_frappe):
        """Test find_existing_student_by_phone_and_name when student exists"""
        mock_frappe.db.sql.return_value = [
            {"name": "STUD_001", "phone": "919876543210", "name1": "Test Student"}
        ]

        result = self.backend_module.find_existing_student_by_phone_and_name("9876543210", "Test Student")

        self.assertIsNotNone(result)
        self.assertEqual(result["name"], "STUD_001")

    @patch(f'{BACKEND_MODULE_PATH}.frappe')
    def test_find_existing_student_by_phone_and_name_not_found(self, mock_frappe):
        """Test find_existing_student_by_phone_and_name when student doesn't exist"""
        mock_frappe.db.sql.return_value = []

        result = self.backend_module.find_existing_student_by_phone_and_name("9876543210", "Test Student")

        self.assertIsNone(result)

    def test_find_existing_student_by_phone_and_name_empty_phone(self):
        """Test find_existing_student_by_phone_and_name with empty phone"""
        result = self.backend_module.find_existing_student_by_phone_and_name("", "Test Student")
        self.assertIsNone(result)

    def test_find_existing_student_by_phone_and_name_empty_name(self):
        """Test find_existing_student_by_phone_and_name with empty name"""
        result = self.backend_module.find_existing_student_by_phone_and_name("9876543210", "")
        self.assertIsNone(result)

    # ============= Batch Management Tests =============

    @patch(f'{BACKEND_MODULE_PATH}.frappe')
    def test_get_onboarding_batches(self, mock_frappe):
        """Test get_onboarding_batches returns draft batches"""
        mock_frappe.get_all.return_value = [
            {
                "name": "BSO_001",
                "set_name": "Batch 1",
                "upload_date": "2025-01-01",
                "uploaded_by": "user@example.com",
                "student_count": 50,
                "processed_student_count": 0
            }
        ]

        result = self.backend_module.get_onboarding_batches()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "BSO_001")
        mock_frappe.get_all.assert_called_once()

    @patch(f'{BACKEND_MODULE_PATH}.frappe')
    @patch(f'{BACKEND_MODULE_PATH}.validate_student')
    def test_get_batch_details(self, mock_validate, mock_frappe):
        """Test get_batch_details returns batch and student data"""
        mock_batch = MagicMock()
        mock_frappe.get_doc.return_value = mock_batch
        mock_frappe.get_all.side_effect = [
            [{"name": "BS_001", "student_name": "Test Student", "phone": "9876543210"}],
            []  # No glific group
        ]
        mock_validate.return_value = {}

        result = self.backend_module.get_batch_details("BSO_001")

        self.assertIn("batch", result)
        self.assertIn("students", result)
        self.assertIn("glific_group", result)

    # ============= Student Validation Tests =============

    @patch(f'{BACKEND_MODULE_PATH}.find_existing_student_by_phone_and_name')
    def test_validate_student_missing_required_fields(self, mock_find):
        """Test validate_student with missing required fields"""
        mock_find.return_value = None
        student = {
            "student_name": "",
            "phone": "9876543210",
            "school": "",
            "grade": "5",
            "language": "English",
            "batch": "BT001"
        }

        result = self.backend_module.validate_student(student)

        self.assertIn("student_name", result)
        self.assertIn("school", result)
        self.assertEqual(result["student_name"], "missing")
        self.assertEqual(result["school"], "missing")

    @patch(f'{BACKEND_MODULE_PATH}.find_existing_student_by_phone_and_name')
    def test_validate_student_duplicate_found(self, mock_find):
        """Test validate_student with duplicate student"""
        student = {
            "student_name": "Test Student",
            "phone": "9876543210",
            "school": "School 1",
            "grade": "5",
            "language": "English",
            "batch": "BT001"
        }

        mock_find.return_value = {
            "name": "STUD_001",
            "name1": "Test Student"
        }

        result = self.backend_module.validate_student(student)

        self.assertIn("duplicate", result)
        self.assertEqual(result["duplicate"]["student_id"], "STUD_001")

    # ============= Student Type Determination Tests =============

    @patch(f'{BACKEND_MODULE_PATH}.frappe')
    def test_determine_student_type_backend_new_student(self, mock_frappe):
        """Test determine_student_type_backend for new student"""
        mock_frappe.db.sql.return_value = []  # No existing student
        mock_frappe.log_error = MagicMock()

        result = self.backend_module.determine_student_type_backend(
            "9876543210", "New Student", "Math"
        )

        self.assertEqual(result, "New")

    @patch(f'{BACKEND_MODULE_PATH}.frappe')
    def test_determine_student_type_backend_old_student_same_vertical(self, mock_frappe):
        """Test determine_student_type_backend for old student with same vertical"""
        # Mock existing student
        mock_frappe.db.sql.side_effect = [
            [{"name": "STUD_001", "phone": "919876543210", "name1": "Test Student"}],
            [{"name": "ENR_001", "course": "MATH_L5", "batch": "BT001", "grade": "5", "school": "SCH001"}],
            [{"vertical_name": "Math"}]  # Same vertical
        ]
        mock_frappe.log_error = MagicMock()

        result = self.backend_module.determine_student_type_backend(
            "9876543210", "Test Student", "Math"
        )

        self.assertEqual(result, "Old")

    @patch(f'{BACKEND_MODULE_PATH}.frappe')
    def test_determine_student_type_backend_invalid_phone(self, mock_frappe):
        """Test determine_student_type_backend with invalid phone"""
        mock_frappe.log_error = MagicMock()

        result = self.backend_module.determine_student_type_backend(
            "invalid", "Test Student", "Math"
        )

        self.assertEqual(result, "New")

    # ============= Process Batch Tests =============

    @patch(f'{BACKEND_MODULE_PATH}.frappe')
    def test_process_batch_background_job(self, mock_frappe):
        """Test process_batch with background job"""
        mock_batch = MagicMock()
        mock_frappe.get_doc.return_value = mock_batch
        mock_job = MagicMock()
        mock_job.id = "job_123"
        mock_frappe.enqueue.return_value = mock_job

        result = self.backend_module.process_batch("BSO_001", use_background_job=True)

        self.assertIn("job_id", result)
        self.assertEqual(result["job_id"], "job_123")
        mock_frappe.enqueue.assert_called_once()

    @patch(f'{BACKEND_MODULE_PATH}.frappe')
    @patch(f'{BACKEND_MODULE_PATH}.process_batch_job')
    def test_process_batch_immediate(self, mock_process_job, mock_frappe):
        """Test process_batch with immediate processing"""
        mock_batch = MagicMock()
        mock_frappe.get_doc.return_value = mock_batch
        mock_process_job.return_value = {"success_count": 5, "failure_count": 0}

        result = self.backend_module.process_batch("BSO_001", use_background_job=False)

        self.assertEqual(result["success_count"], 5)
        mock_process_job.assert_called_once()

    # ============= Academic Year Tests =============

    @patch(f'{BACKEND_MODULE_PATH}.frappe')
    def test_get_current_academic_year_backend_april_onwards(self, mock_frappe):
        """Test get_current_academic_year_backend for April onwards"""
        mock_date = MagicMock()
        mock_date.year = 2025
        mock_date.month = 5  # May
        mock_frappe.utils.getdate.return_value = mock_date
        mock_frappe.log_error = MagicMock()

        result = self.backend_module.get_current_academic_year_backend()

        self.assertEqual(result, "2025-26")

    @patch(f'{BACKEND_MODULE_PATH}.frappe')
    def test_get_current_academic_year_backend_before_april(self, mock_frappe):
        """Test get_current_academic_year_backend for before April"""
        mock_date = MagicMock()
        mock_date.year = 2025
        mock_date.month = 2  # February
        mock_frappe.utils.getdate.return_value = mock_date
        mock_frappe.log_error = MagicMock()

        result = self.backend_module.get_current_academic_year_backend()

        self.assertEqual(result, "2024-25")

    # ============= Error Handling Tests =============

    def test_format_phone_number_valid(self):
        """Test format_phone_number with valid input"""
        result = self.backend_module.format_phone_number("9876543210")
        self.assertEqual(result, "919876543210")

    def test_format_phone_number_already_formatted(self):
        """Test format_phone_number with already formatted input"""
        result = self.backend_module.format_phone_number("919876543210")
        self.assertEqual(result, "919876543210")

    def test_format_phone_number_invalid(self):
        """Test format_phone_number with invalid input"""
        result = self.backend_module.format_phone_number("invalid")
        self.assertIsNone(result)

    # ============= Job Status Tests =============

    @patch(f'{BACKEND_MODULE_PATH}.frappe')
    @patch('rq.job.Job')
    @patch(f'{BACKEND_MODULE_PATH}.get_redis_conn')
    def test_get_job_status_completed(self, mock_redis, mock_job_class, mock_frappe):
        """Test get_job_status for completed job"""
        mock_conn = MagicMock()
        mock_redis.return_value = mock_conn
        
        mock_job = MagicMock()
        mock_job.get_status.return_value = "finished"
        mock_job.result = {"success": True}
        mock_job.meta = {"progress": 100}
        mock_job_class.fetch.return_value = mock_job

        result = self.backend_module.get_job_status("job_123")

        self.assertEqual(result["status"], "Completed")
        self.assertEqual(result["result"], {"success": True})

    @patch(f'{BACKEND_MODULE_PATH}.frappe')
    @patch('rq.job.Job')
    @patch(f'{BACKEND_MODULE_PATH}.get_redis_conn')
    def test_get_job_status_not_found(self, mock_redis, mock_job_class, mock_frappe):
        """Test get_job_status for non-existent job"""
        mock_conn = MagicMock()
        mock_redis.return_value = mock_conn
        mock_job_class.fetch.side_effect = Exception("Job not found")
        mock_frappe.logger.return_value = MagicMock()

        result = self.backend_module.get_job_status("invalid_job")

        self.assertEqual(result["status"], "Not Found")

# if __name__ == '__main__':
#     # Run specific test methods or all tests
#     unittest.main(verbosity=2)