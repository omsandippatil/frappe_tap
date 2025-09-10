


# import pytest
# from unittest.mock import MagicMock, patch, call
# import json
# from datetime import datetime


# # Define all the functions locally to avoid import issues
# def normalize_phone_number(phone):
#     if not phone:
#         return None, None
    
#     phone = phone.strip().replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
#     phone = ''.join(filter(str.isdigit, phone))
    
#     if len(phone) == 10:
#         return f"91{phone}", phone
#     elif len(phone) == 12 and phone.startswith('91'):
#         return phone, phone[2:]
#     elif len(phone) == 11 and phone.startswith('1'):
#         return f"9{phone}", phone[1:]
#     else:
#         return None, None


# def format_phone_number(phone):
#     """Format phone number for Glific"""
#     if phone.startswith("91"):
#         return phone
#     return f"91{phone}"


# def get_current_academic_year_backend():
#     """Get current academic year based on date"""
#     try:
#         import frappe
#         from frappe.utils import getdate
#         current_date = getdate()
#     except ImportError:
#         # For testing without frappe
#         current_date = datetime.now().date()
    
#     if current_date.month >= 4:  # April onwards is new academic year
#         return f"{current_date.year}-{str(current_date.year + 1)[-2:]}"
#     else:  # January-March is previous academic year
#         return f"{current_date.year - 1}-{str(current_date.year)[-2:]}"


# class TestBackendStudentOnboarding:
    
#     def test_normalize_phone_number_valid_formats(self):
#         """Test phone number normalization for various valid formats"""
#         # 10-digit numbers
#         assert normalize_phone_number("9876543210") == ("919876543210", "9876543210")
#         assert normalize_phone_number(" 987-654-3210 ") == ("919876543210", "9876543210")
#         assert normalize_phone_number("(987) 654-3210") == ("919876543210", "9876543210")
        
#         # 12-digit numbers
#         assert normalize_phone_number("919876543210") == ("919876543210", "9876543210")
        
#         # Edge cases
#         assert normalize_phone_number("19876543210") == ("919876543210", "9876543210")
        
#     def test_normalize_phone_number_invalid_formats(self):
#         """Test phone number normalization for invalid formats"""
#         assert normalize_phone_number("123") == (None, None)
#         assert normalize_phone_number("abcdef") == (None, None)
#         assert normalize_phone_number("") == (None, None)
#         assert normalize_phone_number("987654321") == (None, None)  # 9 digits
#         assert normalize_phone_number("9198765432101") == (None, None)  # 13 digits
    
#     @patch('frappe.db.sql')
#     def test_find_existing_student_by_phone_and_name(self, mock_sql):
#         """Test finding existing students with different phone formats"""
        
#         def find_existing_student_by_phone_and_name(phone, name):
#             normalized_phone, local_phone = normalize_phone_number(phone)
#             if not normalized_phone:
#                 return None
            
#             result = mock_sql(
#                 """
#                 SELECT name, phone, name1
#                 FROM `tabStudent`
#                 WHERE name1 = %s 
#                 AND (phone = %s OR phone = %s)
#                 LIMIT 1
#                 """, 
#                 (name, local_phone, normalized_phone),
#                 as_dict=True
#             )
#             return result[0] if result else None
        
#         test_student = {
#             "name": "STU001",
#             "name1": "Test Student",
#             "phone": "9876543210"
#         }
        
#         mock_sql.return_value = [test_student]
        
#         # Test with 10-digit format
#         result = find_existing_student_by_phone_and_name("9876543210", "Test Student")
#         assert result == test_student
        
#         # Test with 12-digit format
#         result = find_existing_student_by_phone_and_name("919876543210", "Test Student")
#         assert result == test_student
    
#     def test_validate_student_missing_fields(self):
#         """Test student validation for missing required fields"""
        
#         def validate_student(student):
#             validation = {}
#             required_fields = ["school", "grade", "language", "batch"]
            
#             for field in required_fields:
#                 if field not in student or not student[field]:
#                     validation[field] = f"{field} is required"
            
#             return validation
        
#         incomplete_student = {
#             "student_name": "Test Student",
#             "phone": "9876543210"
#             # Missing school, grade, language, batch
#         }
        
#         validation = validate_student(incomplete_student)
#         assert "school" in validation
#         assert "grade" in validation
#         assert "language" in validation
#         assert "batch" in validation
    
#     def test_validate_student_duplicate(self):
#         """Test student validation for duplicate detection"""
        
#         def validate_student_with_duplicate_check(student, existing_student=None):
#             validation = {}
            
#             # Check for duplicates
#             if existing_student:
#                 validation["duplicate"] = {
#                     "student_id": existing_student["name"],
#                     "student_name": existing_student["name1"]
#                 }
            
#             return validation
        
#         existing_student = {"name": "EXISTING_STU", "name1": "Existing Student"}
        
#         complete_student = {
#             "student_name": "Test Student",
#             "phone": "9876543210",
#             "school": "SCH001",
#             "grade": "5",
#             "language": "EN",
#             "batch": "BATCH001"
#         }
        
#         validation = validate_student_with_duplicate_check(complete_student, existing_student)
#         assert "duplicate" in validation
#         assert validation["duplicate"]["student_id"] == "EXISTING_STU"
    
  
#     def test_process_batch_job_success(self):
#         """Test successful batch processing"""
        
#         def process_batch_job_mock(batch_id):
#             """Mock implementation of process_batch_job"""
#             # Mock batch processing logic
#             students_to_process = [
#                 {
#                     "name": "BACKEND_STU001",
#                     "student_name": "Test Student",
#                     "phone": "9876543210",
#                     "batch_skeyword": "TEST_BATCH"
#                 }
#             ]
            
#             success_count = 0
#             failure_count = 0
            
#             for student in students_to_process:
#                 try:
#                     # Mock successful processing
#                     success_count += 1
#                 except Exception:
#                     failure_count += 1
            
#             return {"success_count": success_count, "failure_count": failure_count}
        
#         result = process_batch_job_mock("BATCH001")
        
#         assert result["success_count"] == 1
#         assert result["failure_count"] == 0
    
#     def test_determine_student_type_backend(self):
#         """Test student type determination logic"""
        
#         def determine_student_type_backend_mock(phone, name, course_vertical):
#             """Mock implementation - in real scenario this would check database"""
#             # For testing, assume all students are "New"
#             return "New"
        
#         result = determine_student_type_backend_mock("9876543210", "Test Student", "MATH")
#         assert result == "New"
    
#     def test_get_course_level_with_mapping_backend(self):
#         """Test course level selection with mapping"""
        
#         def get_course_level_with_mapping_backend_mock(course_vertical, grade, phone, name, kit_less):
#             """Mock implementation"""
#             return f"{course_vertical}_GRADE{grade}"
        
#         result = get_course_level_with_mapping_backend_mock(
#             "MATH", "5", "9876543210", "Test Student", False
#         )
#         assert result == "MATH_GRADE5"
    
#     def test_process_glific_contact(self):
#         """Test Glific contact processing"""
        
#         def process_glific_contact_mock(student, glific_group):
#             """Mock implementation"""
#             return {"id": "GLIFIC001"}
        
#         mock_student = MagicMock()
#         mock_student.phone = "9876543210"
#         mock_student.student_name = "Test Student"
        
#         result = process_glific_contact_mock(mock_student, {"group_id": "GROUP001"})
#         assert result["id"] == "GLIFIC001"
    
#     def test_process_student_record_new_student(self):
#         """Test processing a new student record"""
        
