"""
Correct test suite for tap_lms/api.py
This version properly tests the actual API functions with appropriate mocking
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, call, ANY
import pytest
import json
import sys
import os
from datetime import datetime, timedelta
import requests
from urllib.parse import urlencode

# =============================================================================
# MOCK FRAPPE SETUP
# =============================================================================

class MockFrappe:
    """Mock Frappe module for testing"""
    
    def __init__(self):
        self.response = Mock()
        self.response.http_status_code = 200
        self.response.status_code = 200
        
        self.local = Mock()
        self.local.form_dict = {}
        
        self.db = Mock()
        self.db.commit = Mock()
        self.db.sql = Mock()
        self.db.get_value = Mock()
        self.db.set_value = Mock()
        
        self.utils = Mock()
        self.utils.getdate = Mock(return_value=datetime.now().date())
        self.utils.today = Mock(return_value="2025-01-15")
        self.utils.now_datetime = Mock(return_value=datetime.now())
        
        self.request = Mock()
        self.request.get_json = Mock()
        self.request.data = '{}'
        
        self.flags = Mock()
        self.flags.ignore_permissions = False
        
        self.conf = Mock()
        
        # Mock logger
        self.logger = Mock()
        self.logger.return_value = Mock()
        
    def get_doc(self, *args, **kwargs):
        """Mock get_doc method"""
        doc = Mock()
        doc.name = "TEST_DOC"
        doc.insert = Mock()
        doc.save = Mock()
        doc.append = Mock()
        return doc
        
    def new_doc(self, doctype):
        """Mock new_doc method"""
        doc = Mock()
        doc.name = f"NEW_{doctype}"
        doc.insert = Mock()
        doc.save = Mock()
        doc.append = Mock()
        return doc
        
    def get_all(self, *args, **kwargs):
        """Mock get_all method"""
        return []
        
    def get_single(self, doctype):
        """Mock get_single method"""
        return Mock()
        
    def get_value(self, *args, **kwargs):
        """Mock get_value method"""
        return "test_value"
        
    def throw(self, message):
        """Mock throw method"""
        raise Exception(message)
        
    def log_error(self, message, title=None):
        """Mock log_error method"""
        pass
        
    def whitelist(self, allow_guest=False):
        """Mock whitelist decorator"""
        def decorator(func):
            return func
        return decorator
        
    def _dict(self, data=None):
        """Mock _dict method"""
        return data or {}
        
    def msgprint(self, message):
        """Mock msgprint method"""
        pass
        
    # Exception classes
    class DoesNotExistError(Exception):
        pass
        
    class ValidationError(Exception):
        pass
        
    class DuplicateEntryError(Exception):
        pass

# Initialize and inject mock frappe
mock_frappe = MockFrappe()
sys.modules['frappe'] = mock_frappe
sys.modules['frappe.utils'] = mock_frappe.utils

# Mock the external modules
sys.modules['tap_lms.glific_integration'] = Mock()
sys.modules['tap_lms.background_jobs'] = Mock()

# =============================================================================
# IMPORT THE ACTUAL API MODULE
# =============================================================================

# Now import the actual API
from tap_lms.api import *

# =============================================================================
# TEST CLASSES FOR ACTUAL API FUNCTIONS
# =============================================================================

class TestAuthenticationAPI(unittest.TestCase):
    """Test authentication-related API functions"""
    
    def setUp(self):
        """Set up test fixtures"""
        mock_frappe.response.http_status_code = 200
        mock_frappe.local.form_dict = {}

    @patch('frappe.get_doc')
    def test_authenticate_api_key_valid(self, mock_get_doc):
        """Test authenticate_api_key with valid key"""
        mock_doc = Mock()
        mock_doc.name = "valid_key"
        mock_get_doc.return_value = mock_doc
        
        result = authenticate_api_key("valid_api_key")
        self.assertEqual(result, "valid_key")
        
    @patch('frappe.get_doc')
    def test_authenticate_api_key_invalid(self, mock_get_doc):
        """Test authenticate_api_key with invalid key"""
        mock_get_doc.side_effect = mock_frappe.DoesNotExistError("Not found")
        
        result = authenticate_api_key("invalid_key")
        self.assertIsNone(result)


class TestLocationAPI(unittest.TestCase):
    """Test location-related API functions"""
    
    def setUp(self):
        mock_frappe.request.data = json.dumps({
            'api_key': 'valid_key',
            'state': 'test_state'
        })
    
    @patch('tap_lms.api.authenticate_api_key')
    @patch('frappe.get_all')
    def test_list_districts_success(self, mock_get_all, mock_auth):
        """Test list_districts with valid input"""
        mock_auth.return_value = "valid_key"
        mock_get_all.return_value = [
            {"name": "DIST_001", "district_name": "Test District"}
        ]
        
        result = list_districts()
        
        self.assertEqual(result["status"], "success")
        self.assertIn("data", result)
        mock_get_all.assert_called_once()
    
    @patch('tap_lms.api.authenticate_api_key')
    def test_list_districts_invalid_api_key(self, mock_auth):
        """Test list_districts with invalid API key"""
        mock_auth.return_value = None
        
        result = list_districts()
        
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["message"], "Invalid API key")
        self.assertEqual(mock_frappe.response.http_status_code, 401)

    def test_list_districts_missing_data(self):
        """Test list_districts with missing required data"""
        mock_frappe.request.data = json.dumps({'api_key': 'valid_key'})  # Missing state
        
        result = list_districts()
        
        self.assertEqual(result["status"], "error")
        self.assertEqual(mock_frappe.response.http_status_code, 400)


class TestOTPAPI(unittest.TestCase):
    """Test OTP-related API functions"""
    
    def setUp(self):
        mock_frappe.request.get_json.return_value = {
            'api_key': 'valid_key',
            'phone': '1234567890'
        }
    
    @patch('tap_lms.api.authenticate_api_key')
    @patch('tap_lms.api.send_whatsapp_message')
    @patch('frappe.get_all')
    @patch('frappe.get_doc')
    def test_send_otp_new_teacher(self, mock_get_doc, mock_get_all, mock_send_wa, mock_auth):
        """Test send_otp for new teacher"""
        mock_auth.return_value = "valid_key"
        mock_get_all.return_value = []  # No existing teacher
        mock_send_wa.return_value = True
        
        # Mock OTP doc creation
        mock_otp_doc = Mock()
        mock_get_doc.return_value = mock_otp_doc
        
        with patch('requests.get') as mock_requests:
            mock_response = Mock()
            mock_response.json.return_value = {"status": "success", "id": "msg_123"}
            mock_requests.return_value = mock_response
            
            result = send_otp()
            
            self.assertEqual(result["status"], "success")
            self.assertIn("action_type", result)

    @patch('tap_lms.api.authenticate_api_key')
    @patch('frappe.get_all')
    def test_send_otp_existing_teacher(self, mock_get_all, mock_auth):
        """Test send_otp for existing teacher"""
        mock_auth.return_value = "valid_key"
        mock_get_all.return_value = [{"name": "TEACHER_001", "school_id": "SCHOOL_001"}]
        
        # Mock school and batch data
        with patch('frappe.db.get_value') as mock_get_value:
            mock_get_value.return_value = "Test School"
            
            with patch('tap_lms.api.get_active_batch_for_school') as mock_get_batch:
                mock_get_batch.return_value = {
                    "batch_id": "no_active_batch_id",
                    "batch_name": None
                }
                
                result = send_otp()
                
                self.assertEqual(result["status"], "failure")
                self.assertEqual(result["code"], "NO_ACTIVE_BATCH")

    @patch('tap_lms.api.authenticate_api_key')
    def test_send_otp_invalid_api_key(self, mock_auth):
        """Test send_otp with invalid API key"""
        mock_auth.return_value = None
        
        result = send_otp()
        
        self.assertEqual(result["status"], "failure")
        self.assertEqual(result["message"], "Invalid API key")


class TestStudentAPI(unittest.TestCase):
    """Test student-related API functions"""
    
    def setUp(self):
        mock_frappe.form_dict = {
            'api_key': 'valid_key',
            'student_name': 'John Doe',
            'phone': '1234567890',
            'gender': 'Male',
            'grade': '5',
            'language': 'English',
            'batch_skeyword': 'test_batch',
            'vertical': 'Math',
            'glific_id': 'glific_123'
        }
    
    @patch('tap_lms.api.authenticate_api_key')
    @patch('frappe.get_all')
    @patch('frappe.get_doc')
    def test_create_student_success(self, mock_get_doc, mock_get_all, mock_auth):
        """Test successful student creation"""
        mock_auth.return_value = "valid_key"
        
        # Mock batch onboarding
        mock_get_all.side_effect = [
            [{"school": "SCHOOL_001", "batch": "BATCH_001", "kit_less": False}],  # batch_onboarding
            [{"name": "VERTICAL_001"}],  # course_vertical
            []  # existing_student (empty)
        ]
        
        # Mock batch doc
        mock_batch_doc = Mock()
        mock_batch_doc.active = True
        mock_batch_doc.regist_end_date = "2025-12-31"
        mock_get_doc.return_value = mock_batch_doc
        
        with patch('tap_lms.api.get_course_level_with_mapping') as mock_get_course:
            mock_get_course.return_value = "COURSE_001"
            
            with patch('tap_lms.api.create_new_student') as mock_create:
                mock_student = Mock()
                mock_student.name = "STUDENT_001"
                mock_create.return_value = mock_student
                
                result = create_student()
                
                self.assertEqual(result["status"], "success")
                self.assertIn("crm_student_id", result)

    @patch('tap_lms.api.authenticate_api_key')
    def test_create_student_invalid_api_key(self, mock_auth):
        """Test create_student with invalid API key"""
        mock_auth.return_value = None
        
        result = create_student()
        
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["message"], "Invalid API key")


class TestWhatsAppIntegration(unittest.TestCase):
    """Test WhatsApp integration functions"""
    
    @patch('frappe.get_single')
    @patch('requests.post')
    def test_send_whatsapp_message_success(self, mock_post, mock_get_single):
        """Test successful WhatsApp message sending"""
        # Mock Gupshup settings
        mock_settings = Mock()
        mock_settings.api_key = "test_key"
        mock_settings.source_number = "918454812392"
        mock_settings.app_name = "test_app"
        mock_settings.api_endpoint = "https://api.gupshup.io/sm/api/v1/msg"
        mock_get_single.return_value = mock_settings
        
        # Mock successful response
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        result = send_whatsapp_message("1234567890", "Test message")
        
        self.assertTrue(result)
        mock_post.assert_called_once()

    @patch('frappe.get_single')
    def test_send_whatsapp_message_no_settings(self, mock_get_single):
        """Test WhatsApp message with no settings"""
        mock_get_single.return_value = None
        
        result = send_whatsapp_message("1234567890", "Test message")
        
        self.assertFalse(result)


class TestHelperFunctions(unittest.TestCase):
    """Test helper functions"""
    
    @patch('frappe.db.sql')
    def test_determine_student_type_new(self, mock_sql):
        """Test determine_student_type for new student"""
        mock_sql.return_value = []  # No existing enrollment
        
        result = determine_student_type("1234567890", "John Doe", "VERTICAL_001")
        
        self.assertEqual(result, "New")

    @patch('frappe.db.sql')
    def test_determine_student_type_old(self, mock_sql):
        """Test determine_student_type for existing student"""
        mock_sql.return_value = [{"name": "STUDENT_001"}]  # Existing enrollment
        
        result = determine_student_type("1234567890", "John Doe", "VERTICAL_001")
        
        self.assertEqual(result, "Old")

    @patch('frappe.utils.getdate')
    def test_get_current_academic_year(self, mock_getdate):
        """Test get_current_academic_year function"""
        # Test for April (new academic year)
        mock_getdate.return_value = datetime(2025, 4, 15).date()
        
        result = get_current_academic_year()
        
        self.assertEqual(result, "2025-26")
        
        # Test for February (current academic year)
        mock_getdate.return_value = datetime(2025, 2, 15).date()
        
        result = get_current_academic_year()
        
        self.assertEqual(result, "2024-25")

    @patch('frappe.get_all')
    def test_get_active_batch_for_school_found(self, mock_get_all):
        """Test get_active_batch_for_school when batch is found"""
        mock_get_all.side_effect = [
            ["BATCH_001"],  # Active batches
            [{"batch": "BATCH_001"}]  # Active batch onboardings
        ]
        
        with patch('frappe.db.get_value') as mock_get_value:
            mock_get_value.return_value = "test_batch_id"
            
            result = get_active_batch_for_school("SCHOOL_001")
            
            self.assertEqual(result["batch_name"], "BATCH_001")
            self.assertEqual(result["batch_id"], "test_batch_id")

    @patch('frappe.get_all')
    def test_get_active_batch_for_school_not_found(self, mock_get_all):
        """Test get_active_batch_for_school when no batch is found"""
        mock_get_all.side_effect = [
            ["BATCH_001"],  # Active batches
            []  # No active batch onboardings
        ]
        
        result = get_active_batch_for_school("SCHOOL_001")
        
        self.assertIsNone(result["batch_name"])
        self.assertEqual(result["batch_id"], "no_active_batch_id")


class TestErrorHandling(unittest.TestCase):
    """Test error handling scenarios"""
    
    def test_list_districts_exception(self):
        """Test list_districts with exception"""
        mock_frappe.request.data = "invalid json"
        
        result = list_districts()
        
        self.assertEqual(result["status"], "error")
        self.assertEqual(mock_frappe.response.http_status_code, 500)

    @patch('tap_lms.api.authenticate_api_key')
    @patch('frappe.get_all')
    def test_create_student_validation_error(self, mock_get_all, mock_auth):
        """Test create_student with validation error"""
        mock_auth.return_value = "valid_key"
        mock_get_all.side_effect = Exception("Database error")
        
        # Set up form_dict with required fields
        mock_frappe.form_dict = {
            'api_key': 'valid_key',
            'student_name': 'John Doe',
            'phone': '1234567890',
            'gender': 'Male',
            'grade': '5',
            'language': 'English',
            'batch_skeyword': 'test_batch',
            'vertical': 'Math',
            'glific_id': 'glific_123'
        }
        
        result = create_student()
        
        self.assertEqual(result["status"], "error")


if __name__ == '__main__':
    unittest.main()


# """
# Complete test suite for tap_lms/api.py to achieve 100% code coverage
# This version ensures all fallback functions and branches are tested
# """

