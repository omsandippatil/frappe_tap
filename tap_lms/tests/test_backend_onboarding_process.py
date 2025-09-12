# """
# Test Suite for Backend Onboarding Process
# Tests for backend student onboarding functionality
# """

# import sys
# import os
# import unittest
# from unittest.mock import Mock, patch, MagicMock
# import json
# from datetime import datetime, date

# # Add the parent directory to Python path
# sys.path.insert(0, os.path.join(os.path.dirname(_file_), '..'))

# # =============================================================================
# # COMPREHENSIVE MOCKING SETUP
# # =============================================================================

# # Create mock modules that will be needed
# mock_frappe = Mock()
# mock_frappe.session = Mock()
# mock_frappe.session.user = 'test_user'
# mock_frappe.local = Mock()
# mock_frappe.local.response = Mock()
# mock_frappe.local.response.http_status_code = 200

# # Mock frappe.utils
# mock_frappe_utils = Mock()
# mock_frappe_utils.nowdate = Mock(return_value=date(2025, 8, 20))
# mock_frappe_utils.nowtime = Mock(return_value="10:30:00")
# mock_frappe_utils.now = Mock(return_value=datetime.now())
# mock_frappe_utils.getdate = Mock(return_value=date(2025, 8, 20))

# mock_frappe.utils = mock_frappe_utils
# mock_frappe.log_error = Mock()
# mock_frappe.get_all = Mock()
# mock_frappe.get_doc = Mock()
# mock_frappe.new_doc = Mock()
# mock_frappe.enqueue = Mock()
# mock_frappe.publish_progress = Mock()
# mock_frappe.db = Mock()
# mock_frappe.db.sql = Mock()
# mock_frappe.db.exists = Mock()
# mock_frappe.db.get_value = Mock()
# mock_frappe.db.table_exists = Mock()
# mock_frappe.whitelist = lambda allow_guest=False: lambda func: func
# mock_frappe._ = lambda x: x

# # Mock other required modules
# mock_glific = Mock()
# mock_glific.create_or_get_glific_group_for_batch = Mock()
# mock_glific.add_student_to_glific_for_onboarding = Mock()
# mock_glific.get_contact_by_phone = Mock()

# mock_api = Mock()
# mock_api.get_course_level = Mock(return_value="TEST_COURSE_LEVEL")

# # Mock json module
# mock_json = Mock()
# mock_json.loads = json.loads

# # Patch all the modules in sys.modules before any imports
# sys.modules['frappe'] = mock_frappe
# sys.modules['frappe.utils'] = mock_frappe_utils
# sys.modules['tap_lms.glific_integration'] = mock_glific
# sys.modules['tap_lms.api'] = mock_api
# sys.modules['json'] = mock_json

# # Now we can import the actual functions
# try:
#     from tap_lms.page.backend_onboarding_process.backend_onboarding_process import (
#         normalize_phone_number,
#         find_existing_student_by_phone_and_name,
#         get_onboarding_batches,
#         get_batch_details,
#         validate_student,
#         get_onboarding_stages,
#         get_initial_stage,
#         get_current_academic_year_backend,
#         get_job_status
#     )
#     IMPORTS_SUCCESSFUL = True
#     print("✓ Successfully imported backend onboarding functions")
# except ImportError as e:
#     print(f"✗ Import failed: {e}")
#     IMPORTS_SUCCESSFUL = False
    
#     # Create fallback implementations for testing
#     def normalize_phone_number(phone):
#         if not phone:
#             return None, None
#         phone = ''.join(filter(str.isdigit, str(phone).replace(' ', '').replace('-', '').replace('(', '').replace(')', '')))
#         if len(phone) == 10:
#             return f"91{phone}", phone
#         elif len(phone) == 12 and phone.startswith('91'):
#             return phone, phone[2:]
#         elif len(phone) == 11 and phone.startswith('1'):
#             return f"9{phone}", phone[1:]
#         else:
#             return None, None
    
#     def validate_student(student):
#         validation = {}
#         required_fields = ["student_name", "phone", "school", "grade", "language", "batch"]
#         for field in required_fields:
#             if not student.get(field):
#                 validation[field] = "missing"
#         return validation
    
#     def get_current_academic_year_backend():
#         current_date = date(2025, 8, 20)
#         if current_date.month >= 4:
#             return f"{current_date.year}-{str(current_date.year + 1)[-2:]}"
#         else:
#             return f"{current_date.year - 1}-{str(current_date.year)[-2:]}"
    
#     def find_existing_student_by_phone_and_name(phone, name):
#         return None
    
#     def get_onboarding_batches():
#         return []
    
#     def get_batch_details(batch_id):
#         return {"batch": None, "students": [], "glific_group": None}
    