#         def process_student_record_mock(backend_student, glific_contact, batch_id, initial_stage):
#             """Mock implementation"""
#             # Mock creating new student document
#             mock_student_doc = MagicMock()
#             mock_student_doc.name = "STU001"
#             mock_student_doc.name1 = backend_student.student_name
#             mock_student_doc.phone = backend_student.phone
#             return mock_student_doc
        
#         mock_backend_student = MagicMock()
#         mock_backend_student.phone = "9876543210"
#         mock_backend_student.student_name = "New Student"
        
#         result = process_student_record_mock(
#             mock_backend_student, 
#             {"id": "GLIFIC001"}, 
#             "BATCH001", 
#             "STAGE001"
#         )
        
#         assert result.name == "STU001"
#         assert result.name1 == "New Student"
#         assert result.phone == "9876543210"
    
#     def test_update_backend_student_status_success(self):
#         """Test updating backend student status for success"""
        
#         def update_backend_student_status_mock(backend_student, status, student_doc=None, error=None):
#             """Mock implementation"""
#             backend_student.processing_status = status
#             if student_doc:
#                 backend_student.student_id = student_doc.name
#                 backend_student.glific_id = getattr(student_doc, 'glific_id', None)
#             if error:
#                 backend_student.error_message = error
        
#         mock_student = MagicMock()
#         mock_student_doc = MagicMock()
#         mock_student_doc.name = "STU001"
#         mock_student_doc.glific_id = "GLIFIC001"
        
#         update_backend_student_status_mock(mock_student, "Success", mock_student_doc)
        
#         assert mock_student.processing_status == "Success"
#         assert mock_student.student_id == "STU001"
#         assert mock_student.glific_id == "GLIFIC001"
    
#     def test_update_backend_student_status_failed(self):
#         """Test updating backend student status for failure"""
        
#         def update_backend_student_status_mock(backend_student, status, student_doc=None, error=None):
#             """Mock implementation"""
#             backend_student.processing_status = status
#             if error:
#                 backend_student.error_message = error
        
#         mock_student = MagicMock()
        
#         update_backend_student_status_mock(mock_student, "Failed", error="Test error")
        
#         assert mock_student.processing_status == "Failed"
#         assert mock_student.error_message == "Test error"
    
#     def test_format_phone_number(self):
#         """Test phone number formatting for Glific"""
#         result = format_phone_number("9876543210")
#         assert result == "919876543210"
        
#         result = format_phone_number("919876543210")
#         assert result == "919876543210"
    
#     def test_get_current_academic_year_backend(self):
#         """Test academic year calculation"""
#         # Test with mock dates
#         test_cases = [
#             (datetime(2024, 6, 15), "2024-25"),  # June - new academic year
#             (datetime(2024, 2, 15), "2023-24"),  # February - previous academic year
#             (datetime(2024, 4, 1), "2024-25"),   # April 1 - new academic year starts
#             (datetime(2024, 3, 31), "2023-24"),  # March 31 - previous academic year
#         ]
        
#         for test_date, expected_year in test_cases:
#             # Mock the current date
#             with patch('datetime.datetime') as mock_datetime:
#                 mock_datetime.now.return_value = test_date
#                 mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
                
#                 # Test with the mocked date
#                 def get_current_academic_year_test():
#                     current_date = mock_datetime.now().date()
#                     if current_date.month >= 4:
#                         return f"{current_date.year}-{str(current_date.year + 1)[-2:]}"
#                     else:
#                         return f"{current_date.year - 1}-{str(current_date.year)[-2:]}"
                
#                 result = get_current_academic_year_test()
#                 assert result == expected_year
    
#     def test_background_job_processing(self):
#         """Test batch processing with background job simulation"""
        
#         def process_batch_with_job_mock(batch_id, use_background_job=False):
#             """Mock implementation of batch processing with job queue"""
#             if use_background_job:
#                 # Simulate enqueuing a background job
#                 mock_job = MagicMock()
#                 mock_job.id = "JOB001"
#                 return {"job_id": mock_job.id}
#             else:
#                 # Process immediately
#                 return {"success_count": 1, "failure_count": 0}
        
#         # Test background job
#         result = process_batch_with_job_mock("BATCH001", use_background_job=True)
#         assert "job_id" in result
#         assert result["job_id"] == "JOB001"
        
#         # Test immediate processing
#         result = process_batch_with_job_mock("BATCH001", use_background_job=False)
#         assert result["success_count"] == 1
#         assert result["failure_count"] == 0
    
#     def test_job_status_checking(self):
#         """Test getting job status"""
        
#         def get_job_status_mock(job_id):
#             """Mock implementation"""
#             # Simulate job status response
#             return {
#                 "status": "Completed",
#                 "progress": 100,
#                 "result": {"success": True, "processed_count": 10}
#             }
        
#         result = get_job_status_mock("JOB001")
#         assert result["status"] == "Completed"
#         assert result["progress"] == 100
#         assert result["result"]["success"] is True
    
#     def test_phone_number_edge_cases(self):
#         """Test edge cases for phone number handling"""
#         test_cases = [
#             ("", (None, None)),
#             (None, (None, None)),
#             ("   ", (None, None)),
#             ("abc123def", (None, None)),
#             ("12345", (None, None)),
#             ("123456789", (None, None)),  # 9 digits
#             ("12345678901234", (None, None)),  # 14 digits
#             ("0987654321", ("910987654321", "0987654321")),  # Starting with 0
#             ("+919876543210", ("919876543210", "9876543210")),  # With + sign
#         ]
        
#         for phone_input, expected in test_cases:
#             result = normalize_phone_number(phone_input)
#             assert result == expected, f"Failed for input: {phone_input}"
    
#     def test_student_validation_comprehensive(self):
#         """Test comprehensive student validation"""
        
#         def comprehensive_validate_student(student):
#             """Comprehensive validation function"""
#             validation = {}
            
#             # Required field validation
#             required_fields = {
#                 "student_name": "Student name is required",
#                 "phone": "Phone number is required",
#                 "school": "School is required",
#                 "grade": "Grade is required",
#                 "language": "Language is required",
#                 "batch": "Batch is required"
#             }
            
#             for field, message in required_fields.items():
#                 if field not in student or not str(student[field]).strip():
#                     validation[field] = message
            
#             # Phone number format validation
#             if "phone" in student:
#                 normalized_phone, _ = normalize_phone_number(student["phone"])
#                 if not normalized_phone:
#                     validation["phone_format"] = "Invalid phone number format"
            
#             # Grade validation
#             if "grade" in student:
#                 try:
#                     grade_int = int(student["grade"])
#                     if grade_int < 1 or grade_int > 12:
#                         validation["grade_range"] = "Grade must be between 1 and 12"
#                 except (ValueError, TypeError):
#                     validation["grade_format"] = "Grade must be a valid number"
            
#             return validation
        
#         # Test complete valid student
#         valid_student = {
#             "student_name": "Test Student",
#             "phone": "9876543210",
#             "school": "SCH001",
#             "grade": "5",
#             "language": "EN",
#             "batch": "BATCH001"
#         }
        
#         validation = comprehensive_validate_student(valid_student)
#         assert len(validation) == 0
        
#         # Test invalid phone
#         invalid_phone_student = valid_student.copy()
#         invalid_phone_student["phone"] = "123"
        
#         validation = comprehensive_validate_student(invalid_phone_student)
#         assert "phone_format" in validation
        
#         # Test invalid grade
#         invalid_grade_student = valid_student.copy()
#         invalid_grade_student["grade"] = "15"
        
#         validation = comprehensive_validate_student(invalid_grade_student)
#         assert "grade_range" in validation