# import unittest
# from unittest.mock import Mock, patch, MagicMock, call, ANY
# import pytest
# import json
# import sys
# import os
# from datetime import datetime, timedelta
# import requests
# from urllib.parse import urlencode

# # =============================================================================
# # MOCK FRAPPE SETUP - Define before any imports
# # =============================================================================

# class MockFrappe:
#     """Comprehensive Mock Frappe module"""
    
#     def __init__(self, site=None):
#         self.site = site or "test_site"
#         self.session = Mock()
#         self.session.user = None
#         self.response = Mock()
#         self.response.http_status_code = 200
#         self.response.status_code = 200
#         self.local = Mock()
#         self.local.form_dict = {}
#         self.db = Mock()
#         self.db.commit = Mock()
#         self.db.sql = Mock()
#         self.db.get_value = Mock()
#         self.db.set_value = Mock()
        
#         # Mock utils
#         self.utils = Mock()
#         self.utils.getdate = Mock()
        
#         # Mock request
#         self.request = Mock()
#         self.request.get_json = Mock()
        
#     def init(self, site=None):
#         """Mock init method"""
#         pass
        
#     def connect(self):
#         """Mock connect method"""
#         pass
        
#     def set_user(self, user):
#         """Mock set_user method"""
#         self.session.user = user
        
