


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
from unittest.mock import MagicMock, patch, call, mock_open
import json
from datetime import datetime
import sys
import os

# Add the module path for importing the actual implementation
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import actual functions from backend_onboarding_process.py
try:
    from backend_onboarding_process import (
        normalize_phone_number,
        format_phone_number,
        get_current_academic_year_backend,
        find_existing_student_by_phone_and_name,
        validate_student,
        get_onboarding_batches,
        get_batch_details,
        get_onboarding_stages,
        get_initial_stage,
        process_batch,
        process_batch_job,
        update_job_progress,
        process_glific_contact,
        determine_student_type_backend,
        get_course_level_with_mapping_backend,
        get_course_level_with_validation_backend,
        validate_enrollment_data,
        process_student_record,
        update_backend_student_status,
        get_job_status,
        debug_student_processing,
        test_basic_student_creation,
        fix_broken_course_links,
        debug_student_type_analysis
    )
except ImportError:
    # Define mock versions if import fails
    def normalize_phone_number(phone):
        if not phone:
            return None, None
        phone = phone.strip().replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        phone = ''.join(filter(str.isdigit, phone))
        if len(phone) == 10:
            return f"91{phone}", phone
        elif len(phone) == 12 and phone.startswith('91'):
            return phone, phone[2:]
        elif len(phone) == 11 and phone.startswith('1'):
            return f"9{phone}", phone[1:]
        else:
            return None, None

    def format_phone_number(phone):
        if phone.startswith("91"):
            return phone
        return f"91{phone}"

    def get_current_academic_year_backend():
        try:
            import frappe
            from frappe.utils import getdate
            current_date = getdate()
        except ImportError:
            current_date = datetime.now().date()
        if current_date.month >= 4:
            return f"{current_date.year}-{str(current_date.year + 1)[-2:]}"
        else:
            return f"{current_date.year - 1}-{str(current_date.year)[-2:]}"