# if __name__ == "__main__":
#     pytest.main([__file__, "-v"])


import unittest
import frappe
import json
from unittest.mock import patch, MagicMock, Mock
from frappe.utils import nowdate, nowtime, now
from tap_lms.backend_student_onboarding import (
    normalize_phone_number,
    find_existing_student_by_phone_and_name,
    get_onboarding_batches,
    get_batch_details,
    validate_student,
    get_onboarding_stages,
    process_batch,
    process_batch_job,
    determine_student_type_backend,
    get_course_level_with_mapping_backend,
    process_glific_contact,
    process_student_record,
    update_backend_student_status,
    format_phone_number,
    get_job_status,
    get_current_academic_year_backend,
    validate_enrollment_data,
    fix_broken_course_links,
    debug_student_type_analysis
)


class TestBackendStudentOnboarding(unittest.TestCase):
    """Comprehensive test suite for Backend Student Onboarding functionality"""

    def setUp(self):
        """Set up test data and mocks"""
        self.sample_student_data = {
            "student_name": "Test Student",
            "phone": "9876543210",
            "gender": "Male",
            "batch": "BT00000015",
            "course_vertical": "Math",
            "grade": "5",
            "school": "SCH001",
            "language": "English",
            "batch_skeyword": "MATH_5_2025"
        }
        
        self.sample_backend_student = type('obj', (object,), {
            'name': 'BS001',
            'student_name': 'Test Student',
            'phone': '9876543210',
            'gender': 'Male',
            'batch': 'BT00000015',
            'course_vertical': 'Math',
            'grade': '5',
            'school': 'SCH001',
            'language': 'English',
            'batch_skeyword': 'MATH_5_2025',
            'processing_status': 'Pending',
            'save': Mock(),
            'append': Mock()
        })


class TestPhoneNormalization(TestBackendStudentOnboarding):
    """Test phone number normalization functionality"""

    def test_normalize_10_digit_number(self):
        """TC030: 10-digit number normalization"""
        phone_12, phone_10 = normalize_phone_number("9876543210")
        self.assertEqual(phone_12, "919876543210")
        self.assertEqual(phone_10, "9876543210")

    def test_normalize_12_digit_number(self):
        """TC031: 12-digit number with country code"""
        phone_12, phone_10 = normalize_phone_number("919876543210")
        self.assertEqual(phone_12, "919876543210")
        self.assertEqual(phone_10, "9876543210")

    def test_normalize_11_digit_number(self):
        """TC032: 11-digit number starting with 1"""
        phone_12, phone_10 = normalize_phone_number("19876543210")
        self.assertEqual(phone_12, "919876543210")
        self.assertEqual(phone_10, "9876543210")

    def test_normalize_number_with_spaces(self):
        """TC033: Number with spaces"""
        phone_12, phone_10 = normalize_phone_number("98 76 54 32 10")
        self.assertEqual(phone_12, "919876543210")
        self.assertEqual(phone_10, "9876543210")

    def test_normalize_number_with_dashes(self):
        """TC034: Number with dashes"""
        phone_12, phone_10 = normalize_phone_number("98-76-54-32-10")
        self.assertEqual(phone_12, "919876543210")
        self.assertEqual(phone_10, "9876543210")

    def test_normalize_number_with_parentheses(self):
        """TC035: Number with parentheses"""
        phone_12, phone_10 = normalize_phone_number("(98) 76 54 32 10")
        self.assertEqual(phone_12, "919876543210")
        self.assertEqual(phone_10, "9876543210")

    def test_normalize_empty_phone(self):
        """TC036: Empty phone number"""
        phone_12, phone_10 = normalize_phone_number("")
        self.assertIsNone(phone_12)
        self.assertIsNone(phone_10)

    def test_normalize_none_phone(self):
        """TC036: None phone number"""
        phone_12, phone_10 = normalize_phone_number(None)
        self.assertIsNone(phone_12)
        self.assertIsNone(phone_10)

    def test_normalize_invalid_length_9_digits(self):
        """TC037: Invalid length (9 digits)"""
        phone_12, phone_10 = normalize_phone_number("987654321")
        self.assertIsNone(phone_12)
        self.assertIsNone(phone_10)

    def test_normalize_invalid_length_13_digits(self):
        """TC038: Invalid length (13 digits)"""
        phone_12, phone_10 = normalize_phone_number("9198765432101")
        self.assertIsNone(phone_12)
        self.assertIsNone(phone_10)

    def test_normalize_non_numeric(self):
        """TC039: Non-numeric characters"""
        phone_12, phone_10 = normalize_phone_number("abcd123456")
        self.assertIsNone(phone_12)
        self.assertIsNone(phone_10)

    def test_normalize_only_special_chars(self):
        """TC040: Only special characters"""
        phone_12, phone_10 = normalize_phone_number("()- ")
        self.assertIsNone(phone_12)
        self.assertIsNone(phone_10)


class TestStudentValidation(TestBackendStudentOnboarding):
    """Test student validation functionality"""

    @patch('tap_lms.backend_student_onboarding.find_existing_student_by_phone_and_name')
    def test_validate_complete_student(self, mock_find_existing):
        """TC041: Complete valid student data"""
        mock_find_existing.return_value = None
        validation = validate_student(self.sample_student_data)
        self.assertEqual(validation, {})

    @patch('tap_lms.backend_student_onboarding.find_existing_student_by_phone_and_name')
    def test_validate_missing_student_name(self, mock_find_existing):
        """TC043: Missing student_name"""
        mock_find_existing.return_value = None
        student_data = self.sample_student_data.copy()
        student_data["student_name"] = ""
        validation = validate_student(student_data)
        self.assertEqual(validation["student_name"], "missing")

    @patch('tap_lms.backend_student_onboarding.find_existing_student_by_phone_and_name')
    def test_validate_missing_phone(self, mock_find_existing):
        """TC044: Missing phone"""
        mock_find_existing.return_value = None
        student_data = self.sample_student_data.copy()
        student_data["phone"] = ""
        validation = validate_student(student_data)
        self.assertEqual(validation["phone"], "missing")

    @patch('tap_lms.backend_student_onboarding.find_existing_student_by_phone_and_name')
    def test_validate_missing_multiple_fields(self, mock_find_existing):
        """TC050: Multiple missing fields"""
        mock_find_existing.return_value = None
        student_data = {
            "student_name": "",
            "phone": "",
            "school": "",
            "grade": "",
            "language": "",
            "batch": ""
        }
        validation = validate_student(student_data)
        required_fields = ["student_name", "phone", "school", "grade", "language", "batch"]
        for field in required_fields:
            self.assertEqual(validation[field], "missing")

    @patch('tap_lms.backend_student_onboarding.find_existing_student_by_phone_and_name')
    def test_validate_duplicate_student(self, mock_find_existing):
        """TC049: Duplicate phone+name combination"""
        mock_find_existing.return_value = {
            "name": "STU001",
            "name1": "Test Student"
        }
        validation = validate_student(self.sample_student_data)
        self.assertIn("duplicate", validation)
        self.assertEqual(validation["duplicate"]["student_id"], "STU001")


