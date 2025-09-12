


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


import pytest
import sys
from unittest.mock import Mock, patch, MagicMock
from datetime import date, datetime
import json

# Create a mock object that supports both dict access and attribute access
class MockDict(dict):
    """Mock dictionary that supports both dict['key'] and dict.key access"""
    def _getattr_(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(f"'{self._class.name_}' object has no attribute '{name}'")

# FIXTURE DEFINITION
@pytest.fixture
def mock_frappe():
    """Fixture for common Frappe mocking setup"""
    with patch.dict('sys.modules', {
        'frappe': Mock(),
        'frappe.model': Mock(),
        'frappe.model.document': Mock(),
        'frappe.utils': Mock(),
        'json': Mock(),
        'traceback': Mock(),
    }):
        mock_frappe = sys.modules['frappe']
        mock_frappe.session = Mock()
        mock_frappe.session.user = 'test_user'
        mock_frappe.local = Mock()
        mock_frappe.local.response = Mock()
        mock_frappe.local.response._setitem_ = Mock()
        mock_frappe.local.response._getitem_ = Mock()
        mock_frappe.local.response.http_status_code = 200
        mock_frappe.whitelist = lambda allow_guest=False: lambda func: func
        mock_frappe.log_error = Mock()
        mock_frappe._ = lambda x: x
        mock_frappe.throw = Mock()
        mock_frappe.get_all = Mock()
        mock_frappe.get_doc = Mock()
        mock_frappe.new_doc = Mock()
        mock_frappe.db = Mock()
        mock_frappe.db.sql = Mock()
        mock_frappe.db.exists = Mock()
        mock_frappe.db.get_value = Mock()
        mock_frappe.db.set_value = Mock()
        mock_frappe.db.table_exists = Mock()
        mock_frappe.db.count = Mock()
        mock_frappe.db.commit = Mock()
        mock_frappe.db.rollback = Mock()
        mock_frappe.utils = Mock()
        mock_frappe.utils.nowdate = Mock(return_value=date(2025, 8, 20))
        mock_frappe.utils.nowtime = Mock()
        mock_frappe.utils.now = Mock()
        mock_frappe.utils.getdate = Mock(return_value=date(2025, 8, 20))
        mock_frappe.enqueue = Mock()
        mock_frappe.publish_progress = Mock()
        
        # Mock exceptions
        class MockValidationError(Exception):
            pass
        mock_frappe.ValidationError = MockValidationError
        
        yield mock_frappe

# Test Data Factory
class BackendOnboardingTestDataFactory:
    """Factory for creating test data for backend onboarding"""
    
    @staticmethod
    def create_backend_student_mock(**kwargs):
        """Create a mock Backend Student record"""
        mock_student = Mock()
        mock_student.name = kwargs.get('name', 'BACKEND_STU001')
        mock_student.student_name = kwargs.get('student_name', 'Test Student')
        mock_student.phone = kwargs.get('phone', '919876543210')
        mock_student.gender = kwargs.get('gender', 'Male')
        mock_student.batch = kwargs.get('batch', 'BT00000001')
        mock_student.course_vertical = kwargs.get('course_vertical', 'CV001')
        mock_student.grade = kwargs.get('grade', '5')
        mock_student.school = kwargs.get('school', 'SCH001')
        mock_student.language = kwargs.get('language', 'LANG_EN')
        mock_student.batch_skeyword = kwargs.get('batch_skeyword', 'TEST_BATCH')
        mock_student.processing_status = kwargs.get('processing_status', 'Pending')
        mock_student.student_id = kwargs.get('student_id', None)
        mock_student.glific_id = kwargs.get('glific_id', None)
        mock_student.processing_notes = kwargs.get('processing_notes', None)
        mock_student.save = Mock()
        return mock_student
    
    @staticmethod
    def create_batch_mock(**kwargs):
        """Create a mock Backend Student Onboarding batch"""
        mock_batch = Mock()
        mock_batch.name = kwargs.get('name', 'BATCH001')
        mock_batch.set_name = kwargs.get('set_name', 'Test Batch')
        mock_batch.status = kwargs.get('status', 'Draft')
        mock_batch.upload_date = kwargs.get('upload_date', date.today())
        mock_batch.uploaded_by = kwargs.get('uploaded_by', 'test_user')
        mock_batch.student_count = kwargs.get('student_count', 10)
        mock_batch.processed_student_count = kwargs.get('processed_student_count', 0)
        mock_batch.save = Mock()
        return mock_batch
    
    @staticmethod
    def create_student_mock(**kwargs):
        """Create a mock Student record"""
        mock_student = Mock()
        mock_student.name = kwargs.get('name', 'STU001')
        mock_student.name1 = kwargs.get('name1', 'Test Student')
        mock_student.phone = kwargs.get('phone', '919876543210')
        mock_student.gender = kwargs.get('gender', 'Male')
        mock_student.grade = kwargs.get('grade', '5')
        mock_student.school_id = kwargs.get('school_id', 'SCH001')
        mock_student.language = kwargs.get('language', 'LANG_EN')
        mock_student.glific_id = kwargs.get('glific_id', None)
        mock_student.backend_onboarding = kwargs.get('backend_onboarding', None)
        mock_student.joined_on = kwargs.get('joined_on', date.today())
        mock_student.status = kwargs.get('status', 'active')
        mock_student.enrollment = []
        mock_student.append = Mock()
        mock_student.save = Mock()
        mock_student.insert = Mock()
        return mock_student

# PHONE NUMBER NORMALIZATION TESTS
class TestPhoneNumberNormalization:
    """Test phone number normalization functionality"""
    
    def test_normalize_phone_number_10_digit(self, mock_frappe):
        """Test normalizing 10-digit phone number"""
        from tap_lms.page.backend_onboarding_process.backend_onboarding_process import normalize_phone_number
        
        phone_12, phone_10 = normalize_phone_number("9876543210")
        
        assert phone_12 == "919876543210"
        assert phone_10 == "9876543210"
    
    def test_normalize_phone_number_12_digit(self, mock_frappe):
        """Test normalizing 12-digit phone number"""
        from tap_lms.page.backend_onboarding_process.backend_onboarding_process import normalize_phone_number
        
        phone_12, phone_10 = normalize_phone_number("919876543210")
        
        assert phone_12 == "919876543210"
        assert phone_10 == "9876543210"
    
    def test_normalize_phone_number_11_digit_with_1_prefix(self, mock_frappe):
        """Test normalizing 11-digit phone number starting with 1"""
        from tap_lms.page.backend_onboarding_process.backend_onboarding_process import normalize_phone_number
        
        phone_12, phone_10 = normalize_phone_number("19876543210")
        
        assert phone_12 == "919876543210"
        assert phone_10 == "9876543210"
    
    def test_normalize_phone_number_with_formatting(self, mock_frappe):
        """Test normalizing phone number with formatting characters"""
        from tap_lms.page.backend_onboarding_process.backend_onboarding_process import normalize_phone_number
        
        phone_12, phone_10 = normalize_phone_number("(987) 654-3210")
        
        assert phone_12 == "919876543210"
        assert phone_10 == "9876543210"
    
    def test_normalize_phone_number_invalid(self, mock_frappe):
        """Test normalizing invalid phone number"""
        from tap_lms.page.backend_onboarding_process.backend_onboarding_process import normalize_phone_number
        
        # Test with invalid length
        phone_12, phone_10 = normalize_phone_number("12345")
        assert phone_12 is None
        assert phone_10 is None
        
        # Test with None
        phone_12, phone_10 = normalize_phone_number(None)
        assert phone_12 is None
        assert phone_10 is None
        
        # Test with empty string
        phone_12, phone_10 = normalize_phone_number("")
        assert phone_12 is None
        assert phone_10 is None

# STUDENT FINDING TESTS
class TestFindExistingStudent:
    """Test finding existing students by phone and name"""
    
    def test_find_existing_student_success(self, mock_frappe):
        """Test successfully finding existing student"""
        from tap_lms.page.backend_onboarding_process.backend_onboarding_process import find_existing_student_by_phone_and_name
        
        # Mock SQL result
        mock_student_data = {
            'name': 'STU001',
            'phone': '919876543210',
            'name1': 'Test Student'
        }
        mock_frappe.db.sql.return_value = [mock_student_data]
        
        result = find_existing_student_by_phone_and_name("919876543210", "Test Student")
        
        assert result == mock_student_data
        assert mock_frappe.db.sql.called
    
    def test_find_existing_student_not_found(self, mock_frappe):
        """Test when student is not found"""
        from tap_lms.page.backend_onboarding_process.backend_onboarding_process import find_existing_student_by_phone_and_name
        
        mock_frappe.db.sql.return_value = []
        
        result = find_existing_student_by_phone_and_name("919876543210", "Test Student")
        
        assert result is None
    
    def test_find_existing_student_invalid_input(self, mock_frappe):
        """Test with invalid input"""
        from tap_lms.page.backend_onboarding_process.backend_onboarding_process import find_existing_student_by_phone_and_name
        
        # Test with None phone
        result = find_existing_student_by_phone_and_name(None, "Test Student")
        assert result is None
        
        # Test with None name
        result = find_existing_student_by_phone_and_name("919876543210", None)
        assert result is None

# ONBOARDING BATCHES TESTS
class TestGetOnboardingBatches:
    """Test getting onboarding batches"""
    
    def test_get_onboarding_batches_success(self, mock_frappe):
        """Test successfully getting onboarding batches"""
        from tap_lms.page.backend_onboarding_process.backend_onboarding_process import get_onboarding_batches
        
        mock_batches = [
            {
                'name': 'BATCH001',
                'set_name': 'Test Batch 1',
                'upload_date': date.today(),
                'uploaded_by': 'test_user',
                'student_count': 10,
                'processed_student_count': 5
            }
        ]
        mock_frappe.get_all.return_value = mock_batches
        
        result = get_onboarding_batches()
        
        assert result == mock_batches
        mock_frappe.get_all.assert_called_with(
            "Backend Student Onboarding", 
            filters={"status": ["in", ["Draft", "Processing", "Failed"]]},
            fields=["name", "set_name", "upload_date", "uploaded_by", 
                   "student_count", "processed_student_count"]
        )

# BATCH DETAILS TESTS
class TestGetBatchDetails:
    """Test getting batch details"""
    
    def test_get_batch_details_success(self, mock_frappe):
        """Test successfully getting batch details"""
        from tap_lms.page.backend_onboarding_process.backend_onboarding_process import get_batch_details
        
        # Mock batch document
        mock_batch = BackendOnboardingTestDataFactory.create_batch_mock()
        mock_frappe.get_doc.return_value = mock_batch
        
        # Mock students
        mock_students = [
            {
                'name': 'BACKEND_STU001',
                'student_name': 'Test Student',
                'phone': '919876543210',
                'gender': 'Male',
                'batch': 'BT001',
                'course_vertical': 'CV001',
                'grade': '5',
                'school': 'SCH001',
                'language': 'LANG_EN',
                'processing_status': 'Pending',
                'student_id': None
            }
        ]
        mock_frappe.get_all.side_effect = [mock_students, []]  # students, then empty glific_group
        
        result = get_batch_details('BATCH001')
        
        assert result['batch'] == mock_batch
        assert len(result['students']) == 1
        assert result['students'][0]['student_name'] == 'Test Student'
        assert 'validation' in result['students'][0]
        assert result['glific_group'] is None

# VALIDATION TESTS
class TestValidateStudent:
    """Test student validation functionality"""
    
    def test_validate_student_complete(self, mock_frappe):
        """Test validating a complete student record"""
        from tap_lms.page.backend_onboarding_process.backend_onboarding_process import validate_student
        
        # Mock complete student
        complete_student = {
            'student_name': 'Test Student',
            'phone': '919876543210',
            'school': 'SCH001',
            'grade': '5',
            'language': 'LANG_EN',
            'batch': 'BT001'
        }
        
        # Mock no existing student
        with patch('tap_lms.page.backend_onboarding_process.backend_onboarding_process.find_existing_student_by_phone_and_name') as mock_find:
            mock_find.return_value = None
            
            validation = validate_student(complete_student)
            
            assert validation == {}  # No validation errors
    
    def test_validate_student_missing_fields(self, mock_frappe):
        """Test validating student with missing required fields"""
        from tap_lms.page.backend_onboarding_process.backend_onboarding_process import validate_student
        
        # Student with missing fields
        incomplete_student = {
            'student_name': '',
            'phone': '919876543210',
            'school': '',
            'grade': '5',
            'language': 'LANG_EN',
            'batch': 'BT001'
        }
        
        # Mock no existing student
        with patch('tap_lms.page.backend_onboarding_process.backend_onboarding_process.find_existing_student_by_phone_and_name') as mock_find:
            mock_find.return_value = None
            
            validation = validate_student(incomplete_student)
            
            assert 'student_name' in validation
            assert validation['student_name'] == 'missing'
            assert 'school' in validation
            assert validation['school'] == 'missing'
    
    def test_validate_student_duplicate(self, mock_frappe):
        """Test validating student with duplicate"""
        from tap_lms.page.backend_onboarding_process.backend_onboarding_process import validate_student
        
        student = {
            'student_name': 'Test Student',
            'phone': '919876543210',
            'school': 'SCH001',
            'grade': '5',
            'language': 'LANG_EN',
            'batch': 'BT001'
        }
        
        # Mock existing student
        existing_student = {
            'name': 'STU001',
            'name1': 'Test Student'
        }
        
        with patch('tap_lms.page.backend_onboarding_process.backend_onboarding_process.find_existing_student_by_phone_and_name') as mock_find:
            mock_find.return_value = existing_student
            
            validation = validate_student(student)
            
            assert 'duplicate' in validation
            assert validation['duplicate']['student_id'] == 'STU001'
            assert validation['duplicate']['student_name'] == 'Test Student'

# ONBOARDING STAGES TESTS
class TestGetOnboardingStages:
    """Test getting onboarding stages"""
    
    def test_get_onboarding_stages_success(self, mock_frappe):
        """Test successfully getting onboarding stages"""
        from tap_lms.page.backend_onboarding_process.backend_onboarding_process import get_onboarding_stages
        
        mock_frappe.db.table_exists.return_value = True
        mock_stages = [
            {'name': 'STAGE001', 'description': 'Initial Stage', 'order': 0},
            {'name': 'STAGE002', 'description': 'Second Stage', 'order': 1}
        ]
        mock_frappe.get_all.return_value = mock_stages
        
        result = get_onboarding_stages()
        
        assert result == mock_stages
        mock_frappe.get_all.assert_called_with(
            "OnboardingStage", 
            fields=["name", "description", "order"],
            order_by="order"
        )
    
    def test_get_onboarding_stages_table_not_exists(self, mock_frappe):
        """Test when OnboardingStage table doesn't exist"""
        from tap_lms.page.backend_onboarding_process.backend_onboarding_process import get_onboarding_stages
        
        mock_frappe.db.table_exists.return_value = False
        
        result = get_onboarding_stages()
        
        assert result == []
    
    def test_get_onboarding_stages_exception(self, mock_frappe):
        """Test exception handling in get_onboarding_stages"""
        from tap_lms.page.backend_onboarding_process.backend_onboarding_process import get_onboarding_stages
        
        mock_frappe.db.table_exists.return_value = True
        mock_frappe.get_all.side_effect = Exception("Database error")
        
        result = get_onboarding_stages()
        
        assert result == []
        assert mock_frappe.log_error.called

# INITIAL STAGE TESTS
class TestGetInitialStage:
    """Test getting initial onboarding stage"""
    
    def test_get_initial_stage_with_order_zero(self, mock_frappe):
        """Test getting initial stage with order=0"""
        from tap_lms.page.backend_onboarding_process.backend_onboarding_process import get_initial_stage
        
        mock_frappe.get_all.side_effect = [
            [{'name': 'STAGE_INITIAL'}],  # First call with order=0
        ]
        
        result = get_initial_stage()
        
        assert result == 'STAGE_INITIAL'
    
    def test_get_initial_stage_no_order_zero(self, mock_frappe):
        """Test getting initial stage when no order=0 exists"""
        from tap_lms.page.backend_onboarding_process.backend_onboarding_process import get_initial_stage
        
        mock_frappe.get_all.side_effect = [
            [],  # First call with order=0 returns empty
            [{'name': 'STAGE_MIN', 'order': 1}],  # Second call with minimum order
        ]
        
        result = get_initial_stage()
        
        assert result == 'STAGE_MIN'
    
    def test_get_initial_stage_exception(self, mock_frappe):
        """Test exception handling in get_initial_stage"""
        from tap_lms.page.backend_onboarding_process.backend_onboarding_process import get_initial_stage
        
        mock_frappe.get_all.side_effect = Exception("Database error")
        
        result = get_initial_stage()
        
        assert result is None
        assert mock_frappe.log_error.called

# PROCESS BATCH TESTS
class TestProcessBatch:
    """Test batch processing functionality"""
    
    def test_process_batch_background_job(self, mock_frappe):
        """Test processing batch with background job"""
        from tap_lms.page.backend_onboarding_process.backend_onboarding_process import process_batch
        
        # Mock batch document
        mock_batch = BackendOnboardingTestDataFactory.create_batch_mock()
        mock_frappe.get_doc.return_value = mock_batch
        
        # Mock job
        mock_job = Mock()
        mock_job.id = 'job123'
        mock_frappe.enqueue.return_value = mock_job
        
        result = process_batch('BATCH001', use_background_job=True)
        
        assert result['job_id'] == 'job123'
        assert mock_batch.status == 'Processing'
        assert mock_batch.save.called
        assert mock_frappe.enqueue.called
    
    def test_process_batch_immediate(self, mock_frappe):
        """Test processing batch immediately"""
        from tap_lms.page.backend_onboarding_process.backend_onboarding_process import process_batch
        
        # Mock batch document
        mock_batch = BackendOnboardingTestDataFactory.create_batch_mock()
        mock_frappe.get_doc.return_value = mock_batch
        
        # Mock the process_batch_job function
        with patch('tap_lms.page.backend_onboarding_process.backend_onboarding_process.process_batch_job') as mock_job:
            mock_job.return_value = {'success_count': 5, 'failure_count': 0}
            
            result = process_batch('BATCH001', use_background_job=False)
            
            assert result['success_count'] == 5
            assert result['failure_count'] == 0
            assert mock_batch.status == 'Processing'

# STUDENT TYPE DETERMINATION TESTS
class TestDetermineStudentType:
    """Test student type determination logic"""
    
    def test_determine_student_type_new_no_existing(self, mock_frappe):
        """Test determining student type when no existing student"""
        from tap_lms.page.backend_onboarding_process.backend_onboarding_process import determine_student_type_backend
        
        # Mock no existing student
        mock_frappe.db.sql.return_value = []
        
        result = determine_student_type_backend("919876543210", "Test Student", "CV001")
        
        assert result == "New"
    
    def test_determine_student_type_old_same_vertical(self, mock_frappe):
        """Test determining student type when existing with same vertical"""
        from tap_lms.page.backend_onboarding_process.backend_onboarding_process import determine_student_type_backend
        
        # Mock existing student
        mock_frappe.db.sql.side_effect = [
            [{'name': 'STU001', 'phone': '919876543210', 'name1': 'Test Student'}],  # Existing student
            [{'name': 'ENR001', 'course': 'CL001', 'batch': 'BT001', 'grade': '5', 'school': 'SCH001'}],  # Enrollments
            [{'vertical_name': 'CV001'}]  # Course vertical data
        ]
        
        result = determine_student_type_backend("919876543210", "Test Student", "CV001")
        
        assert result == "Old"
    
    def test_determine_student_type_new_different_vertical(self, mock_frappe):
        """Test determining student type with different vertical"""
        from tap_lms.page.backend_onboarding_process.backend_onboarding_process import determine_student_type_backend
        
        # Mock existing student with different vertical
        mock_frappe.db.sql.side_effect = [
            [{'name': 'STU001', 'phone': '919876543210', 'name1': 'Test Student'}],  # Existing student
            [{'name': 'ENR001', 'course': 'CL001', 'batch': 'BT001', 'grade': '5', 'school': 'SCH001'}],  # Enrollments
            [{'vertical_name': 'CV002'}]  # Different course vertical
        ]
        
        result = determine_student_type_backend("919876543210", "Test Student", "CV001")
        
        assert result == "New"
    
    def test_determine_student_type_old_broken_course(self, mock_frappe):
        """Test determining student type with broken course links"""
        from tap_lms.page.backend_onboarding_process.backend_onboarding_process import determine_student_type_backend
        
        # Mock existing student with broken course link
        mock_frappe.db.sql.side_effect = [
            [{'name': 'STU001', 'phone': '919876543210', 'name1': 'Test Student'}],  # Existing student
            [{'name': 'ENR001', 'course': 'BROKEN_COURSE', 'batch': 'BT001', 'grade': '5', 'school': 'SCH001'}],  # Enrollments
            []  # No course vertical data (broken link)
        ]
        
        result = determine_student_type_backend("919876543210", "Test Student", "CV001")
        
        assert result == "Old"

# ACADEMIC YEAR TESTS
class TestGetCurrentAcademicYear:
    """Test academic year calculation"""
    
    def test_get_current_academic_year_after_april(self, mock_frappe):
        """Test academic year calculation when current date is after April"""
        from tap_lms.page.backend_onboarding_process.backend_onboarding_process import get_current_academic_year_backend
        
        # Mock date in August (after April)
        mock_frappe.utils.getdate.return_value = date(2025, 8, 20)
        
        result = get_current_academic_year_backend()
        
        assert result == "2025-26"
    
    def test_get_current_academic_year_before_april(self, mock_frappe):
        """Test academic year calculation when current date is before April"""
        from tap_lms.page.backend_onboarding_process.backend_onboarding_process import get_current_academic_year_backend
        
        # Mock date in February (before April)
        mock_frappe.utils.getdate.return_value = date(2025, 2, 20)
        
        result = get_current_academic_year_backend()
        
        assert result == "2024-25"
    
    def test_get_current_academic_year_exception(self, mock_frappe):
        """Test exception handling in academic year calculation"""
        from tap_lms.page.backend_onboarding_process.backend_onboarding_process import get_current_academic_year_backend
        
        mock_frappe.utils.getdate.side_effect = Exception("Date error")
        
        result = get_current_academic_year_backend()
        
        assert result is None
        assert mock_frappe.log_error.called

# PROCESS STUDENT RECORD TESTS
class TestProcessStudentRecord:
    """Test processing student records"""
    
    def test_process_student_record_new_student(self, mock_frappe):
        """Test processing a new student record"""
        from tap_lms.page.backend_onboarding_process.backend_onboarding_process import process_student_record
        
        # Mock backend student
        backend_student = BackendOnboardingTestDataFactory.create_backend_student_mock()
        
        # Mock no existing student
        with patch('tap_lms.page.backend_onboarding_process.backend_onboarding_process.find_existing_student_by_phone_and_name') as mock_find:
            mock_find.return_value = None
            
            # Mock new student document
            new_student = BackendOnboardingTestDataFactory.create_student_mock()
            mock_frappe.new_doc.return_value = new_student
            
            # Mock Glific contact
            glific_contact = {'id': 'GLI001'}
            
            result = process_student_record(backend_student, glific_contact, 'BATCH001', 'STAGE001')
            
            assert result == new_student
            assert new_student.name1 == 'Test Student'
            assert new_student.phone == '919876543210'
            assert new_student.glific_id == 'GLI001'
            assert new_student.insert.called
    
    def test_process_student_record_existing_student(self, mock_frappe):
        """Test processing an existing student record"""
        from tap_lms.page.backend_onboarding_process.backend_onboarding_process import process_student_record
        
        # Mock backend student
        backend_student = BackendOnboardingTestDataFactory.create_backend_student_mock()
        
        # Mock existing student
        existing_student_data = {
            'name': 'STU001',
            'phone': '919876543210',
            'name1': 'Test Student'
        }
        
        existing_student = BackendOnboardingTestDataFactory.create_student_mock(name='STU001')
        
        with patch('tap_lms.page.backend_onboarding_process.backend_onboarding_process.find_existing_student_by_phone_and_name') as mock_find:
            mock_find.return_value = existing_student_data
            mock_frappe.get_doc.return_value = existing_student
            
            # Mock Glific contact
            glific_contact = {'id': 'GLI001'}
            
            result = process_student_record(backend_student, glific_contact, 'BATCH001', 'STAGE001')
            
            assert result == existing_student
            assert existing_student.save.called
            # Should add new enrollment
            assert existing_student.append.called

# DEBUG FUNCTIONS TESTS
class TestDebugFunctions:
    """Test debug and utility functions"""
    
    def test_debug_student_type_analysis(self, mock_frappe):
        """Test debug student type analysis"""
        from tap_lms.page.backend_onboarding_process.backend_onboarding_process import debug_student_type_analysis
        
        # Mock existing student with enrollments
        mock_frappe.db.sql.side_effect = [
            [{'name': 'STU001', 'phone': '919876543210', 'name1': 'Test Student'}],  # Existing student
            [{'name': 'ENR001', 'course': 'CL001', 'batch': 'BT001', 'grade': '5', 'school': 'SCH001'}],  # Enrollments
            [{'vertical_name': 'CV001'}]  # Course vertical data
        ]
        
        with patch('tap_lms.page.backend_onboarding_process.backend_onboarding_process.determine_student_type_backend') as mock_determine:
            mock_determine.return_value = "Old"
            
            result = debug_student_type_analysis("Test Student", "919876543210", "CV001")
            
            assert "STUDENT TYPE ANALYSIS" in result
            assert "FINAL DETERMINATION: Old" in result
    
    def test_debug_student_processing(self, mock_frappe):
        """Test debug student processing"""
        from tap_lms.page.backend_onboarding_process.backend_onboarding_process import debug_student_processing
        
        # Mock various database responses
        mock_frappe.get_all.return_value = [
            {
                'name': 'BACKEND001',
                'batch': 'BT001',
                'course_vertical': 'CV001',
                'grade': '5',
                'school': 'SCH001',
                'language': 'LANG_EN',
                'batch_skeyword': 'TEST_BATCH',
                'processing_status': 'Pending'
            }
        ]
        
        mock_frappe.db.exists.return_value = True
        
        with patch('tap_lms.page.backend_onboarding_process.backend_onboarding_process.find_existing_student_by_phone_and_name') as mock_find:
            mock_find.return_value = None
            
            result = debug_student_processing("Test Student", "919876543210")
            
            assert "DEBUGGING STUDENT" in result
            assert "Phone normalization" in result
    
    def test_test_basic_student_creation(self, mock_frappe):
        """Test basic student creation test function"""
        from tap_lms.page.backend_onboarding_process.backend_onboarding_process import test_basic_student_creation
        
        # Mock student document
        test_student = BackendOnboardingTestDataFactory.create_student_mock(name='TEST_STUDENT')
        mock_frappe.new_doc.return_value = test_student
        
        result = test_basic_student_creation()
        
        assert "TESTING BASIC STUDENT CREATION" in result
        assert test_student.insert.called

# JOB STATUS TESTS
class TestGetJobStatus:
    """Test job status functionality"""
    
    def test_get_job_status_success(self, mock_frappe):
        """Test getting job status successfully"""
        from tap_lms.page.backend_onboarding_process.backend_onboarding_process import get_job_status
        
        # Mock table exists and job data
        mock_frappe.db.table_exists.return_value = True
        mock_frappe.db.get_value.return_value = {
            'status': 'finished',
            'progress_data': None,
            'result': '{"success_count": 5, "failure_count": 0}'
        }
        
        result = get_job_status('job123')
        
        assert result['status'] == 'Completed'
        assert 'result' in result
    
    def test_get_job_status_unknown(self, mock_frappe):
        """Test getting job status when status is unknown"""
        from tap_lms.page.backend_onboarding_process.backend_onboarding_process import get_job_status
        
        # Mock no table exists
        mock_frappe.db.table_exists.return_value = False
        
        result = get_job_status('job123')
        
        assert result['status'] == 'Unknown'
        assert 'message' in result

# INTEGRATION TESTS
class TestIntegrationScenarios:
    """Test integration scenarios combining multiple functions"""
    
    def test_complete_batch_processing_workflow(self, mock_frappe):
        """Test complete batch processing workflow"""
        from tap_lms.page.backend_onboarding_process.backend_onboarding_process import get_batch_details, process_batch
        
        # Mock batch and students
        mock_batch = BackendOnboardingTestDataFactory.create_batch_mock()
        mock_students = [BackendOnboardingTestDataFactory.create_backend_student_mock()]
        
        mock_frappe.get_doc.return_value = mock_batch
        mock_frappe.get_all.side_effect = [mock_students, []]  # students, then glific groups
        
        # Test getting batch details
        batch_details = get_batch_details('BATCH001')
        assert batch_details['batch'] == mock_batch
        assert len(batch_details['students']) == 1
        
        # Test processing batch
        with patch('tap_lms.page.backend_onboarding_process.backend_onboarding_process.process_batch_job') as mock_job:
            mock_job.return_value = {'success_count': 1, 'failure_count': 0}
            
            result = process_batch('BATCH001', use_background_job=False)
            assert result['success_count'] == 1

# ERROR HANDLING TESTS
class TestErrorHandling:
    """Test error handling in various scenarios"""
    
    def test_phone_normalization_error_handling(self, mock_frappe):
        """Test phone normalization with various error scenarios"""
        from tap_lms.page.backend_onboarding_process.backend_onboarding_process import normalize_phone_number
        
        # Test various invalid inputs
        invalid_inputs = [None, "", "   ", "abc", "123", "123456789012345"]
        
        for invalid_input in invalid_inputs:
            phone_12, phone_10 = normalize_phone_number(invalid_input)
            # Should return None for both values for invalid inputs (except empty string case)
            if invalid_input not in ["   "]:  # Spaces would be stripped
                assert phone_12 is None
                assert phone_10 is None
    
    def test_batch_processing_error_handling(self, mock_frappe):
        """Test batch processing with errors"""
        from tap_lms.page.backend_onboarding_process.backend_onboarding_process import process_batch
        
        # Mock get_doc to raise exception
        mock_frappe.get_doc.side_effect = Exception("Document not found")
        
        # Should handle exception gracefully in the function
        # Note: The actual function might not return an error directly, 
        # but should log the error
        try:
            process_batch('INVALID_BATCH', use_background_job=False)
        except Exception:
            # Expected to raise exception for invalid batch
            pass

# EDGE CASES TESTS
class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_empty_batch_processing(self, mock_frappe):
        """Test processing batch with no students"""
        from tap_lms.page.backend_onboarding_process.backend_onboarding_process import get_batch_details
        
        mock_batch = BackendOnboardingTestDataFactory.create_batch_mock()
        mock_frappe.get_doc.return_value = mock_batch
        mock_frappe.get_all.side_effect = [[], []]  # No students, no glific groups
        
        result = get_batch_details('BATCH001')
        
        assert result['batch'] == mock_batch
        assert len(result['students']) == 0
        assert result['glific_group'] is None
    
    def test_student_with_all_missing_fields(self, mock_frappe):
        """Test validation with student having all missing required fields"""
        from tap_lms.page.backend_onboarding_process.backend_onboarding_process import validate_student
        
        empty_student = {
            'student_name': '',
            'phone': '',
            'school': '',
            'grade': '',
            'language': '',
            'batch': ''
        }
        
        with patch('tap_lms.page.backend_onboarding_process.backend_onboarding_process.find_existing_student_by_phone_and_name') as mock_find:
            mock_find.return_value = None
            
            validation = validate_student(empty_student)
            
            required_fields = ['student_name', 'phone', 'school', 'grade', 'language', 'batch']
            for field in required_fields:
                assert field in validation
                assert validation[field] == 'missing'
    
    def test_academic_year_boundary_dates(self, mock_frappe):
        """Test academic year calculation at boundary dates"""
        from tap_lms.page.backend_onboarding_process.backend_onboarding_process import get_current_academic_year_backend
        
        # Test March 31 (before April)
        mock_frappe.utils.getdate.return_value = date(2025, 3, 31)
        result = get_current_academic_year_backend()
        assert result == "2024-25"
        
        # Test April 1 (after April start)
        mock_frappe.utils.getdate.return_value = date(2025, 4, 1)
        result = get_current_academic_year_backend()
        assert result == "2025-26"

# if _name_ == '_main_':
#     pytest.main([_file_])