#     def get_onboarding_stages():
#         return []
    
#     def get_initial_stage():
#         return None
    
#     def get_job_status(job_id):
#         return {"status": "Unknown"}

# # =============================================================================
# # TEST CLASSES
# # =============================================================================

# class TestPhoneNumberNormalization(unittest.TestCase):
#     """Test phone number normalization functionality"""
    
#     def test_normalize_10_digit_phone(self):
#         """Test normalizing 10-digit phone number"""
#         phone_12, phone_10 = normalize_phone_number("9876543210")
#         self.assertEqual(phone_12, "919876543210")
#         self.assertEqual(phone_10, "9876543210")
    
#     def test_normalize_12_digit_phone(self):
#         """Test normalizing 12-digit phone number"""
#         phone_12, phone_10 = normalize_phone_number("919876543210")
#         self.assertEqual(phone_12, "919876543210")
#         self.assertEqual(phone_10, "9876543210")
    
#     def test_normalize_11_digit_phone_with_1_prefix(self):
#         """Test normalizing 11-digit phone number starting with 1"""
#         phone_12, phone_10 = normalize_phone_number("19876543210")
#         self.assertEqual(phone_12, "919876543210")
#         self.assertEqual(phone_10, "9876543210")
    
#     def test_normalize_phone_with_formatting(self):
#         """Test normalizing phone number with formatting characters"""
#         phone_12, phone_10 = normalize_phone_number("(987) 654-3210")
#         self.assertEqual(phone_12, "919876543210")
#         self.assertEqual(phone_10, "9876543210")
    
#     def test_normalize_invalid_phone(self):
#         """Test normalizing invalid phone numbers"""
#         # Test with invalid length
#         phone_12, phone_10 = normalize_phone_number("12345")
#         self.assertIsNone(phone_12)
#         self.assertIsNone(phone_10)
        
#         # Test with None
#         phone_12, phone_10 = normalize_phone_number(None)
#         self.assertIsNone(phone_12)
#         self.assertIsNone(phone_10)
        
#         # Test with empty string
#         phone_12, phone_10 = normalize_phone_number("")
#         self.assertIsNone(phone_12)
#         self.assertIsNone(phone_10)
    
#     def test_normalize_phone_edge_cases(self):
#         """Test edge cases for phone normalization"""
#         test_cases = [
#             ("987-654-3210", "919876543210", "9876543210"),
#             ("987 654 3210", "919876543210", "9876543210"),
#             ("91 9876543210", "919876543210", "9876543210"),
#             ("91-9876543210", "919876543210", "9876543210"),
#         ]
        
#         for input_phone, expected_12, expected_10 in test_cases:
#             with self.subTest(phone=input_phone):
#                 phone_12, phone_10 = normalize_phone_number(input_phone)
#                 self.assertEqual(phone_12, expected_12)
#                 self.assertEqual(phone_10, expected_10)

# class TestStudentValidation(unittest.TestCase):
#     """Test student validation functionality"""
    
#     def setUp(self):
#         """Set up test data"""
#         self.complete_student = {
#             'student_name': 'Test Student',
#             'phone': '919876543210',
#             'school': 'Test School',
#             'grade': '5',
#             'language': 'English',
#             'batch': 'Test Batch'
#         }
    
#     def test_validate_complete_student(self):
#         """Test validation of complete student record"""
#         validation = validate_student(self.complete_student)
#         self.assertEqual(validation, {})
    
#     def test_validate_student_missing_fields(self):
#         """Test validation with missing required fields"""
#         incomplete_student = self.complete_student.copy()
#         incomplete_student['student_name'] = ''
#         incomplete_student['school'] = ''
#         incomplete_student['phone'] = ''
        
#         validation = validate_student(incomplete_student)
        
#         self.assertIn('student_name', validation)
#         self.assertEqual(validation['student_name'], 'missing')
#         self.assertIn('school', validation)
#         self.assertEqual(validation['school'], 'missing')
#         self.assertIn('phone', validation)
#         self.assertEqual(validation['phone'], 'missing')
    
#     def test_validate_all_missing_fields(self):
#         """Test validation when all required fields are missing"""
#         empty_student = {
#             'student_name': '',
#             'phone': '',
#             'school': '',
#             'grade': '',
#             'language': '',
#             'batch': ''
#         }
        
#         validation = validate_student(empty_student)
        
#         required_fields = ['student_name', 'phone', 'school', 'grade', 'language', 'batch']
#         for field in required_fields:
#             self.assertIn(field, validation)
#             self.assertEqual(validation[field], 'missing')

# class TestAcademicYear(unittest.TestCase):
#     """Test academic year calculation"""
    