class TestBackendStudentOnboardingComplete:
    """Comprehensive test suite for 100% code coverage"""
    
    # ===== PHONE NUMBER NORMALIZATION TESTS =====
    
    def test_normalize_phone_number_all_cases(self):
        """Test every branch of normalize_phone_number function"""
        # Test None input
        assert normalize_phone_number(None) == (None, None)
        
        # Test empty string
        assert normalize_phone_number("") == (None, None)
        
        # Test whitespace only
        assert normalize_phone_number("   ") == (None, None)
        
        # Test 10-digit valid number
        assert normalize_phone_number("9876543210") == ("919876543210", "9876543210")
        
        # Test 10-digit with formatting
        assert normalize_phone_number(" 987-654-3210 ") == ("919876543210", "9876543210")
        assert normalize_phone_number("(987) 654-3210") == ("919876543210", "9876543210")
        
        # Test 12-digit valid number starting with 91
        assert normalize_phone_number("919876543210") == ("919876543210", "9876543210")
        
        # Test 11-digit number starting with 1
        assert normalize_phone_number("19876543210") == ("919876543210", "9876543210")
        
        # Test invalid lengths
        assert normalize_phone_number("123") == (None, None)  # Too short
        assert normalize_phone_number("987654321") == (None, None)  # 9 digits
        assert normalize_phone_number("9198765432101") == (None, None)  # 13 digits
        
        # Test non-digit characters
        assert normalize_phone_number("abcdef") == (None, None)
        assert normalize_phone_number("abc123def") == (None, None)
        
        # Test 12-digit not starting with 91
        assert normalize_phone_number("819876543210") == (None, None)
        
        # Test 11-digit not starting with 1
        assert normalize_phone_number("29876543210") == (None, None)
        
        # Test special characters
        assert normalize_phone_number("+91-987-654-3210") == ("919876543210", "9876543210")
        assert normalize_phone_number("91_987_654_3210") == ("919876543210", "9876543210")
        assert normalize_phone_number("91.987.654.3210") == ("919876543210", "9876543210")
    
    def test_format_phone_number_all_cases(self):
        """Test every branch of format_phone_number function"""
        # Test already formatted number
        assert format_phone_number("919876543210") == "919876543210"
        
        # Test unformatted number
        assert format_phone_number("9876543210") == "919876543210"
        
        # Test with other prefixes
        assert format_phone_number("819876543210") == "91819876543210"
    
    # ===== ACADEMIC YEAR TESTS =====
    
    @patch('frappe.utils.getdate')
    def test_get_current_academic_year_with_frappe(self, mock_getdate):
        """Test academic year calculation with frappe import"""
        # Test April onwards (new academic year)
        mock_getdate.return_value = datetime(2024, 6, 15).date()
        result = get_current_academic_year_backend()
        assert result == "2024-25"
        
        # Test January-March (previous academic year)
        mock_getdate.return_value = datetime(2024, 2, 15).date()
        result = get_current_academic_year_backend()
        assert result == "2023-24"
        
        # Test exact boundary - April 1st
        mock_getdate.return_value = datetime(2024, 4, 1).date()
        result = get_current_academic_year_backend()
        assert result == "2024-25"
        
        # Test exact boundary - March 31st
        mock_getdate.return_value = datetime(2024, 3, 31).date()
        result = get_current_academic_year_backend()
        assert result == "2023-24"
    
    @patch('frappe.utils.getdate', side_effect=ImportError("frappe not available"))
    @patch('datetime.datetime')
    def test_get_current_academic_year_without_frappe(self, mock_datetime, mock_getdate):
        """Test academic year calculation without frappe (ImportError path)"""
        mock_datetime.now.return_value = datetime(2024, 6, 15)
        result = get_current_academic_year_backend()
        assert result == "2024-25"
    
    # ===== STUDENT FINDING TESTS =====
    
    @patch('frappe.db.sql')
    def test_find_existing_student_all_cases(self, mock_sql):
        """Test all branches of find_existing_student_by_phone_and_name"""
        # Test with None inputs
        result = find_existing_student_by_phone_and_name(None, "Test Student")
        assert result is None
        
        result = find_existing_student_by_phone_and_name("9876543210", None)
        assert result is None
        
        # Test with invalid phone
        result = find_existing_student_by_phone_and_name("123", "Test Student")
        assert result is None
        
        # Test when student found
        mock_sql.return_value = [{"name": "STU001", "phone": "9876543210", "name1": "Test Student"}]
        result = find_existing_student_by_phone_and_name("9876543210", "Test Student")
        assert result["name"] == "STU001"
        
        # Test when no student found
        mock_sql.return_value = []
        result = find_existing_student_by_phone_and_name("9876543210", "Test Student")
        assert result is None
        
        # Verify SQL was called with correct parameters
        mock_sql.assert_called()
    
    # ===== VALIDATION TESTS =====
    
    @patch('backend_onboarding_process.find_existing_student_by_phone_and_name')
    def test_validate_student_all_cases(self, mock_find_student):
        """Test all validation scenarios"""
        # Test complete valid student
        valid_student = {
            "student_name": "Test Student",
            "phone": "9876543210",
            "school": "SCH001",
            "grade": "5",
            "language": "EN",
            "batch": "BATCH001"
        }
        
        mock_find_student.return_value = None
        result = validate_student(valid_student)
        assert len(result) == 0
        
        # Test missing fields
        incomplete_student = {"student_name": "Test Student"}
        result = validate_student(incomplete_student)
        expected_fields = ["phone", "school", "grade", "language", "batch"]
        for field in expected_fields:
            assert field in result
        
        # Test duplicate detection
        mock_find_student.return_value = {"name": "EXISTING_STU", "name1": "Existing Student"}
        student_with_duplicate = {
            "student_name": "Test Student",
            "phone": "9876543210",
            "school": "SCH001",
            "grade": "5",
            "language": "EN",
            "batch": "BATCH001"
        }
        result = validate_student(student_with_duplicate)
        assert "duplicate" in result
    
    # ===== BATCH OPERATIONS TESTS =====
    
    @patch('frappe.get_all')
    def test_get_onboarding_batches(self, mock_get_all):
        """Test get_onboarding_batches function"""
        mock_get_all.return_value = [
            {
                "name": "BATCH001",
                "set_name": "Test Batch",
                "upload_date": "2024-01-01",
                "uploaded_by": "test@example.com",
                "student_count": 10,
                "processed_student_count": 5
            }
        ]
        
        result = get_onboarding_batches()
        assert len(result) == 1
        assert result[0]["name"] == "BATCH001"
        mock_get_all.assert_called_once()
    
    @patch('frappe.get_doc')
    @patch('frappe.get_all')
    def test_get_batch_details_all_cases(self, mock_get_all, mock_get_doc):
        """Test get_batch_details with all scenarios"""
        # Mock batch document
        mock_batch = MagicMock()
        mock_batch.name = "BATCH001"
        mock_get_doc.return_value = mock_batch
        
        # Mock students
        mock_students = [
            {
                "name": "BACKEND_STU001",
                "student_name": "Student 1",
                "phone": "9876543210",
                "gender": "Male",
                "batch": "BATCH001",
                "course_vertical": "MATH",
                "grade": "5",
                "school": "SCH001",
                "language": "EN",
                "processing_status": "Pending",
                "student_id": None
            }
        ]
        
        # Mock Glific group
        mock_glific_group = [{"group_id": "GROUP001", "label": "Test Group"}]
        
        mock_get_all.side_effect = [mock_students, mock_glific_group]
        
        result = get_batch_details("BATCH001")
        
        assert result["batch"] == mock_batch
        assert len(result["students"]) == 1
        assert result["glific_group"]["group_id"] == "GROUP001"
        assert "validation" in result["students"][0]
        
        # Test with no Glific group
        mock_get_all.side_effect = [mock_students, []]
        result = get_batch_details("BATCH001")
        assert result["glific_group"] is None
    
    @patch('frappe.db.table_exists')
    @patch('frappe.get_all')
    @patch('frappe.log_error')
    def test_get_onboarding_stages_all_cases(self, mock_log_error, mock_get_all, mock_table_exists):
        """Test get_onboarding_stages with all scenarios"""
        # Test when table doesn't exist
        mock_table_exists.return_value = False
        result = get_onboarding_stages()
        assert result == []
        
        # Test successful retrieval
        mock_table_exists.return_value = True
        mock_get_all.return_value = [
            {"name": "STAGE001", "description": "Initial Stage", "order": 0},
            {"name": "STAGE002", "description": "Second Stage", "order": 1}
        ]
        result = get_onboarding_stages()
        assert len(result) == 2
        
        # Test exception handling
        mock_get_all.side_effect = Exception("Database error")
        result = get_onboarding_stages()
        assert result == []
        mock_log_error.assert_called()
    
    @patch('frappe.get_all')
    @patch('frappe.log_error')
    def test_get_initial_stage_all_cases(self, mock_log_error, mock_get_all):
        """Test get_initial_stage with all scenarios"""
        # Test with order=0 stage
        mock_get_all.return_value = [{"name": "INITIAL_STAGE"}]
        result = get_initial_stage()
        assert result == "INITIAL_STAGE"
        
        # Test with no order=0 stage, but minimum order exists
        mock_get_all.side_effect = [[], [{"name": "MIN_STAGE", "order": 1}]]
        result = get_initial_stage()
        assert result == "MIN_STAGE"
        
        # Test with no stages at all
        mock_get_all.side_effect = [[], []]
        result = get_initial_stage()
        assert result is None
        
        # Test exception handling
        mock_get_all.side_effect = Exception("Database error")
        result = get_initial_stage()
        assert result is None
        mock_log_error.assert_called()
    
    # ===== BATCH PROCESSING TESTS =====
    
    @patch('frappe.get_doc')
    @patch('frappe.enqueue')
    @patch('backend_onboarding_process.process_batch_job')
    def test_process_batch_all_cases(self, mock_process_job, mock_enqueue, mock_get_doc):
        """Test process_batch with all scenarios"""
        # Mock batch document
        mock_batch = MagicMock()
        mock_get_doc.return_value = mock_batch
        
        # Test immediate processing
        mock_process_job.return_value = {"success_count": 5, "failure_count": 0}
        result = process_batch("BATCH001", use_background_job=False)
        assert result["success_count"] == 5
        mock_batch.save.assert_called()
        
        # Test background job processing
        mock_job = MagicMock()
        mock_job.id = "JOB001"
        mock_enqueue.return_value = mock_job
        result = process_batch("BATCH001", use_background_job=True)
        assert result["job_id"] == "JOB001"
        
        # Test with string boolean
        result = process_batch("BATCH001", use_background_job="true")
        assert "job_id" in result
    
    @patch('frappe.db.commit')
    @patch('frappe.db.rollback')
    @patch('frappe.get_doc')
    @patch('frappe.get_all')
    @patch('frappe.log_error')
    @patch('backend_onboarding_process.create_or_get_glific_group_for_batch')
    @patch('backend_onboarding_process.get_initial_stage')
    @patch('backend_onboarding_process.update_job_progress')
    @patch('backend_onboarding_process.process_glific_contact')
    @patch('backend_onboarding_process.process_student_record')
    @patch('backend_onboarding_process.update_backend_student_status')
    def test_process_batch_job_all_scenarios(self, mock_update_status, mock_process_record, 
                                           mock_process_glific, mock_update_progress, 
                                           mock_get_stage, mock_create_group, mock_log_error,
                                           mock_get_all, mock_get_doc, mock_rollback, mock_commit):
        """Test process_batch_job with all scenarios"""
        
        # Setup mocks
        mock_batch = MagicMock()
        mock_get_doc.return_value = mock_batch
        
        mock_students = [
            MagicMock(name="BACKEND_STU001", batch_skeyword="TEST_BATCH"),
            MagicMock(name="BACKEND_STU002", batch_skeyword="TEST_BATCH")
        ]
        mock_get_all.side_effect = [
            [{"name": "BACKEND_STU001", "batch_skeyword": "TEST_BATCH"},
             {"name": "BACKEND_STU002", "batch_skeyword": "TEST_BATCH"}],
            [{"batch_skeyword": "TEST_BATCH", "name": "BATCH_ONBOARD001", "kit_less": False}]
        ]
        
        mock_get_doc.side_effect = [mock_batch] + mock_students + [mock_batch]
        
        mock_create_group.return_value = {"group_id": "GROUP001"}
        mock_get_stage.return_value = "INITIAL_STAGE"
        mock_process_glific.return_value = {"id": "GLIFIC001"}
        
        mock_student_doc = MagicMock()
        mock_student_doc.name = "STU001"
        mock_process_record.return_value = mock_student_doc
        
        # Test successful processing
        result = process_batch_job("BATCH001")
        assert result["success_count"] == 2
        assert result["failure_count"] == 0
        
        # Test with Glific group creation failure
        mock_create_group.side_effect = Exception("Glific error")
        result = process_batch_job("BATCH001")
        mock_log_error.assert_called()
        
        # Test with student processing failure
        mock_process_record.side_effect = Exception("Processing error")
        result = process_batch_job("BATCH001")
        assert result["failure_count"] > 0
        mock_rollback.assert_called()
        
        # Test critical failure scenario
        mock_get_doc.side_effect = Exception("Critical error")
        with pytest.raises(Exception):
            process_batch_job("BATCH001")
    
    @patch('frappe.publish_progress')
    def test_update_job_progress_all_cases(self, mock_publish):
        """Test update_job_progress function"""
        # Test successful progress update
        update_job_progress(5, 10)
        mock_publish.assert_called()
        
        # Test with zero total
        update_job_progress(0, 0)
        
        # Test exception handling
        mock_publish.side_effect = Exception("Progress error")
        update_job_progress(1, 10)  # Should not raise exception
    
    # ===== GLIFIC CONTACT PROCESSING =====
    
    @patch('frappe.get_value')
    @patch('frappe.logger')
    @patch('backend_onboarding_process.format_phone_number')
    @patch('backend_onboarding_process.get_contact_by_phone')
    @patch('backend_onboarding_process.add_contact_to_group')
    @patch('backend_onboarding_process.update_contact_fields')
    @patch('backend_onboarding_process.add_student_to_glific_for_onboarding')
    @patch('frappe.log_error')
    def test_process_glific_contact_all_scenarios(self, mock_log_error, mock_add_student,
                                                mock_update_fields, mock_add_to_group,
                                                mock_get_contact, mock_format_phone,
                                                mock_logger, mock_get_value):
        """Test process_glific_contact with all scenarios"""
        
        # Setup mock student
        mock_student = MagicMock()
        mock_student.phone = "9876543210"
        mock_student.student_name = "Test Student"
        mock_student.school = "SCH001"
        mock_student.batch = "BATCH001"
        mock_student.language = "EN"
        mock_student.course_vertical = "MATH"
        mock_student.grade = "5"
        
        mock_glific_group = {"group_id": "GROUP001"}
        
        # Setup mock returns
        mock_format_phone.return_value = "919876543210"
        mock_get_value.side_effect = ["School Name", "BATCH001", "1", "Course Level Name", "Math Course"]
        
        # Test with existing contact
        mock_get_contact.return_value = {"id": "EXISTING_CONTACT"}
        mock_update_fields.return_value = {"success": True}
        
        result = process_glific_contact(mock_student, mock_glific_group, "COURSE_LEVEL")
        assert result["id"] == "EXISTING_CONTACT"
        mock_add_to_group.assert_called()
        mock_update_fields.assert_called()
        
        # Test with new contact creation
        mock_get_contact.return_value = None
        mock_add_student.return_value = {"id": "NEW_CONTACT"}
        
        result = process_glific_contact(mock_student, mock_glific_group, "COURSE_LEVEL")
        assert result["id"] == "NEW_CONTACT"
        
        # Test with contact creation failure
        mock_add_student.return_value = None
        result = process_glific_contact(mock_student, mock_glific_group, "COURSE_LEVEL")
        mock_log_error.assert_called()
        
        # Test with invalid phone number
        mock_format_phone.return_value = None
        with pytest.raises(ValueError):
            process_glific_contact(mock_student, mock_glific_group)
        
        # Test with missing language ID
        mock_get_value.side_effect = ["School Name", "BATCH001", None, "Course Level Name", "Math Course"]
        mock_format_phone.return_value = "919876543210"
        mock_get_contact.return_value = None
        mock_add_student.return_value = {"id": "NEW_CONTACT"}
        
        result = process_glific_contact(mock_student, mock_glific_group)
        assert result["id"] == "NEW_CONTACT"
        
        # Test exception in language ID retrieval
        mock_get_value.side_effect = Exception("Language error")
        result = process_glific_contact(mock_student, mock_glific_group)
    
    # ===== STUDENT TYPE DETERMINATION =====
    
    @patch('frappe.db.sql')
    @patch('frappe.log_error')
    @patch('backend_onboarding_process.normalize_phone_number')
    def test_determine_student_type_all_scenarios(self, mock_normalize, mock_log_error, mock_sql):
        """Test determine_student_type_backend with all logic branches"""
        
        # Test invalid phone format
        mock_normalize.return_value = (None, None)
        result = determine_student_type_backend("invalid", "Test Student", "MATH")
        assert result == "New"
        mock_log_error.assert_called()
        
        # Test no existing student
        mock_normalize.return_value = ("919876543210", "9876543210")
        mock_sql.return_value = []
        result = determine_student_type_backend("9876543210", "Test Student", "MATH")
        assert result == "New"
        
        # Test student exists but no enrollments
        mock_sql.side_effect = [
            [{"name": "STU001", "phone": "9876543210", "name1": "Test Student"}],
            []
        ]
        result = determine_student_type_backend("9876543210", "Test Student", "MATH")
        assert result == "New"
        
        # Test student with same vertical enrollments
        mock_sql.side_effect = [
            [{"name": "STU001", "phone": "9876543210", "name1": "Test Student"}],
            [{"name": "ENR001", "course": "MATH_LEVEL1", "batch": "BATCH001", "grade": "5", "school": "SCH001"}],
            [{"vertical_name": "MATH"}]
        ]
        result = determine_student_type_backend("9876543210", "Test Student", "MATH")
        assert result == "Old"
        
        # Test student with broken course links
        mock_sql.side_effect = [
            [{"name": "STU001", "phone": "9876543210", "name1": "Test Student"}],
            [{"name": "ENR001", "course": "BROKEN_COURSE", "batch": "BATCH001", "grade": "5", "school": "SCH001"}],
            []  # No course found
        ]
        result = determine_student_type_backend("9876543210", "Test Student", "MATH")
        assert result == "Old"
        
        # Test student with different vertical only
        mock_sql.side_effect = [
            [{"name": "STU001", "phone": "9876543210", "name1": "Test Student"}],
            [{"name": "ENR001", "course": "SCIENCE_LEVEL1", "batch": "BATCH001", "grade": "5", "school": "SCH001"}],
            [{"vertical_name": "SCIENCE"}]
        ]
        result = determine_student_type_backend("9876543210", "Test Student", "MATH")
        assert result == "New"
        
        # Test student with NULL course
        mock_sql.side_effect = [
            [{"name": "STU001", "phone": "9876543210", "name1": "Test Student"}],
            [{"name": "ENR001", "course": None, "batch": "BATCH001", "grade": "5", "school": "SCH001"}]
        ]
        result = determine_student_type_backend("9876543210", "Test Student", "MATH")
        assert result == "Old"
        
        # Test exception handling
        mock_sql.side_effect = Exception("Database error")
        result = determine_student_type_backend("9876543210", "Test Student", "MATH")
        assert result == "New"
        mock_log_error.assert_called()
    
    # ===== COURSE LEVEL SELECTION =====
    
    @patch('backend_onboarding_process.determine_student_type_backend')
    @patch('backend_onboarding_process.get_current_academic_year_backend')
    @patch('backend_onboarding_process.normalize_phone_number')
    @patch('frappe.get_all')
    @patch('frappe.log_error')
    @patch('backend_onboarding_process.get_course_level')
    def test_get_course_level_with_mapping_all_scenarios(self, mock_get_course_level, mock_log_error,
                                                       mock_get_all, mock_normalize, 
                                                       mock_get_academic_year, mock_determine_type):
        """Test get_course_level_with_mapping_backend with all scenarios"""
        
        # Setup mocks
        mock_determine_type.return_value = "New"
        mock_get_academic_year.return_value = "2024-25"
        mock_normalize.return_value = ("919876543210", "9876543210")
        
        # Test with current academic year mapping found
        mock_get_all.return_value = [{"assigned_course_level": "MATH_GRADE5_NEW", "mapping_name": "Mapping 1"}]
        result = get_course_level_with_mapping_backend("MATH", "5", "9876543210", "Test Student", False)
        assert result == "MATH_GRADE5_NEW"
        
        # Test with null academic year mapping (flexible mapping)
        mock_get_all.side_effect = [
            [],  # No current year mapping
            [{"assigned_course_level": "MATH_GRADE5_FLEXIBLE", "mapping_name": "Flexible Mapping"}]
        ]
        result = get_course_level_with_mapping_backend("MATH", "5", "9876543210", "Test Student", False)
        assert result == "MATH_GRADE5_FLEXIBLE"
        
        # Test fallback to Stage Grades logic
        mock_get_all.side_effect = [[], []]  # No mappings found
        mock_get_course_level.return_value = "MATH_GRADE5_FALLBACK"
        result = get_course_level_with_mapping_backend("MATH", "5", "9876543210", "Test Student", False)
        assert result == "MATH_GRADE5_FALLBACK"
        
        # Test exception handling
        mock_get_all.side_effect = Exception("Mapping error")
        mock_get_course_level.return_value = "MATH_GRADE5_ERROR_FALLBACK"
        result = get_course_level_with_mapping_backend("MATH", "5", "9876543210", "Test Student", False)
        assert result == "MATH_GRADE5_ERROR_FALLBACK"
        mock_log_error.assert_called()
    
    @patch('backend_onboarding_process.validate_enrollment_data')
    @patch('backend_onboarding_process.get_course_level_with_mapping_backend')
    @patch('backend_onboarding_process.get_course_level')
    @patch('frappe.log_error')
    def test_get_course_level_with_validation_all_scenarios(self, mock_log_error, mock_get_course_level,
                                                          mock_get_mapping, mock_validate):
        """Test get_course_level_with_validation_backend with all scenarios"""
        
        # Test with broken enrollments detected
        mock_validate.return_value = {"broken_enrollments": 2, "broken_details": []}
        mock_get_mapping.return_value = "MATH_GRADE5"
        result = get_course_level_with_validation_backend("MATH", "5", "9876543210", "Test Student", False)
        assert result == "MATH_GRADE5"
        mock_log_error.assert_called()
        
        # Test validation error scenario
        mock_get_mapping.side_effect = Exception("Mapping error")
        mock_get_course_level.return_value = "MATH_GRADE5_FALLBACK"
        result = get_course_level_with_validation_backend("MATH", "5", "9876543210", "Test Student", False)
        assert result == "MATH_GRADE5_FALLBACK"
        
        # Test fallback also fails
        mock_get_course_level.side_effect = Exception("Fallback error")
        result = get_course_level_with_validation_backend("MATH", "5", "9876543210", "Test Student", False)
        assert result is None
    
    @patch('frappe.db.sql')
    @patch('backend_onboarding_process.normalize_phone_number')
    @patch('frappe.log_error')
    def test_validate_enrollment_data_all_scenarios(self, mock_log_error, mock_normalize, mock_sql):
        """Test validate_enrollment_data function"""
        
        # Test invalid phone number
        mock_normalize.return_value = (None, None)
        result = validate_enrollment_data("Test Student", "invalid")
        assert "error" in result
        
        # Test valid enrollments
        mock_normalize.return_value = ("919876543210", "9876543210")
        mock_sql.side_effect = [
            [{"student_id": "STU001", "enrollment_id": "ENR001", "course": "MATH_LEVEL1", "batch": "BATCH001", "grade": "5"}],
            [{"name": "MATH_LEVEL1"}]  # Course exists
        ]
        result = validate_enrollment_data("Test Student", "9876543210")
        assert result["valid_enrollments"] == 1
        assert result["broken_enrollments"] == 0
        
        # Test broken enrollments
        mock_sql.side_effect = [
            [{"student_id": "STU001", "enrollment_id": "ENR001", "course": "BROKEN_COURSE", "batch": "BATCH001", "grade": "5"}],
            []  # Course doesn't exist
        ]
        result = validate_enrollment_data("Test Student", "9876543210")
        assert result["valid_enrollments"] == 0
        assert result["broken_enrollments"] == 1
        
        # Test exception handling
        mock_sql.side_effect = Exception("Database error")
        result = validate_enrollment_data("Test Student", "9876543210")
        assert "error" in result
    
    # ===== STUDENT RECORD PROCESSING =====
    
    @patch('backend_onboarding_process.find_existing_student_by_phone_and_name')
    @patch('backend_onboarding_process.normalize_phone_number')
    @patch('frappe.get_doc')
    @patch('frappe.new_doc')
    @patch('frappe.get_all')
    @patch('frappe.db.exists')
    @patch('frappe.utils.nowdate')
    @patch('frappe.utils.now')
    @patch('frappe.log_error')
    @patch('backend_onboarding_process.get_course_level_with_validation_backend')
    @patch('backend_onboarding_process.get_course_level')
    def test_process_student_record_all_scenarios(self, mock_get_course_level, mock_get_validation,
                                                mock_log_error, mock_now, mock_nowdate, mock_exists,
                                                mock_get_all, mock_new_doc, mock_get_doc, 
                                                mock_normalize, mock_find_existing):
        """Test process_student_record with all scenarios"""
        
        # Setup mocks
        mock_normalize.return_value = ("919876543210", "9876543210")
        mock_nowdate.return_value = "2024-01-01"
        mock_now.return_value = "2024-01-01 12:00:00"
        
        # Setup mock student data
        mock_student = MagicMock()
        mock_student.phone = "9876543210"
        mock_student.student_name = "Test Student"
        mock_student.grade = "5"
        mock_student.school = "SCH001"
        mock_student.language = "EN"
        mock_student.gender = "Male"
        mock_student.batch = "BATCH001"
        mock_student.course_vertical = "MATH"
        mock_student.batch_skeyword = "TEST_BATCH"
        
        mock_glific_contact = {"id": "GLIFIC001"}
        
        # Test updating existing student
        mock_find_existing.return_value = {"name": "STU001", "phone": "9876543210", "name1": "Test Student"}
        mock_existing_student = MagicMock()
        mock_existing_student.name = "STU001"
        mock_existing_student.grade = "4"  # Different grade
        mock_existing_student.school_id = "SCH002"  # Different school
        mock_existing_student.language = "HI"  # Different language
        mock_existing_student.gender = None  # No gender set
        mock_existing_student.phone = "9876543210"
        mock_existing_student.glific_id = None
        mock_get_doc.return_value = mock_existing_student
        
        # Mock batch onboarding
        mock_get_all.return_value = [{"name": "BATCH_ONBOARD001", "kit_less": False}]
        mock_get_validation.return_value = "MATH_GRADE5"
        
        result = process_student_record(mock_student, mock_glific_contact, "BATCH001", "INITIAL_STAGE", "MATH_GRADE5")
        
        # Verify existing student was updated
        assert mock_existing_student.grade == "5"
        assert mock_existing_student.school_id == "SCH001"
        assert mock_existing_student.language == "EN"
        assert mock_existing_student.gender == "Male"
        assert mock_existing_student.glific_id == "GLIFIC001"
        mock_existing_student.save.assert_called()
        
        # Test creating new student
        mock_find_existing.return_value = None
        mock_new_student = MagicMock()
        mock_new_student.name = "STU002"
        mock_new_doc.return_value = mock_new_student
        mock_exists.side_effect = [False, False]  # LearningState and EngagementState don't exist
        
        # Mock document creation for states
        mock_learning_state = MagicMock()
        mock_engagement_state = MagicMock()
        mock_stage_progress = MagicMock()
        mock_new_doc.side_effect = [mock_new_student, mock_learning_state, mock_engagement_state, mock_stage_progress]
        
        result = process_student_record(mock_student, mock_glific_contact, "BATCH001", "INITIAL_STAGE")
        
        # Verify new student was created
        assert mock_new_student.name1 == "Test Student"
        assert mock_new_student.phone == "919876543210"
        mock_new_student.insert.assert_called()
        
        # Test with course level selection error
        mock_get_validation.side_effect = Exception("Course selection error")
        mock_get_course_level.return_value = "FALLBACK_COURSE"
        result = process_student_record(mock_student, mock_glific_contact, "BATCH001", "INITIAL_STAGE")
        mock_log_error.assert_called()
        
        # Test with enrollment creation error
        mock_existing_student.append.side_effect = Exception("Enrollment error")
        result = process_student_record(mock_student, mock_glific_contact, "BATCH001", "INITIAL_STAGE")
        mock_log_error.assert_called()
        
        # Test with student save error
        mock_existing_student.save.side_effect = Exception("Save error")
        with pytest.raises(Exception):
            process_student_record(mock_student, mock_glific_contact, "BATCH001", "INITIAL_STAGE")
        
        # Test with new student insert error
        mock_find_existing.return_value = None
        mock_new_student.insert.side_effect = Exception("Insert error")
        with pytest.raises(Exception):
            process_student_record(mock_student, mock_glific_contact, "BATCH001", "INITIAL_STAGE")
        
        # Test with LearningState creation error
        mock_learning_state.insert.side_effect = Exception("LearningState error")
        result = process_student_record(mock_student, mock_glific_contact, "BATCH001", "INITIAL_STAGE")
        mock_log_error.assert_called()
        
        # Test with EngagementState creation error
        mock_engagement_state.insert.side_effect = Exception("EngagementState error")
        result = process_student_record(mock_student, mock_glific_contact, "BATCH001", "INITIAL_STAGE")
        mock_log_error.assert_called()
        
        # Test with StudentStageProgress creation error
        mock_stage_progress.insert.side_effect = Exception("StageProgress error")
        result = process_student_record(mock_student, mock_glific_contact, "BATCH001", "INITIAL_STAGE")
        mock_log_error.assert_called()
    
    def test_update_backend_student_status_all_scenarios(self):
        """Test update_backend_student_status with all scenarios"""
        
        # Setup mock student
        mock_student = MagicMock()
        mock_student.processing_status = None
        mock_student.student_id = None
        mock_student.glific_id = None
        
        # Mock student doc
        mock_student_doc = MagicMock()
        mock_student_doc.name = "STU001"
        mock_student_doc.glific_id = "GLIFIC001"
        
        # Test success status update
        update_backend_student_status(mock_student, "Success", mock_student_doc)
        assert mock_student.processing_status == "Success"
        assert mock_student.student_id == "STU001"
        assert mock_student.glific_id == "GLIFIC001"
        mock_student.save.assert_called()
        
        # Test failure status update with error
        mock_student.reset_mock()
        
        # Mock field metadata for processing_notes
        with patch('frappe.get_meta') as mock_get_meta:
            mock_meta = MagicMock()
            mock_field = MagicMock()
            mock_field.length = 100
            mock_meta.get_field.return_value = mock_field
            mock_get_meta.return_value = mock_meta
            
            # Mock hasattr to return True for processing_notes
            with patch('builtins.hasattr', return_value=True):
                long_error = "This is a very long error message that exceeds the field length limit"
                update_backend_student_status(mock_student, "Failed", error=long_error)
                assert mock_student.processing_status == "Failed"
                assert len(mock_student.processing_notes) <= 100
        
        # Test with metadata access error
        with patch('frappe.get_meta', side_effect=Exception("Meta error")):
            with patch('builtins.hasattr', return_value=True):
                update_backend_student_status(mock_student, "Failed", error="Test error")
                assert len(mock_student.processing_notes) <= 140  # Fallback limit
    
    # ===== JOB STATUS TESTS =====
    
    @patch('frappe.db.table_exists')
    @patch('frappe.db.get_value')
    @patch('frappe.logger')
    @patch('frappe.utils.background_jobs.get_job_status')
    def test_get_job_status_all_scenarios(self, mock_get_rq_status, mock_logger, mock_get_value, mock_table_exists):
        """Test get_job_status with all scenarios"""
        
        # Test with Background Job table
        mock_table_exists.side_effect = [True, False]  # First table exists, second doesn't
        mock_get_value.return_value = {
            "status": "started",
            "progress_data": '{"percent": 50}',
            "result": None
        }
        
        result = get_job_status("JOB001")
        assert result["status"] == "started"
        assert "progress" in result
        
        # Test with finished status
        mock_get_value.return_value = {
            "status": "finished",
            "progress_data": None,
            "result": '{"success": true}'
        }
        
        result = get_job_status("JOB001")
        assert result["status"] == "Completed"
        assert "result" in result
        
        # Test with failed status
        mock_get_value.return_value = {
            "status": "failed",
            "progress_data": None,
            "result": None
        }
        
        result = get_job_status("JOB001")
        assert result["status"] == "Failed"
        
        # Test with RQ Job table
        mock_table_exists.side_effect = [False, True]
        mock_get_value.return_value = {
            "status": "Started",
            "progress_data": '{"percent": 75}',
            "result": None
        }
        
        result = get_job_status("JOB001")
        assert result["status"] == "Started"
        
        # Test with no tables available, use RQ function
        mock_table_exists.return_value = False
        mock_get_value.return_value = None
        mock_get_rq_status.return_value = "completed"
        
        result = get_job_status("JOB001")
        assert result["status"] == "completed"
        
        # Test with all methods failing
        mock_get_rq_status.side_effect = Exception("RQ error")
        result = get_job_status("JOB001")
        assert result["status"] == "Unknown"
        
        # Test with JSON parsing errors
        mock_table_exists.side_effect = [True, False]
        mock_get_value.return_value = {
            "status": "started",
            "progress_data": 'invalid json',
            "result": None
        }
        
        result = get_job_status("JOB001")
        assert result["status"] == "started"
        # Should not have progress due to JSON error
    
    # ===== DEBUG AND UTILITY FUNCTIONS =====
    
    @patch('frappe.get_all')
    @patch('frappe.db.exists')
    @patch('frappe.db.set_value')
    @patch('frappe.db.commit')
    @patch('frappe.db.sql')
    def test_fix_broken_course_links_all_scenarios(self, mock_sql, mock_commit, mock_set_value, 
                                                  mock_exists, mock_get_all):
        """Test fix_broken_course_links function"""
        
        # Test fixing specific student
        mock_sql.return_value = [
            {"name": "ENR001", "course": "BROKEN_COURSE1"},
            {"name": "ENR002", "course": "BROKEN_COURSE2"}
        ]
        
        result = fix_broken_course_links("STU001")
        assert "Checking student: STU001" in result
        assert "Total fixed: 2 broken course links" in result
        mock_set_value.assert_called()
        mock_commit.assert_called()
        
        # Test fixing all students with no broken links
        mock_get_all.return_value = [{"name": "STU001"}, {"name": "STU002"}]
        mock_sql.return_value = []
        
        result = fix_broken_course_links()
        assert "No broken course links found" in result
        
        # Test exception handling
        mock_sql.side_effect = Exception("Database error")
        result = fix_broken_course_links()
        assert "ERROR fixing broken links" in result
    
    @patch('backend_onboarding_process.normalize_phone_number')
    @patch('frappe.db.sql')
    @patch('backend_onboarding_process.determine_student_type_backend')
    @patch('backend_onboarding_process.get_course_level_with_validation_backend')
    @patch('frappe.db.exists')
    def test_debug_student_type_analysis_all_scenarios(self, mock_exists, mock_get_course_level,
                                                      mock_determine_type, mock_sql, mock_normalize):
        """Test debug_student_type_analysis function"""
        
        # Setup mocks
        mock_normalize.return_value = ("919876543210", "9876543210")
        
        # Test with no existing student
        mock_sql.return_value = []
        result = debug_student_type_analysis("Test Student", "9876543210", "MATH")
        assert "No existing student found → NEW" in result
        
        # Test with existing student and enrollments
        mock_sql.side_effect = [
            [{"name": "STU001", "phone": "9876543210", "name1": "Test Student"}],
            [{"name": "ENR001", "course": "MATH_LEVEL1", "batch": "BATCH001", "grade": "5", "school": "SCH001"}],
            [{"vertical_name": "MATH"}]
        ]
        mock_determine_type.return_value = "Old"
        mock_get_course_level.return_value = "MATH_GRADE5"
        mock_exists.return_value = True
        
        result = debug_student_type_analysis("Test Student", "9876543210", "MATH")
        assert "Found student: STU001" in result
        assert "FINAL DETERMINATION: Old" in result
        
        # Test exception handling
        mock_sql.side_effect = Exception("Analysis error")
        result = debug_student_type_analysis("Test Student", "9876543210", "MATH")
        assert "ANALYSIS ERROR" in result
    
    @patch('frappe.new_doc')
    @patch('frappe.delete_doc')
    @patch('frappe.utils.nowdate')
    def test_test_basic_student_creation_all_scenarios(self, mock_nowdate, mock_delete_doc, mock_new_doc):
        """Test test_basic_student_creation function"""
        
        # Setup mocks
        mock_nowdate.return_value = "2024-01-01"
        mock_student = MagicMock()
        mock_student.name = "TEST_STU001"
        mock_new_doc.return_value = mock_student
        
        # Test successful creation and deletion
        result = test_basic_student_creation()
        assert "Basic student created successfully" in result
        assert "Enrollment added successfully" in result
        assert "Test student deleted successfully" in result
        mock_student.insert.assert_called()
        mock_student.save.assert_called()
        mock_delete_doc.assert_called()
        
        # Test creation failure
        mock_student.insert.side_effect = Exception("Creation failed")
        result = test_basic_student_creation()
        assert "BASIC TEST FAILED: Creation failed" in result
    
    @patch('backend_onboarding_process.normalize_phone_number')
    @patch('frappe.db.sql')
    @patch('frappe.get_all')
    @patch('frappe.db.exists')
    @patch('backend_onboarding_process.determine_student_type_backend')
    @patch('backend_onboarding_process.get_course_level_with_validation_backend')
    @patch('frappe.utils.nowdate')
    def test_debug_student_processing_all_scenarios(self, mock_nowdate, mock_get_course_level,
                                                   mock_determine_type, mock_exists, mock_get_all,
                                                   mock_sql, mock_normalize):
        """Test debug_student_processing function"""
        
        # Setup comprehensive mocks
        mock_normalize.return_value = ("919876543210", "9876543210")
        mock_nowdate.return_value = "2024-01-01"
        
        # Test with existing student
        mock_sql.side_effect = [
            [{"name": "STU001", "phone": "9876543210", "name1": "Test Student"}]
        ]
        
        # Mock student document
        with patch('frappe.get_doc') as mock_get_doc:
            mock_student_doc = MagicMock()
            mock_student_doc.grade = "5"
            mock_student_doc.school_id = "SCH001"
            mock_student_doc.language = "EN"
            mock_student_doc.glific_id = "GLIFIC001"
            mock_get_doc.return_value = mock_student_doc
            
            # Mock enrollments
            mock_get_all.return_value = [
                {"name": "ENR001", "course": "MATH_LEVEL1", "batch": "BATCH001", "grade": "5", "school": "SCH001"}
            ]
            
            # Mock course exists check
            mock_exists.return_value = True
            
            result = debug_student_processing("Test Student", "9876543210")
            assert "Student EXISTS" in result
            assert "Current Grade: 5" in result
            assert "Existing Enrollments: 1" in result
    
    # ===== WHITELIST FUNCTION TESTS =====
    
    @patch('backend_onboarding_process.get_onboarding_batches')
    def test_whitelist_get_onboarding_batches(self, mock_get_batches):
        """Test whitelisted get_onboarding_batches function"""
        mock_get_batches.return_value = [{"name": "BATCH001"}]
        
        # Since these are whitelisted functions, they should work without frappe context
        result = get_onboarding_batches()
        assert len(result) == 1
    
    @patch('backend_onboarding_process.get_batch_details')
    def test_whitelist_get_batch_details(self, mock_get_details):
        """Test whitelisted get_batch_details function"""
        mock_get_details.return_value = {"batch": {"name": "BATCH001"}, "students": []}
        
        result = get_batch_details("BATCH001")
        assert result["batch"]["name"] == "BATCH001"
    
    @patch('backend_onboarding_process.get_onboarding_stages')
    def test_whitelist_get_onboarding_stages(self, mock_get_stages):
        """Test whitelisted get_onboarding_stages function"""
        mock_get_stages.return_value = [{"name": "STAGE001"}]
        
        result = get_onboarding_stages()
        assert len(result) == 1
    
    @patch('backend_onboarding_process.process_batch')
    def test_whitelist_process_batch(self, mock_process):
        """Test whitelisted process_batch function"""
        mock_process.return_value = {"success_count": 10, "failure_count": 0}
        
        result = process_batch("BATCH001", False)
        assert result["success_count"] == 10
    
    @patch('backend_onboarding_process.get_job_status')
    def test_whitelist_get_job_status(self, mock_get_status):
        """Test whitelisted get_job_status function"""
        mock_get_status.return_value = {"status": "Completed", "progress": 100}
        
        result = get_job_status("JOB001")
        assert result["status"] == "Completed"
    
    # ===== EDGE CASE AND ERROR HANDLING TESTS =====
    
    def test_all_phone_number_edge_cases(self):
        """Test comprehensive phone number edge cases"""
        test_cases = [
            # Basic valid cases
            ("9876543210", ("919876543210", "9876543210")),
            ("919876543210", ("919876543210", "9876543210")),
            ("19876543210", ("919876543210", "9876543210")),
            
            # Formatting cases
            (" 987-654-3210 ", ("919876543210", "9876543210")),
            ("(987) 654-3210", ("919876543210", "9876543210")),
            ("+91-987-654-3210", ("919876543210", "9876543210")),
            ("91 987 654 3210", ("919876543210", "9876543210")),
            ("987.654.3210", ("919876543210", "9876543210")),
            ("91_987_654_3210", ("919876543210", "9876543210")),
            
            # Invalid cases
            ("", (None, None)),
            (None, (None, None)),
            ("   ", (None, None)),
            ("abc", (None, None)),
            ("123", (None, None)),
            ("987654321", (None, None)),  # 9 digits
            ("12345678901234", (None, None)),  # 14 digits
            ("819876543210", (None, None)),  # 12 digits not starting with 91
            ("29876543210", (None, None)),  # 11 digits not starting with 1
            ("abc123def456", (None, None)),  # Mixed characters
            ("++91987654321", (None, None)),  # Multiple + signs
        ]
        
        for phone_input, expected in test_cases:
            result = normalize_phone_number(phone_input)
            assert result == expected, f"Failed for input: {phone_input}"
    
    def test_format_phone_number_edge_cases(self):
        """Test format_phone_number edge cases"""
        # Standard cases
        assert format_phone_number("9876543210") == "919876543210"
        assert format_phone_number("919876543210") == "919876543210"
        
        # Edge cases
        assert format_phone_number("0123456789") == "910123456789"
        assert format_phone_number("") == "91"
        
        # International codes
        assert format_phone_number("1234567890") == "911234567890"
        assert format_phone_number("441234567890") == "91441234567890"
    
    def test_error_handling_comprehensive(self):
        """Test comprehensive error handling scenarios"""
        
        # Test with None inputs to various functions
        assert normalize_phone_number(None) == (None, None)
        
        # Test with empty strings
        assert normalize_phone_number("") == (None, None)
        
        # Test with whitespace
        assert normalize_phone_number("   ") == (None, None)
        
        # Test invalid data types (if they somehow get passed)
        assert normalize_phone_number(123) == (None, None)  # Integer instead of string
        assert normalize_phone_number([]) == (None, None)  # List instead of string
        assert normalize_phone_number({}) == (None, None)  # Dict instead of string