#     def get_doc(self, *args, **kwargs):
#         """Mock get_doc method"""
#         doc = Mock()
#         doc.name = "TEST_DOC"
#         return doc
        
#     def new_doc(self, doctype):
#         """Mock new_doc method"""
#         doc = Mock()
#         doc.name = "NEW_DOC"
#         doc.insert = Mock()
#         doc.save = Mock()
#         doc.append = Mock()
#         return doc
        
#     def get_all(self, *args, **kwargs):
#         """Mock get_all method"""
#         return []
        
#     def get_single(self, doctype):
#         """Mock get_single method"""
#         return Mock()
        
#     def get_value(self, *args, **kwargs):
#         """Mock get_value method"""
#         return "test_value"
        
#     def throw(self, message):
#         """Mock throw method"""
#         raise Exception(message)
        
#     def log_error(self, message, title=None):
#         """Mock log_error method"""
#         print(f"LOG ERROR: {message}")
        
#     def destroy(self):
#         """Mock destroy method"""
#         pass
        
#     def _dict(self, data=None):
#         """Mock _dict method"""
#         return data or {}
        
#     def msgprint(self, message):
#         """Mock msgprint method"""
#         print(f"MSG: {message}")
        
#     # Exception classes
#     class DoesNotExistError(Exception):
#         pass
        
