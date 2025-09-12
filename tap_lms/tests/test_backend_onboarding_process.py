import pytest
import sys
from unittest.mock import Mock, patch, MagicMock
from datetime import date, datetime
import json

# Mock the required modules before importing
with patch.dict('sys.modules', {
    'frappe': Mock(),
    'frappe.model': Mock(),
    'frappe.model.document': Mock(),
    'frappe.utils': Mock(),
    'tap_lms.glific_integration': Mock(),
    'tap_lms.api': Mock(),
}):
    # Now we can import the actual module
    pass

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
        'tap_lms.glific_integration': Mock(),
        'tap_lms.api': Mock(),
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
        
        # Mock the imported modules
        mock_glific = sys.modules['tap_lms.glific_integration']
        mock_glific.create_or_get_glific_group_for_batch = Mock()
        mock_glific.add_student_to_glific_for_onboarding = Mock()
        mock_glific.get_contact_by_phone = Mock()
        
        mock_api = sys.modules['tap_lms.api']
        mock_api.get_course_level = Mock()
        
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
        # Import inside the test to ensure mocking is active
        import sys
        with patch.dict('sys.modules', {
            'tap_lms.glific_integration': Mock(),
            'tap_lms.api': Mock(),
        }):
            from tap_lms.page.backend_onboarding_process.backend_onboarding_process import normalize_phone_number
            
            phone_12, phone_10 = normalize_phone_number("9876543210")
            
            assert phone_12 == "919876543210"
            assert phone_10 == "9876543210"
    
    def test_normalize_phone_number_12_digit(self, mock_frappe):
        """Test normalizing 12-digit phone number"""
        import sys
        with patch.dict('sys.modules', {
            'tap_lms.glific_integration': Mock(),
            'tap_lms.api': Mock(),
        }):
            from tap_lms.page.backend_onboarding_process.backend_onboarding_process import normalize_phone_number
            
            phone_12, phone_10 = normalize_phone_number("919876543210")
            
            assert phone_12 == "919876543210"
            assert phone_10 == "9876543210"
    
    def test_normalize_phone_number_11_digit_with_1_prefix(self, mock_frappe):
        """Test normalizing 11-digit phone number starting with 1"""
        import sys
        with patch.dict('sys.modules', {
            'tap_lms.glific_integration': Mock(),
            'tap_lms.api': Mock(),
        }):
            from tap_lms.page.backend_onboarding_process.backend_onboarding_process import normalize_phone_number
            
            phone_12, phone_10 = normalize_phone_number("19876543210")
            
            assert phone_12 == "919876543210"
            assert phone_10 == "9876543210"
    
    def test_normalize_phone_number_with_formatting(self, mock_frappe):
        """Test normalizing phone number with formatting characters"""
        import sys
        with patch.dict('sys.modules', {
            'tap_lms.glific_integration': Mock(),
            'tap_lms.api': Mock(),
        }):
            from tap_lms.page.backend_onboarding_process.backend_onboarding_process import normalize_phone_number
            
            phone_12, phone_10 = normalize_phone_number("(987) 654-3210")
            
            assert phone_12 == "919876543210"
            assert phone_10 == "9876543210"
    
    def test_normalize_phone_number_invalid(self, mock_frappe):
        """Test normalizing invalid phone number"""
        import sys
        with patch.dict('sys.modules', {
            'tap_lms.glific_integration': Mock(),
            'tap_lms.api': Mock(),
        }):
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
        import sys
        with patch.dict('sys.modules', {
            'tap_lms.glific_integration': Mock(),
            'tap_lms.api': Mock(),
        }):
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
        import sys
        with patch.dict('sys.modules', {
            'tap_lms.glific_integration': Mock(),
            'tap_lms.api': Mock(),
        }):
            from tap_lms.page.backend_onboarding_process.backend_onboarding_process import find_existing_student_by_phone_and_name
            
            mock_frappe.db.sql.return_value = []
            
            result = find_existing_student_by_phone_and_name("919876543210", "Test Student")
            
            assert result is None
    
    def test_find_existing_student_invalid_input(self, mock_frappe):
        """Test with invalid input"""
        import sys
        with patch.dict('sys.modules', {
            'tap_lms.glific_integration': Mock(),
            'tap_lms.api': Mock(),
        }):
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
        import sys
        with patch.dict('sys.modules', {
            'tap_lms.glific_integration': Mock(),
            'tap_lms.api': Mock(),
        }):
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
        import sys
        with patch.dict('sys.modules', {
            'tap_lms.glific_integration': Mock(),
            'tap_lms.api': Mock(),
        }):
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
        import sys
        with patch.dict('sys.modules', {
            'tap_lms.glific_integration': Mock(),
            'tap_lms.api': Mock(),
        }):
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
        import sys
        with patch.dict('sys.modules', {
            'tap_lms.glific_integration': Mock(),
            'tap_lms.api': Mock(),
        }):
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
        import sys
        with patch.dict('sys.modules', {
            'tap_lms.glific_integration': Mock(),
            'tap_lms.api': Mock(),
        }):
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
        import sys
        with patch.dict('sys.modules', {
            'tap_lms.glific_integration': Mock(),
            'tap_lms.api': Mock(),
        }):
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
        import sys
        with patch.dict('sys.modules', {
            'tap_lms.glific_integration': Mock(),
            'tap_lms.api': Mock(),
        }):
            from tap_lms.page.backend_onboarding_process.backend_onboarding_process import get_onboarding_stages
            
            mock_frappe.db.table_exists.return_value = False
            
            result = get_onboarding_stages()
            
            assert result == []
    
    def test_get_onboarding_stages_exception(self, mock_frappe):
        """Test exception handling in get_onboarding_stages"""
        import sys
        with patch.dict('sys.modules', {
            'tap_lms.glific_integration': Mock(),
            'tap_lms.api': Mock(),
        }):
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
        import sys
        with patch.dict('sys.modules', {
            'tap_lms.glific_integration': Mock(),
            'tap_lms.api': Mock(),
        }):
            from tap_lms.page.backend_onboarding_process.backend_onboarding_process import get_initial_stage
            
            mock_frappe.get_all.side_effect = [
                [{'name': 'STAGE_INITIAL'}],  # First call with order=0
            ]
            
            result = get_initial_stage()
            
            assert result == 'STAGE_INITIAL'
    
    def test_get_initial_stage_no_order_zero(self, mock_frappe):
        """Test getting initial stage when no order=0 exists"""
        import sys
        with patch.dict('sys.modules', {
            'tap_lms.glific_integration': Mock(),
            'tap_lms.api': Mock(),
        }):
            from tap_lms.page.backend_onboarding_process.backend_onboarding_process import get_initial_stage
            
            mock_frappe.get_all.side_effect = [
                [],  # First call with order=0 returns empty
                [{'name': 'STAGE_MIN', 'order': 1}],  # Second call with minimum order
            ]
            
            result = get_initial_stage()
            
            assert result == 'STAGE_MIN'
    
    def test_get_initial_stage_exception(self, mock_frappe):
        """Test exception handling in get_initial_stage"""
        import sys
        with patch.dict('sys.modules', {
            'tap_lms.glific_integration': Mock(),
            'tap_lms.api': Mock(),
        }):
            from tap_lms.page.backend_onboarding_process.backend_onboarding_process import get_initial_stage
            
            mock_frappe.get_all.side_effect = Exception("Database error")
            
            result = get_initial_stage()
            
            assert result is None
            assert mock_frappe.log_error.called