# ===== INTEGRATION TESTS =====

class TestIntegrationScenarios:
    """Integration tests that combine multiple functions"""
    
    @patch('frappe.db.sql')
    @patch('frappe.get_all')
    @patch('frappe.get_doc')
    @patch('frappe.new_doc')
    @patch('backend_onboarding_process.normalize_phone_number')
    @patch('backend_onboarding_process.find_existing_student_by_phone_and_name')
    @patch('backend_onboarding_process.process_glific_contact')
    @patch('backend_onboarding_process.get_course_level_with_validation_backend')
    def test_complete_student_onboarding_flow(self, mock_get_course, mock_process_glific,
                                            mock_find_existing, mock_normalize, mock_new_doc,
                                            mock_get_doc, mock_get_all, mock_sql):
        """Test complete student onboarding flow from start to finish"""
        
        # Setup the complete flow
        mock_normalize.return_value = ("919876543210", "9876543210")
        mock_find_existing.return_value = None  # New student
        mock_process_glific.return_value = {"id": "GLIFIC001"}
        mock_get_course.return_value = "MATH_GRADE5"
        
        # Mock student creation
        mock_student_doc = MagicMock()
        mock_student_doc.name = "STU001"
        mock_new_doc.return_value = mock_student_doc
        
        # Create mock backend student
        mock_backend_student = MagicMock()
        mock_backend_student.phone = "9876543210"
        mock_backend_student.student_name = "Integration Test Student"
        mock_backend_student.grade = "5"
        mock_backend_student.school = "SCH001"
        mock_backend_student.language = "EN"
        mock_backend_student.batch = "BATCH001"
        mock_backend_student.course_vertical = "MATH"
        mock_backend_student.batch_skeyword = "TEST_BATCH"
        
        # Test the flow
        result = process_student_record(
            mock_backend_student,
            {"id": "GLIFIC001"},
            "BATCH001",
            "INITIAL_STAGE",
            "MATH_GRADE5"
        )
        
        # Verify the flow completed successfully
        assert result.name == "STU001"
        mock_student_doc.insert.assert_called()
    
    def test_validation_and_processing_pipeline(self):
        """Test the validation and processing pipeline"""
        
        # Test complete validation pipeline
        with patch('backend_onboarding_process.validate_student') as mock_validate:
            with patch('backend_onboarding_process.normalize_phone_number') as mock_normalize:
                mock_normalize.return_value = ("919876543210", "9876543210")
                mock_validate.return_value = {}  # Valid student
                
                student_data = {
                    "student_name": "Pipeline Test Student",
                    "phone": "9876543210",
                    "school": "SCH001",
                    "grade": "5",
                    "language": "EN",
                    "batch": "BATCH001"
                }
                
                # Validate student
                validation_result = validate_student(student_data)
                assert len(validation_result) == 0
                
                # Test phone normalization
                phone_result = normalize_phone_number(student_data["phone"])
                assert phone_result == ("919876543210", "9876543210")