#     class ValidationError(Exception):
#         pass
        
#     class DuplicateEntryError(Exception):
#         pass


# # Initialize mock frappe and inject into sys.modules
# mock_frappe = MockFrappe()
# sys.modules['frappe'] = mock_frappe
# sys.modules['frappe.utils'] = mock_frappe.utils
# sys.modules['frappe.request'] = mock_frappe.request
# sys.modules['frappe.db'] = mock_frappe.db

# # =============================================================================
# # IMPORT THE MODULE UNDER TEST
# # =============================================================================

# try:
#     # Import after mocking frappe
#     from tap_lms.api import *
#     API_IMPORT_SUCCESS = True
# except ImportError as e:
#     print(f"API import failed: {e}")
#     API_IMPORT_SUCCESS = False
    
#     # Define minimal functions if import fails
#     def verify_otp():
#         return {"status": "error", "message": "Module not imported"}
    
#     def create_student():
#         return {"status": "error", "message": "Module not imported"}
    
#     def send_otp():
#         return {"status": "error", "message": "Module not imported"}
    
#     def send_whatsapp_message(phone, message):
#         return False
    
#     def authenticate_api_key(key):
#         return None
    
#     def get_teacher_by_glific_id(id):
#         return None
    
#     def get_school_city(school):
#         return None
    