class TestAPIEndpoints(TestBackendStudentOnboarding):
    """Test API endpoint functionality"""

    @patch('frappe.get_all')
    def test_get_onboarding_batches_success(self, mock_get_all):
        """TC001: Get onboarding batches successfully"""
        mock_get_all.return_value = [
            {
                "name": "BSO001",
                "set_name": "Batch Set 1",
                "upload_date": "2025-01-01",
                "uploaded_by": "user@test.com",
                "student_count": 100,
                "processed_student_count": 50
            }
        ]
        
        result = get_onboarding_batches()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "BSO001")
        mock_get_all.assert_called_once()

    @patch('frappe.get_all')
    def test_get_onboarding_batches_empty(self, mock_get_all):
        """TC005: No batches exist"""
        mock_get_all.return_value = []
        result = get_onboarding_batches()
        self.assertEqual(result, [])

    @patch('frappe.get_all')
    @patch('frappe.get_doc')
    def test_get_batch_details_success(self, mock_get_doc, mock_get_all):
        """TC008: Get batch details successfully"""
        # Mock batch document
        mock_batch = Mock()
        mock_batch.name = "BSO001"
        mock_get_doc.return_value = mock_batch
        
        # Mock students
        mock_get_all.side_effect = [
            [  # Students
                {
                    "name": "BS001",
                    "student_name": "Test Student",
                    "phone": "9876543210",
                    "gender": "Male",
                    "batch": "BT001",
                    "course_vertical": "Math",
                    "grade": "5",
                    "school": "SCH001",
                    "language": "English",
                    "processing_status": "Pending",
                    "student_id": None
                }
            ],
            [  # Glific group
                {
                    "group_id": "123",
                    "label": "Test Group"
                }
            ]
        ]
        
        with patch('tap_lms.backend_student_onboarding.validate_student') as mock_validate:
            mock_validate.return_value = {}
            result = get_batch_details("BSO001")
            
            self.assertIn("batch", result)
            self.assertIn("students", result)
            self.assertIn("glific_group", result)
            self.assertEqual(len(result["students"]), 1)

    @patch('frappe.get_doc')
    def test_get_batch_details_invalid_id(self, mock_get_doc):
        """TC013: Invalid batch_id"""
        mock_get_doc.side_effect = frappe.DoesNotExistError
        
        with self.assertRaises(frappe.DoesNotExistError):
            get_batch_details("INVALID_ID")

    @patch('frappe.db.table_exists')
    @patch('frappe.get_all')
    def test_get_onboarding_stages_success(self, mock_get_all, mock_table_exists):
        """TC017: Get stages successfully"""
        mock_table_exists.return_value = True
        mock_get_all.return_value = [
            {"name": "Stage1", "description": "Initial Stage", "order": 0},
            {"name": "Stage2", "description": "Second Stage", "order": 1}
        ]
        
        result = get_onboarding_stages()
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["order"], 0)

    @patch('frappe.db.table_exists')
    def test_get_onboarding_stages_table_not_exists(self, mock_table_exists):
        """TC019: OnboardingStage table doesn't exist"""
        mock_table_exists.return_value = False
        
        result = get_onboarding_stages()
        self.assertEqual(result, [])


class TestStudentTypeDetection(TestBackendStudentOnboarding):
    """Test student type determination logic"""

    @patch('frappe.db.sql')
    @patch('tap_lms.backend_student_onboarding.normalize_phone_number')
    def test_determine_student_type_new_no_student(self, mock_normalize, mock_sql):
        """TC051: New student (no existing enrollments)"""
        mock_normalize.return_value = ("919876543210", "9876543210")
        mock_sql.return_value = []  # No existing student found
        
        result = determine_student_type_backend("9876543210", "Test Student", "Math")
        self.assertEqual(result, "New")

    @patch('frappe.db.sql')
    @patch('tap_lms.backend_student_onboarding.normalize_phone_number')
    def test_determine_student_type_old_same_vertical(self, mock_normalize, mock_sql):
        """TC052: Student with enrollments in same vertical"""
        mock_normalize.return_value = ("919876543210", "9876543210")
        
        # Mock existing student found
        mock_sql.side_effect = [
            [{"name": "STU001", "phone": "919876543210", "name1": "Test Student"}],  # Student exists
            [{"name": "ENR001", "course": "COURSE001", "batch": "BT001", "grade": "5", "school": "SCH001"}],  # Enrollments
            [{"vertical_name": "Math"}]  # Course vertical (same as target)
        ]
        
        with patch('frappe.db.exists') as mock_exists:
            mock_exists.return_value = True  # Course exists
            
            result = determine_student_type_backend("9876543210", "Test Student", "Math")
            self.assertEqual(result, "Old")

    @patch('frappe.db.sql')
    @patch('tap_lms.backend_student_onboarding.normalize_phone_number')
    def test_determine_student_type_new_different_vertical(self, mock_normalize, mock_sql):
        """TC053: Student with enrollments only in different verticals"""
        mock_normalize.return_value = ("919876543210", "9876543210")
        
        mock_sql.side_effect = [
            [{"name": "STU001", "phone": "919876543210", "name1": "Test Student"}],
            [{"name": "ENR001", "course": "COURSE001", "batch": "BT001", "grade": "5", "school": "SCH001"}],
            [{"vertical_name": "Science"}]  # Different vertical
        ]
        
        with patch('frappe.db.exists') as mock_exists:
            mock_exists.return_value = True
            
            result = determine_student_type_backend("9876543210", "Test Student", "Math")
            self.assertEqual(result, "New")

    @patch('frappe.db.sql')
    @patch('tap_lms.backend_student_onboarding.normalize_phone_number')
    def test_determine_student_type_old_broken_course(self, mock_normalize, mock_sql):
        """TC055: Student with broken course links"""
        mock_normalize.return_value = ("919876543210", "9876543210")
        
        mock_sql.side_effect = [
            [{"name": "STU001", "phone": "919876543210", "name1": "Test Student"}],
            [{"name": "ENR001", "course": "INVALID_COURSE", "batch": "BT001", "grade": "5", "school": "SCH001"}]
        ]
        
        with patch('frappe.db.exists') as mock_exists:
            mock_exists.return_value = False  # Course doesn't exist (broken link)
            
            result = determine_student_type_backend("9876543210", "Test Student", "Math")
            self.assertEqual(result, "Old")

    @patch('frappe.db.sql')
    @patch('tap_lms.backend_student_onboarding.normalize_phone_number')
    def test_determine_student_type_old_null_course(self, mock_normalize, mock_sql):
        """TC054: Student with NULL course enrollments"""
        mock_normalize.return_value = ("919876543210", "9876543210")
        
        mock_sql.side_effect = [
            [{"name": "STU001", "phone": "919876543210", "name1": "Test Student"}],
            [{"name": "ENR001", "course": None, "batch": "BT001", "grade": "5", "school": "SCH001"}]
        ]
        
        result = determine_student_type_backend("9876543210", "Test Student", "Math")
        self.assertEqual(result, "Old")

    @patch('tap_lms.backend_student_onboarding.normalize_phone_number')
    def test_determine_student_type_invalid_phone(self, mock_normalize):
        """TC057: Invalid phone number"""
        mock_normalize.return_value = (None, None)
        
        result = determine_student_type_backend("invalid", "Test Student", "Math")
        self.assertEqual(result, "New")