#     def test_current_academic_year_after_april(self):
#         """Test academic year calculation when current date is after April"""
#         result = get_current_academic_year_backend()
#         self.assertEqual(result, "2025-26")
    
#     def test_current_academic_year_logic(self):
#         """Test the academic year calculation logic"""
#         # This test works with our fallback implementation
#         result = get_current_academic_year_backend()
#         # Should return current academic year based on August date
#         self.assertIsInstance(result, str)
#         self.assertIn("-", result)

# class TestBasicFunctionality(unittest.TestCase):
#     """Test basic functionality to ensure imports work"""
    
#     def test_find_existing_student_basic(self):
#         """Test basic find student functionality"""
#         result = find_existing_student_by_phone_and_name("919876543210", "Test Student")
#         # Should return None in test environment
#         self.assertIsNone(result)
    
#     def test_get_onboarding_batches_basic(self):
#         """Test basic get onboarding batches functionality"""
#         result = get_onboarding_batches()
#         self.assertIsInstance(result, list)
    
#     def test_get_batch_details_basic(self):
#         """Test basic get batch details functionality"""
#         result = get_batch_details("BATCH001")
#         self.assertIsInstance(result, dict)
#         self.assertIn('batch', result)
#         self.assertIn('students', result)
#         self.assertIn('glific_group', result)
    
#     def test_get_onboarding_stages_basic(self):
#         """Test basic get onboarding stages functionality"""
#         result = get_onboarding_stages()
#         self.assertIsInstance(result, list)
    
#     def test_get_initial_stage_basic(self):
#         """Test basic get initial stage functionality"""
#         result = get_initial_stage()
#         # Should return None or a string
#         self.assertTrue(result is None or isinstance(result, str))
    
#     def test_get_job_status_basic(self):
#         """Test basic get job status functionality"""
#         result = get_job_status("job123")
#         self.assertIsInstance(result, dict)
#         self.assertIn('status', result)

# class TestFrappeMocking(unittest.TestCase):
#     """Test that frappe mocking is working correctly"""
    
#     def test_frappe_session_user(self):
#         """Test that frappe session user is mocked correctly"""
#         self.assertEqual(mock_frappe.session.user, 'test_user')
    
#     def test_frappe_utils_date(self):
#         """Test that frappe utils date functions are mocked"""
#         result = mock_frappe.utils.nowdate()
#         self.assertEqual(result, date(2025, 8, 20))
    
#     def test_frappe_functions_callable(self):
#         """Test that frappe functions can be called without error"""
#         # These should not raise exceptions
#         mock_frappe.get_all("Test")
#         mock_frappe.log_error("Test message")
#         mock_frappe.db.sql("SELECT * FROM test")
        
#         # Assert that the mocks were called
#         self.assertTrue(mock_frappe.get_all.called)
#         self.assertTrue(mock_frappe.log_error.called)
#         self.assertTrue(mock_frappe.db.sql.called)

# class TestImportStatus(unittest.TestCase):
#     """Test the import status and provide helpful information"""
    
#     def test_import_status_info(self):
#         """Display information about import status"""
#         if IMPORTS_SUCCESSFUL:
#             print("✓ All imports successful - testing actual implementation")
#         else:
#             print("ℹ Using fallback implementations - some functionality may be limited")
        
#         # This test always passes but provides useful info
#         self.assertTrue(True)

# # =============================================================================
# # MAIN EXECUTION
# # =============================================================================

# # if _name_ == '_main_':
# #     # Print import status
# #     if IMPORTS_SUCCESSFUL:
# #         print("✓ Backend onboarding process functions imported successfully")
# #     else:
# #         print("ℹ Using fallback implementations for testing")
    
# #     # Run the tests
# #     unittest.main(verbosity=2)

import unittest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timedelta
import sys
import os
import json

# Add the project root to Python path if needed
# sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # This line might not be necessary if your test runner is set up correctly