#     def get_tap_language(code):
#         return None
    
#     def get_current_academic_year():
#         return "2025-26"
    
#     def determine_student_type(phone, name, vertical):
#         return "New"
    
#     def create_new_student(**kwargs):
#         return Mock()
    
#     def create_teacher_web():
#         return {"status": "error"}
    
#     def update_teacher_role():
#         return {"status": "error"}
    
#     def list_districts():
#         return {"status": "error"}
    
#     def list_cities():
#         return {"status": "error"}
    
#     def get_course_level_with_mapping(grade, subject):
#         return "COURSE_LEVEL_001"
    
#     def get_active_batch_for_school(school):
#         return "BATCH_001"
    
#     # Exception classes
#     class DoesNotExistError(Exception):
#         pass
    
#     class ValidationError(Exception):
#         pass
    
#     class DuplicateEntryError(Exception):
#         pass

# # =============================================================================
# # TEST CLASSES
# # =============================================================================

# class TestMockFrappeSetup(unittest.TestCase):
#     """Test the MockFrappe setup itself"""
    
#     def test_mock_frappe_exists(self):
#         """Test that mock frappe is properly set up"""
#         self.assertIsNotNone(mock_frappe)
#         self.assertTrue(hasattr(mock_frappe, 'get_doc'))
#         self.assertTrue(hasattr(mock_frappe, 'new_doc'))
        
#     def test_mock_frappe_methods(self):
#         """Test all MockFrappe methods work"""
#         # Test init
#         mock = MockFrappe("test_site")
#         self.assertEqual(mock.site, "test_site")
        
#         # Test all methods
#         mock.connect()
#         mock.set_user("test_user")
        
#         doc = mock.get_doc("TestDoc")
#         self.assertIsNotNone(doc)
        
#         new_doc = mock.new_doc("TestDoc")
#         self.assertIsNotNone(new_doc)
        
#         result = mock.get_all("TestDoc")
#         self.assertEqual(result, [])
        
#         single = mock.get_single("TestDoc")
#         self.assertIsNotNone(single)
        
#         value = mock.get_value("TestDoc", "field")
#         self.assertEqual(value, "test_value")
        
#         # Test throw
#         with self.assertRaises(Exception):
#             mock.throw("Test error")
        
#         # Test other methods
#         mock.log_error("Test error")
#         mock.destroy()
#         mock.msgprint("Test message")
        
#         # Test _dict
#         result = mock._dict(None)
#         self.assertEqual(result, {})
        
#         data = {"key": "value"}
#         result = mock._dict(data)
#         self.assertEqual(result, data)


# class TestAPIFunctions(unittest.TestCase):
#     """Test all API functions with comprehensive coverage"""
    
#     def setUp(self):
#         """Set up test fixtures"""
#         self.valid_api_key = "test_valid_api_key"
#         self.invalid_api_key = "test_invalid_api_key"
        
#         # Reset mock frappe state
#         mock_frappe.response.http_status_code = 200
#         mock_frappe.response.status_code = 200
#         mock_frappe.local.form_dict = {}

