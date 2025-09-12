import unittest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timedelta
import sys
import os
import json

# Add the project root to Python path if needed
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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

        # Import after patching
        from tap_lms.backend_student_onboarding import backend_student_onboarding

        # Store references to the actual functions
        self.module = backend_student_onboarding
        self.normalize_phone_number = backend_student_onboarding.normalize_phone_number
        self.find_existing_student_by_phone_and_name = backend_student_onboarding.find_existing_student_by_phone_and_name
        self.get_onboarding_batches = backend_student_onboarding.get_onboarding_batches
        self.get_batch_details = backend_student_onboarding.get_batch_details
        self.process_batch = backend_student_onboarding.process_batch
        self.process_batch_job = backend_student_onboarding.process_batch_job
        self.determine_student_type_backend = backend_student_onboarding.determine_student_type_backend
        self.process_student_record = backend_student_onboarding.process_student_record
        self.validate_student = backend_student_onboarding.validate_student

    def tearDown(self):
        """Clean up after each test."""
        self.frappe_patcher.stop()

    # ============= Phone Number Normalization Tests =============

    def test_normalize_phone_number_10_digit(self):
        """Test normalize_phone_number with 10-digit number"""
        result = self.normalize_phone_number("9876543210")
        self.assertEqual(result, ("919876543210", "9876543210"))

    def test_normalize_phone_number_12_digit(self):
        """Test normalize_phone_number with 12-digit number"""
        result = self.normalize_phone_number("919876543210")
        self.assertEqual(result, ("919876543210", "9876543210"))

    def test_normalize_phone_number_11_digit_with_1_prefix(self):
        """Test normalize_phone_number with 11-digit number starting with 1"""
        result = self.normalize_phone_number("19876543210")
        self.assertEqual(result, ("919876543210", "9876543210"))

    def test_normalize_phone_number_with_formatting(self):
        """Test normalize_phone_number with formatted input"""
        result = self.normalize_phone_number("(987) 654-3210")
        self.assertEqual(result, ("919876543210", "9876543210"))

    def test_normalize_phone_number_invalid_length(self):
        """Test normalize_phone_number with invalid length"""
        result = self.normalize_phone_number("123456")
        self.assertEqual(result, (None, None))

    def test_normalize_phone_number_empty_input(self):
        """Test normalize_phone_number with empty input"""
        result = self.normalize_phone_number("")
        self.assertEqual(result, (None, None))

    def test_normalize_phone_number_none_input(self):
        """Test normalize_phone_number with None input"""
        result = self.normalize_phone_number(None)
        self.assertEqual(result, (None, None))

    def test_normalize_phone_number_non_91_12_digit(self):
        """Test normalize_phone_number with 12-digit number not starting with 91"""
        result = self.normalize_phone_number("129876543210")
        self.assertEqual(result, (None, None))

    # ============= Student Finding Tests =============

    @patch('tap_lms.backend_student_onboarding.backend_student_onboarding.frappe')
    def test_find_existing_student_by_phone_and_name_found(self, mock_frappe):
        """Test find_existing_student_by_phone_and_name when student exists"""
        mock_frappe.db.sql.return_value = [
            {"name": "STUD_001", "phone": "919876543210", "name1": "Test Student"}
        ]

        result = self.find_existing_student_by_phone_and_name("9876543210", "Test Student")

        self.assertIsNotNone(result)
        self.assertEqual(result["name"], "STUD_001")

    @patch('tap_lms.backend_student_onboarding.backend_student_onboarding.frappe')
    def test_find_existing_student_by_phone_and_name_not_found(self, mock_frappe):
        """Test find_existing_student_by_phone_and_name when student doesn't exist"""
        mock_frappe.db.sql.return_value = []

        result = self.find_existing_student_by_phone_and_name("9876543210", "Test Student")

        self.assertIsNone(result)

    def test_find_existing_student_by_phone_and_name_empty_phone(self):
        """Test find_existing_student_by_phone_and_name with empty phone"""
        result = self.find_existing_student_by_phone_and_name("", "Test Student")
        self.assertIsNone(result)

    def test_find_existing_student_by_phone_and_name_empty_name(self):
        """Test find_existing_student_by_phone_and_name with empty name"""
        result = self.find_existing_student_by_phone_and_name("9876543210", "")
        self.assertIsNone(result)

    # ============= Batch Management Tests =============

    @patch('tap_lms.backend_student_onboarding.backend_student_onboarding.frappe')
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

        result = self.get_onboarding_batches()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "BSO_001")
        mock_frappe.get_all.assert_called_once()

    @patch('tap_lms.backend_student_onboarding.backend_student_onboarding.frappe')
    def test_get_batch_details(self, mock_frappe):
        """Test get_batch_details returns batch and student data"""
        mock_batch = MagicMock()
        mock_frappe.get_doc.return_value = mock_batch
        mock_frappe.get_all.side_effect = [
            [{"name": "BS_001", "student_name": "Test Student", "phone": "9876543210"}],
            []  # No glific group
        ]

        with patch.object(self.module, 'validate_student', return_value={}):
            result = self.get_batch_details("BSO_001")

        self.assertIn("batch", result)
        self.assertIn("students", result)
        self.assertIn("glific_group", result)

    # ============= Student Validation Tests =============

    def test_validate_student_missing_required_fields(self):
        """Test validate_student with missing required fields"""
        student = {
            "student_name": "",
            "phone": "9876543210",
            "school": "",
            "grade": "5",
            "language": "English",
            "batch": "BT001"
        }

        result = self.validate_student(student)

        self.assertIn("student_name", result)
        self.assertIn("school", result)
        self.assertEqual(result["student_name"], "missing")
        self.assertEqual(result["school"], "missing")

    @patch('tap_lms.backend_student_onboarding.backend_student_onboarding.find_existing_student_by_phone_and_name')
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

        result = self.validate_student(student)

        self.assertIn("duplicate", result)
        self.assertEqual(result["duplicate"]["student_id"], "STUD_001")

    # ============= Student Type Determination Tests =============

    @patch('tap_lms.backend_student_onboarding.backend_student_onboarding.frappe')
    def test_determine_student_type_backend_new_student(self, mock_frappe):
        """Test determine_student_type_backend for new student"""
        mock_frappe.db.sql.return_value = []  # No existing student
        mock_frappe.log_error = MagicMock()

        result = self.determine_student_type_backend(
            "9876543210", "New Student", "Math"
        )

        self.assertEqual(result, "New")

    @patch('tap_lms.backend_student_onboarding.backend_student_onboarding.frappe')
    def test_determine_student_type_backend_old_student_same_vertical(self, mock_frappe):
        """Test determine_student_type_backend for old student with same vertical"""
        # Mock existing student
        mock_frappe.db.sql.side_effect = [
            [{"name": "STUD_001", "phone": "919876543210", "name1": "Test Student"}],
            [{"name": "ENR_001", "course": "MATH_L5", "batch": "BT001", "grade": "5", "school": "SCH001"}],
            [{"vertical_name": "Math"}]  # Same vertical
        ]
        mock_frappe.log_error = MagicMock()

        result = self.determine_student_type_backend(
            "9876543210", "Test Student", "Math"
        )

        self.assertEqual(result, "Old")

    @patch('tap_lms.backend_student_onboarding.backend_student_onboarding.frappe')
    def test_determine_student_type_backend_old_student_broken_course(self, mock_frappe):
        """Test determine_student_type_backend for old student with broken course links"""
        # Mock existing student with broken course
        mock_frappe.db.sql.side_effect = [
            [{"name": "STUD_001", "phone": "919876543210", "name1": "Test Student"}],
            [{"name": "ENR_001", "course": "BROKEN_COURSE", "batch": "BT001", "grade": "5", "school": "SCH001"}]
        ]
        mock_frappe.db.exists.return_value = False  # Broken course
        mock_frappe.log_error = MagicMock()

        result = self.determine_student_type_backend(
            "9876543210", "Test Student", "Math"
        )

        self.assertEqual(result, "Old")

    @patch('tap_lms.backend_student_onboarding.backend_student_onboarding.frappe')
    def test_determine_student_type_backend_new_student_different_vertical(self, mock_frappe):
        """Test determine_student_type_backend for student with only different verticals"""
        # Mock existing student with different vertical
        mock_frappe.db.sql.side_effect = [
            [{"name": "STUD_001", "phone": "919876543210", "name1": "Test Student"}],
            [{"name": "ENR_001", "course": "ENG_L5", "batch": "BT001", "grade": "5", "school": "SCH001"}],
            [{"vertical_name": "English"}]  # Different vertical
        ]
        mock_frappe.db.exists.return_value = True
        mock_frappe.log_error = MagicMock()

        result = self.determine_student_type_backend(
            "9876543210", "Test Student", "Math"
        )

        self.assertEqual(result, "New")

    @patch('tap_lms.backend_student_onboarding.backend_student_onboarding.frappe')
    def test_determine_student_type_backend_invalid_phone(self, mock_frappe):
        """Test determine_student_type_backend with invalid phone"""
        mock_frappe.log_error = MagicMock()

        result = self.determine_student_type_backend(
            "invalid", "Test Student", "Math"
        )

        self.assertEqual(result, "New")

    # ============= Process Batch Tests =============

    @patch('tap_lms.backend_student_onboarding.backend_student_onboarding.frappe')
    def test_process_batch_background_job(self, mock_frappe):
        """Test process_batch with background job"""
        mock_batch = MagicMock()
        mock_frappe.get_doc.return_value = mock_batch
        mock_frappe.enqueue.return_value = MagicMock(id="job_123")

        result = self.process_batch("BSO_001", use_background_job=True)

        self.assertIn("job_id", result)
        self.assertEqual(result["job_id"], "job_123")
        mock_frappe.enqueue.assert_called_once()

    @patch('tap_lms.backend_student_onboarding.backend_student_onboarding.frappe')
    @patch('tap_lms.backend_student_onboarding.backend_student_onboarding.process_batch_job')
    def test_process_batch_immediate(self, mock_process_job, mock_frappe):
        """Test process_batch with immediate processing"""
        mock_batch = MagicMock()
        mock_frappe.get_doc.return_value = mock_batch
        mock_process_job.return_value = {"success_count": 5, "failure_count": 0}

        result = self.process_batch("BSO_001", use_background_job=False)

        self.assertEqual(result["success_count"], 5)
        mock_process_job.assert_called_once()

    # ============= Batch Processing Job Tests =============

    @patch('tap_lms.backend_student_onboarding.backend_student_onboarding.frappe')
    @patch('tap_lms.backend_student_onboarding.backend_student_onboarding.create_or_get_glific_group_for_batch')
    @patch('tap_lms.backend_student_onboarding.backend_student_onboarding.get_initial_stage')
    def test_process_batch_job_success(self, mock_get_stage, mock_create_group, mock_frappe):
        """Test process_batch_job with successful processing"""
        # Setup mocks
        mock_batch = MagicMock()
        mock_frappe.get_doc.return_value = mock_batch
        mock_frappe.get_all.side_effect = [
            [{"name": "BS_001", "batch_skeyword": "MATH_2025"}],  # Backend students
            [{"batch_skeyword": "MATH_2025", "name": "BO_001", "kit_less": False}]  # Batch onboarding
        ]
        mock_create_group.return_value = {"group_id": "group_123"}
        mock_get_stage.return_value = "STAGE_001"
        mock_frappe.db.count.return_value = 1

        # Mock student processing
        mock_student = MagicMock()
        mock_student.name = "BS_001"
        mock_student.student_name = "Test Student"
        mock_student.phone = "9876543210"
        mock_student.batch_skeyword = "MATH_2025"
        mock_student.course_vertical = "Math"
        mock_student.grade = "5"

        with patch.object(self.module, 'process_glific_contact', return_value={"id": "contact_123"}):
            with patch.object(self.module, 'process_student_record', return_value=MagicMock(name="STUD_001")):
                with patch.object(self.module, 'update_backend_student_status'):
                    with patch.object(self.module, 'update_job_progress'):
                        with patch.object(self.module, 'get_course_level_with_validation_backend', return_value="MATH_L5"):
                            mock_frappe.get_doc.side_effect = lambda doctype, name: mock_student if name == "BS_001" else mock_batch

                            result = self.process_batch_job("BSO_001")

        self.assertEqual(result["success_count"], 1)
        self.assertEqual(result["failure_count"], 0)

    @patch('tap_lms.backend_student_onboarding.backend_student_onboarding.frappe')
    def test_process_batch_job_no_students(self, mock_frappe):
        """Test process_batch_job with no students to process"""
        mock_batch = MagicMock()
        mock_frappe.get_doc.return_value = mock_batch
        mock_frappe.get_all.return_value = []  # No students

        result = self.process_batch_job("BSO_001")

        self.assertEqual(result["success_count"], 0)
        self.assertEqual(result["failure_count"], 0)

    @patch('tap_lms.backend_student_onboarding.backend_student_onboarding.frappe')
    def test_process_batch_job_exception_handling(self, mock_frappe):
        """Test process_batch_job exception handling"""
        mock_frappe.get_doc.side_effect = Exception("Database error")
        mock_frappe.log_error = MagicMock()

        with self.assertRaises(Exception):
            self.process_batch_job("BSO_001")

        mock_frappe.log_error.assert_called()

    # ============= Student Record Processing Tests =============

    @patch('tap_lms.backend_student_onboarding.backend_student_onboarding.frappe')
    @patch('tap_lms.backend_student_onboarding.backend_student_onboarding.find_existing_student_by_phone_and_name')
    @patch('tap_lms.backend_student_onboarding.backend_student_onboarding.nowdate')
    def test_process_student_record_new_student(self, mock_nowdate, mock_find, mock_frappe):
        """Test process_student_record creating new student"""
        mock_nowdate.return_value = "2025-01-01"
        mock_find.return_value = None  # No existing student

        mock_student = MagicMock()
        mock_student.student_name = "New Student"
        mock_student.phone = "9876543210"
        mock_student.gender = "Male"
        mock_student.school = "SCH001"
        mock_student.grade = "5"
        mock_student.language = "English"
        mock_student.batch = "BT001"

        mock_glific_contact = {"id": "contact_123"}
        mock_student_doc = MagicMock()
        mock_frappe.new_doc.return_value = mock_student_doc
        mock_frappe.db.exists.return_value = False  # No existing states

        result = self.process_student_record(
            mock_student, mock_glific_contact, "BSO_001", "STAGE_001", "MATH_L5"
        )

        mock_student_doc.insert.assert_called_once()
        self.assertEqual(result, mock_student_doc)

    @patch('tap_lms.backend_student_onboarding.backend_student_onboarding.frappe')
    @patch('tap_lms.backend_student_onboarding.backend_student_onboarding.find_existing_student_by_phone_and_name')
    def test_process_student_record_existing_student(self, mock_find, mock_frappe):
        """Test process_student_record updating existing student"""
        mock_existing = {"name": "STUD_001", "phone": "919876543210", "name1": "Test Student"}
        mock_find.return_value = mock_existing

        mock_student = MagicMock()
        mock_student.student_name = "Test Student"
        mock_student.phone = "9876543210"
        mock_student.grade = "6"  # Updated grade
        mock_student.batch = "BT001"

        mock_student_doc = MagicMock()
        mock_student_doc.name = "STUD_001"
        mock_student_doc.grade = "5"  # Old grade
        mock_student_doc.phone = "919876543210"
        mock_frappe.get_doc.return_value = mock_student_doc
        mock_frappe.log_error = MagicMock()

        result = self.process_student_record(
            mock_student, None, "BSO_001", "STAGE_001"
        )

        mock_student_doc.save.assert_called_once()
        self.assertEqual(result, mock_student_doc)

    # ============= Academic Year Tests =============

    @patch('tap_lms.backend_student_onboarding.backend_student_onboarding.frappe')
    def test_get_current_academic_year_backend_april_onwards(self, mock_frappe):
        """Test get_current_academic_year_backend for April onwards"""
        mock_date = MagicMock()
        mock_date.year = 2025
        mock_date.month = 5  # May
        mock_frappe.utils.getdate.return_value = mock_date
        mock_frappe.log_error = MagicMock()

        from tap_lms.backend_student_onboarding.backend_student_onboarding import get_current_academic_year_backend
        result = get_current_academic_year_backend()

        self.assertEqual(result, "2025-26")

    @patch('tap_lms.backend_student_onboarding.backend_student_onboarding.frappe')
    def test_get_current_academic_year_backend_before_april(self, mock_frappe):
        """Test get_current_academic_year_backend for before April"""
        mock_date = MagicMock()
        mock_date.year = 2025
        mock_date.month = 2  # February
        mock_frappe.utils.getdate.return_value = mock_date
        mock_frappe.log_error = MagicMock()

        from tap_lms.backend_student_onboarding.backend_student_onboarding import get_current_academic_year_backend
        result = get_current_academic_year_backend()

        self.assertEqual(result, "2024-25")

    # ============= Course Level Selection Tests =============

    @patch('tap_lms.backend_student_onboarding.backend_student_onboarding.frappe')
    @patch('tap_lms.backend_student_onboarding.backend_student_onboarding.determine_student_type_backend')
    @patch('tap_lms.backend_student_onboarding.backend_student_onboarding.get_current_academic_year_backend')
    def test_get_course_level_with_mapping_backend_found(self, mock_get_year, mock_determine_type, mock_frappe):
        """Test get_course_level_with_mapping_backend finding mapping"""
        mock_get_year.return_value = "2025-26"
        mock_determine_type.return_value = "New"
        mock_frappe.get_all.return_value = [
            {"assigned_course_level": "MATH_L5", "mapping_name": "Math Grade 5 New"}
        ]
        mock_frappe.log_error = MagicMock()

        from tap_lms.backend_student_onboarding.backend_student_onboarding import get_course_level_with_mapping_backend
        result = get_course_level_with_mapping_backend(
            "Math", "5", "9876543210", "Test Student", False
        )

        self.assertEqual(result, "MATH_L5")

    @patch('tap_lms.backend_student_onboarding.backend_student_onboarding.frappe')
    @patch('tap_lms.backend_student_onboarding.backend_student_onboarding.determine_student_type_backend')
    @patch('tap_lms.backend_student_onboarding.backend_student_onboarding.get_current_academic_year_backend')
    @patch('tap_lms.backend_student_onboarding.backend_student_onboarding.get_course_level')
    def test_get_course_level_with_mapping_backend_fallback(self, mock_get_course_level, mock_get_year, mock_determine_type, mock_frappe):
        """Test get_course_level_with_mapping_backend fallback to original logic"""
        mock_get_year.return_value = "2025-26"
        mock_determine_type.return_value = "New"
        mock_frappe.get_all.return_value = []  # No mapping found
        mock_get_course_level.return_value = "MATH_BASIC"
        mock_frappe.log_error = MagicMock()

        from tap_lms.backend_student_onboarding.backend_student_onboarding import get_course_level_with_mapping_backend
        result = get_course_level_with_mapping_backend(
            "Math", "5", "9876543210", "Test Student", False
        )

        self.assertEqual(result, "MATH_BASIC")
        mock_get_course_level.assert_called_once()

    # ============= Error Handling Tests =============

    @patch('tap_lms.backend_student_onboarding.backend_student_onboarding.frappe')
    def test_process_glific_contact_invalid_phone(self, mock_frappe):
        """Test process_glific_contact with invalid phone number"""
        mock_student = MagicMock()
        mock_student.phone = "invalid"
        mock_student.student_name = "Test Student"

        from tap_lms.backend_student_onboarding.backend_student_onboarding import process_glific_contact
        with self.assertRaises(ValueError):
            process_glific_contact(mock_student, None)

    @patch('tap_lms.backend_student_onboarding.backend_student_onboarding.frappe')
    def test_update_backend_student_status_success(self, mock_frappe):
        """Test update_backend_student_status for success"""
        mock_student = MagicMock()
        mock_student_doc = MagicMock()
        mock_student_doc.name = "STUD_001"
        mock_student_doc.glific_id = "contact_123"

        from tap_lms.backend_student_onboarding.backend_student_onboarding import update_backend_student_status
        update_backend_student_status(mock_student, "Success", mock_student_doc)

        self.assertEqual(mock_student.processing_status, "Success")
        self.assertEqual(mock_student.student_id, "STUD_001")
        mock_student.save.assert_called_once()

    @patch('tap_lms.backend_student_onboarding.backend_student_onboarding.frappe')
    def test_update_backend_student_status_failure(self, mock_frappe):
        """Test update_backend_student_status for failure"""
        mock_student = MagicMock()
        mock_student.processing_notes = ""

        mock_meta = MagicMock()
        mock_field = MagicMock()
        mock_field.length = 140
        mock_meta.get_field.return_value = mock_field
        mock_frappe.get_meta.return_value = mock_meta

        from tap_lms.backend_student_onboarding.backend_student_onboarding import update_backend_student_status
        update_backend_student_status(mock_student, "Failed", error="Error message")

        self.assertEqual(mock_student.processing_status, "Failed")
        self.assertEqual(mock_student.processing_notes, "Error message")
        mock_student.save.assert_called_once()

    # ============= Format Phone Number Tests =============

    def test_format_phone_number_valid(self):
        """Test format_phone_number with valid input"""
        from tap_lms.backend_student_onboarding.backend_student_onboarding import format_phone_number
        result = format_phone_number("9876543210")
        self.assertEqual(result, "919876543210")

    def test_format_phone_number_already_formatted(self):
        """Test format_phone_number with already formatted input"""
        from tap_lms.backend_student_onboarding.backend_student_onboarding import format_phone_number
        result = format_phone_number("919876543210")
        self.assertEqual(result, "919876543210")

    def test_format_phone_number_invalid(self):
        """Test format_phone_number with invalid input"""
        from tap_lms.backend_student_onboarding.backend_student_onboarding import format_phone_number
        result = format_phone_number("invalid")
        self.assertIsNone(result)

# if __name__ == '__main__':
#     unittest.main()