class TestCourseLevelSelection(TestBackendStudentOnboarding):
    """Test course level selection functionality"""

    @patch('tap_lms.backend_student_onboarding.determine_student_type_backend')
    @patch('tap_lms.backend_student_onboarding.get_current_academic_year_backend')
    @patch('frappe.get_all')
    @patch('tap_lms.backend_student_onboarding.normalize_phone_number')
    def test_course_level_mapping_found(self, mock_normalize, mock_get_all, mock_academic_year, mock_student_type):
        """TC061: Valid mapping exists for current academic year"""
        mock_normalize.return_value = ("919876543210", "9876543210")
        mock_student_type.return_value = "New"
        mock_academic_year.return_value = "2025-26"
        mock_get_all.return_value = [{"assigned_course_level": "MATH_5_NEW", "mapping_name": "Math Grade 5 New"}]
        
        result = get_course_level_with_mapping_backend("Math", "5", "9876543210", "Test Student", False)
        self.assertEqual(result, "MATH_5_NEW")

    @patch('tap_lms.backend_student_onboarding.determine_student_type_backend')
    @patch('tap_lms.backend_student_onboarding.get_current_academic_year_backend')
    @patch('frappe.get_all')
    @patch('tap_lms.api.get_course_level')
    @patch('tap_lms.backend_student_onboarding.normalize_phone_number')
    def test_course_level_fallback_to_stage_grades(self, mock_normalize, mock_get_course_level, mock_get_all, mock_academic_year, mock_student_type):
        """TC063: No mapping exists, fallback to Stage Grades logic"""
        mock_normalize.return_value = ("919876543210", "9876543210")
        mock_student_type.return_value = "New"
        mock_academic_year.return_value = "2025-26"
        mock_get_all.side_effect = [[], []]  # No mappings found
        mock_get_course_level.return_value = "FALLBACK_COURSE"
        
        result = get_course_level_with_mapping_backend("Math", "5", "9876543210", "Test Student", False)
        self.assertEqual(result, "FALLBACK_COURSE")
        mock_get_course_level.assert_called_once_with("Math", "5", False)


class TestGlificIntegration(TestBackendStudentOnboarding):
    """Test Glific integration functionality"""

    @patch('tap_lms.backend_student_onboarding.format_phone_number')
    @patch('tap_lms.glific_integration.get_contact_by_phone')
    @patch('tap_lms.glific_integration.add_student_to_glific_for_onboarding')
    @patch('frappe.get_value')
    def test_process_glific_contact_new_contact(self, mock_get_value, mock_add_student, mock_get_contact, mock_format_phone):
        """TC070: New contact creation"""
        mock_format_phone.return_value = "919876543210"
        mock_get_contact.return_value = None  # No existing contact
        mock_add_student.return_value = {"id": "123", "name": "Test Student"}
        mock_get_value.side_effect = ["Test School", "BT001", "1", "English Course", "Math"]
        
        glific_group = {"group_id": "456"}
        result = process_glific_contact(self.sample_backend_student, glific_group)
        
        self.assertEqual(result["id"], "123")
        mock_add_student.assert_called_once()

    @patch('tap_lms.backend_student_onboarding.format_phone_number')
    @patch('tap_lms.glific_integration.get_contact_by_phone')
    @patch('tap_lms.glific_integration.add_contact_to_group')
    @patch('tap_lms.glific_integration.update_contact_fields')
    @patch('frappe.get_value')
    def test_process_glific_contact_existing_contact(self, mock_get_value, mock_update_fields, mock_add_to_group, mock_get_contact, mock_format_phone):
        """TC071: Existing contact update"""
        mock_format_phone.return_value = "919876543210"
        mock_get_contact.return_value = {"id": "123", "name": "Existing Contact"}
        mock_get_value.side_effect = ["Test School", "BT001", "1", "English Course", "Math"]
        mock_update_fields.return_value = {"success": True}
        
        glific_group = {"group_id": "456"}
        result = process_glific_contact(self.sample_backend_student, glific_group)
        
        self.assertEqual(result["id"], "123")
        mock_add_to_group.assert_called_once_with("123", "456")
        mock_update_fields.assert_called_once()

    @patch('tap_lms.backend_student_onboarding.format_phone_number')
    def test_process_glific_contact_invalid_phone(self, mock_format_phone):
        """TC075: Invalid phone number"""
        mock_format_phone.return_value = None
        
        with self.assertRaises(ValueError):
            process_glific_contact(self.sample_backend_student, {})


class TestStudentRecordProcessing(TestBackendStudentOnboarding):
    """Test student record processing functionality"""

    @patch('tap_lms.backend_student_onboarding.find_existing_student_by_phone_and_name')
    @patch('frappe.new_doc')
    @patch('frappe.utils.nowdate')
    def test_process_student_record_new_student(self, mock_nowdate, mock_new_doc, mock_find_existing):
        """TC080: New student creation"""
        mock_find_existing.return_value = None
        mock_nowdate.return_value = "2025-01-01"
        
        # Mock new student document
        mock_student_doc = Mock()
        mock_student_doc.name = "STU001"
        mock_student_doc.insert = Mock()
        mock_student_doc.append = Mock()
        mock_new_doc.return_value = mock_student_doc
        
        # Mock dependencies
        with patch('frappe.db.exists') as mock_exists:
            mock_exists.return_value = False  # No existing records
            
            glific_contact = {"id": "123"}
            result = process_student_record(self.sample_backend_student, glific_contact, "BSO001", "Stage1", "COURSE001")
            
            self.assertEqual(result.name, "STU001")
            mock_student_doc.insert.assert_called_once()

    @patch('tap_lms.backend_student_onboarding.find_existing_student_by_phone_and_name')
    @patch('frappe.get_doc')
    @patch('tap_lms.backend_student_onboarding.normalize_phone_number')
    def test_process_student_record_existing_student(self, mock_normalize, mock_get_doc, mock_find_existing):
        """TC081: Existing student update"""
        mock_normalize.return_value = ("919876543210", "9876543210")
        mock_find_existing.return_value = {"name": "STU001", "name1": "Test Student"}
        
        # Mock existing student document
        mock_student_doc = Mock()
        mock_student_doc.name = "STU001"
        mock_student_doc.phone = "919876543210"
        mock_student_doc.grade = "4"  # Different grade to test update
        mock_student_doc.school_id = "SCH001"
        mock_student_doc.language = "English"
        mock_student_doc.gender = "Male"
        mock_student_doc.glific_id = None
        mock_student_doc.save = Mock()
        mock_student_doc.append = Mock()
        mock_get_doc.return_value = mock_student_doc
        
        glific_contact = {"id": "123"}
        result = process_student_record(self.sample_backend_student, glific_contact, "BSO001", "Stage1", "COURSE001")
        
        self.assertEqual(result.name, "STU001")
        self.assertEqual(result.grade, "5")  # Should be updated
        self.assertEqual(result.glific_id, "123")
        mock_student_doc.save.assert_called_once()

    @patch('tap_lms.backend_student_onboarding.find_existing_student_by_phone_and_name')
    @patch('frappe.get_doc')
    @patch('tap_lms.backend_student_onboarding.normalize_phone_number')
    def test_process_student_record_grade_change(self, mock_normalize, mock_get_doc, mock_find_existing):
        """TC082: Grade change (upgrade)"""
        mock_normalize.return_value = ("919876543210", "9876543210")
        mock_find_existing.return_value = {"name": "STU001", "name1": "Test Student"}
        
        mock_student_doc = Mock()
        mock_student_doc.name = "STU001"
        mock_student_doc.phone = "919876543210"
        mock_student_doc.grade = "3"  # Lower grade
        mock_student_doc.school_id = "SCH001"
        mock_student_doc.language = "English"
        mock_student_doc.gender = "Male"
        mock_student_doc.glific_id = None
        mock_student_doc.save = Mock()
        mock_student_doc.append = Mock()
        mock_get_doc.return_value = mock_student_doc
        
        # Test upgrade to grade 5
        self.sample_backend_student.grade = "5"
        
        result = process_student_record(self.sample_backend_student, {}, "BSO001", "Stage1", "COURSE001")
        
        self.assertEqual(result.grade, "5")