# ACADEMIC YEAR TESTS
class TestGetCurrentAcademicYear:
    """Test academic year calculation"""
    
    def test_get_current_academic_year_after_april(self, mock_frappe):
        """Test academic year calculation when current date is after April"""
        import sys
        with patch.dict('sys.modules', {
            'tap_lms.glific_integration': Mock(),
            'tap_lms.api': Mock(),
        }):
            from tap_lms.page.backend_onboarding_process.backend_onboarding_process import get_current_academic_year_backend
            
            # Mock date in August (after April)
            mock_frappe.utils.getdate.return_value = date(2025, 8, 20)
            
            result = get_current_academic_year_backend()
            
            assert result == "2025-26"
    
    def test_get_current_academic_year_before_april(self, mock_frappe):
        """Test academic year calculation when current date is before April"""
        import sys
        with patch.dict('sys.modules', {
            'tap_lms.glific_integration': Mock(),
            'tap_lms.api': Mock(),
        }):
            from tap_lms.page.backend_onboarding_process.backend_onboarding_process import get_current_academic_year_backend
            
            # Mock date in February (before April)
            mock_frappe.utils.getdate.return_value = date(2025, 2, 20)
            
            result = get_current_academic_year_backend()
            
            assert result == "2024-25"
    
    def test_get_current_academic_year_exception(self, mock_frappe):
        """Test exception handling in academic year calculation"""
        import sys
        with patch.dict('sys.modules', {
            'tap_lms.glific_integration': Mock(),
            'tap_lms.api': Mock(),
        }):
            from tap_lms.page.backend_onboarding_process.backend_onboarding_process import get_current_academic_year_backend
            
            mock_frappe.utils.getdate.side_effect = Exception("Date error")
            
            result = get_current_academic_year_backend()
            
            assert result is None
            assert mock_frappe.log_error.called

