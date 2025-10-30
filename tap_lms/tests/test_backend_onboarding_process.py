import unittest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timedelta
import sys
import os

# Add the parent directories to the path
current_dir = os.path.dirname(os.path.abspath(__file__))
app_dir = os.path.dirname(current_dir)  # tap_lms directory
sys.path.insert(0, app_dir)

# Mock frappe and dependencies BEFORE importing the module
mock_frappe = MagicMock()
mock_frappe.utils = MagicMock()
mock_frappe.utils.nowdate = MagicMock(return_value="2025-01-01")
mock_frappe.utils.now = MagicMock(return_value="2025-01-01 10:00:00")
mock_frappe.utils.getdate = MagicMock()
mock_frappe._ = lambda x: x  # Mock translation function
mock_frappe.whitelist = lambda func: func  # Mock decorator

sys.modules['frappe'] = mock_frappe
sys.modules['frappe.utils'] = mock_frappe.utils
sys.modules['tap_lms.glific_integration'] = MagicMock()
sys.modules['tap_lms.api'] = MagicMock()
sys.modules['rq.job'] = MagicMock()
sys.modules['rq'] = MagicMock()
sys.modules['frappe.utils.background_jobs'] = MagicMock()

# Now import the module
try:
    from tap_lms.page.backend_onboarding_process import backend_onboarding_process as backend_module
    MODULE_IMPORTED = True
    print("✅ Module imported successfully!")
except ImportError as e:
    print(f"❌ Import error: {e}")
    backend_module = None
    MODULE_IMPORTED = False


