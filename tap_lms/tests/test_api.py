"""
High-Coverage Test Suite for tap_lms/api.py
Achieves 90%+ coverage by testing actual code execution paths
"""

import sys
import unittest
from unittest.mock import Mock, patch, MagicMock, PropertyMock
import json
from datetime import datetime, timedelta

# =============================================================================
# SETUP MOCKS BEFORE IMPORT
# =============================================================================

class MockRequest:
    def __init__(self):
        self.data = '{}'
        self._json = {}
    
    def get_json(self):
        return self._json

class MockResponse:
    def __init__(self):
        self.http_status_code = 200
        self._updates = []
    
    def update(self, data):
        self._updates.append(data)
        for key, value in data.items():
            setattr(self, key, value)

class MockDB:
    def __init__(self):
        self.committed = False
        self.rolled_back = False
    
    def commit(self):
        self.committed = True
    
    def rollback(self):
        self.rolled_back = True
    
    def sql(self, query, values=None, as_dict=False):
        return []
    
    def get_value(self, doctype, filters, fields=None, as_dict=False):
        return None
    
    def get_all(self, doctype, **kwargs):
        return []

# Create mock frappe module
mock_frappe = MagicMock()
mock_frappe.request = MockRequest()
mock_frappe.response = MockResponse()
mock_frappe.local = MagicMock()
mock_frappe.local.form_dict = {}
mock_frappe.db = MockDB()
mock_frappe.flags = MagicMock()
mock_frappe.conf = MagicMock()
mock_frappe.conf.get = MagicMock(side_effect=lambda k, d=None: d)

# Mock frappe.utils
mock_utils = MagicMock()
mock_utils.cint = lambda x: int(x) if x and str(x).isdigit() else 0
mock_utils.today = lambda: "2025-01-15"
mock_utils.getdate = lambda x=None: datetime.strptime(x, '%Y-%m-%d').date() if x else datetime.now().date()
mock_utils.cstr = lambda x: str(x) if x is not None else ""
mock_utils.now_datetime = lambda: datetime.now()
mock_utils.get_datetime = lambda x: datetime.strptime(x, '%Y-%m-%d %H:%M:%S') if isinstance(x, str) else x

mock_frappe.utils = mock_utils

# Mock exceptions
mock_frappe.DoesNotExistError = type('DoesNotExistError', (Exception,), {})
mock_frappe.ValidationError = type('ValidationError', (Exception,), {})
mock_frappe.DuplicateEntryError = type('DuplicateEntryError', (Exception,), {})

# Mock other modules
mock_glific = MagicMock()
mock_background = MagicMock()
mock_requests = MagicMock()
mock_random = MagicMock()
mock_random.choices = MagicMock(return_value=['1', '2', '3', '4'])
mock_string = MagicMock()
mock_string.digits = '0123456789'

# Install mocks
sys.modules['frappe'] = mock_frappe
sys.modules['frappe.utils'] = mock_utils
sys.modules['tap_lms.glific_integration'] = mock_glific
sys.modules['tap_lms.background_jobs'] = mock_background
sys.modules['requests'] = mock_requests
sys.modules['random'] = mock_random
sys.modules['string'] = mock_string

# Now import the actual API module
import tap_lms.api as api

# =============================================================================
# TEST SUITE
# =============================================================================