# JOB STATUS TESTS
class TestGetJobStatus:
    """Test job status functionality"""
    
    def test_get_job_status_success(self, mock_frappe):
        """Test getting job status successfully"""
        import sys
        with patch.dict('sys.modules', {
            'tap_lms.glific_integration': Mock(),
            'tap_lms.api': Mock(),
        }):
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
        import sys
        with patch.dict('sys.modules', {
            'tap_lms.glific_integration': Mock(),
            'tap_lms.api': Mock(),
        }):
            from tap_lms.page.backend_onboarding_process.backend_onboarding_process import get_job_status
            
            # Mock no table exists
            mock_frappe.db.table_exists.return_value = False
            
            result = get_job_status('job123')
            
            assert result['status'] == 'Unknown'
            assert 'message' in result

# ERROR HANDLING TESTS
class TestErrorHandling:
    """Test error handling in various scenarios"""
    
    def test_phone_normalization_error_handling(self, mock_frappe):
        """Test phone normalization with various error scenarios"""
        import sys
        with patch.dict('sys.modules', {
            'tap_lms.glific_integration': Mock(),
            'tap_lms.api': Mock(),
        }):
            from tap_lms.page.backend_onboarding_process.backend_onboarding_process import normalize_phone_number
            
            # Test various invalid inputs
            invalid_inputs = [None, "", "   ", "abc", "123", "123456789012345"]
            
            for invalid_input in invalid_inputs:
                phone_12, phone_10 = normalize_phone_number(invalid_input)
                # Should return None for both values for invalid inputs (except empty string case)
                if invalid_input not in ["   "]:  # Spaces would be stripped
                    assert phone_12 is None
                    assert phone_10 is None

# EDGE CASES TESTS
class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_empty_batch_processing(self, mock_frappe):
        """Test processing batch with no students"""
        import sys
        with patch.dict('sys.modules', {
            'tap_lms.glific_integration': Mock(),
            'tap_lms.api': Mock(),
        }):
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
        import sys
        with patch.dict('sys.modules', {
            'tap_lms.glific_integration': Mock(),
            'tap_lms.api': Mock(),
        }):
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
        import sys
        with patch.dict('sys.modules', {
            'tap_lms.glific_integration': Mock(),
            'tap_lms.api': Mock(),
        }):
            from tap_lms.page.backend_onboarding_process.backend_onboarding_process import get_current_academic_year_backend
            
            # Test March 31 (before April)
            mock_frappe.utils.getdate.return_value = date(2025, 3, 31)
            result = get_current_academic_year_backend()
            assert result == "2024-25"
            
            # Test April 1 (after April start)
            mock_frappe.utils.getdate.return_value = date(2025, 4, 1)
            result = get_current_academic_year_backend()
            assert result == "2025-26"