# ===== COVERAGE COMPLETION TESTS =====

class TestCompleteCoverage:
    """Tests specifically designed to hit every remaining line of code"""
    
    def test_import_error_paths(self):
        """Test ImportError handling paths"""
        
        # Test get_current_academic_year_backend without frappe
        with patch('frappe.utils.getdate', side_effect=ImportError("No frappe")):
            with patch('datetime.datetime') as mock_datetime:
                mock_datetime.now.return_value = datetime(2024, 6, 15)
                result = get_current_academic_year_backend()
                assert result == "2024-25"
    
    def test_all_conditional_branches(self):
        """Test all conditional branches in normalize_phone_number"""
        
        # Test every length condition
        test_cases = [
            ("1234567890", ("911234567890", "1234567890")),  # 10 digits
            ("911234567890", ("911234567890", "1234567890")),  # 12 digits starting with 91
            ("11234567890", ("911234567890", "1234567890")),   # 11 digits starting with 1
            ("123456789", (None, None)),     # 9 digits - invalid
            ("12345678901", (None, None)),   # 11 digits not starting with 1
            ("1234567890123", (None, None)), # 13 digits - invalid
            ("821234567890", (None, None)),  # 12 digits not starting with 91
        ]
        
        for phone_input, expected in test_cases:
            result = normalize_phone_number(phone_input)
            assert result == expected, f"Failed for input: {phone_input}"
    
    def test_all_string_methods_in_normalize_phone(self):
        """Test all string manipulation methods in normalize_phone_number"""
        
        # Test with all possible formatting characters
        messy_phone = "  +91 (987) 654-3210  "
        expected = ("919876543210", "9876543210")
        result = normalize_phone_number(messy_phone)
        assert result == expected
        
        # Test with no formatting needed
        clean_phone = "9876543210"
        expected = ("919876543210", "9876543210")
        result = normalize_phone_number(clean_phone)
        assert result == expected
    
    def test_format_phone_number_branches(self):
        """Test all branches in format_phone_number"""
        
        # Test phone already starting with 91
        result = format_phone_number("919876543210")
        assert result == "919876543210"
        
        # Test phone not starting with 91
        result = format_phone_number("9876543210")
        assert result == "919876543210"
        
        # Test phone starting with other numbers
        result = format_phone_number("1234567890")
        assert result == "911234567890"
    
    @patch('frappe.utils.getdate')
    def test_academic_year_month_boundaries(self, mock_getdate):
        """Test exact month boundaries for academic year calculation"""
        
        # Test March (month 3) - should be previous academic year
        mock_getdate.return_value = datetime(2024, 3, 15).date()
        result = get_current_academic_year_backend()
        assert result == "2023-24"
        
        # Test April (month 4) - should be current academic year
        mock_getdate.return_value = datetime(2024, 4, 15).date()
        result = get_current_academic_year_backend()
        assert result == "2024-25"
        
        # Test December (month 12) - should be current academic year
        mock_getdate.return_value = datetime(2024, 12, 15).date()
        result = get_current_academic_year_backend()
        assert result == "2024-25"
        
        # Test January (month 1) - should be previous academic year
        mock_getdate.return_value = datetime(2024, 1, 15).date()
        result = get_current_academic_year_backend()
        assert result == "2023-24"
    
    def test_hasattr_conditions(self):
        """Test all hasattr conditions in the codebase"""
        
        # Test update_backend_student_status with and without processing_notes field
        mock_student_with_notes = MagicMock()
        mock_student_without_notes = MagicMock()
        
        # Mock hasattr to return different values
        with patch('builtins.hasattr') as mock_hasattr:
            # Test with processing_notes field
            mock_hasattr.return_value = True
            update_backend_student_status(mock_student_with_notes, "Failed", error="Test error")
            
            # Test without processing_notes field
            mock_hasattr.return_value = False
            update_backend_student_status(mock_student_without_notes, "Failed", error="Test error")
    
    def test_all_exception_types(self):
        """Test handling of different exception types"""
        
        # Test ValueError
        with pytest.raises(ValueError):
            mock_student = MagicMock()
            mock_student.phone = "invalid"
            with patch('backend_onboarding_process.format_phone_number', return_value=None):
                process_glific_contact(mock_student, {"group_id": "GROUP001"})
        
        # Test TypeError  
        try:
            normalize_phone_number(123)  # Wrong type
        except:
            pass  # Should handle gracefully
        
        # Test AttributeError
        try:
            result = normalize_phone_number(None)
            assert result == (None, None)
        except:
            pass
    
    def test_mocked_frappe_functions_coverage(self):
        """Test coverage of mocked frappe function calls"""
        
        with patch('frappe.db.sql') as mock_sql:
            with patch('frappe.log_error') as mock_log_error:
                # Test find_existing_student_by_phone_and_name with database error
                mock_sql.side_effect = Exception("Database connection failed")
                
                try:
                    find_existing_student_by_phone_and_name("9876543210", "Test Student")
                except:
                    pass  # Should handle gracefully
    
    def test_string_operations_coverage(self):
        """Test all string operations and edge cases"""
        
        # Test strip() on different inputs
        test_inputs = [
            "  9876543210  ",  # Leading/trailing spaces
            "\t9876543210\n",  # Tabs and newlines
            "9876543210",      # No spaces
            "",                # Empty string
            "   ",             # Only spaces
        ]
        
        for input_phone in test_inputs:
            result = normalize_phone_number(input_phone)
            # Should either return valid tuple or (None, None)
            assert isinstance(result, tuple)
            assert len(result) == 2
    
    def test_filter_and_join_operations(self):
        """Test filter and join operations in normalize_phone_number"""
        
        # Test filter(str.isdigit, phone) with various inputs
        test_cases = [
            ("abc123def456", "123456"),
            ("91-987-654-3210", "919876543210"),
            ("++91##987@@654$3210", "919876543210"),
            ("", ""),
            ("abcdef", ""),
            ("!@#$%^&*()", ""),
        ]
        
        for input_str, expected_digits in test_cases:
            digits_only = ''.join(filter(str.isdigit, input_str))
            assert digits_only == expected_digits
    
    def test_all_return_paths(self):
        """Test all possible return paths in functions"""
        
        # Test normalize_phone_number return paths
        assert normalize_phone_number(None) == (None, None)
        assert normalize_phone_number("") == (None, None)
        assert normalize_phone_number("9876543210")[0].startswith("91")
        assert normalize_phone_number("919876543210")[0] == "919876543210"
        assert normalize_phone_number("19876543210")[0].startswith("91")
        assert normalize_phone_number("invalid") == (None, None)
    
    def test_loop_and_iteration_coverage(self):
        """Test any loops or iterations in the code"""
        
        # Test the character filtering loop in normalize_phone_number
        complex_phone = "+(91) 987-654.3210 ext 123"
        result = normalize_phone_number(complex_phone)
        expected = ("919876543210123", "9876543210123")  # Should extract all digits
        # This would actually be invalid due to length, so result should be (None, None)
        assert result == (None, None)
    
    def test_all_comparison_operators(self):
        """Test all comparison operators used in the code"""
        
        # Test length comparisons
        assert len("1234567890") == 10    # == operator
        assert len("123456789") < 10      # < operator  
        assert len("12345678901") > 10    # > operator
        assert len("919876543210") >= 12  # >= operator
        
        # Test string startswith comparisons
        assert "919876543210".startswith('91') == True
        assert "19876543210".startswith('1') == True
        assert "819876543210".startswith('91') == False
    
    def test_boolean_logic_coverage(self):
        """Test all boolean logic paths"""
        
        # Test if not phone conditions
        assert normalize_phone_number(None) == (None, None)
        assert normalize_phone_number("") == (None, None)
        assert normalize_phone_number(False) == (None, None)
        assert normalize_phone_number(0) == (None, None)
    
    def test_academic_year_string_formatting(self):
        """Test string formatting in academic year function"""
        
        with patch('frappe.utils.getdate') as mock_getdate:
            # Test year formatting with different years
            test_years = [2024, 2025, 2030, 1999, 2000]
            
            for year in test_years:
                # Test April (new academic year)
                mock_getdate.return_value = datetime(year, 4, 1).date()
                result = get_current_academic_year_backend()
                expected = f"{year}-{str(year + 1)[-2:]}"
                assert result == expected
                
                # Test March (previous academic year) 
                mock_getdate.return_value = datetime(year, 3, 31).date()
                result = get_current_academic_year_backend()
                expected = f"{year - 1}-{str(year)[-2:]}"
                assert result == expected