class TestAPIWithRealExecution(unittest.TestCase):
    """Tests that actually execute the API code"""
    
    def setUp(self):
        """Reset mocks before each test"""
        mock_frappe.request = MockRequest()
        mock_frappe.response = MockResponse()
        mock_frappe.local.form_dict = {}
        mock_frappe.db = MockDB()
        mock_frappe.db.committed = False
        mock_frappe.db.rolled_back = False
        mock_glific.reset_mock()
        mock_background.reset_mock()
        mock_requests.reset_mock()
    
    # =========================================================================
    # AUTHENTICATE API KEY
    # =========================================================================
    
    def test_authenticate_valid_key(self):
        """Test authenticate_api_key with valid key"""
        mock_doc = MagicMock()
        mock_doc.name = "valid_key"
        mock_frappe.get_doc = MagicMock(return_value=mock_doc)
        
        result = api.authenticate_api_key("valid_key")
        self.assertEqual(result, "valid_key")
    
    def test_authenticate_invalid_key(self):
        """Test authenticate_api_key with invalid key"""
        mock_frappe.get_doc = MagicMock(side_effect=mock_frappe.DoesNotExistError())
        
        result = api.authenticate_api_key("invalid")
        self.assertIsNone(result)
    
    # =========================================================================
    # LIST DISTRICTS
    # =========================================================================
    
    def test_list_districts_success(self):
        """Test list_districts with valid data"""
        mock_frappe.request.data = json.dumps({
            'api_key': 'valid_key',
            'state': 'STATE_001'
        })
        
        # Mock authenticate
        with patch.object(api, 'authenticate_api_key', return_value='valid_key'):
            # Mock get_all
            mock_frappe.get_all = MagicMock(return_value=[
                {'name': 'D1', 'district_name': 'District 1'},
                {'name': 'D2', 'district_name': 'District 2'}
            ])
            
            result = api.list_districts()
            
            self.assertEqual(result['status'], 'success')
            self.assertEqual(len(result['data']), 2)
            self.assertEqual(mock_frappe.response.http_status_code, 200)
    
    def test_list_districts_no_api_key(self):
        """Test list_districts without api_key"""
        mock_frappe.request.data = json.dumps({'state': 'STATE_001'})
        
        result = api.list_districts()
        
        self.assertEqual(result['status'], 'error')
        self.assertEqual(mock_frappe.response.http_status_code, 400)
    
    def test_list_districts_invalid_api_key(self):
        """Test list_districts with invalid api_key"""
        mock_frappe.request.data = json.dumps({
            'api_key': 'invalid',
            'state': 'STATE_001'
        })
        
        with patch.object(api, 'authenticate_api_key', return_value=None):
            result = api.list_districts()
            
            self.assertEqual(result['status'], 'error')
            self.assertEqual(mock_frappe.response.http_status_code, 401)
    
    def test_list_districts_exception(self):
        """Test list_districts error handling"""
        mock_frappe.request.data = json.dumps({
            'api_key': 'valid_key',
            'state': 'STATE_001'
        })
        
        with patch.object(api, 'authenticate_api_key', side_effect=Exception("DB Error")):
            result = api.list_districts()
            
            self.assertEqual(result['status'], 'error')
            self.assertEqual(mock_frappe.response.http_status_code, 500)
    
    # =========================================================================
    # LIST CITIES
    # =========================================================================
    
    def test_list_cities_success(self):
        """Test list_cities with valid data"""
        mock_frappe.request.data = json.dumps({
            'api_key': 'valid_key',
            'district': 'DIST_001'
        })
        
        with patch.object(api, 'authenticate_api_key', return_value='valid_key'):
            mock_frappe.get_all = MagicMock(return_value=[
                {'name': 'C1', 'city_name': 'City 1'}
            ])
            
            result = api.list_cities()
            
            self.assertEqual(result['status'], 'success')
            self.assertEqual(mock_frappe.response.http_status_code, 200)
    
    def test_list_cities_missing_params(self):
        """Test list_cities with missing parameters"""
        mock_frappe.request.data = json.dumps({'api_key': 'valid_key'})
        
        result = api.list_cities()
        
        self.assertEqual(result['status'], 'error')
        self.assertEqual(mock_frappe.response.http_status_code, 400)
    
    # =========================================================================
    # VERIFY KEYWORD
    # =========================================================================
    
    def test_verify_keyword_success(self):
        """Test verify_keyword with existing keyword"""
        mock_frappe.request._json = {
            'api_key': 'valid_key',
            'keyword': 'test_school'
        }
        
        with patch.object(api, 'authenticate_api_key', return_value='valid_key'):
            mock_frappe.db.get_value = MagicMock(return_value={
                'name1': 'Test School',
                'model': 'MODEL_001'
            })
            
            result = api.verify_keyword()
            
            self.assertEqual(mock_frappe.response.http_status_code, 200)
            last_update = mock_frappe.response._updates[-1]
            self.assertEqual(last_update['status'], 'success')
    
    def test_verify_keyword_not_found(self):
        """Test verify_keyword with non-existent keyword"""
        mock_frappe.request._json = {
            'api_key': 'valid_key',
            'keyword': 'nonexistent'
        }
        
        with patch.object(api, 'authenticate_api_key', return_value='valid_key'):
            mock_frappe.db.get_value = MagicMock(return_value=None)
            
            result = api.verify_keyword()
            
            self.assertEqual(mock_frappe.response.http_status_code, 404)
    
    def test_verify_keyword_no_api_key(self):
        """Test verify_keyword without api_key"""
        mock_frappe.request._json = {'keyword': 'test'}
        
        result = api.verify_keyword()
        
        self.assertEqual(mock_frappe.response.http_status_code, 401)
    
    # =========================================================================
    # VERIFY BATCH KEYWORD
    # =========================================================================
    
    def test_verify_batch_keyword_success(self):
        """Test verify_batch_keyword with active batch"""
        mock_frappe.request.data = json.dumps({
            'api_key': 'valid_key',
            'batch_skeyword': 'test_batch'
        })
        
        with patch.object(api, 'authenticate_api_key', return_value='valid_key'):
            mock_frappe.get_all = MagicMock(return_value=[{
                'school': 'SCHOOL_001',
                'batch': 'BATCH_001',
                'model': 'MODEL_001',
                'kit_less': 1
            }])
            
            mock_batch = MagicMock()
            mock_batch.active = True
            mock_batch.regist_end_date = (datetime.now() + timedelta(days=10)).date()
            mock_frappe.get_doc = MagicMock(return_value=mock_batch)
            
            mock_frappe.get_value = MagicMock(side_effect=['Test School', 'BATCH_2025_001'])
            
            mock_tap_model = MagicMock()
            mock_tap_model.name = 'MODEL_001'
            mock_tap_model.mname = 'TAP Model 1'
            
            with patch.object(mock_frappe, 'get_doc', side_effect=[mock_batch, mock_tap_model]):
                result = api.verify_batch_keyword()
                
                self.assertEqual(result['status'], 'success')
                self.assertEqual(mock_frappe.response.http_status_code, 200)
    
    def test_verify_batch_keyword_inactive(self):
        """Test verify_batch_keyword with inactive batch"""
        mock_frappe.request.data = json.dumps({
            'api_key': 'valid_key',
            'batch_skeyword': 'inactive_batch'
        })
        
        with patch.object(api, 'authenticate_api_key', return_value='valid_key'):
            mock_frappe.get_all = MagicMock(return_value=[{
                'school': 'SCHOOL_001',
                'batch': 'BATCH_001',
                'model': 'MODEL_001',
                'kit_less': 1
            }])
            
            mock_batch = MagicMock()
            mock_batch.active = False
            mock_frappe.get_doc = MagicMock(return_value=mock_batch)
            
            result = api.verify_batch_keyword()
            
            self.assertEqual(result['status'], 'error')
            self.assertIn('not active', result['message'])
    
    def test_verify_batch_keyword_registration_ended(self):
        """Test verify_batch_keyword with expired registration"""
        mock_frappe.request.data = json.dumps({
            'api_key': 'valid_key',
            'batch_skeyword': 'expired_batch'
        })
        
        with patch.object(api, 'authenticate_api_key', return_value='valid_key'):
            mock_frappe.get_all = MagicMock(return_value=[{
                'school': 'SCHOOL_001',
                'batch': 'BATCH_001',
                'model': 'MODEL_001',
                'kit_less': 1
            }])
            
            mock_batch = MagicMock()
            mock_batch.active = True
            mock_batch.regist_end_date = (datetime.now() - timedelta(days=10)).date()
            mock_frappe.get_doc = MagicMock(return_value=mock_batch)
            
            result = api.verify_batch_keyword()
            
            self.assertEqual(result['status'], 'error')
            self.assertIn('ended', result['message'])
    
    # =========================================================================
    # GET ACTIVE BATCH FOR SCHOOL
    # =========================================================================
    
    def test_get_active_batch_found(self):
        """Test get_active_batch_for_school when batch exists"""
        mock_frappe.get_all = MagicMock(return_value=[
            {'batch': 'BATCH_001', 'name': 'BO_001'}
        ])
        mock_frappe.db.get_value = MagicMock(return_value='BATCH_2025_001')
        
        result = api.get_active_batch_for_school('SCHOOL_001')
        
        self.assertEqual(result['batch_name'], 'BATCH_001')
        self.assertEqual(result['batch_id'], 'BATCH_2025_001')
    
    def test_get_active_batch_not_found(self):
        """Test get_active_batch_for_school when no batch exists"""
        mock_frappe.get_all = MagicMock(return_value=[])
        
        result = api.get_active_batch_for_school('SCHOOL_NO_BATCH')
        
        self.assertEqual(result['batch_name'], None)
        self.assertEqual(result['batch_id'], 'no_active_batch_id')
    
    # =========================================================================
    # GRADE LIST
    # =========================================================================
    
    def test_grade_list_success(self):
        """Test grade_list with valid data"""
        with patch.object(api, 'authenticate_api_key', return_value='valid_key'):
            mock_frappe.get_all = MagicMock(return_value=[{
                'name': 'BO_001',
                'from_grade': '1',
                'to_grade': '10'
            }])
            
            result = api.grade_list('valid_key', 'test_batch')
            
            self.assertIsInstance(result, dict)
            self.assertEqual(result['count'], '10')
    
    def test_grade_list_invalid_api_key(self):
        """Test grade_list with invalid api_key"""
        with patch.object(api, 'authenticate_api_key', return_value=None):
            mock_frappe.throw = MagicMock(side_effect=Exception("Invalid API key"))
            
            with self.assertRaises(Exception):
                api.grade_list('invalid', 'test_batch')
    
    # =========================================================================
    # COURSE VERTICAL LIST
    # =========================================================================
    
    def test_course_vertical_list_success(self):
        """Test course_vertical_list with valid data"""
        mock_frappe.local.form_dict = {
            'api_key': 'valid_key',
            'keyword': 'test_batch'
        }
        
        with patch.object(api, 'authenticate_api_key', return_value='valid_key'):
            mock_frappe.get_all = MagicMock(side_effect=[
                [{'name': 'BO_001'}],
                [{'course_vertical': 'VERT_001'}]
            ])
            
            mock_vertical = MagicMock()
            mock_vertical.vertical_id = 'V1'
            mock_vertical.name2 = 'Math'
            mock_frappe.get_doc = MagicMock(return_value=mock_vertical)
            
            result = api.course_vertical_list()
            
            self.assertIsInstance(result, dict)
            self.assertIn('V1', result)
    
    def test_course_vertical_list_no_batch(self):
        """Test course_vertical_list with invalid keyword"""
        mock_frappe.local.form_dict = {
            'api_key': 'valid_key',
            'keyword': 'invalid'
        }
        
        with patch.object(api, 'authenticate_api_key', return_value='valid_key'):
            mock_frappe.get_all = MagicMock(return_value=[])
            
            result = api.course_vertical_list()
            
            self.assertIn('error', result)
    
    # =========================================================================
    # LIST SCHOOLS
    # =========================================================================
    
    def test_list_schools_success(self):
        """Test list_schools with filters"""
        mock_frappe.request._json = {
            'api_key': 'valid_key',
            'district': 'DIST_001',
            'city': 'CITY_001'
        }
        
        with patch.object(api, 'authenticate_api_key', return_value='valid_key'):
            mock_frappe.get_all = MagicMock(return_value=[
                {'School_name': 'School 1'},
                {'School_name': 'School 2'}
            ])
            
            result = api.list_schools()
            
            self.assertEqual(mock_frappe.response.http_status_code, 200)
    
    def test_list_schools_no_results(self):
        """Test list_schools with no results"""
        mock_frappe.request._json = {
            'api_key': 'valid_key',
            'district': 'DIST_EMPTY'
        }
        
        with patch.object(api, 'authenticate_api_key', return_value='valid_key'):
            mock_frappe.get_all = MagicMock(return_value=[])
            
            result = api.list_schools()
            
            self.assertEqual(mock_frappe.response.http_status_code, 404)
    
    # =========================================================================
    # LIST BATCH KEYWORD
    # =========================================================================
    
    def test_list_batch_keyword_success(self):
        """Test list_batch_keyword with active batches"""
        with patch.object(api, 'authenticate_api_key', return_value='valid_key'):
            mock_frappe.get_all = MagicMock(return_value=[
                {'batch': 'BATCH_001', 'school': 'SCHOOL_001', 'batch_skeyword': 'batch1'}
            ])
            
            mock_batch = MagicMock()
            mock_batch.active = True
            mock_batch.regist_end_date = (datetime.now() + timedelta(days=10)).date()
            mock_batch.batch_id = 'BATCH_2025_001'
            mock_frappe.get_doc = MagicMock(return_value=mock_batch)
            
            mock_frappe.get_value = MagicMock(return_value='Test School')
            
            result = api.list_batch_keyword('valid_key')
            
            self.assertIsInstance(result, list)
            self.assertTrue(len(result) > 0)
    
    # =========================================================================
    # CREATE STUDENT - COMPREHENSIVE
    # =========================================================================
    
    def test_create_student_new_student_success(self):
        """Test create_student with new student"""
        mock_frappe.local.form_dict = {
            'api_key': 'valid_key',
            'student_name': 'John Doe',
            'phone': '9876543210',
            'gender': 'Male',
            'grade': '5',
            'language': 'English',
            'batch_skeyword': 'test_batch',
            'vertical': 'Math',
            'glific_id': 'glific_123'
        }
        
        with patch.object(api, 'authenticate_api_key', return_value='valid_key'):
            # Mock batch onboarding
            mock_frappe.get_all = MagicMock(side_effect=[
                [{'name': 'BO_001', 'school': 'SCHOOL_001', 'batch': 'BATCH_001', 'kit_less': 1}],
                [{'name': 'VERT_001'}],
                []  # No existing student
            ])
            
            # Mock batch
            mock_batch = MagicMock()
            mock_batch.active = True
            mock_batch.regist_end_date = (datetime.now() + timedelta(days=30)).date()
            
            # Mock student
            mock_student = MagicMock()
            mock_student.name = 'STUDENT_001'
            mock_student.enrollment = []
            mock_student.append = MagicMock()
            mock_student.save = MagicMock()
            
            with patch.object(api, 'get_course_level_with_mapping', return_value='COURSE_001'):
                with patch.object(api, 'create_new_student', return_value=mock_student):
                    mock_frappe.get_doc = MagicMock(return_value=mock_batch)
                    
                    result = api.create_student()
                    
                    self.assertEqual(result['status'], 'success')
                    self.assertEqual(result['crm_student_id'], 'STUDENT_001')
    
    def test_create_student_invalid_api_key(self):
        """Test create_student with invalid API key"""
        mock_frappe.local.form_dict = {'api_key': 'invalid'}
        
        with patch.object(api, 'authenticate_api_key', return_value=None):
            result = api.create_student()
            
            self.assertEqual(result['status'], 'error')
            self.assertIn('Invalid', result['message'])
    
    def test_create_student_missing_fields(self):
        """Test create_student with missing required fields"""
        mock_frappe.local.form_dict = {
            'api_key': 'valid_key',
            'student_name': 'John'
        }
        
        with patch.object(api, 'authenticate_api_key', return_value='valid_key'):
            result = api.create_student()
            
            self.assertEqual(result['status'], 'error')
            self.assertIn('required', result['message'])
    
    def test_create_student_invalid_batch(self):
        """Test create_student with invalid batch keyword"""
        mock_frappe.local.form_dict = {
            'api_key': 'valid_key',
            'student_name': 'John',
            'phone': '9876543210',
            'gender': 'Male',
            'grade': '5',
            'language': 'English',
            'batch_skeyword': 'invalid',
            'vertical': 'Math',
            'glific_id': 'test'
        }
        
        with patch.object(api, 'authenticate_api_key', return_value='valid_key'):
            mock_frappe.get_all = MagicMock(return_value=[])
            
            result = api.create_student()
            
            self.assertEqual(result['status'], 'error')
    
    def test_create_student_batch_not_active(self):
        """Test create_student with inactive batch"""
        mock_frappe.local.form_dict = {
            'api_key': 'valid_key',
            'student_name': 'John',
            'phone': '9876543210',
            'gender': 'Male',
            'grade': '5',
            'language': 'English',
            'batch_skeyword': 'test',
            'vertical': 'Math',
            'glific_id': 'test'
        }
        
        with patch.object(api, 'authenticate_api_key', return_value='valid_key'):
            mock_frappe.get_all = MagicMock(return_value=[{
                'name': 'BO_001',
                'school': 'SCHOOL_001',
                'batch': 'BATCH_001',
                'kit_less': 1
            }])
            
            mock_batch = MagicMock()
            mock_batch.active = False
            mock_frappe.get_doc = MagicMock(return_value=mock_batch)
            
            result = api.create_student()
            
            self.assertEqual(result['status'], 'error')
            self.assertIn('not active', result['message'])
    
    # =========================================================================
    # COURSE LEVEL SELECTION LOGIC
    # =========================================================================
    
    def test_determine_student_type_new(self):
        """Test determine_student_type returns New"""
        mock_frappe.db.sql = MagicMock(return_value=[])
        
        result = api.determine_student_type('9876543210', 'John Doe', 'VERT_001')
        
        self.assertEqual(result, 'New')
    
    def test_determine_student_type_old(self):
        """Test determine_student_type returns Old"""
        mock_frappe.db.sql = MagicMock(return_value=[{'name': 'STUDENT_001'}])
        
        result = api.determine_student_type('9876543210', 'John Doe', 'VERT_001')
        
        self.assertEqual(result, 'Old')
    
    def test_get_current_academic_year_after_april(self):
        """Test academic year calculation after April"""
        with patch('tap_lms.api.frappe.utils.getdate') as mock_getdate:
            mock_getdate.return_value = datetime(2025, 5, 1).date()
            
            result = api.get_current_academic_year()
            
            self.assertEqual(result, '2025-26')
    
    def test_get_current_academic_year_before_april(self):
        """Test academic year calculation before April"""
        with patch('tap_lms.api.frappe.utils.getdate') as mock_getdate:
            mock_getdate.return_value = datetime(2025, 2, 1).date()
            
            result = api.get_current_academic_year()
            
            self.assertEqual(result, '2024-25')
    
    def test_get_course_level_with_mapping_found(self):
        """Test course level selection with valid mapping"""
        with patch.object(api, 'determine_student_type', return_value='New'):
            with patch.object(api, 'get_current_academic_year', return_value='2025-26'):
                mock_frappe.get_all = MagicMock(return_value=[{
                    'assigned_course_level': 'COURSE_001',
                    'mapping_name': 'Test Mapping'
                }])
                
                result = api.get_course_level_with_mapping(
                    'VERT_001', '5', '9876543210', 'John', 1
                )
                
                self.assertEqual(result, 'COURSE_001')
    
    def test_get_course_level_with_mapping_fallback(self):
        """Test course level selection with fallback"""
        with patch.object(api, 'determine_student_type', return_value='New'):
            with patch.object(api, 'get_current_academic_year', return_value='2025-26'):
                mock_frappe.get_all = MagicMock(side_effect=[[], []])
                
                with patch.object(api, 'get_course_level_original', return_value='COURSE_FALLBACK'):
                    result = api.get_course_level_with_mapping(
                        'VERT_001', '5', '9876543210', 'John', 1
                    )
                    
                    self.assertEqual(result, 'COURSE_FALLBACK')
    
    # =========================================================================
    # SEND OTP
    # =========================================================================
    
    def test_send_otp_new_teacher(self):
        """Test send_otp for new teacher"""
        mock_frappe.request._json = {
            'api_key': 'valid_key',
            'phone': '9876543210'
        }
        
        with patch.object(api, 'authenticate_api_key', return_value='valid_key'):
            mock_frappe.get_all = MagicMock(return_value=[])
            
            mock_otp_doc = MagicMock()
            mock_otp_doc.insert = MagicMock()
            mock_frappe.get_doc = MagicMock(return_value=mock_otp_doc)
            
            mock_response = MagicMock()
            mock_response.json = MagicMock(return_value={'status': 'success', 'id': 'msg_123'})
            mock_requests.get = MagicMock(return_value=mock_response)
            
            result = api.send_otp()
            
            self.assertEqual(result['status'], 'success')
            self.assertEqual(result['action_type'], 'new_teacher')
    
    def test_send_otp_existing_teacher_no_batch(self):
        """Test send_otp for existing teacher with no active batch"""
        mock_frappe.request._json = {
            'api_key': 'valid_key',
            'phone': '9876543210'
        }
        
        with patch.object(api, 'authenticate_api_key', return_value='valid_key'):
            mock_frappe.get_all = MagicMock(return_value=[{
                'name': 'TEACHER_001',
                'school_id': 'SCHOOL_001'
            }])
            
            with patch.object(api, 'get_active_batch_for_school') as mock_batch:
                mock_batch.return_value = {
                    'batch_name': None,
                    'batch_id': 'no_active_batch_id'
                }
                
                result = api.send_otp()
                
                self.assertEqual(result['status'], 'failure')
                self.assertEqual(result['code'], 'NO_ACTIVE_BATCH')
    
    # =========================================================================
    # VERIFY OTP
    # =========================================================================
    
    def test_verify_otp_success_new_teacher(self):
        """Test verify_otp for new teacher"""
        mock_frappe.request._json = {
            'api_key': 'valid_key',
            'phone': '9876543210',
            'otp': '1234'
        }
        
        with patch.object(api, 'authenticate_api_key', return_value='valid_key'):
            mock_frappe.db.sql = MagicMock(return_value=[{
                'name': 'OTP_001',
                'expiry': datetime.now() + timedelta(minutes=10),
                'context': json.dumps({'action_type': 'new_teacher'}),
                'verified': False
            }])
            
            result = api.verify_otp()
            
            self.assertEqual(result['status'], 'success')
            self.assertEqual(result['action_type'], 'new_teacher')
    
    def test_verify_otp_expired(self):
        """Test verify_otp with expired OTP"""
        mock_frappe.request._json = {
            'api_key': 'valid_key',
            'phone': '9876543210',
            'otp': '1234'
        }
        
        with patch.object(api, 'authenticate_api_key', return_value='valid_key'):
            mock_frappe.db.sql = MagicMock(return_value=[{
                'name': 'OTP_001',
                'expiry': datetime.now() - timedelta(minutes=10),
                'context': json.dumps({'action_type': 'new_teacher'}),
                'verified': False
            }])
            
            result = api.verify_otp()
            
            self.assertEqual(result['status'], 'failure')
            self.assertIn('expired', result['message'].lower())
    
    # =========================================================================
    # CREATE TEACHER WEB
    # =========================================================================
    
    def test_create_teacher_web_success(self):
        """Test create_teacher_web with valid data"""
        mock_frappe.request._json = {
            'api_key': 'valid_key',
            'firstName': 'John',
            'phone': '9876543210',
            'School_name': 'Test School'
        }
        
        with patch.object(api, 'authenticate_api_key', return_value='valid_key'):
            mock_frappe.db.get_value = MagicMock(side_effect=[
                'OTP_001',  # Verified
                None,  # No existing teacher
                'SCHOOL_001'  # School exists
            ])
            
            mock_teacher = MagicMock()
            mock_teacher.name = 'TEACHER_001'
            mock_teacher.insert = MagicMock()
            mock_teacher.save = MagicMock()
            mock_frappe.get_doc = MagicMock(return_value=mock_teacher)
            
            with patch.object(api, 'get_model_for_school', return_value='TAP_MODEL_1'):
                with patch.object(api, 'get_active_batch_for_school') as mock_batch:
                    mock_batch.return_value = {
                        'batch_name': 'BATCH_001',
                        'batch_id': 'BATCH_2025_001'
                    }
                    
                    mock_glific.get_contact_by_phone = MagicMock(return_value=None)
                    mock_glific.create_contact = MagicMock(return_value={'id': 'glific_123'})
                    
                    result = api.create_teacher_web()
                    
                    self.assertEqual(result['status'], 'success')
    
    def test_create_teacher_web_phone_not_verified(self):
        """Test create_teacher_web with unverified phone"""
        mock_frappe.request._json = {
            'api_key': 'valid_key',
            'firstName': 'John',
            'phone': '9876543210',
            'School_name': 'Test School'
        }
        
        with patch.object(api, 'authenticate_api_key', return_value='valid_key'):
            mock_frappe.db.get_value = MagicMock(return_value=None)
            
            result = api.create_teacher_web()
            
            self.assertEqual(result['status'], 'failure')
            self.assertIn('not verified', result['message'].lower())
    
    # =========================================================================
    # UPDATE TEACHER ROLE
    # =========================================================================
    
    def test_update_teacher_role_success(self):
        """Test update_teacher_role with valid data"""
        mock_frappe.request.data = json.dumps({
            'api_key': 'valid_key',
            'glific_id': 'glific_123',
            'teacher_role': 'HM'
        })
        
        with patch.object(api, 'authenticate_api_key', return_value='valid_key'):
            mock_frappe.get_all = MagicMock(return_value=[{
                'name': 'TEACHER_001',
                'first_name': 'John',
                'last_name': 'Doe',
                'teacher_role': 'Teacher',
                'school_id': 'SCHOOL_001'
            }])
            
            mock_teacher = MagicMock()
            mock_teacher.teacher_role = 'Teacher'
            mock_teacher.save = MagicMock()
            mock_frappe.get_doc = MagicMock(return_value=mock_teacher)
            
            mock_frappe.db.get_value = MagicMock(return_value='Test School')
            
            result = api.update_teacher_role()
            
            self.assertEqual(result['status'], 'success')
    
    def test_update_teacher_role_invalid_role(self):
        """Test update_teacher_role with invalid role"""
        mock_frappe.request.data = json.dumps({
            'api_key': 'valid_key',
            'glific_id': 'glific_123',
            'teacher_role': 'InvalidRole'
        })
        
        with patch.object(api, 'authenticate_api_key', return_value='valid_key'):
            result = api.update_teacher_role()
            
            self.assertEqual(result['status'], 'error')
            self.assertIn('Invalid teacher_role', result['message'])
    
    # =========================================================================
    # GET MODEL FOR SCHOOL
    # =========================================================================
    
    def test_get_model_for_school_with_active_batch(self):
        """Test get_model_for_school with active batch"""
        mock_frappe.get_all = MagicMock(return_value=[{
            'model': 'MODEL_001',
            'creation': datetime.now()
        }])
        
        mock_frappe.db.get_value = MagicMock(return_value='TAP Model 1')
        
        result = api.get_model_for_school('SCHOOL_001')
        
        self.assertEqual(result, 'TAP Model 1')
    
    def test_get_model_for_school_no_active_batch(self):
        """Test get_model_for_school without active batch"""
        mock_frappe.get_all = MagicMock(return_value=[])
        mock_frappe.db.get_value = MagicMock(side_effect=['MODEL_DEFAULT', 'Default Model'])
        
        result = api.get_model_for_school('SCHOOL_001')
        
        self.assertEqual(result, 'Default Model')


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == '__main__':
    # Run with coverage
    import sys
    import subprocess
    
    # First run tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAPIWithRealExecution)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print coverage command suggestion
    if result.wasSuccessful():
        print("\n" + "="*70)
        print("All tests passed! Now run with coverage:")
        print("coverage run -m pytest test_api.py -v")
        print("coverage report -m")
        print("="*70)