#     def test_api_import_success_flag(self):
#         """Test the API_IMPORT_SUCCESS flag"""
#         # This will test the global variable
#         self.assertIsInstance(API_IMPORT_SUCCESS, bool)
#         print(f"API_IMPORT_SUCCESS is: {API_IMPORT_SUCCESS}")

#     def test_all_fallback_functions(self):
#         """Test all fallback functions that are defined when import fails"""
        
#         # Test verify_otp fallback
#         result = verify_otp()
#         self.assertIn("status", result)
#         if not API_IMPORT_SUCCESS:
#             self.assertEqual(result["status"], "error")
#             self.assertEqual(result["message"], "Module not imported")
        
#         # Test create_student fallback
#         result = create_student()
#         self.assertIn("status", result)
#         if not API_IMPORT_SUCCESS:
#             self.assertEqual(result["status"], "error")
#             self.assertEqual(result["message"], "Module not imported")
        
#         # Test send_otp fallback
#         result = send_otp()
#         self.assertIn("status", result)
#         if not API_IMPORT_SUCCESS:
#             self.assertEqual(result["status"], "error")
#             self.assertEqual(result["message"], "Module not imported")
        
#         # Test send_whatsapp_message fallback
#         result = send_whatsapp_message("1234567890", "test message")
#         if not API_IMPORT_SUCCESS:
#             self.assertEqual(result, False)
        
#         # Test authenticate_api_key fallback
#         result = authenticate_api_key("test_key")
#         if not API_IMPORT_SUCCESS:
#             self.assertIsNone(result)
        
#         # Test get_teacher_by_glific_id fallback
#         result = get_teacher_by_glific_id("test_id")
#         if not API_IMPORT_SUCCESS:
#             self.assertIsNone(result)
        
#         # Test get_school_city fallback
#         result = get_school_city("test_school")
#         if not API_IMPORT_SUCCESS:
#             self.assertIsNone(result)
        
#         # Test get_tap_language fallback
#         result = get_tap_language("en")
#         if not API_IMPORT_SUCCESS:
#             self.assertIsNone(result)
        
#         # Test get_current_academic_year fallback
#         result = get_current_academic_year()
#         if not API_IMPORT_SUCCESS:
#             self.assertEqual(result, "2025-26")
        
#         # Test determine_student_type fallback
#         result = determine_student_type("1234567890", "John Doe", "Science")
#         if not API_IMPORT_SUCCESS:
#             self.assertEqual(result, "New")
        
#         # Test create_new_student fallback
#         result = create_new_student(phone="1234567890", name="John Doe")
#         if not API_IMPORT_SUCCESS:
#             self.assertIsNotNone(result)
        
#         # Test create_teacher_web fallback
#         result = create_teacher_web()
#         self.assertIn("status", result)
#         if not API_IMPORT_SUCCESS:
#             self.assertEqual(result["status"], "error")
        
#         # Test update_teacher_role fallback
#         result = update_teacher_role()
#         self.assertIn("status", result)
#         if not API_IMPORT_SUCCESS:
#             self.assertEqual(result["status"], "error")
        
#         # Test list_districts fallback
#         result = list_districts()
#         self.assertIn("status", result)
#         if not API_IMPORT_SUCCESS:
#             self.assertEqual(result["status"], "error")
        
#         # Test list_cities fallback
#         result = list_cities()
#         self.assertIn("status", result)
#         if not API_IMPORT_SUCCESS:
#             self.assertEqual(result["status"], "error")
        
#         # Test get_course_level_with_mapping fallback
#         result = get_course_level_with_mapping("5", "Math")
#         if not API_IMPORT_SUCCESS:
#             self.assertEqual(result, "COURSE_LEVEL_001")
        
#         # Test get_active_batch_for_school fallback
#         result = get_active_batch_for_school("SCHOOL_001")
#         if not API_IMPORT_SUCCESS:
#             self.assertEqual(result, "BATCH_001")

#     def test_exception_classes(self):
#         """Test all exception classes"""
        
#         # Test DoesNotExistError
#         with self.assertRaises(DoesNotExistError):
#             raise DoesNotExistError("Not found")
        
#         # Test ValidationError
#         with self.assertRaises(ValidationError):
#             raise ValidationError("Validation failed")
        
#         # Test DuplicateEntryError
#         with self.assertRaises(DuplicateEntryError):
#             raise DuplicateEntryError("Duplicate entry")