class TestBackendOnboardingProcess(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Set up the backend module for all tests"""
        if not MODULE_IMPORTED:
            raise unittest.SkipTest("Could not import backend_onboarding_process module")
        
        cls.backend_module = backend_module
        available_functions = [name for name in dir(cls.backend_module) 
                             if not name.startswith('_') and callable(getattr(cls.backend_module, name))]
        print(f"📦 Available functions: {len(available_functions)}")

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.mock_batch_id = "BSO_001"
        self.mock_student_name = "Test Student"
        self.mock_phone_10 = "9876543210"
        self.mock_phone_12 = "919876543210"
        self.mock_course_vertical = "Math"
        self.mock_grade = "5"

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

    def test_normalize_phone_number_non_91_12_digit(self):
        """Test normalize_phone_number with 12-digit number not starting with 91"""
        result = self.backend_module.normalize_phone_number("129876543210")
        self.assertEqual(result, (None, None))

    # ============= Student Finding Tests =============

    @patch('tap_lms.page.backend_onboarding_process.backend_onboarding_process.frappe')
    def test_find_existing_student_by_phone_and_name_found(self, mock_frappe):
        """Test find_existing_student_by_phone_and_name when student exists"""
        mock_frappe.db.sql.return_value = [
            {"name": "STUD_001", "phone": "919876543210", "name1": "Test Student"}
        ]

        result = self.backend_module.find_existing_student_by_phone_and_name("9876543210", "Test Student")

        self.assertIsNotNone(result)
        self.assertEqual(result["name"], "STUD_001")

    @patch('tap_lms.page.backend_onboarding_process.backend_onboarding_process.frappe')
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

    # ============= CRITICAL: Student Type Determination Tests =============

    @patch('tap_lms.page.backend_onboarding_process.backend_onboarding_process.frappe')
    def test_determine_student_type_backend_no_existing_student(self, mock_frappe):
        """CRITICAL: Test student type determination when student doesn't exist"""
        mock_frappe.db.sql.return_value = []

        result = self.backend_module.determine_student_type_backend(
            "9876543210", "New Student", "Math"
        )

        self.assertEqual(result, "New")

    @patch('tap_lms.page.backend_onboarding_process.backend_onboarding_process.frappe')
    def test_determine_student_type_backend_same_vertical(self, mock_frappe):
        """CRITICAL: Test student with enrollment in same vertical"""
        mock_frappe.db.sql.side_effect = [
            [{"name": "STUD_001", "phone": "919876543210", "name1": "Test Student"}],
            [{
                "name": "ENR_001",
                "course": "MATH_L5",
                "batch": "BT001",
                "grade": "5",
                "school": "SCH001"
            }],
            [{"vertical_name": "Math"}]
        ]
        mock_frappe.db.exists.return_value = True

        result = self.backend_module.determine_student_type_backend(
            "9876543210", "Test Student", "Math"
        )

        self.assertEqual(result, "Old")

    @patch('tap_lms.page.backend_onboarding_process.backend_onboarding_process.frappe')
    def test_determine_student_type_backend_broken_course_links(self, mock_frappe):
        """CRITICAL: Test student with broken course links"""
        mock_frappe.db.sql.side_effect = [
            [{"name": "STUD_001", "phone": "919876543210", "name1": "Test Student"}],
            [{
                "name": "ENR_001",
                "course": "BROKEN_COURSE_ID",
                "batch": "BT001",
                "grade": "5",
                "school": "SCH001"
            }]
        ]
        mock_frappe.db.exists.return_value = False

        result = self.backend_module.determine_student_type_backend(
            "9876543210", "Test Student", "Math"
        )

        self.assertEqual(result, "Old")

    @patch('tap_lms.page.backend_onboarding_process.backend_onboarding_process.frappe')
    def test_determine_student_type_backend_null_course(self, mock_frappe):
        """CRITICAL: Test student with NULL course enrollment"""
        mock_frappe.db.sql.side_effect = [
            [{"name": "STUD_001", "phone": "919876543210", "name1": "Test Student"}],
            [{"name": "ENR_001", "course": None, "batch": "BT001", "grade": "5", "school": "SCH001"}]
        ]

        result = self.backend_module.determine_student_type_backend(
            "9876543210", "Test Student", "Math"
        )

        self.assertEqual(result, "Old")

    # ============= Batch Management Tests =============

    @patch('tap_lms.page.backend_onboarding_process.backend_onboarding_process.frappe')
    def test_get_onboarding_batches(self, mock_frappe):
        """Test get_onboarding_batches returns draft/processing batches"""
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

    @patch('tap_lms.page.backend_onboarding_process.backend_onboarding_process.frappe')
    def test_get_onboarding_stages(self, mock_frappe):
        """Test get_onboarding_stages returns stages"""
        mock_frappe.db.table_exists.return_value = True
        mock_frappe.get_all.return_value = [
            {"name": "STAGE_001", "description": "Initial Stage", "order": 0},
            {"name": "STAGE_002", "description": "Second Stage", "order": 1}
        ]

        result = self.backend_module.get_onboarding_stages()

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["name"], "STAGE_001")

    @patch('tap_lms.page.backend_onboarding_process.backend_onboarding_process.frappe')
    def test_get_onboarding_stages_no_table(self, mock_frappe):
        """Test get_onboarding_stages when table doesn't exist"""
        mock_frappe.db.table_exists.return_value = False

        result = self.backend_module.get_onboarding_stages()

        self.assertEqual(result, [])

    # ============= Process Batch Tests =============

    @patch('tap_lms.page.backend_onboarding_process.backend_onboarding_process.frappe')
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

    # ============= Academic Year Tests =============

    @patch('tap_lms.page.backend_onboarding_process.backend_onboarding_process.frappe')
    def test_get_current_academic_year_backend_april_onwards(self, mock_frappe):
        """Test academic year for April onwards"""
        mock_date = MagicMock()
        mock_date.year = 2025
        mock_date.month = 5
        mock_frappe.utils.getdate.return_value = mock_date

        result = self.backend_module.get_current_academic_year_backend()

        self.assertEqual(result, "2025-26")

    @patch('tap_lms.page.backend_onboarding_process.backend_onboarding_process.frappe')
    def test_get_current_academic_year_backend_before_april(self, mock_frappe):
        """Test academic year before April"""
        mock_date = MagicMock()
        mock_date.year = 2025
        mock_date.month = 2
        mock_frappe.utils.getdate.return_value = mock_date

        result = self.backend_module.get_current_academic_year_backend()

        self.assertEqual(result, "2024-25")

    # ============= Course Level Tests =============

    @patch('tap_lms.page.backend_onboarding_process.backend_onboarding_process.get_course_level')
    @patch('tap_lms.page.backend_onboarding_process.backend_onboarding_process.get_current_academic_year_backend')
    @patch('tap_lms.page.backend_onboarding_process.backend_onboarding_process.determine_student_type_backend')
    @patch('tap_lms.page.backend_onboarding_process.backend_onboarding_process.frappe')
    def test_get_course_level_with_mapping_backend_fallback(self, mock_frappe, mock_student_type, 
                                                            mock_academic_year, mock_get_course):
        """Test course level fallback to Stage Grades"""
        mock_student_type.return_value = "New"
        mock_academic_year.return_value = "2025-26"
        mock_get_course.return_value = "MATH_BASIC"
        mock_frappe.get_all.return_value = []

        result = self.backend_module.get_course_level_with_mapping_backend(
            "Math", "5", "9876543210", "Test Student", False
        )

        self.assertEqual(result, "MATH_BASIC")

    # ============= Utility Tests =============

    def test_format_phone_number_valid(self):
        """Test format_phone_number"""
        result = self.backend_module.format_phone_number("9876543210")
        self.assertEqual(result, "919876543210")

    def test_format_phone_number_invalid(self):
        """Test format_phone_number with invalid input"""
        result = self.backend_module.format_phone_number("invalid")
        self.assertIsNone(result)

    # ============= Error Handling Tests =============

    @patch('tap_lms.page.backend_onboarding_process.backend_onboarding_process.frappe')
    def test_fix_broken_course_links_no_student_id(self, mock_frappe):
        """Test fix_broken_course_links without student ID"""
        mock_frappe.get_all.return_value = [{"name": "STUD_001"}]
        mock_frappe.db.sql.return_value = []
        mock_frappe.db.commit = MagicMock()
        
        result = self.backend_module.fix_broken_course_links()
        
        self.assertIn("No broken course links found", result)

    @patch('tap_lms.page.backend_onboarding_process.backend_onboarding_process.frappe')
    def test_update_backend_student_status_success(self, mock_frappe):
        """Test update_backend_student_status for success"""
        mock_student = MagicMock()
        mock_student_doc = MagicMock()
        mock_student_doc.name = "STUD_001"
        mock_student_doc.glific_id = "contact_123"

        self.backend_module.update_backend_student_status(mock_student, "Success", mock_student_doc)

        self.assertEqual(mock_student.processing_status, "Success")
        self.assertEqual(mock_student.student_id, "STUD_001")


if __name__ == '__main__':
    unittest.main(verbosity=2)