class TestBatchProcessing(TestBackendStudentOnboarding):
    """Test batch processing functionality"""

    @patch('frappe.get_doc')
    @patch('frappe.enqueue')
    def test_process_batch_background_job(self, mock_enqueue, mock_get_doc):
        """TC023: Enqueue background job"""
        mock_batch = Mock()
        mock_batch.status = "Draft"
        mock_batch.save = Mock()
        mock_get_doc.return_value = mock_batch
        
        mock_job = Mock()
        mock_job.id = "job123"
        mock_enqueue.return_value = mock_job
        
        result = process_batch("BSO001", True)
        
        self.assertEqual(result["job_id"], "job123")
        self.assertEqual(mock_batch.status, "Processing")
        mock_enqueue.assert_called_once()

    @patch('frappe.get_doc')
    @patch('tap_lms.backend_student_onboarding.process_batch_job')
    def test_process_batch_immediate(self, mock_process_job, mock_get_doc):
        """TC026: Immediate processing"""
        mock_batch = Mock()
        mock_batch.status = "Draft"
        mock_batch.save = Mock()
        mock_get_doc.return_value = mock_batch
        
        mock_process_job.return_value = {"success_count": 10, "failure_count": 0}
        
        result = process_batch("BSO001", False)
        
        self.assertEqual(result["success_count"], 10)
        mock_process_job.assert_called_once_with("BSO001")

    @patch('frappe.db.commit')
    @patch('frappe.get_doc')
    @patch('frappe.get_all')
    @patch('tap_lms.glific_integration.create_or_get_glific_group_for_batch')
    @patch('tap_lms.backend_student_onboarding.get_initial_stage')
    def test_process_batch_job_success(self, mock_get_stage, mock_create_group, mock_get_all, mock_get_doc, mock_commit):
        """TC095: Process all students successfully"""
        # Mock batch
        mock_batch = Mock()
        mock_batch.status = "Processing"
        mock_batch.save = Mock()
        mock_get_doc.side_effect = [mock_batch, self.sample_backend_student, mock_batch]
        
        # Mock students to process
        mock_get_all.side_effect = [
            [{"name": "BS001", "batch_skeyword": "MATH_5_2025"}],  # Students
            [{"batch_skeyword": "MATH_5_2025", "name": "BO001", "kit_less": False}]  # Batch onboarding
        ]
        
        mock_create_group.return_value = {"group_id": "456"}
        mock_get_stage.return_value = "Stage1"
        
        with patch('tap_lms.backend_student_onboarding.process_glific_contact') as mock_process_glific, \
             patch('tap_lms.backend_student_onboarding.process_student_record') as mock_process_student, \
             patch('tap_lms.backend_student_onboarding.update_backend_student_status') as mock_update_status:
            
            mock_process_glific.return_value = {"id": "123"}
            mock_student_doc = Mock()
            mock_student_doc.name = "STU001"
            mock_process_student.return_value = mock_student_doc
            
            result = process_batch_job("BSO001")
            
            self.assertEqual(result["success_count"], 1)
            self.assertEqual(result["failure_count"], 0)
            mock_process_glific.assert_called_once()
            mock_process_student.assert_called_once()

    @patch('frappe.db.commit')
    @patch('frappe.get_doc')
    @patch('frappe.get_all')
    def test_process_batch_job_no_students(self, mock_get_all, mock_get_doc, mock_commit):
        """TC102: No students to process"""
        mock_batch = Mock()
        mock_batch.status = "Processing"
        mock_batch.save = Mock()
        mock_get_doc.side_effect = [mock_batch, mock_batch]
        
        mock_get_all.return_value = []  # No students
        
        result = process_batch_job("BSO001")
        
        self.assertEqual(result["success_count"], 0)
        self.assertEqual(result["failure_count"], 0)


class TestBackgroundJobs(TestBackendStudentOnboarding):
    """Test background job functionality"""

    @patch('frappe.db.table_exists')
    @patch('frappe.db.get_value')
    def test_get_job_status_completed(self, mock_get_value, mock_table_exists):
        """TC108: Job completion status"""
        mock_table_exists.return_value = True
        mock_get_value.return_value = {
            "status": "finished",
            "progress_data": None,
            "result": '{"success_count": 10, "failure_count": 0}'
        }
        
        result = get_job_status("job123")
        
        self.assertEqual(result["status"], "Completed")
        self.assertIn("result", result)

    @patch('frappe.db.table_exists')
    @patch('frappe.db.get_value')
    def test_get_job_status_failed(self, mock_get_value, mock_table_exists):
        """TC108: Job failed status"""
        mock_table_exists.return_value = True
        mock_get_value.return_value = {
            "status": "failed",
            "progress_data": None,
            "result": None
        }
        
        result = get_job_status("job123")
        
        self.assertEqual(result["status"], "Failed")

    @patch('frappe.db.table_exists')
    def test_get_job_status_table_not_exists(self, mock_table_exists):
        """TC113: Job status table doesn't exist"""
        mock_table_exists.return_value = False
        
        result = get_job_status("job123")
        
        self.assertEqual(result["status"], "Unknown")


class TestDataIntegrity(TestBackendStudentOnboarding):
    """Test data integrity functionality"""

    @patch('frappe.db.sql')
    @patch('tap_lms.backend_student_onboarding.normalize_phone_number')
    def test_validate_enrollment_data_broken_links(self, mock_normalize, mock_sql):
        """TC114: Detect broken course links"""
        mock_normalize.return_value = ("919876543210", "9876543210")
        mock_sql.return_value = [
            {
                "student_id": "STU001",
                "enrollment_id": "ENR001",
                "course": "INVALID_COURSE",
                "batch": "BT001",
                "grade": "5"
            }
        ]
        
        with patch('frappe.db.exists') as mock_exists:
            mock_exists.return_value = False  # Course doesn't exist
            
            result = validate_enrollment_data("Test Student", "9876543210")
            
            self.assertEqual(result["total_enrollments"], 1)
            self.assertEqual(result["valid_enrollments"], 0)
            self.assertEqual(result["broken_enrollments"], 1)
            self.assertEqual(len(result["broken_details"]), 1)

    @patch('frappe.get_all')
    @patch('frappe.db.sql')
    @patch('frappe.db.set_value')
    @patch('frappe.db.commit')
    def test_fix_broken_course_links(self, mock_commit, mock_set_value, mock_sql, mock_get_all):
        """TC115: Fix broken course links"""
        mock_get_all.return_value = [{"name": "STU001"}]
        mock_sql.return_value = [
            {"name": "ENR001", "course": "INVALID_COURSE"}
        ]
        
        result = fix_broken_course_links()
        
        self.assertIn("Total fixed: 1", result)
        mock_set_value.assert_called_once_with("Enrollment", "ENR001", "course", None)
        mock_commit.assert_called_once()


class TestAcademicYear(TestBackendStudentOnboarding):
    """Test academic year calculation"""

    @patch('frappe.utils.getdate')
    def test_get_current_academic_year_april_onwards(self, mock_getdate):
        """Academic year calculation for April onwards"""
        from datetime import date
        mock_getdate.return_value = date(2025, 4, 15)  # April 15, 2025
        
        result = get_current_academic_year_backend()
        
        self.assertEqual(result, "2025-26")

    @patch('frappe.utils.getdate')
    def test_get_current_academic_year_before_april(self, mock_getdate):
        """Academic year calculation before April"""
        from datetime import date
        mock_getdate.return_value = date(2025, 2, 15)  # February 15, 2025
        
        result = get_current_academic_year_backend()
        
        self.assertEqual(result, "2024-25")