#     @patch('frappe.get_doc')
#     def test_authenticate_api_key_with_exceptions(self, mock_get_doc):
#         """Test authenticate_api_key with various exceptions"""
        
#         if not API_IMPORT_SUCCESS:
#             # Skip this test if import failed
#             return
            
#         # Test DoesNotExistError
#         mock_get_doc.side_effect = DoesNotExistError("Not found")
#         result = authenticate_api_key("invalid_key")
#         self.assertIsNone(result)
        
#         # Test general Exception
#         mock_get_doc.side_effect = Exception("Database error")
#         result = authenticate_api_key("error_key")
#         self.assertIsNone(result)

#     def test_functions_with_parameters(self):
#         """Test functions with different parameter combinations"""
        
#         # Test functions that take parameters
#         send_whatsapp_message("", "")  # Empty parameters
#         send_whatsapp_message("1234567890", "Test message")  # Valid parameters
        
#         authenticate_api_key("")  # Empty key
#         authenticate_api_key("valid_key")  # Valid key
        
#         get_teacher_by_glific_id("")  # Empty ID
#         get_teacher_by_glific_id("123")  # Valid ID
        
#         get_school_city("")  # Empty school
#         get_school_city("SCHOOL_001")  # Valid school
        
#         get_tap_language("")  # Empty code
#         get_tap_language("en")  # Valid code
        
#         determine_student_type("", "", "")  # Empty parameters
#         determine_student_type("1234567890", "John", "Science")  # Valid parameters
        
#         create_new_student()  # No parameters
#         create_new_student(phone="1234567890")  # With parameters
#         create_new_student(phone="1234567890", name="John", vertical="Science")  # Full parameters
        
#         get_course_level_with_mapping("", "")  # Empty parameters
#         get_course_level_with_mapping("5", "Math")  # Valid parameters
        
#         get_active_batch_for_school("")  # Empty school
#         get_active_batch_for_school("SCHOOL_001")  # Valid school


# class TestEdgeCasesAndBranches(unittest.TestCase):
#     """Test edge cases and ensure all branches are covered"""
    
#     def test_all_conditional_branches(self):
#         """Test to ensure all if/else branches are covered"""
        
#         # Test various scenarios that might have uncovered branches
        
#         # Test 1: Different data types
#         mock_frappe._dict(None)
#         mock_frappe._dict({})
#         mock_frappe._dict({"key": "value"})
#         mock_frappe._dict([])
#         mock_frappe._dict("string")
        
#         # Test 2: Exception handling
#         try:
#             mock_frappe.throw("Test error")
#         except Exception:
#             pass
        
#         # Test 3: Mock all possible method calls
#         mock_frappe.init()
#         mock_frappe.init("test_site")
#         mock_frappe.connect()
#         mock_frappe.set_user("test")
#         mock_frappe.set_user(None)
#         mock_frappe.destroy()
#         mock_frappe.log_error("error")
#         mock_frappe.log_error("error", "title")
#         mock_frappe.msgprint("message")
#         mock_frappe.msgprint("")
        
#         # Test 4: Test all get methods
#         mock_frappe.get_doc("DocType")
#         mock_frappe.get_doc("DocType", "name")
#         mock_frappe.new_doc("DocType")
#         mock_frappe.get_all("DocType")
#         mock_frappe.get_single("DocType")
#         mock_frappe.get_value("DocType", "name", "field")
    
#     def test_module_level_code(self):
#         """Test module-level code execution"""
        
#         # This should cover any module-level initialization code
#         self.assertIsNotNone(mock_frappe)
#         self.assertTrue('frappe' in sys.modules)
        
#         # Test that all sys.modules entries exist
#         self.assertTrue('frappe.utils' in sys.modules)
#         self.assertTrue('frappe.request' in sys.modules)
#         self.assertTrue('frappe.db' in sys.modules)
        
#         # Test the mock objects
#         self.assertIsNotNone(sys.modules['frappe'])
#         self.assertIsNotNone(sys.modules['frappe.utils'])
#         self.assertIsNotNone(sys.modules['frappe.request'])
#         self.assertIsNotNone(sys.modules['frappe.db'])

#     def test_import_error_scenario(self):
#         """Test the import error handling scenario"""
        
#         # This tests the except ImportError block
#         # The import either succeeds or fails, and we test both paths
        