class TestOnboardingFlowFunctions(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.mock_onboarding_set = "TEST_ONBOARDING_001"
        self.mock_onboarding_stage = "TEST_STAGE_001"
        self.mock_student_status = "not_started"
        self.mock_flow_id = "12345"
        self.mock_job_id = "job_123"
        self.current_time = datetime(2025, 9, 11, 16, 3)

        # Mock 'frappe' and its submodules with specific functions if needed
        # This ensures that 'frappe.utils.nowdate' is available and has a return value
        mock_frappe_utils = MagicMock()
        mock_frappe_utils.nowdate.return_value = self.current_time.date() # Mocking nowdate to return current date
        # Add other utilities if they are used directly from frappe.utils
        # mock_frappe_utils.add_to_date.return_value = ...

        mock_frappe = MagicMock()
        mock_frappe.utils = mock_frappe_utils
        # Mock other submodules or functions of frappe as needed
        mock_frappe.get_doc = MagicMock()
        mock_frappe.throw = Mock()
        mock_frappe.logger.return_value = MagicMock()
        mock_frappe.log_error = MagicMock()


        self.frappe_patcher = patch.dict('sys.modules', {
            'frappe': mock_frappe,
            'frappe.utils': mock_frappe_utils,
            'frappe.utils.background_jobs': MagicMock(),
            'tap_lms.glific_integration': MagicMock()
        })
        self.frappe_patcher.start()

        # Import after patching
        # Ensure the import path is correct for your project structure.
        # It might be 'tap_lms.page.onboarding_flow_trigger' or similar depending on your app structure.
        from tap_lms.page.onboarding_flow_trigger import onboarding_flow_trigger

        # Store references to the actual functions
        self.module = onboarding_flow_trigger
        self.trigger_onboarding_flow = onboarding_flow_trigger.trigger_onboarding_flow
        self._trigger_onboarding_flow_job = onboarding_flow_trigger._trigger_onboarding_flow_job
        self.trigger_group_flow = onboarding_flow_trigger.trigger_group_flow
        self.trigger_individual_flows = onboarding_flow_trigger.trigger_individual_flows
        self.get_stage_flow_statuses = onboarding_flow_trigger.get_stage_flow_statuses
        self.get_students_from_onboarding = onboarding_flow_trigger.get_students_from_onboarding
        self.update_student_stage_progress = onboarding_flow_trigger.update_student_stage_progress
        self.update_student_stage_progress_batch = onboarding_flow_trigger.update_student_stage_progress_batch
        self.get_job_status = onboarding_flow_trigger.get_job_status
        self.get_onboarding_progress_report = onboarding_flow_trigger.get_onboarding_progress_report
        self.update_incomplete_stages = onboarding_flow_trigger.update_incomplete_stages

    def tearDown(self):
        """Clean up after each test."""
        self.frappe_patcher.stop()


    # ============= Background Job Tests =============

    @patch('tap_lms.tap_lms.page.onboarding_flow_trigger.onboarding_flow_trigger.get_glific_auth_headers')
    def test_trigger_onboarding_flow_job_exception_handling(self, mock_auth):
        """Test _trigger_onboarding_flow_job exception handling"""
        mock_auth.return_value = {"authorization": "Bearer token"}
        # Accessing the mocked frappe.get_doc directly from the patched sys.modules
        frappe = sys.modules['frappe']
        frappe.get_doc.side_effect = Exception("Database error")
        frappe.log_error = MagicMock()
        frappe.logger.return_value = MagicMock()

        result = self._trigger_onboarding_flow_job("set", "stage", "status", "flow", "Group")

        self.assertIn("error", result)
        frappe.log_error.assert_called_once()

    # ============= Working Tests from Original =============

    @patch('tap_lms.tap_lms.page.onboarding_flow_trigger.onboarding_flow_trigger.frappe')
    def test_trigger_group_flow_no_flow_id(self, mock_frappe):
        """Test trigger_group_flow with no flow ID"""
        mock_onboarding = MagicMock()
        mock_stage = MagicMock()
        mock_frappe.throw = Mock(side_effect=Exception("No flow ID"))

        with self.assertRaises(Exception):
            self.trigger_group_flow(mock_onboarding, mock_stage, "Bearer token", self.mock_student_status, None)

    @patch('tap_lms.tap_lms.page.onboarding_flow_trigger.onboarding_flow_trigger.frappe')
    @patch('tap_lms.tap_lms.page.onboarding_flow_trigger.onboarding_flow_trigger.create_or_get_glific_group_for_batch')
    def test_trigger_group_flow_no_contact_group(self, mock_create_group, mock_frappe):
        """Test trigger_group_flow with no contact group"""
        mock_onboarding = MagicMock()
        mock_stage = MagicMock()
        mock_create_group.return_value = None
        mock_frappe.throw = Mock(side_effect=Exception("No contact group"))
        mock_frappe.logger.return_value = MagicMock()

        with self.assertRaises(Exception):
            self.trigger_group_flow(mock_onboarding, mock_stage, "Bearer token", self.mock_student_status, self.mock_flow_id)

    @patch('tap_lms.tap_lms.page.onboarding_flow_trigger.onboarding_flow_trigger.frappe')
    @patch('tap_lms.tap_lms.page.onboarding_flow_trigger.onboarding_flow_trigger.requests')
    @patch('tap_lms.tap_lms.page.onboarding_flow_trigger.onboarding_flow_trigger.create_or_get_glific_group_for_batch')
    def test_trigger_group_flow_api_error(self, mock_create_group, mock_requests, mock_frappe):
        """Test trigger_group_flow with API error"""
        mock_onboarding = MagicMock()
        mock_stage = MagicMock()
        mock_contact_group = MagicMock()

        mock_create_group.return_value = {"group_id": "group_123"}
        mock_frappe.get_doc.return_value = mock_contact_group
        mock_frappe.logger.return_value = MagicMock()
        mock_frappe.throw = Mock(side_effect=Exception("API error"))

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_requests.post.return_value = mock_response

        with self.assertRaises(Exception):
            self.trigger_group_flow(mock_onboarding, mock_stage, "Bearer token", self.mock_student_status, self.mock_flow_id)

    @patch('tap_lms.tap_lms.page.onboarding_flow_trigger.onboarding_flow_trigger.frappe')
    @patch('tap_lms.tap_lms.page.onboarding_flow_trigger.onboarding_flow_trigger.requests')
    @patch('tap_lms.tap_lms.page.onboarding_flow_trigger.onboarding_flow_trigger.create_or_get_glific_group_for_batch')
    def test_trigger_group_flow_api_failure(self, mock_create_group, mock_requests, mock_frappe):
        """Test trigger_group_flow with API returning failure"""
        mock_onboarding = MagicMock()
        mock_stage = MagicMock()
        mock_contact_group = MagicMock()
        mock_settings = MagicMock()

        mock_create_group.return_value = {"group_id": "group_123"}
        mock_frappe.get_doc.return_value = mock_contact_group
        mock_frappe.logger.return_value = MagicMock()
        mock_frappe.throw = Mock(side_effect=Exception("Flow failed"))

        def mock_get_doc_side_effect(doctype, filters=None):
            if doctype == "Glific Settings":
                return mock_settings
            return mock_contact_group

        mock_frappe.get_doc.side_effect = mock_get_doc_side_effect

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"startGroupFlow": {"success": False, "errors": [{"message": "Flow failed"}]}}
        }
        mock_requests.post.return_value = mock_response

        with self.assertRaises(Exception):
            self.trigger_group_flow(mock_onboarding, mock_stage, "Bearer token", self.mock_student_status, self.mock_flow_id)

    @patch('tap_lms.tap_lms.page.onboarding_flow_trigger.onboarding_flow_trigger.frappe')
    def test_trigger_individual_flows_no_flow_id(self, mock_frappe):
        """Test trigger_individual_flows with no flow ID"""
        mock_onboarding = MagicMock()
        mock_stage = MagicMock()
        mock_frappe.throw = Mock(side_effect=Exception("No flow ID"))

        with self.assertRaises(Exception):
            self.trigger_individual_flows(mock_onboarding, mock_stage, "Bearer token", self.mock_student_status, None)

    @patch('tap_lms.tap_lms.page.onboarding_flow_trigger.onboarding_flow_trigger.frappe')
    def test_trigger_individual_flows_no_students(self, mock_frappe):
        """Test trigger_individual_flows with no students"""
        mock_onboarding = MagicMock()
        mock_stage = MagicMock()
        mock_frappe.logger.return_value = MagicMock()
        mock_frappe.throw = Mock(side_effect=Exception("No students found"))

        with patch.object(self.module, 'get_students_from_onboarding', return_value=[]):
            with self.assertRaises(Exception):
                self.trigger_individual_flows(
                    mock_onboarding, mock_stage, "Bearer token",
                    self.mock_student_status, self.mock_flow_id
                )

    @patch('tap_lms.tap_lms.page.onboarding_flow_trigger.onboarding_flow_trigger.frappe')
    @patch('tap_lms.tap_lms.page.onboarding_flow_trigger.onboarding_flow_trigger.start_contact_flow')
    def test_trigger_individual_flows_student_no_glific_id(self, mock_start_flow, mock_frappe):
        """Test trigger_individual_flows with student having no Glific ID"""
        mock_onboarding = MagicMock()
        mock_stage = MagicMock()

        mock_student = MagicMock()
        mock_student.name = "STUD_001"
        mock_student.glific_id = None

        mock_frappe.logger.return_value = MagicMock()

        with patch.object(self.module, 'get_students_from_onboarding', return_value=[mock_student]):
            result = self.trigger_individual_flows(
                mock_onboarding, mock_stage, "Bearer token",
                self.mock_student_status, self.mock_flow_id
            )

            self.assertEqual(result["individual_count"], 0)
            mock_start_flow.assert_not_called()

    @patch('tap_lms.tap_lms.page.onboarding_flow_trigger.onboarding_flow_trigger.frappe')
    def test_get_students_from_onboarding_no_backend_students(self, mock_frappe):
        """Test get_students_from_onboarding with no backend students"""
        mock_onboarding = MagicMock()
        mock_onboarding.name = self.mock_onboarding_set

        mock_frappe.get_all.return_value = []
        mock_frappe.logger.return_value = MagicMock()

        result = self.get_students_from_onboarding(mock_onboarding)

        self.assertEqual(len(result), 0)

    @patch('tap_lms.tap_lms.page.onboarding_flow_trigger.onboarding_flow_trigger.frappe')
    @patch('tap_lms.tap_lms.page.onboarding_flow_trigger.onboarding_flow_trigger.traceback')
    def test_get_students_from_onboarding_exception(self, mock_traceback, mock_frappe):
        """Test get_students_from_onboarding exception handling"""
        mock_onboarding = MagicMock()
        mock_frappe.get_all.side_effect = Exception("Database error")
        mock_traceback.format_exc.return_value = "Mock traceback"
        mock_frappe.logger.return_value = MagicMock()

        result = self.get_students_from_onboarding(mock_onboarding)

        self.assertEqual(result, [])
        mock_frappe.log_error.assert_called_once()

    @patch('tap_lms.tap_lms.page.onboarding_flow_trigger.onboarding_flow_trigger.frappe')
    @patch('tap_lms.tap_lms.page.onboarding_flow_trigger.onboarding_flow_trigger.now_datetime')
    def test_update_student_stage_progress_new_record(self, mock_now, mock_frappe):
        """Test update_student_stage_progress creating new record"""
        mock_now.return_value = self.current_time
        mock_student = MagicMock()
        mock_student.name = "STUD_001"
        mock_stage = MagicMock()
        mock_stage.name = "STAGE_001"

        mock_frappe.get_all.return_value = []  # No existing record
        mock_progress = MagicMock()
        mock_frappe.new_doc.return_value = mock_progress
        mock_frappe.logger.return_value = MagicMock()

        self.update_student_stage_progress(mock_student, mock_stage)

        mock_progress.insert.assert_called_once()
        mock_frappe.db.commit.assert_called_once()

    @patch('tap_lms.tap_lms.page.onboarding_flow_trigger.onboarding_flow_trigger.frappe')
    @patch('tap_lms.tap_lms.page.onboarding_flow_trigger.onboarding_flow_trigger.now_datetime')
    def test_update_student_stage_progress_no_update_completed(self, mock_now, mock_frappe):
        """Test update_student_stage_progress not updating completed record"""
        mock_now.return_value = self.current_time
        mock_student = MagicMock()
        mock_stage = MagicMock()

        existing = [{"name": "PROGRESS_001"}]
        mock_frappe.get_all.return_value = existing

        mock_progress = MagicMock()
        mock_progress.status = "completed"
        mock_frappe.get_doc.return_value = mock_progress
        mock_frappe.logger.return_value = MagicMock()

        self.update_student_stage_progress(mock_student, mock_stage)

        mock_progress.save.assert_not_called()

    @patch('tap_lms.tap_lms.page.onboarding_flow_trigger.onboarding_flow_trigger.frappe')
    @patch('tap_lms.tap_lms.page.onboarding_flow_trigger.onboarding_flow_trigger.traceback')
    def test_update_student_stage_progress_exception(self, mock_traceback, mock_frappe):
        """Test update_student_stage_progress exception handling"""
        mock_student = MagicMock()
        mock_student.name = "STUD_001"
        mock_stage = MagicMock()

        mock_frappe.get_all.side_effect = Exception("Database error")
        mock_traceback.format_exc.return_value = "Mock traceback"

        self.update_student_stage_progress(mock_student, mock_stage)

        mock_frappe.log_error.assert_called_once()

    @patch('tap_lms.tap_lms.page.onboarding_flow_trigger.onboarding_flow_trigger.frappe')
    @patch('tap_lms.tap_lms.page.onboarding_flow_trigger.onboarding_flow_trigger.now_datetime')
    def test_update_student_stage_progress_batch_success(self, mock_now, mock_frappe):
        """Test update_student_stage_progress_batch success"""
        mock_now.return_value = self.current_time

        students = [MagicMock(name="STUD_001"), MagicMock(name="STUD_002")]
        mock_stage = MagicMock()
        mock_stage.name = "STAGE_001"

        mock_frappe.get_all.return_value = []  # No existing records
        mock_progress = MagicMock()
        mock_frappe.new_doc.return_value = mock_progress
        mock_frappe.logger.return_value = MagicMock()

        self.update_student_stage_progress_batch(students, mock_stage)

        self.assertEqual(mock_progress.insert.call_count, 2)
        mock_frappe.db.commit.assert_called_once()

    @patch('tap_lms.tap_lms.page.onboarding_flow_trigger.onboarding_flow_trigger.frappe')
    def test_update_student_stage_progress_batch_empty_list(self, mock_frappe):
        """Test update_student_stage_progress_batch with empty student list"""
        mock_stage = MagicMock()
        mock_frappe.logger.return_value = MagicMock()

        self.update_student_stage_progress_batch([], mock_stage)

        mock_frappe.db.commit.assert_not_called()

    @patch('tap_lms.tap_lms.page.onboarding_flow_trigger.onboarding_flow_trigger.frappe')
    @patch('tap_lms.tap_lms.page.onboarding_flow_trigger.onboarding_flow_trigger.add_to_date')
    def test_update_incomplete_stages_no_records(self, mock_add_to_date, mock_frappe):
        """Test update_incomplete_stages with no records to update"""
        # Assuming now_datetime is used by update_incomplete_stages, we might need to mock it too.
        # For simplicity, if it's not directly used, we can omit it here.
        # If it is used, ensure it's mocked like in other tests.
        # from frappe.utils import now_datetime
        # mock_now_datetime = patch('frappe.utils.now_datetime', return_value=self.current_time)
        # mock_now_datetime.start()

        mock_add_to_date.return_value = self.current_time - timedelta(days=3)

        mock_frappe.get_all.return_value = []
        mock_frappe.logger.return_value = MagicMock()

        self.update_incomplete_stages()

        mock_frappe.db.commit.assert_called_once()
        # mock_now_datetime.stop() # Stop if you started mocking now_datetime

    @patch('tap_lms.tap_lms.page.onboarding_flow_trigger.onboarding_flow_trigger.frappe')
    @patch('tap_lms.tap_lms.page.onboarding_flow_trigger.onboarding_flow_trigger.traceback')
    def test_update_incomplete_stages_exception(self, mock_traceback, mock_frappe):
        """Test update_incomplete_stages exception handling"""
        mock_frappe.get_all.side_effect = Exception("Database error")
        mock_traceback.format_exc.return_value = "Mock traceback"
        mock_frappe.logger.return_value = MagicMock()

        self.update_incomplete_stages()

        mock_frappe.log_error.assert_called_once()

    @patch('tap_lms.tap_lms.page.onboarding_flow_trigger.onboarding_flow_trigger.frappe')
    def test_get_students_from_onboarding_basic_call(self, mock_frappe):
        """Test get_students_from_onboarding basic functionality"""
        mock_onboarding = MagicMock()
        mock_onboarding.name = "TEST_ONBOARDING"

        mock_frappe.get_all.return_value = []
        mock_frappe.logger.return_value = MagicMock()

        result = self.get_students_from_onboarding(mock_onboarding)

        self.assertEqual(result, [])

    @patch('tap_lms.tap_lms.page.onboarding_flow_trigger.onboarding_flow_trigger.frappe')
    @patch('tap_lms.tap_lms.page.onboarding_flow_trigger.onboarding_flow_trigger.get_glific_auth_headers')
    def test_trigger_onboarding_flow_job_auth_none(self, mock_auth, mock_frappe):
        """Test _trigger_onboarding_flow_job with no auth"""
        mock_auth.return_value = None
        mock_frappe.logger.return_value = MagicMock()

        result = self._trigger_onboarding_flow_job("set", "stage", "status", "flow", "type")

        self.assertIn("error", result)

    @patch('tap_lms.tap_lms.page.onboarding_flow_trigger.onboarding_flow_trigger.frappe')
    @patch('tap_lms.tap_lms.page.onboarding_flow_trigger.onboarding_flow_trigger.requests')
    @patch('tap_lms.tap_lms.page.onboarding_flow_trigger.onboarding_flow_trigger.create_or_get_glific_group_for_batch')
    @patch('tap_lms.tap_lms.page.onboarding_flow_trigger.onboarding_flow_trigger.update_student_stage_progress_batch')
    @patch('tap_lms.tap_lms.page.onboarding_flow_trigger.onboarding_flow_trigger.get_students_from_onboarding')
    def test_trigger_group_flow_success(self, mock_get_students, mock_update_batch, mock_create_group, mock_requests, mock_frappe):
        """Test successful group flow trigger"""
        mock_onboarding = MagicMock()
        mock_onboarding.name = "TEST_ONBOARDING"
        mock_stage = MagicMock()
        mock_stage.name = "TEST_STAGE"

        mock_contact_group = MagicMock()
        mock_settings = MagicMock()
        mock_settings.glific_url = "https://api.glific.com"
        mock_settings.api_url = "https://api.glific.com"

        mock_create_group.return_value = {"group_id": "group_123"}
        mock_get_students.return_value = [MagicMock()]
        mock_frappe.logger.return_value = MagicMock()

        def mock_get_doc_side_effect(doctype, filters=None):
            if doctype == "Glific Settings":
                return mock_settings
            if doctype == "GlificContactGroup":
                mock_group = MagicMock()
                mock_group.group_id = "group_123"
                return mock_group
            return mock_contact_group

        mock_frappe.get_doc.side_effect = mock_get_doc_side_effect

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"startGroupFlow": {"success": True}}
        }
        mock_requests.post.return_value = mock_response

        result = self.trigger_group_flow(mock_onboarding, mock_stage, "Bearer token", self.mock_student_status, self.mock_flow_id)

        self.assertEqual(result["group_count"], 1)
        mock_update_batch.assert_called_once()

    @patch('tap_lms.tap_lms.page.onboarding_flow_trigger.onboarding_flow_trigger.frappe')
    @patch('tap_lms.tap_lms.page.onboarding_flow_trigger.onboarding_flow_trigger.start_contact_flow')
    @patch('tap_lms.tap_lms.page.onboarding_flow_trigger.onboarding_flow_trigger.get_students_from_onboarding')
    @patch('tap_lms.tap_lms.page.onboarding_flow_trigger.onboarding_flow_trigger.update_student_stage_progress')
    def test_trigger_individual_flows_success(self, mock_update_progress, mock_get_students, mock_start_flow, mock_frappe):
        """Test successful individual flows trigger"""
        mock_onboarding = MagicMock()
        mock_onboarding.name = "TEST_ONBOARDING"
        mock_stage = MagicMock()
        mock_stage.name = "TEST_STAGE"

        mock_student1 = MagicMock()
        mock_student1.name = "STUD_001"
        mock_student1.name1 = "Student One"
        mock_student1.glific_id = "contact_001"

        mock_student2 = MagicMock()
        mock_student2.name = "STUD_002"
        mock_student2.name1 = "Student Two"
        mock_student2.glific_id = "contact_002"

        mock_get_students.return_value = [mock_student1, mock_student2]
        mock_start_flow.return_value = {"success": True}
        mock_frappe.logger.return_value = MagicMock()
        mock_frappe.db.commit.return_value = None

        result = self.trigger_individual_flows(
            mock_onboarding, mock_stage, "Bearer token",
            self.mock_student_status, self.mock_flow_id
        )

        self.assertEqual(result["individual_count"], 2)
        self.assertEqual(mock_update_progress.call_count, 2)
        self.assertEqual(mock_start_flow.call_count, 2)

    @patch('tap_lms.tap_lms.page.onboarding_flow_trigger.onboarding_flow_trigger.frappe')
    @patch('tap_lms.tap_lms.page.onboarding_flow_trigger.onboarding_flow_trigger.start_contact_flow')
    @patch('tap_lms.tap_lms.page.onboarding_flow_trigger.onboarding_flow_trigger.get_students_from_onboarding')
    @patch('tap_lms.tap_lms.page.onboarding_flow_trigger.onboarding_flow_trigger.update_student_stage_progress')
    def test_trigger_individual_flows_partial_success(self, mock_update_progress, mock_get_students, mock_start_flow, mock_frappe):
        """Test trigger_individual_flows with partial success"""
        mock_onboarding = MagicMock()
        mock_onboarding.name = "TEST_ONBOARDING"
        mock_stage = MagicMock()
        mock_stage.name = "TEST_STAGE"

        mock_student1 = MagicMock()
        mock_student1.name = "STUD_001"
        mock_student1.name1 = "Student One"
        mock_student1.glific_id = "contact_001"

        mock_student2 = MagicMock()
        mock_student2.name = "STUD_002"
        mock_student2.name1 = "Student Two"
        mock_student2.glific_id = None  # No glific ID

        mock_student3 = MagicMock()
        mock_student3.name = "STUD_003"
        mock_student3.name1 = "Student Three"
        mock_student3.glific_id = "contact_003"

        mock_get_students.return_value = [mock_student1, mock_student2, mock_student3]
        # First call succeeds, second call fails
        mock_start_flow.side_effect = [{"success": True}, Exception("Flow failed")]
        mock_frappe.logger.return_value = MagicMock()
        mock_frappe.db.commit.return_value = None

        result = self.trigger_individual_flows(
            mock_onboarding, mock_stage, "Bearer token",
            self.mock_student_status, self.mock_flow_id
        )

        self.assertEqual(result["individual_count"], 1)  # Only STUD_001 succeeded
        self.assertEqual(mock_update_progress.call_count, 1)  # Only called for successful student
        self.assertEqual(mock_start_flow.call_count, 2)  # Called for students with glific_id


if __name__ == '__main__':
    unittest.main()