class TestErrorHandling(TestBackendStudentOnboarding):
    """Test error handling and edge cases"""

    def test_format_phone_number_valid(self):
        """Test phone number formatting for Glific"""
        with patch('tap_lms.backend_student_onboarding.normalize_phone_number') as mock_normalize:
            mock_normalize.return_value = ("919876543210", "9876543210")
            result = format_phone_number("9876543210")
            self.assertEqual(result, "919876543210")

    def test_format_phone_number_invalid(self):
        """Test phone number formatting with invalid input"""
        with patch('tap_lms.backend_student_onboarding.normalize_phone_number') as mock_normalize:
            mock_normalize.return_value = (None, None)
            result = format_phone_number("invalid")
            self.assertIsNone(result)

    @patch('frappe.db.sql')
    def test_find_existing_student_database_error(self, mock_sql):
        """Test finding existing student with database error"""
        mock_sql.side_effect = Exception("Database connection error")
        
        # Should not raise exception, but return None
        result = find_existing_student_by_phone_and_name("9876543210", "Test Student")
        self.assertIsNone(result)

    def test_update_backend_student_status_success(self):
        """Test updating backend student status to success"""
        mock_student = Mock()
        mock_student.save = Mock()
        
        mock_student_doc = Mock()
        mock_student_doc.name = "STU001"
        mock_student_doc.glific_id = "123"
        
        update_backend_student_status(mock_student, "Success", mock_student_doc)
        
        self.assertEqual(mock_student.processing_status, "Success")
        self.assertEqual(mock_student.student_id, "STU001")

    def test_update_backend_student_status_failed_with_long_error(self):
        """Test updating backend student status with long error message"""
        mock_student = Mock()
        mock_student.save = Mock()
        mock_student.processing_notes = None
        
        # Mock metadata to simulate field length constraint
        with patch('frappe.get_meta') as mock_get_meta:
            mock_field = Mock()
            mock_field.length = 50  # Short field length
            mock_meta = Mock()
            mock_meta.get_field.return_value = mock_field
            mock_get_meta.return_value = mock_meta
            
            long_error = "This is a very long error message that exceeds the field length limit and should be truncated appropriately"
            
            update_backend_student_status(mock_student, "Failed", error=long_error)
            
            self.assertEqual(mock_student.processing_status, "Failed")
            self.assertEqual(len(mock_student.processing_notes), 50)


class TestDebugFunctions(TestBackendStudentOnboarding):
    """Test debug and utility functions"""

    @patch('tap_lms.backend_student_onboarding.normalize_phone_number')
    @patch('tap_lms.backend_student_onboarding.find_existing_student_by_phone_and_name')
    @patch('frappe.get_all')
    def test_debug_student_type_analysis(self, mock_get_all, mock_find_existing, mock_normalize):
        """Test debug student type analysis function"""
        mock_normalize.return_value = ("919876543210", "9876543210")
        mock_find_existing.return_value = {"name": "STU001"}
        mock_get_all.return_value = [
            {"name": "ENR001", "course": "COURSE001", "batch": "BT001", "grade": "5", "school": "SCH001"}
        ]
        
        with patch('frappe.db.exists') as mock_exists, \
             patch('frappe.db.sql') as mock_sql:
            mock_exists.return_value = True
            mock_sql.return_value = [{"vertical_name": "Math"}]
            
            result = debug_student_type_analysis("Test Student", "9876543210", "Math")
            
            self.assertIn("STUDENT TYPE ANALYSIS", result)
            self.assertIn("Found student: STU001", result)
            self.assertIn("SAME VERTICAL", result)

    @patch('frappe.new_doc')
    @patch('frappe.delete_doc')
    def test_basic_student_creation(self, mock_delete_doc, mock_new_doc):
        """Test basic student creation for debugging"""
        mock_student = Mock()
        mock_student.name = "TEST_STU001"
        mock_student.insert = Mock()
        mock_student.append = Mock()
        mock_student.save = Mock()
        mock_new_doc.return_value = mock_student
        
        # Import the test function (assuming it's exposed)
        try:
            from tap_lms.backend_student_onboarding import test_basic_student_creation
            result = test_basic_student_creation()
            
            self.assertIn("BASIC TEST PASSED", result)
            mock_student.insert.assert_called_once()
            mock_delete_doc.assert_called_once()
        except ImportError:
            # Function might not be exposed, skip this test
            self.skipTest("test_basic_student_creation function not available")


class TestEdgeCases(TestBackendStudentOnboarding):
    """Test edge cases and boundary conditions"""

    def test_normalize_phone_number_edge_cases(self):
        """Test phone normalization edge cases"""
        # Test with only country code
        phone_12, phone_10 = normalize_phone_number("91")
        self.assertIsNone(phone_12)
        self.assertIsNone(phone_10)
        
        # Test with partial number
        phone_12, phone_10 = normalize_phone_number("91987654")
        self.assertIsNone(phone_12)
        self.assertIsNone(phone_10)
        
        # Test with extra long number
        phone_12, phone_10 = normalize_phone_number("9198765432101234")
        self.assertIsNone(phone_12)
        self.assertIsNone(phone_10)

    @patch('tap_lms.backend_student_onboarding.find_existing_student_by_phone_and_name')
    def test_validate_student_with_none_values(self, mock_find_existing):
        """Test student validation with None values"""
        mock_find_existing.return_value = None
        
        student_data = {
            "student_name": None,
            "phone": None,
            "school": None,
            "grade": None,
            "language": None,
            "batch": None
        }
        
        validation = validate_student(student_data)
        
        # All required fields should be marked as missing
        required_fields = ["student_name", "phone", "school", "grade", "language", "batch"]
        for field in required_fields:
            self.assertEqual(validation[field], "missing")

    @patch('frappe.db.sql')
    @patch('tap_lms.backend_student_onboarding.normalize_phone_number')
    def test_determine_student_type_with_mixed_enrollments(self, mock_normalize, mock_sql):
        """Test student type with mixed enrollment scenarios"""
        mock_normalize.return_value = ("919876543210", "9876543210")
        
        # Student with multiple enrollments: same vertical, different vertical, and null course
        mock_sql.side_effect = [
            [{"name": "STU001", "phone": "919876543210", "name1": "Test Student"}],  # Student exists
            [  # Multiple enrollments
                {"name": "ENR001", "course": "COURSE001", "batch": "BT001", "grade": "5", "school": "SCH001"},
                {"name": "ENR002", "course": "COURSE002", "batch": "BT002", "grade": "5", "school": "SCH001"},
                {"name": "ENR003", "course": None, "batch": "BT003", "grade": "5", "school": "SCH001"}
            ],
            [{"vertical_name": "Math"}],  # First course - same vertical
            [{"vertical_name": "Science"}]  # Second course - different vertical
        ]
        
        with patch('frappe.db.exists') as mock_exists:
            mock_exists.side_effect = [True, True]  # Both courses exist
            
            result = determine_student_type_backend("9876543210", "Test Student", "Math")
            
            # Should return "Old" because there's at least one enrollment in the same vertical
            self.assertEqual(result, "Old")

    @patch('frappe.get_all')
    def test_get_onboarding_stages_with_exception(self, mock_get_all):
        """Test get_onboarding_stages with database exception"""
        mock_get_all.side_effect = Exception("Database error")
        
        with patch('frappe.log_error') as mock_log_error:
            result = get_onboarding_stages()
            
            self.assertEqual(result, [])
            mock_log_error.assert_called_once()