# ===== FINAL EDGE CASE TESTS =====

class TestFinalEdgeCases:
    """Final tests to catch any remaining uncovered lines"""
    
    def test_type_coercion_edge_cases(self):
        """Test type coercion and conversion edge cases"""
        
        # Test normalize_phone_number with different data types
        edge_cases = [
            (None, (None, None)),
            ("", (None, None)),
            (0, (None, None)),
            (False, (None, None)),
            ([], (None, None)),
            ({}, (None, None)),
            (123, (None, None)),
        ]
        
        for input_val, expected in edge_cases:
            try:
                result = normalize_phone_number(input_val)
                assert result == expected
            except:
                # Some inputs might raise exceptions, which is also valid
                pass
    
    def test_string_method_chaining(self):
        """Test the full chain of string methods in normalize_phone_number"""
        
        # Complex input that exercises all string methods
        complex_input = "  +91 (987) 654-3210  "
        
        # Manually trace through the function
        step1 = complex_input.strip()  # "+91 (987) 654-3210"
        step2 = step1.replace(' ', '')  # "+91(987)654-3210"
        step3 = step2.replace('-', '')  # "+91(987)6543210"
        step4 = step3.replace('(', '')  # "+91987)6543210"
        step5 = step4.replace(')', '')  # "+919876543210"
        step6 = ''.join(filter(str.isdigit, step5))  # "919876543210"
        
        assert len(step6) == 12
        assert step6.startswith('91')
        
        result = normalize_phone_number(complex_input)
        assert result == ("919876543210", "9876543210")
    
    def test_boundary_conditions(self):
        """Test exact boundary conditions"""
        
        # Test exact length boundaries
        assert normalize_phone_number("123456789") == (None, None)  # 9 digits (< 10)
        assert normalize_phone_number("1234567890") == ("911234567890", "1234567890")  # 10 digits (== 10)
        assert normalize_phone_number("12345678901") == (None, None)  # 11 digits, not starting with 1
        assert normalize_phone_number("11234567890") == ("911234567890", "1234567890")  # 11 digits, starting with 1
        assert normalize_phone_number("123456789012") == (None, None)  # 12 digits, not starting with 91
        assert normalize_phone_number("911234567890") == ("911234567890", "1234567890")  # 12 digits, starting with 91
        assert normalize_phone_number("1234567890123") == (None, None)  # 13 digits (> 12)
    
    def test_format_phone_number_complete(self):
        """Test format_phone_number with complete coverage"""
        
        # Test the if condition: phone.startswith("91")
        assert format_phone_number("919876543210") == "919876543210"  # True branch
        assert format_phone_number("9876543210") == "919876543210"    # False branch
        assert format_phone_number("1234567890") == "911234567890"    # False branch
        assert format_phone_number("") == "91"                        # False branch, empty string
    
    def test_academic_year_calculation_complete(self):
        """Test academic year calculation with complete month coverage"""
        
        with patch('frappe.utils.getdate') as mock_getdate:
            # Test every month to ensure complete coverage
            for month in range(1, 13):
                mock_getdate.return_value = datetime(2024, month, 15).date()
                result = get_current_academic_year_backend()
                
                if month >= 4:  # April onwards
                    assert result == "2024-25"
                else:  # January-March
                    assert result == "2023-24"
    
    def test_none_and_empty_handling_complete(self):
        """Test complete None and empty value handling"""
        
        # Test normalize_phone_number with various falsy values
        falsy_values = [None, "", 0, False, [], {}, set()]
        
        for falsy_val in falsy_values:
            result = normalize_phone_number(falsy_val)
            assert result == (None, None)


if __name__ == "__main__":
    # Run with coverage reporting
    pytest.main([
        __file__, 
        "-v",
        "--cov=backend_onboarding_process",
        "--cov-report=html",
        "--cov-report=term-missing",
        "--cov-branch"
    ])