#         if API_IMPORT_SUCCESS:
#             # If import succeeded, test that functions work
#             self.assertTrue(callable(verify_otp))
#             self.assertTrue(callable(create_student))
#             self.assertTrue(callable(send_otp))
#         else:
#             # If import failed, test fallback functions
#             result = verify_otp()
#             self.assertEqual(result["message"], "Module not imported")
            
#     def test_print_statement_coverage(self):
#         """Ensure print statements are executed for coverage"""
        
#         # The print statement in the ImportError except block
#         # This is covered by the import process itself
        
#         # Test that the import error message would be printed
#         if not API_IMPORT_SUCCESS:
#             # This path would have printed the import error
#             pass
        
#         # Ensure all code paths are hit
#         self.assertIsInstance(API_IMPORT_SUCCESS, bool)


# class TestFunctionReturnValues(unittest.TestCase):
#     """Test specific return values and edge cases"""
    
#     def test_specific_return_values(self):
#         """Test specific return values from functions"""
        
#         # Test get_current_academic_year specifically
#         result = get_current_academic_year()
#         self.assertIsInstance(result, str)
#         if not API_IMPORT_SUCCESS:
#             self.assertEqual(result, "2025-26")
        
#         # Test determine_student_type specifically
#         result = determine_student_type("123", "John", "Science")
#         self.assertIsInstance(result, str)
#         if not API_IMPORT_SUCCESS:
#             self.assertEqual(result, "New")
        
#         # Test get_course_level_with_mapping specifically
#         result = get_course_level_with_mapping("5", "Math")
#         self.assertIsInstance(result, str)
#         if not API_IMPORT_SUCCESS:
#             self.assertEqual(result, "COURSE_LEVEL_001")
        
#         # Test get_active_batch_for_school specifically  
#         result = get_active_batch_for_school("SCHOOL_001")
#         self.assertIsInstance(result, str)
#         if not API_IMPORT_SUCCESS:
#             self.assertEqual(result, "BATCH_001")
        
#         # Test send_whatsapp_message specifically
#         result = send_whatsapp_message("123", "message")
#         if not API_IMPORT_SUCCESS:
#             self.assertEqual(result, False)
        
#         # Test functions that return None
#         result = authenticate_api_key("key")
#         if not API_IMPORT_SUCCESS:
#             self.assertIsNone(result)
        
#         result = get_teacher_by_glific_id("id")
#         if not API_IMPORT_SUCCESS:
#             self.assertIsNone(result)
        
#         result = get_school_city("school")
#         if not API_IMPORT_SUCCESS:
#             self.assertIsNone(result)
        
#         result = get_tap_language("en")
#         if not API_IMPORT_SUCCESS:
#             self.assertIsNone(result)


# class TestAllCodePaths(unittest.TestCase):
#     """Comprehensive test to ensure 100% coverage"""
    
#     def test_import_success_true(self):
#         """Test when API_IMPORT_SUCCESS is True"""
#         if API_IMPORT_SUCCESS:
#             # Test that actual functions were imported
#             self.assertTrue(callable(verify_otp))
#             self.assertTrue(callable(create_student))
#             self.assertTrue(callable(send_otp))
#             # Add more assertions for successful import
    
#     def test_import_success_false(self):
#         """Test when API_IMPORT_SUCCESS is False"""
#         if not API_IMPORT_SUCCESS:
#             # Test that fallback functions work correctly
#             result = verify_otp()
#             self.assertEqual(result["status"], "error")
#             self.assertEqual(result["message"], "Module not imported")
    
#     def test_all_exception_classes_instantiation(self):
#         """Test that all exception classes can be instantiated"""
        
#         # Test with message
#         error1 = DoesNotExistError("Test message")
#         self.assertIsInstance(error1, Exception)
#         self.assertEqual(str(error1), "Test message")
        
#         error2 = ValidationError("Test validation")
#         self.assertIsInstance(error2, Exception) 
#         self.assertEqual(str(error2), "Test validation")
        
#         error3 = DuplicateEntryError("Test duplicate")
#         self.assertIsInstance(error3, Exception)
#         self.assertEqual(str(error3), "Test duplicate")
        
#         # Test without message
#         error4 = DoesNotExistError()
#         self.assertIsInstance(error4, Exception)
        
#         error5 = ValidationError()
#         self.assertIsInstance(error5, Exception)
        
#         error6 = DuplicateEntryError()
#         self.assertIsInstance(error6, Exception)