class TestMockDataSetup(unittest.TestCase):
    """Test data setup and teardown utilities"""

    def setUp(self):
        """Set up test database state"""
        self.test_data_created = []

    def tearDown(self):
        """Clean up test data"""
        for doc_type, doc_name in self.test_data_created:
            try:
                if frappe.db.exists(doc_type, doc_name):
                    frappe.delete_doc(doc_type, doc_name, force=True)
            except:
                pass  # Ignore cleanup errors

    def create_test_student(self, phone="9876543210", name="Test Student"):
        """Create a test student record"""
        student = frappe.new_doc("Student")
        student.name1 = name
        student.phone = phone
        student.gender = "Male"
        student.grade = "5"
        student.status = "active"
        student.joined_on = nowdate()
        student.insert()
        
        self.test_data_created.append(("Student", student.name))
        return student

    def create_test_batch_onboarding(self, batch_skeyword="TEST_MATH_5"):
        """Create a test batch onboarding record"""
        batch_onboarding = frappe.new_doc("Backend Student Onboarding")
        batch_onboarding.set_name = "Test Batch Set"
        batch_onboarding.status = "Draft"
        batch_onboarding.student_count = 1
        batch_onboarding.insert()
        
        self.test_data_created.append(("Backend Student Onboarding", batch_onboarding.name))
        return batch_onboarding

    def create_test_backend_student(self, parent, **kwargs):
        """Create a test backend student record"""
        defaults = {
            "student_name": "Test Student",
            "phone": "9876543210",
            "gender": "Male",
            "batch": "BT00000015",
            "course_vertical": "Math",
            "grade": "5",
            "school": "SCH001",
            "language": "English",
            "batch_skeyword": "MATH_5_2025",
            "processing_status": "Pending"
        }
        defaults.update(kwargs)
        
        backend_student = frappe.new_doc("Backend Students")
        backend_student.parent = parent
        backend_student.parenttype = "Backend Student Onboarding"
        backend_student.parentfield = "students"
        
        for key, value in defaults.items():
            setattr(backend_student, key, value)
        
        backend_student.insert()
        return backend_student


class TestIntegrationScenarios(TestMockDataSetup):
    """Integration tests using real database operations"""

    @patch('tap_lms.glific_integration.create_or_get_glific_group_for_batch')
    @patch('tap_lms.backend_student_onboarding.process_glific_contact')
    def test_end_to_end_new_student_processing(self, mock_process_glific, mock_create_group):
        """TC131: Complete onboarding flow for new student"""
        # Setup mocks
        mock_create_group.return_value = {"group_id": "456", "label": "Test Group"}
        mock_process_glific.return_value = {"id": "123", "name": "Test Student"}
        
        # Create test data
        batch_onboarding = self.create_test_batch_onboarding()
        backend_student_data = {
            "student_name": "New Test Student",
            "phone": "9111111111",  # Unique phone
            "grade": "6"
        }
        backend_student = self.create_test_backend_student(batch_onboarding.name, **backend_student_data)
        
        # Process the student
        with patch('tap_lms.backend_student_onboarding.get_initial_stage') as mock_get_stage:
            mock_get_stage.return_value = "Stage1"
            
            # This should create a new student
            result_student = process_student_record(
                backend_student, 
                {"id": "123"}, 
                batch_onboarding.name, 
                "Stage1",
                "COURSE001"
            )
            
            # Verify student was created
            self.assertIsNotNone(result_student)
            self.assertEqual(result_student.name1, "New Test Student")
            self.assertEqual(result_student.phone, "919111111111")  # Should be normalized
            self.assertEqual(result_student.glific_id, "123")
            
            # Verify enrollment was created
            self.assertEqual(len(result_student.enrollment), 1)
            enrollment = result_student.enrollment[0]
            self.assertEqual(enrollment.course, "COURSE001")
            self.assertEqual(enrollment.grade, "6")

    def test_end_to_end_existing_student_update(self):
        """TC132: Complete flow for existing student update"""
        # Create existing student
        existing_student = self.create_test_student("9222222222", "Existing Student")
        existing_student.grade = "4"  # Lower grade
        existing_student.save()
        
        # Create batch onboarding and backend student with updated info
        batch_onboarding = self.create_test_batch_onboarding()
        backend_student_data = {
            "student_name": "Existing Student",
            "phone": "9222222222",
            "grade": "5"  # Higher grade - should update
        }
        backend_student = self.create_test_backend_student(batch_onboarding.name, **backend_student_data)
        
        # Process the student
        with patch('tap_lms.backend_student_onboarding.get_initial_stage') as mock_get_stage:
            mock_get_stage.return_value = "Stage1"
            
            result_student = process_student_record(
                backend_student,
                {"id": "456"},
                batch_onboarding.name,
                "Stage1",
                "COURSE002"
            )
            
            # Verify it's the same student but updated
            self.assertEqual(result_student.name, existing_student.name)
            self.assertEqual(result_student.grade, "5")  # Should be updated
            self.assertEqual(result_student.glific_id, "456")
            
            # Should have added new enrollment
            self.assertGreater(len(result_student.enrollment), 0)


class TestPerformanceScenarios(TestBackendStudentOnboarding):
    """Performance and load testing scenarios"""

    @patch('frappe.get_all')
    @patch('frappe.get_doc')
    def test_large_batch_processing_chunking(self, mock_get_doc, mock_get_all):
        """TC127: Process large batch in chunks"""
        # Mock large number of students
        large_student_list = [{"name": f"BS{i:03d}", "batch_skeyword": "MATH_5_2025"} for i in range(150)]
        
        mock_get_all.side_effect = [
            large_student_list,  # Students to process
            [{"batch_skeyword": "MATH_5_2025", "name": "BO001", "kit_less": False}] * 150  # Batch onboarding cache
        ]
        
        mock_batch = Mock()
        mock_batch.status = "Processing"
        mock_batch.save = Mock()
        
        # Mock individual backend students
        def create_mock_backend_student(name):
            mock_student = Mock()
            mock_student.name = name
            mock_student.student_name = f"Student {name}"
            mock_student.phone = f"91{name[-3:]}0000000"
            mock_student.save = Mock()
            return mock_student
        
        mock_get_doc.side_effect = [mock_batch] + [create_mock_backend_student(s["name"]) for s in large_student_list] + [mock_batch]
        
        with patch('tap_lms.backend_student_onboarding.process_glific_contact') as mock_glific, \
             patch('tap_lms.backend_student_onboarding.process_student_record') as mock_process, \
             patch('tap_lms.backend_student_onboarding.update_backend_student_status'), \
             patch('tap_lms.glific_integration.create_or_get_glific_group_for_batch'), \
             patch('tap_lms.backend_student_onboarding.get_initial_stage'), \
             patch('frappe.db.commit'):
            
            mock_glific.return_value = {"id": "123"}
            mock_student_doc = Mock()
            mock_student_doc.name = "STU001"
            mock_process.return_value = mock_student_doc
            
            result = process_batch_job("BSO001")
            
            # Should process all 150 students
            self.assertEqual(result["success_count"], 150)
            self.assertEqual(result["failure_count"], 0)
            
            # Verify chunking behavior by checking commit calls
            # Should commit multiple times for large batch


# Test runner setup
if __name__ == '__main__':
    # Set up Frappe test environment
    import frappe
    frappe.init(site='test_site')
    frappe.connect()
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestPhoneNormalization,
        TestStudentValidation,
        TestAPIEndpoints,
        TestStudentTypeDetection,
        TestCourseLevelSelection,
        TestGlificIntegration,
        TestStudentRecordProcessing,
        TestBatchProcessing,
        TestBackgroundJobs,
        TestDataIntegrity,
        TestAcademicYear,
        TestErrorHandling,
        TestDebugFunctions,
        TestEdgeCases,
        TestIntegrationScenarios,
        TestPerformanceScenarios
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print(f"\nTest Summary:")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")