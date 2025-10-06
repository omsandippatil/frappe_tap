"""
Production-Ready Test Suite for tap_lms/api.py
Comprehensive coverage: Success paths, error paths, edge cases, and complex flows
"""

import sys
import unittest
from unittest.mock import Mock, patch, MagicMock, call
import json
from datetime import datetime, timedelta

# =============================================================================
# MOCK SETUP
# =============================================================================

class MockFrappeUtils:
    @staticmethod
    def cint(value):
        try:
            return 0 if value is None or value == '' else int(value)
        except (ValueError, TypeError):
            return 0
    
    @staticmethod
    def today():
        return "2025-01-15"
    
    @staticmethod
    def get_url():
        return "http://localhost:8000"
    
    @staticmethod
    def now_datetime():
        return datetime.now()
    
    @staticmethod
    def getdate(date_str=None):
        if date_str is None:
            return datetime.now().date()
        if isinstance(date_str, str):
            try:
                return datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return datetime.now().date()
        return date_str
    
    @staticmethod
    def cstr(value):
        return "" if value is None else str(value)
    
    @staticmethod
    def get_datetime(dt):
        if isinstance(dt, str):
            try:
                return datetime.strptime(dt, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                return datetime.now()
        return dt if dt else datetime.now()


class MockFrappeDocument:
    def __init__(self, doctype, name=None, **kwargs):
        self.doctype = doctype
        self.name = name or f"{doctype.upper().replace(' ', '_')}_001"
        self.creation = kwargs.get('creation', datetime.now())
        self.modified = kwargs.get('modified', datetime.now())
        self.owner = kwargs.get('owner', 'Administrator')
        self.modified_by = kwargs.get('modified_by', 'Administrator')
        self.docstatus = kwargs.get('docstatus', 0)
        self.idx = kwargs.get('idx', 1)
        
        self._setup_attributes(doctype, kwargs)
        
        for key, value in kwargs.items():
            if not hasattr(self, key):
                setattr(self, key, value)
    
    def _setup_attributes(self, doctype, kwargs):
        if doctype == "API Key":
            self.key = kwargs.get('key', 'valid_key')
            self.enabled = kwargs.get('enabled', 1)
            self.api_key_name = kwargs.get('api_key_name', 'Test API Key')
            
        elif doctype == "Student":
            self.name1 = kwargs.get('name1', 'Test Student')
            self.phone = kwargs.get('phone', '9876543210')
            self.grade = kwargs.get('grade', '5')
            self.language = kwargs.get('language', 'LANG_001')
            self.school_id = kwargs.get('school_id', 'SCHOOL_001')
            self.glific_id = kwargs.get('glific_id', 'glific_123')
            self.gender = kwargs.get('gender', 'Male')
            self.joined_on = kwargs.get('joined_on', datetime.now().date())
            self.status = kwargs.get('status', 'active')
            self.enrollment = kwargs.get('enrollment', [])
            
        elif doctype == "Teacher":
            self.first_name = kwargs.get('first_name', 'Test')
            self.last_name = kwargs.get('last_name', 'Teacher')
            self.phone_number = kwargs.get('phone_number', '9876543210')
            self.school_id = kwargs.get('school_id', 'SCHOOL_001')
            self.glific_id = kwargs.get('glific_id', '')
            self.email_id = kwargs.get('email_id', 'teacher@example.com')
            self.teacher_role = kwargs.get('teacher_role', 'Teacher')
            self.language = kwargs.get('language', 'LANG_001')
            
        elif doctype == "OTP Verification":
            self.phone_number = kwargs.get('phone_number', '9876543210')
            self.otp = kwargs.get('otp', '1234')
            self.expiry = kwargs.get('expiry', datetime.now() + timedelta(minutes=15))
            self.verified = kwargs.get('verified', 0)
            self.context = kwargs.get('context', '{}')
            
        elif doctype == "Batch":
            self.batch_id = kwargs.get('batch_id', 'BATCH_2025_001')
            self.name1 = kwargs.get('name1', 'Batch 2025')
            self.active = kwargs.get('active', True)
            self.regist_end_date = kwargs.get('regist_end_date', (datetime.now() + timedelta(days=30)).date())
            self.start_date = kwargs.get('start_date', datetime.now().date())
            self.end_date = kwargs.get('end_date', (datetime.now() + timedelta(days=90)).date())
            
        elif doctype == "School":
            self.name1 = kwargs.get('name1', 'Test School')
            self.keyword = kwargs.get('keyword', 'test_school')
            self.city = kwargs.get('city', 'CITY_001')
            self.district = kwargs.get('district', 'DISTRICT_001')
            self.state = kwargs.get('state', 'STATE_001')
            self.model = kwargs.get('model', 'MODEL_001')
            
        elif doctype == "Batch onboarding":
            self.batch_skeyword = kwargs.get('batch_skeyword', 'test_batch')
            self.school = kwargs.get('school', 'SCHOOL_001')
            self.batch = kwargs.get('batch', 'BATCH_001')
            self.kit_less = kwargs.get('kit_less', 1)
            self.model = kwargs.get('model', 'MODEL_001')
            self.from_grade = kwargs.get('from_grade', '1')
            self.to_grade = kwargs.get('to_grade', '10')
    
    def insert(self, ignore_permissions=False):
        return self
    
    def save(self, ignore_permissions=False):
        return self
    
    def append(self, field, data):
        if not hasattr(self, field):
            setattr(self, field, [])
        getattr(self, field).append(data)
        return self
    
    def get(self, field, default=None):
        return getattr(self, field, default)


class MockFrappe:
    def __init__(self):
        self.utils = MockFrappeUtils()
        self.response = Mock()
        self.response.http_status_code = 200
        self.response.update = Mock()
        self.local = Mock()
        self.local.form_dict = {}
        self.db = Mock()
        self.db.commit = Mock()
        self.db.rollback = Mock()
        self.db.sql = Mock(return_value=[])
        self.db.get_value = Mock(return_value="test_value")
        self.db.get_all = Mock(return_value=[])
        self.request = Mock()
        self.request.get_json = Mock(return_value={})
        self.request.data = '{}'
        self.flags = Mock()
        self.flags.ignore_permissions = False
        self.conf = Mock()
        self.conf.get = Mock(side_effect=lambda key, default: default)
        self.logger = Mock(return_value=Mock())
        
        self.DoesNotExistError = type('DoesNotExistError', (Exception,), {})
        self.ValidationError = type('ValidationError', (Exception,), {})
        self.DuplicateEntryError = type('DuplicateEntryError', (Exception,), {})
        
        self._configure_mocks()
    
    def _configure_mocks(self):
        def get_doc_side_effect(doctype, filters=None, **kwargs):
            if doctype == "API Key":
                key = filters.get('key') if isinstance(filters, dict) else filters
                if key in ['valid_key', 'test_key']:
                    return MockFrappeDocument(doctype, key=key, enabled=1)
                raise self.DoesNotExistError("API Key not found")
            return MockFrappeDocument(doctype, **kwargs)
        
        self.get_doc = Mock(side_effect=get_doc_side_effect)
    
    def new_doc(self, doctype):
        return MockFrappeDocument(doctype)
    
    def get_single(self, doctype):
        return MockFrappeDocument(doctype)
    
    def get_all(self, *args, **kwargs):
        return []
    
    def throw(self, message):
        raise Exception(message)
    
    def log_error(self, message, title=None):
        pass
    
    def whitelist(self, allow_guest=False):
        def decorator(func):
            return func
        return decorator


mock_frappe = MockFrappe()
mock_glific = Mock()
mock_background = Mock()
mock_requests = Mock()
mock_random = Mock()
mock_random.choices = Mock(return_value=['1', '2', '3', '4'])
mock_string = Mock()
mock_string.digits = '0123456789'

sys.modules['frappe'] = mock_frappe
sys.modules['frappe.utils'] = mock_frappe.utils
sys.modules['.glific_integration'] = mock_glific
sys.modules['tap_lms.glific_integration'] = mock_glific
sys.modules['.background_jobs'] = mock_background
sys.modules['tap_lms.background_jobs'] = mock_background
sys.modules['requests'] = mock_requests
sys.modules['random'] = mock_random
sys.modules['string'] = mock_string

try:
    import tap_lms.api as api_module
    API_MODULE_IMPORTED = True
except ImportError as e:
    print(f"ERROR: Could not import tap_lms.api: {e}")
    API_MODULE_IMPORTED = False
    api_module = None

# =============================================================================
# TEST SUITE
# =============================================================================

class BaseAPITest(unittest.TestCase):
    """Base test class with common setup and helper methods"""
    
    def setUp(self):
        """Reset all mocks before each test"""
        mock_frappe.response.http_status_code = 200
        mock_frappe.response.update = Mock()
        mock_frappe.local.form_dict = {}
        mock_frappe.request.data = '{}'
        mock_frappe.request.get_json.return_value = {}
        mock_frappe.request.get_json.side_effect = None
        mock_frappe.db.commit.reset_mock()
        mock_frappe.db.rollback.reset_mock()
        mock_frappe.db.sql.reset_mock()
        mock_frappe.db.get_value.reset_mock()
        mock_frappe.db.get_all.reset_mock()
        
        mock_glific.reset_mock()
        mock_glific.get_contact_by_phone = Mock(return_value={'id': 'contact_123'})
        mock_glific.create_contact = Mock(return_value={'id': 'new_contact_123'})
        mock_glific.update_contact_fields = Mock(return_value=True)
        mock_glific.add_contact_to_group = Mock(return_value=True)
        mock_glific.create_or_get_teacher_group_for_batch = Mock(return_value={'group_id': 'group_123', 'label': 'teacher_batch_test'})
        
        mock_background.reset_mock()
        mock_background.enqueue_glific_actions = Mock()
        
        mock_requests.reset_mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_requests.get.return_value = mock_response
        mock_requests.post.return_value = mock_response
    
    def assert_error_response(self, result, status_code, message_contains=None):
        """Helper to assert error responses"""
        self.assertEqual(result['status'], 'error')
        self.assertEqual(mock_frappe.response.http_status_code, status_code)
        if message_contains:
            self.assertIn(message_contains, result.get('message', ''))
    
    def assert_success_response(self, result, status_code=200):
        """Helper to assert success responses"""
        self.assertEqual(result['status'], 'success')
        self.assertEqual(mock_frappe.response.http_status_code, status_code)


# =============================================================================
# AUTHENTICATION TESTS
# =============================================================================

@unittest.skipUnless(API_MODULE_IMPORTED, "API module not available")
class TestAuthentication(BaseAPITest):
    """Test authentication functionality"""
    
    def test_valid_api_key(self):
        """Test authentication with valid API key"""
        result = api_module.authenticate_api_key("valid_key")
        self.assertEqual(result, "valid_key")
    
    def test_invalid_api_key(self):
        """Test authentication with invalid API key"""
        result = api_module.authenticate_api_key("invalid_key")
        self.assertIsNone(result)
    
    def test_empty_api_key(self):
        """Test authentication with empty API key"""
        result = api_module.authenticate_api_key("")
        self.assertIsNone(result)
    
    def test_none_api_key(self):
        """Test authentication with None API key"""
        result = api_module.authenticate_api_key(None)
        self.assertIsNone(result)


# =============================================================================
# LIST DISTRICTS TESTS
# =============================================================================

@unittest.skipUnless(API_MODULE_IMPORTED, "API module not available")
class TestListDistricts(BaseAPITest):
    """Test list_districts endpoint"""
    
    def test_success_with_districts(self):
        """Test successful district listing"""
        mock_frappe.request.data = json.dumps({
            'api_key': 'valid_key',
            'state': 'STATE_001'
        })
        
        with patch.object(mock_frappe, 'get_all') as mock_get_all:
            mock_get_all.return_value = [
                {'name': 'DIST_001', 'district_name': 'District 1'},
                {'name': 'DIST_002', 'district_name': 'District 2'}
            ]
            
            result = api_module.list_districts()
            
            self.assert_success_response(result)
            self.assertEqual(len(result['data']), 2)
            self.assertEqual(result['data']['DIST_001'], 'District 1')
            self.assertEqual(result['data']['DIST_002'], 'District 2')
            mock_get_all.assert_called_once()
    
    def test_no_districts_found(self):
        """Test when no districts exist for state"""
        mock_frappe.request.data = json.dumps({
            'api_key': 'valid_key',
            'state': 'STATE_EMPTY'
        })
        
        with patch.object(mock_frappe, 'get_all') as mock_get_all:
            mock_get_all.return_value = []
            
            result = api_module.list_districts()
            
            self.assert_success_response(result)
            self.assertEqual(len(result['data']), 0)
    
    def test_invalid_api_key(self):
        """Test with invalid API key"""
        mock_frappe.request.data = json.dumps({
            'api_key': 'invalid_key',
            'state': 'STATE_001'
        })
        
        result = api_module.list_districts()
        self.assert_error_response(result, 401, "Invalid API key")
    
    def test_missing_api_key(self):
        """Test with missing API key"""
        mock_frappe.request.data = json.dumps({
            'state': 'STATE_001'
        })
        
        result = api_module.list_districts()
        self.assert_error_response(result, 400, "required")
    
    def test_missing_state(self):
        """Test with missing state parameter"""
        mock_frappe.request.data = json.dumps({
            'api_key': 'valid_key'
        })
        
        result = api_module.list_districts()
        self.assert_error_response(result, 400, "required")
    
    def test_malformed_json(self):
        """Test with malformed JSON request"""
        mock_frappe.request.data = "not valid json"
        
        result = api_module.list_districts()
        self.assertEqual(result['status'], 'error')
        self.assertEqual(mock_frappe.response.http_status_code, 500)


# =============================================================================
# VERIFY KEYWORD TESTS
# =============================================================================

@unittest.skipUnless(API_MODULE_IMPORTED, "API module not available")
class TestVerifyKeyword(BaseAPITest):
    """Test verify_keyword endpoint"""
    
    def test_success_keyword_found(self):
        """Test successful keyword verification"""
        mock_frappe.request.get_json.return_value = {
            'api_key': 'valid_key',
            'keyword': 'test_school'
        }
        
        with patch.object(mock_frappe.db, 'get_value') as mock_get:
            mock_get.return_value = {
                'name1': 'Test School',
                'model': 'MODEL_001'
            }
            
            result = api_module.verify_keyword()
            
            call_args = mock_frappe.response.update.call_args[0][0]
            self.assertEqual(call_args['status'], 'success')
            self.assertEqual(call_args['school_name'], 'Test School')
            self.assertEqual(call_args['model'], 'MODEL_001')
            self.assertEqual(mock_frappe.response.http_status_code, 200)
    
    def test_keyword_not_found(self):
        """Test with non-existent keyword"""
        mock_frappe.request.get_json.return_value = {
            'api_key': 'valid_key',
            'keyword': 'nonexistent'
        }
        
        with patch.object(mock_frappe.db, 'get_value') as mock_get:
            mock_get.return_value = None
            
            result = api_module.verify_keyword()
            
            call_args = mock_frappe.response.update.call_args[0][0]
            self.assertEqual(call_args['status'], 'failure')
            self.assertEqual(mock_frappe.response.http_status_code, 404)
    
    def test_invalid_api_key(self):
        """Test with invalid API key"""
        mock_frappe.request.get_json.return_value = {
            'api_key': 'invalid_key',
            'keyword': 'test_school'
        }
        
        result = api_module.verify_keyword()
        
        call_args = mock_frappe.response.update.call_args[0][0]
        self.assertEqual(call_args['status'], 'failure')
        self.assertIn('Invalid API key', call_args['error'])
        self.assertEqual(mock_frappe.response.http_status_code, 401)
    
    def test_missing_keyword(self):
        """Test with missing keyword parameter"""
        mock_frappe.request.get_json.return_value = {
            'api_key': 'valid_key'
        }
        
        result = api_module.verify_keyword()
        
        call_args = mock_frappe.response.update.call_args[0][0]
        self.assertEqual(call_args['status'], 'failure')
        self.assertIn('missing', call_args['error'])
        self.assertEqual(mock_frappe.response.http_status_code, 400)


# =============================================================================
# OTP FLOW TESTS
# =============================================================================

@unittest.skipUnless(API_MODULE_IMPORTED, "API module not available")
class TestOTPFlow(BaseAPITest):
    """Test OTP send and verify endpoints"""
    
    def test_send_otp_new_teacher_success(self):
        """Test sending OTP for new teacher"""
        mock_frappe.request.get_json.return_value = {
            'api_key': 'valid_key',
            'phone': '9876543210'
        }
        
        with patch.object(mock_frappe, 'get_all') as mock_get_all:
            mock_get_all.return_value = []  # No existing teacher
            
            mock_response = Mock()
            mock_response.json.return_value = {"status": "success", "id": "msg_123"}
            mock_requests.get.return_value = mock_response
            
            with patch.object(mock_frappe, 'new_doc') as mock_new:
                mock_otp_doc = MockFrappeDocument('OTP Verification')
                mock_otp_doc.insert = Mock()
                mock_new.return_value = mock_otp_doc
                
                result = api_module.send_otp()
                
                self.assert_success_response(result)
                self.assertEqual(result['action_type'], 'new_teacher')
                mock_new.assert_called_with('OTP Verification')
                mock_otp_doc.insert.assert_called_once()
    
    def test_send_otp_existing_teacher_with_active_batch(self):
        """Test sending OTP for existing teacher with active batch"""
        mock_frappe.request.get_json.return_value = {
            'api_key': 'valid_key',
            'phone': '9876543210'
        }
        
        with patch.object(mock_frappe, 'get_all') as mock_get_all:
            # Existing teacher
            mock_get_all.return_value = [{'name': 'TEACHER_001', 'school_id': 'SCHOOL_001'}]
            
            with patch.object(mock_frappe.db, 'get_value') as mock_get_value:
                # School name and batch info
                def get_value_side_effect(doctype, name, field):
                    if doctype == 'School' and field == 'name1':
                        return 'Test School'
                    return None
                
                mock_get_value.side_effect = get_value_side_effect
                
                with patch.object(api_module, 'get_active_batch_for_school') as mock_batch:
                    mock_batch.return_value = {
                        'batch_name': 'BATCH_001',
                        'batch_id': 'BATCH_2025_001'
                    }
                    
                    with patch.object(mock_frappe, 'new_doc') as mock_new:
                        mock_otp_doc = MockFrappeDocument('OTP Verification')
                        mock_otp_doc.insert = Mock()
                        mock_new.return_value = mock_otp_doc
                        
                        mock_response = Mock()
                        mock_response.json.return_value = {"status": "success"}
                        mock_requests.get.return_value = mock_response
                        
                        result = api_module.send_otp()
                        
                        self.assert_success_response(result)
                        self.assertEqual(result['action_type'], 'update_batch')
    
    def test_send_otp_no_active_batch(self):
        """Test sending OTP when no active batch exists"""
        mock_frappe.request.get_json.return_value = {
            'api_key': 'valid_key',
            'phone': '9876543210'
        }
        
        with patch.object(mock_frappe, 'get_all') as mock_get_all:
            mock_get_all.return_value = [{'name': 'TEACHER_001', 'school_id': 'SCHOOL_001'}]
            
            with patch.object(api_module, 'get_active_batch_for_school') as mock_batch:
                mock_batch.return_value = {
                    'batch_name': None,
                    'batch_id': 'no_active_batch_id'
                }
                
                result = api_module.send_otp()
                
                self.assertEqual(result['status'], 'failure')
                self.assertEqual(result['code'], 'NO_ACTIVE_BATCH')
                self.assertEqual(mock_frappe.response.http_status_code, 409)
    
    def test_send_otp_whatsapp_api_failure(self):
        """Test OTP send when WhatsApp API fails"""
        mock_frappe.request.get_json.return_value = {
            'api_key': 'valid_key',
            'phone': '9876543210'
        }
        
        with patch.object(mock_frappe, 'get_all') as mock_get_all:
            mock_get_all.return_value = []
            
            with patch.object(mock_frappe, 'new_doc') as mock_new:
                mock_otp_doc = MockFrappeDocument('OTP Verification')
                mock_otp_doc.insert = Mock()
                mock_new.return_value = mock_otp_doc
                
                mock_response = Mock()
                mock_response.json.return_value = {"status": "failure", "message": "API Error"}
                mock_requests.get.return_value = mock_response
                
                result = api_module.send_otp()
                
                self.assertEqual(result['status'], 'failure')
                self.assertIn('WhatsApp', result['message'])
                self.assertEqual(mock_frappe.response.http_status_code, 500)
    
    def test_verify_otp_success_new_teacher(self):
        """Test OTP verification for new teacher"""
        mock_frappe.request.get_json.return_value = {
            'api_key': 'valid_key',
            'phone': '9876543210',
            'otp': '1234'
        }
        
        with patch.object(mock_frappe.db, 'sql') as mock_sql:
            mock_sql.return_value = [{
                'name': 'OTP_001',
                'expiry': datetime.now() + timedelta(minutes=10),
                'context': json.dumps({"action_type": "new_teacher"}),
                'verified': False
            }]
            
            result = api_module.verify_otp()
            
            self.assert_success_response(result)
            self.assertEqual(result['action_type'], 'new_teacher')
            
            # Verify OTP was marked as verified
            update_call = [call for call in mock_sql.call_args_list if 'UPDATE' in str(call)]
            self.assertTrue(len(update_call) > 0)
    
    def test_verify_otp_expired(self):
        """Test OTP verification with expired OTP"""
        mock_frappe.request.get_json.return_value = {
            'api_key': 'valid_key',
            'phone': '9876543210',
            'otp': '1234'
        }
        
        with patch.object(mock_frappe.db, 'sql') as mock_sql:
            mock_sql.return_value = [{
                'name': 'OTP_001',
                'expiry': datetime.now() - timedelta(minutes=10),  # Expired
                'context': json.dumps({"action_type": "new_teacher"}),
                'verified': False
            }]
            
            result = api_module.verify_otp()
            
            self.assertEqual(result['status'], 'failure')
            self.assertIn('expired', result['message'].lower())
            self.assertEqual(mock_frappe.response.http_status_code, 400)
    
    def test_verify_otp_already_verified(self):
        """Test OTP verification with already used OTP"""
        mock_frappe.request.get_json.return_value = {
            'api_key': 'valid_key',
            'phone': '9876543210',
            'otp': '1234'
        }
        
        with patch.object(mock_frappe.db, 'sql') as mock_sql:
            mock_sql.return_value = [{
                'name': 'OTP_001',
                'expiry': datetime.now() + timedelta(minutes=10),
                'context': json.dumps({"action_type": "new_teacher"}),
                'verified': True  # Already verified
            }]
            
            result = api_module.verify_otp()
            
            self.assertEqual(result['status'], 'failure')
            self.assertIn('already used', result['message'].lower())
            self.assertEqual(mock_frappe.response.http_status_code, 400)
    
    def test_verify_otp_invalid_otp(self):
        """Test OTP verification with invalid OTP"""
        mock_frappe.request.get_json.return_value = {
            'api_key': 'valid_key',
            'phone': '9876543210',
            'otp': 'wrong'
        }
        
        with patch.object(mock_frappe.db, 'sql') as mock_sql:
            mock_sql.return_value = []  # No matching OTP
            
            result = api_module.verify_otp()
            
            self.assertEqual(result['status'], 'failure')
            self.assertIn('Invalid OTP', result['message'])
            self.assertEqual(mock_frappe.response.http_status_code, 400)
    
    def test_verify_otp_update_batch_success(self):
        """Test OTP verification for update_batch action"""
        mock_frappe.request.get_json.return_value = {
            'api_key': 'valid_key',
            'phone': '9876543210',
            'otp': '1234'
        }
        
        context = {
            "action_type": "update_batch",
            "teacher_id": "TEACHER_001",
            "school_id": "SCHOOL_001",
            "batch_info": {
                "batch_name": "BATCH_001",
                "batch_id": "BATCH_2025_001"
            }
        }
        
        with patch.object(mock_frappe.db, 'sql') as mock_sql:
            mock_sql.return_value = [{
                'name': 'OTP_001',
                'expiry': datetime.now() + timedelta(minutes=10),
                'context': json.dumps(context),
                'verified': False
            }]
            
            with patch.object(mock_frappe, 'get_doc') as mock_get_doc:
                mock_teacher = MockFrappeDocument('Teacher',
                    name='TEACHER_001',
                    first_name='Test',
                    phone_number='9876543210',
                    glific_id='glific_123')
                mock_teacher.save = Mock()
                mock_get_doc.return_value = mock_teacher
                
                with patch.object(api_module, 'get_model_for_school') as mock_model:
                    mock_model.return_value = 'TAP_MODEL_1'
                    
                    with patch.object(mock_frappe.db, 'get_value') as mock_get_value:
                        mock_get_value.return_value = 'Test School'
                        
                        result = api_module.verify_otp()
                        
                        self.assert_success_response(result)
                        self.assertEqual(result['action_type'], 'update_batch')
                        self.assertEqual(result['teacher_id'], 'TEACHER_001')
                        self.assertEqual(result['batch_id'], 'BATCH_2025_001')
                        
                        # Verify Glific operations were called
                        mock_glific.update_contact_fields.assert_called()
                        mock_glific.create_or_get_teacher_group_for_batch.assert_called()
                        mock_glific.add_contact_to_group.assert_called()
                        mock_background.enqueue_glific_actions.assert_called()
    
    def test_verify_otp_update_batch_no_glific_id(self):
        """Test update_batch when teacher has no Glific ID"""
        mock_frappe.request.get_json.return_value = {
            'api_key': 'valid_key',
            'phone': '9876543210',
            'otp': '1234'
        }
        
        context = {
            "action_type": "update_batch",
            "teacher_id": "TEACHER_001",
            "school_id": "SCHOOL_001",
            "batch_info": {
                "batch_name": "BATCH_001",
                "batch_id": "BATCH_2025_001"
            }
        }
        
        with patch.object(mock_frappe.db, 'sql') as mock_sql:
            mock_sql.return_value = [{
                'name': 'OTP_001',
                'expiry': datetime.now() + timedelta(minutes=10),
                'context': json.dumps(context),
                'verified': False
            }]
            
            with patch.object(mock_frappe, 'get_doc') as mock_get_doc:
                mock_teacher = MockFrappeDocument('Teacher',
                    name='TEACHER_001',
                    first_name='Test',
                    phone_number='9876543210',
                    glific_id='')  # No Glific ID
                mock_teacher.save = Mock()
                mock_get_doc.return_value = mock_teacher
                
                with patch.object(api_module, 'get_model_for_school') as mock_model:
                    mock_model.return_value = 'TAP_MODEL_1'
                    
                    with patch.object(mock_frappe.db, 'get_value') as mock_get_value:
                        mock_get_value.return_value = 'Test School'
                        
                        # Mock get_contact_by_phone to return existing contact
                        mock_glific.get_contact_by_phone.return_value = {'id': 'new_glific_123'}
                        
                        result = api_module.verify_otp()
                        
                        self.assert_success_response(result)
                        # Verify teacher was linked to Glific contact
                        mock_teacher.save.assert_called()
                        self.assertEqual(mock_teacher.glific_id, 'new_glific_123')


# =============================================================================
# CREATE STUDENT TESTS
# =============================================================================

@unittest.skipUnless(API_MODULE_IMPORTED, "API module not available")
class TestCreateStudent(BaseAPITest):
    """Test create_student endpoint"""
    
    def test_success_new_student(self):
        """Test creating a new student successfully"""
        mock_frappe.local.form_dict = {
            'api_key': 'valid_key',
            'student_name': 'John Doe',
            'phone': '9876543210',
            'gender': 'Male',
            'grade': '5',
            'language': 'English',
            'batch_skeyword': 'test_batch',
            'vertical': 'Math',
            'glific_id': 'new_glific_123'
        }
        
        with patch.object(mock_frappe, 'get_all') as mock_get_all:
            mock_get_all.side_effect = [
                [{'name': 'BO_001', 'school': 'SCHOOL_001', 
                  'batch': 'BATCH_001', 'kit_less': 1}],
                [{'name': 'VERT_001'}],
                []  # No existing student
            ]
            
            with patch.object(mock_frappe, 'get_doc') as mock_get_doc:
                mock_batch = MockFrappeDocument('Batch',
                    name='BATCH_001',
                    active=True,
                    regist_end_date=(datetime.now() + timedelta(days=30)).date())
                mock_get_doc.return_value = mock_batch
                
                with patch.object(api_module, 'get_course_level_with_mapping') as mock_course:
                    mock_course.return_value = 'COURSE_LEVEL_001'
                    
                    with patch.object(api_module, 'create_new_student') as mock_create:
                        mock_student = MockFrappeDocument('Student', 
                            name='STUDENT_NEW_001',
                            name1='John Doe',
                            phone='9876543210')
                        mock_student.enrollment = []
                        mock_student.save = Mock()
                        mock_create.return_value = mock_student
                        
                        result = api_module.create_student()
                        
                        self.assertEqual(result['status'], 'success')
                        self.assertEqual(result['crm_student_id'], 'STUDENT_NEW_001')
                        self.assertEqual(result['assigned_course_level'], 'COURSE_LEVEL_001')
                        
                        # Verify enrollment was added
                        self.assertEqual(len(mock_student.enrollment), 1)
                        enrollment = mock_student.enrollment[0]
                        self.assertEqual(enrollment['batch'], 'BATCH_001')
                        self.assertEqual(enrollment['course'], 'COURSE_LEVEL_001')
                        self.assertEqual(enrollment['grade'], '5')
    
    def test_update_existing_student_matching_details(self):
        """Test updating existing student with matching name and phone"""
        mock_frappe.local.form_dict = {
            'api_key': 'valid_key',
            'student_name': 'John Doe',
            'phone': '9876543210',
            'gender': 'Male',
            'grade': '6',  # Different grade
            'language': 'Hindi',  # Different language
            'batch_skeyword': 'test_batch',
            'vertical': 'Math',
            'glific_id': 'existing_glific_123'
        }
        
        with patch.object(mock_frappe, 'get_all') as mock_get_all:
            mock_get_all.side_effect = [
                [{'name': 'BO_001', 'school': 'SCHOOL_001', 
                  'batch': 'BATCH_001', 'kit_less': 1}],
                [{'name': 'VERT_001'}],
                [{'name': 'STUDENT_001', 'name1': 'John Doe', 'phone': '9876543210'}]  # Existing student
            ]
            
            with patch.object(mock_frappe, 'get_doc') as mock_get_doc:
                def get_doc_side_effect(doctype, name_or_filters):
                    if doctype == 'Batch':
                        return MockFrappeDocument('Batch',
                            name='BATCH_001',
                            active=True,
                            regist_end_date=(datetime.now() + timedelta(days=30)).date())
                    elif doctype == 'Student':
                        mock_student = MockFrappeDocument('Student',
                            name='STUDENT_001',
                            name1='John Doe',
                            phone='9876543210',
                            grade='5',  # Old grade
                            language='LANG_001')
                        mock_student.enrollment = []
                        mock_student.save = Mock()
                        return mock_student
                
                mock_get_doc.side_effect = get_doc_side_effect
                
                with patch.object(api_module, 'get_course_level_with_mapping') as mock_course:
                    mock_course.return_value = 'COURSE_LEVEL_002'
                    
                    with patch.object(api_module, 'get_tap_language') as mock_lang:
                        mock_lang.return_value = 'LANG_002'
                        
                        result = api_module.create_student()
                        
                        self.assertEqual(result['status'], 'success')
                        self.assertEqual(result['crm_student_id'], 'STUDENT_001')
    
    def test_missing_required_fields(self):
        """Test with missing required fields"""
        mock_frappe.local.form_dict = {
            'api_key': 'valid_key',
            'student_name': 'Test'
            # Missing other required fields
        }
        
        result = api_module.create_student()
        
        self.assertEqual(result['status'], 'error')
        self.assertIn('required', result['message'].lower())
    
    def test_invalid_batch_keyword(self):
        """Test with invalid batch keyword"""
        mock_frappe.local.form_dict = {
            'api_key': 'valid_key',
            'student_name': 'Test',
            'phone': '9876543210',
            'gender': 'Male',
            'grade': '5',
            'language': 'English',
            'batch_skeyword': 'invalid_batch',
            'vertical': 'Math',
            'glific_id': 'test'
        }
        
        with patch.object(mock_frappe, 'get_all') as mock_get_all:
            mock_get_all.return_value = []  # No batch onboarding found
            
            result = api_module.create_student()
            
            self.assertEqual(result['status'], 'error')
            self.assertIn('Invalid batch_skeyword', result['message'])
    
    def test_inactive_batch(self):
        """Test registration for inactive batch"""
        mock_frappe.local.form_dict = {
            'api_key': 'valid_key',
            'student_name': 'Test',
            'phone': '9876543210',
            'gender': 'Male',
            'grade': '5',
            'language': 'English',
            'batch_skeyword': 'inactive_batch',
            'vertical': 'Math',
            'glific_id': 'test'
        }
        
        with patch.object(mock_frappe, 'get_all') as mock_get_all:
            mock_get_all.return_value = [
                {'name': 'BO_001', 'school': 'SCHOOL_001', 
                 'batch': 'BATCH_001', 'kit_less': 1}
            ]
            
            with patch.object(mock_frappe, 'get_doc') as mock_get_doc:
                mock_batch = MockFrappeDocument('Batch', 
                    active=False,  # Inactive
                    regist_end_date=(datetime.now() + timedelta(days=30)).date())
                mock_get_doc.return_value = mock_batch
                
                result = api_module.create_student()
                
                self.assertEqual(result['status'], 'error')
                self.assertIn('not active', result['message'])
    
    def test_registration_ended(self):
        """Test registration after end date"""
        mock_frappe.local.form_dict = {
            'api_key': 'valid_key',
            'student_name': 'Test',
            'phone': '9876543210',
            'gender': 'Male',
            'grade': '5',
            'language': 'English',
            'batch_skeyword': 'past_batch',
            'vertical': 'Math',
            'glific_id': 'test'
        }
        
        with patch.object(mock_frappe, 'get_all') as mock_get_all:
            mock_get_all.return_value = [
                {'name': 'BO_001', 'school': 'SCHOOL_001', 
                 'batch': 'BATCH_001', 'kit_less': 1}
            ]
            
            with patch.object(mock_frappe, 'get_doc') as mock_get_doc:
                mock_batch = MockFrappeDocument('Batch',
                    active=True,
                    regist_end_date=(datetime.now() - timedelta(days=10)).date())  # Past date
                mock_get_doc.return_value = mock_batch
                
                result = api_module.create_student()
                
                self.assertEqual(result['status'], 'error')
                self.assertIn('ended', result['message'].lower())
    
    def test_invalid_vertical(self):
        """Test with invalid course vertical"""
        mock_frappe.local.form_dict = {
            'api_key': 'valid_key',
            'student_name': 'Test',
            'phone': '9876543210',
            'gender': 'Male',
            'grade': '5',
            'language': 'English',
            'batch_skeyword': 'test_batch',
            'vertical': 'InvalidVertical',
            'glific_id': 'test'
        }
        
        with patch.object(mock_frappe, 'get_all') as mock_get_all:
            mock_get_all.side_effect = [
                [{'name': 'BO_001', 'school': 'SCHOOL_001', 
                  'batch': 'BATCH_001', 'kit_less': 1}],
                []  # No vertical found
            ]
            
            with patch.object(mock_frappe, 'get_doc') as mock_get_doc:
                mock_batch = MockFrappeDocument('Batch',
                    active=True,
                    regist_end_date=(datetime.now() + timedelta(days=30)).date())
                mock_get_doc.return_value = mock_batch
                
                result = api_module.create_student()
                
                self.assertEqual(result['status'], 'error')
                self.assertIn('Invalid vertical', result['message'])


# =============================================================================
# COURSE LEVEL SELECTION TESTS
# =============================================================================

@unittest.skipUnless(API_MODULE_IMPORTED, "API module not available")
class TestCourseLevelSelection(BaseAPITest):
    """Test course level selection logic"""
    
    def test_determine_student_type_new(self):
        """Test determining new student type"""
        with patch.object(mock_frappe.db, 'sql') as mock_sql:
            mock_sql.return_value = []  # No previous enrollment
            
            result = api_module.determine_student_type('9876543210', 'John Doe', 'VERT_001')
            
            self.assertEqual(result, 'New')
    
    def test_determine_student_type_old(self):
        """Test determining old student type"""
        with patch.object(mock_frappe.db, 'sql') as mock_sql:
            mock_sql.return_value = [{'name': 'STUDENT_001'}]  # Has previous enrollment
            
            result = api_module.determine_student_type('9876543210', 'John Doe', 'VERT_001')
            
            self.assertEqual(result, 'Old')
    
    def test_get_current_academic_year_after_april(self):
        """Test academic year calculation after April"""
        test_date = datetime(2025, 5, 1).date()  # May 2025
        
        with patch('tap_lms.api.frappe.utils.getdate') as mock_getdate:
            mock_getdate.return_value = test_date
            
            result = api_module.get_current_academic_year()
            
            self.assertEqual(result, '2025-26')
    
    def test_get_current_academic_year_before_april(self):
        """Test academic year calculation before April"""
        test_date = datetime(2025, 2, 1).date()  # February 2025
        
        with patch('tap_lms.api.frappe.utils.getdate') as mock_getdate:
            mock_getdate.return_value = test_date
            
            result = api_module.get_current_academic_year()
            
            self.assertEqual(result, '2024-25')
    
    def test_course_level_with_mapping_found(self):
        """Test course level selection with valid mapping"""
        with patch.object(api_module, 'determine_student_type') as mock_type:
            mock_type.return_value = 'New'
            
            with patch.object(api_module, 'get_current_academic_year') as mock_year:
                mock_year.return_value = '2025-26'
                
                with patch.object(mock_frappe, 'get_all') as mock_get_all:
                    mock_get_all.return_value = [{
                        'assigned_course_level': 'COURSE_LEVEL_001',
                        'mapping_name': 'Test Mapping'
                    }]
                    
                    result = api_module.get_course_level_with_mapping(
                        'VERT_001', '5', '9876543210', 'John Doe', 1
                    )
                    
                    self.assertEqual(result, 'COURSE_LEVEL_001')
    
    def test_course_level_with_flexible_mapping(self):
        """Test course level selection with flexible mapping (null academic year)"""
        with patch.object(api_module, 'determine_student_type') as mock_type:
            mock_type.return_value = 'New'
            
            with patch.object(api_module, 'get_current_academic_year') as mock_year:
                mock_year.return_value = '2025-26'
                
                with patch.object(mock_frappe, 'get_all') as mock_get_all:
                    def get_all_side_effect(doctype, filters, **kwargs):
                        # First call with academic year - no results
                        if filters.get('academic_year') == '2025-26':
                            return []
                        # Second call with null academic year - has results
                        elif filters.get('academic_year') == ["is", "not set"]:
                            return [{
                                'assigned_course_level': 'COURSE_LEVEL_FLEX',
                                'mapping_name': 'Flexible Mapping'
                            }]
                        return []
                    
                    mock_get_all.side_effect = get_all_side_effect
                    
                    result = api_module.get_course_level_with_mapping(
                        'VERT_001', '5', '9876543210', 'John Doe', 1
                    )
                    
                    self.assertEqual(result, 'COURSE_LEVEL_FLEX')
    
    def test_course_level_fallback_to_stage_grades(self):
        """Test fallback to Stage Grades logic"""
        with patch.object(api_module, 'determine_student_type') as mock_type:
            mock_type.return_value = 'New'
            
            with patch.object(api_module, 'get_current_academic_year') as mock_year:
                mock_year.return_value = '2025-26'
                
                with patch.object(mock_frappe, 'get_all') as mock_get_all:
                    mock_get_all.return_value = []  # No mapping found
                    
                    with patch.object(api_module, 'get_course_level_original') as mock_original:
                        mock_original.return_value = 'COURSE_LEVEL_FALLBACK'
                        
                        result = api_module.get_course_level_with_mapping(
                            'VERT_001', '5', '9876543210', 'John Doe', 1
                        )
                        
                        self.assertEqual(result, 'COURSE_LEVEL_FALLBACK')
                        mock_original.assert_called_once()


# =============================================================================
# CREATE TEACHER WEB TESTS
# =============================================================================

@unittest.skipUnless(API_MODULE_IMPORTED, "API module not available")
class TestCreateTeacherWeb(BaseAPITest):
    """Test create_teacher_web endpoint"""
    
    def test_success_new_teacher_new_glific_contact(self):
        """Test creating new teacher with new Glific contact"""
        mock_frappe.request.get_json.return_value = {
            'api_key': 'valid_key',
            'firstName': 'John',
            'lastName': 'Teacher',
            'phone': '9876543210',
            'School_name': 'Test School',
            'language': 'LANG_001'
        }
        
        with patch.object(mock_frappe.db, 'get_value') as mock_get_value:
            def get_value_side_effect(doctype, filters, fields=None):
                if doctype == 'OTP Verification':
                    return 'OTP_001'  # Verified
                elif doctype == 'Teacher':
                    return None  # No existing teacher
                elif doctype == 'School':
                    return 'SCHOOL_001'
                elif doctype == 'TAP Language':
                    return 'lang_id_123'
                return 'Test School'
            
            mock_get_value.side_effect = get_value_side_effect
            
            with patch.object(mock_frappe, 'new_doc') as mock_new:
                mock_teacher = MockFrappeDocument('Teacher',
                    name='TEACHER_NEW_001',
                    first_name='John',
                    phone_number='9876543210')
                mock_teacher.insert = Mock()
                mock_teacher.save = Mock()
                mock_new.return_value = mock_teacher
                
                with patch.object(api_module, 'get_active_batch_for_school') as mock_batch:
                    mock_batch.return_value = {
                        'batch_name': 'BATCH_001',
                        'batch_id': 'BATCH_2025_001'
                    }
                    
                    with patch.object(api_module, 'get_model_for_school') as mock_model:
                        mock_model.return_value = 'TAP_MODEL_1'
                        
                        # No existing Glific contact
                        mock_glific.get_contact_by_phone.return_value = None
                        mock_glific.create_contact.return_value = {'id': 'new_glific_456'}
                        
                        result = api_module.create_teacher_web()
                        
                        self.assertEqual(result['status'], 'success')
                        self.assertEqual(result['teacher_id'], 'TEACHER_NEW_001')
                        self.assertEqual(result['glific_contact_id'], 'new_glific_456')
                        
                        # Verify Glific operations
                        mock_glific.create_contact.assert_called_once()
                        mock_background.enqueue_glific_actions.assert_called_once()
    
    def test_success_new_teacher_existing_glific_contact(self):
        """Test creating new teacher with existing Glific contact"""
        mock_frappe.request.get_json.return_value = {
            'api_key': 'valid_key',
            'firstName': 'Jane',
            'phone': '9876543211',
            'School_name': 'Test School',
            'language': 'LANG_001'
        }
        
        with patch.object(mock_frappe.db, 'get_value') as mock_get_value:
            def get_value_side_effect(doctype, filters, fields=None):
                if doctype == 'OTP Verification':
                    return 'OTP_001'
                elif doctype == 'Teacher':
                    return None
                elif doctype == 'School':
                    return 'SCHOOL_001'
                return 'Test School'
            
            mock_get_value.side_effect = get_value_side_effect
            
            with patch.object(mock_frappe, 'new_doc') as mock_new:
                mock_teacher = MockFrappeDocument('Teacher',
                    name='TEACHER_NEW_002',
                    first_name='Jane',
                    phone_number='9876543211')
                mock_teacher.insert = Mock()
                mock_teacher.save = Mock()
                mock_new.return_value = mock_teacher
                
                with patch.object(api_module, 'get_active_batch_for_school') as mock_batch:
                    mock_batch.return_value = {
                        'batch_name': 'BATCH_001',
                        'batch_id': 'BATCH_2025_001'
                    }
                    
                    with patch.object(api_module, 'get_model_for_school') as mock_model:
                        mock_model.return_value = 'TAP_MODEL_1'
                        
                        # Existing Glific contact
                        mock_glific.get_contact_by_phone.return_value = {'id': 'existing_glific_789'}
                        
                        result = api_module.create_teacher_web()
                        
                        self.assertEqual(result['status'], 'success')
                        self.assertEqual(result['glific_contact_id'], 'existing_glific_789')
                        
                        # Should update, not create
                        mock_glific.create_contact.assert_not_called()
                        mock_glific.update_contact_fields.assert_called_once()
    
    def test_phone_not_verified(self):
        """Test teacher creation with unverified phone"""
        mock_frappe.request.get_json.return_value = {
            'api_key': 'valid_key',
            'firstName': 'John',
            'phone': '9876543210',
            'School_name': 'Test School'
        }
        
        with patch.object(mock_frappe.db, 'get_value') as mock_get_value:
            mock_get_value.return_value = None  # Not verified
            
            result = api_module.create_teacher_web()
            
            self.assertEqual(result['status'], 'failure')
            self.assertIn('not verified', result['message'].lower())
    
    def test_duplicate_phone_number(self):
        """Test teacher creation with duplicate phone number"""
        mock_frappe.request.get_json.return_value = {
            'api_key': 'valid_key',
            'firstName': 'John',
            'phone': '9876543210',
            'School_name': 'Test School'
        }
        
        with patch.object(mock_frappe.db, 'get_value') as mock_get_value:
            def get_value_side_effect(doctype, filters, fields=None):
                if doctype == 'OTP Verification':
                    return 'OTP_001'  # Verified
                elif doctype == 'Teacher':
                    return 'TEACHER_EXISTS_001'  # Existing teacher
                return None
            
            mock_get_value.side_effect = get_value_side_effect
            
            result = api_module.create_teacher_web()
            
            self.assertEqual(result['status'], 'failure')
            self.assertIn('already exists', result['message'].lower())
    
    def test_school_not_found(self):
        """Test teacher creation with non-existent school"""
        mock_frappe.request.get_json.return_value = {
            'api_key': 'valid_key',
            'firstName': 'John',
            'phone': '9876543210',
            'School_name': 'Nonexistent School'
        }
        
        with patch.object(mock_frappe.db, 'get_value') as mock_get_value:
            def get_value_side_effect(doctype, filters, fields=None):
                if doctype == 'OTP Verification':
                    return 'OTP_001'
                elif doctype == 'Teacher':
                    return None
                elif doctype == 'School':
                    return None  # School not found
                return None
            
            mock_get_value.side_effect = get_value_side_effect
            
            result = api_module.create_teacher_web()
            
            self.assertEqual(result['status'], 'failure')
            self.assertIn('not found', result['message'].lower())


# =============================================================================
# BATCH KEYWORD LIST TESTS
# =============================================================================

@unittest.skipUnless(API_MODULE_IMPORTED, "API module not available")
class TestBatchKeywordList(BaseAPITest):
    """Test list_batch_keyword endpoint"""
    
    def test_multiple_active_batches(self):
        """Test listing multiple active batches"""
        with patch.object(mock_frappe, 'get_all') as mock_get_all:
            mock_get_all.return_value = [
                {'batch': 'BATCH_001', 'school': 'SCHOOL_001', 'batch_skeyword': 'batch1'},
                {'batch': 'BATCH_002', 'school': 'SCHOOL_002', 'batch_skeyword': 'batch2'},
                {'batch': 'BATCH_003', 'school': 'SCHOOL_003', 'batch_skeyword': 'batch3'}
            ]
            
            with patch.object(mock_frappe, 'get_doc') as mock_get_doc:
                def get_doc_side_effect(doctype, name):
                    batches = {
                        'BATCH_001': MockFrappeDocument('Batch', name='BATCH_001', batch_id='B1',
                            active=True, regist_end_date=(datetime.now() + timedelta(days=5)).date()),
                        'BATCH_002': MockFrappeDocument('Batch', name='BATCH_002', batch_id='B2',
                            active=True, regist_end_date=(datetime.now() + timedelta(days=10)).date()),
                        'BATCH_003': MockFrappeDocument('Batch', name='BATCH_003', batch_id='B3',
                            active=True, regist_end_date=(datetime.now() + timedelta(days=15)).date())
                    }
                    return batches.get(name, MockFrappeDocument(doctype))
                
                mock_get_doc.side_effect = get_doc_side_effect
                
                with patch.object(mock_frappe, 'get_value') as mock_get_val:
                    def get_value_side_effect(dt, name, field):
                        schools = {
                            'SCHOOL_001': 'School One',
                            'SCHOOL_002': 'School Two',
                            'SCHOOL_003': 'School Three'
                        }
                        return schools.get(name, 'Unknown')
                    
                    mock_get_val.side_effect = get_value_side_effect
                    
                    result = api_module.list_batch_keyword('valid_key')
                    
                    self.assertIsInstance(result, list)
                    self.assertEqual(len(result), 3)
                    
                    batch_ids = [item['batch_id'] for item in result]
                    self.assertIn('B1', batch_ids)
                    self.assertIn('B2', batch_ids)
                    self.assertIn('B3', batch_ids)
    
    def test_filters_inactive_batches(self):
        """Test that inactive batches are filtered out"""
        with patch.object(mock_frappe, 'get_all') as mock_get_all:
            mock_get_all.return_value = [
                {'batch': 'BATCH_ACTIVE', 'school': 'SCHOOL_001', 'batch_skeyword': 'active'},
                {'batch': 'BATCH_INACTIVE', 'school': 'SCHOOL_002', 'batch_skeyword': 'inactive'}
            ]
            
            with patch.object(mock_frappe, 'get_doc') as mock_get_doc:
                def get_doc_side_effect(doctype, name):
                    if name == 'BATCH_ACTIVE':
                        return MockFrappeDocument('Batch', name=name, batch_id='ACTIVE_001',
                            active=True, regist_end_date=(datetime.now() + timedelta(days=10)).date())
                    else:
                        return MockFrappeDocument('Batch', name=name, batch_id='INACTIVE_001',
                            active=False, regist_end_date=(datetime.now() + timedelta(days=10)).date())
                
                mock_get_doc.side_effect = get_doc_side_effect
                
                with patch.object(mock_frappe, 'get_value') as mock_get_val:
                    mock_get_val.return_value = 'Test School'
                    
                    result = api_module.list_batch_keyword('valid_key')
                    
                    self.assertEqual(len(result), 1)
                    self.assertEqual(result[0]['batch_id'], 'ACTIVE_001')
    
    def test_filters_expired_registration(self):
        """Test that batches with expired registration are filtered out"""
        with patch.object(mock_frappe, 'get_all') as mock_get_all:
            mock_get_all.return_value = [
                {'batch': 'BATCH_CURRENT', 'school': 'SCHOOL_001', 'batch_skeyword': 'current'},
                {'batch': 'BATCH_EXPIRED', 'school': 'SCHOOL_002', 'batch_skeyword': 'expired'}
            ]
            
            with patch.object(mock_frappe, 'get_doc') as mock_get_doc:
                def get_doc_side_effect(doctype, name):
                    if name == 'BATCH_CURRENT':
                        return MockFrappeDocument('Batch', name=name, batch_id='CURRENT_001',
                            active=True, regist_end_date=(datetime.now() + timedelta(days=10)).date())
                    else:
                        return MockFrappeDocument('Batch', name=name, batch_id='EXPIRED_001',
                            active=True, regist_end_date=(datetime.now() - timedelta(days=10)).date())
                
                mock_get_doc.side_effect = get_doc_side_effect
                
                with patch.object(mock_frappe, 'get_value') as mock_get_val:
                    mock_get_val.return_value = 'Test School'
                    
                    result = api_module.list_batch_keyword('valid_key')
                    
                    self.assertEqual(len(result), 1)
                    self.assertEqual(result[0]['batch_id'], 'CURRENT_001')


# =============================================================================
# GET ACTIVE BATCH TESTS
# =============================================================================

@unittest.skipUnless(API_MODULE_IMPORTED, "API module not available")
class TestGetActiveBatch(BaseAPITest):
    """Test get_active_batch_for_school function"""
    
    def test_success_batch_found(self):
        """Test finding active batch for school"""
        with patch.object(mock_frappe, 'get_all') as mock_get_all:
            mock_get_all.return_value = [
                {'batch': 'BATCH_ACTIVE_001', 'name': 'BO_001'}
            ]
            
            with patch.object(mock_frappe, 'get_doc') as mock_get_doc:
                mock_batch = MockFrappeDocument('Batch',
                    name='BATCH_ACTIVE_001',
                    batch_id='BATCH_2025_ACTIVE',
                    active=True,
                    regist_end_date=(datetime.now() + timedelta(days=10)).date())
                mock_get_doc.return_value = mock_batch
                
                result = api_module.get_active_batch_for_school('SCHOOL_001')
                
                self.assertIsNotNone(result)
                self.assertEqual(result['batch_name'], 'BATCH_ACTIVE_001')
                self.assertEqual(result['batch_id'], 'BATCH_2025_ACTIVE')
                mock_get_doc.assert_called_with('Batch', 'BATCH_ACTIVE_001')
    
    def test_no_active_batch(self):
        """Test when no active batch exists"""
        with patch.object(mock_frappe, 'get_all') as mock_get_all:
            mock_get_all.return_value = []
            
            result = api_module.get_active_batch_for_school('SCHOOL_NO_BATCH')
            
            self.assertEqual(result['batch_name'], None)
            self.assertEqual(result['batch_id'], 'no_active_batch_id')


# =============================================================================
# UPDATE TEACHER ROLE TESTS
# =============================================================================

@unittest.skipUnless(API_MODULE_IMPORTED, "API module not available")
class TestUpdateTeacherRole(BaseAPITest):
    """Test update_teacher_role endpoint"""
    
    def test_success_update_role(self):
        """Test successfully updating teacher role"""
        mock_frappe.request.data = json.dumps({
            'api_key': 'valid_key',
            'glific_id': 'glific_123',
            'teacher_role': 'HM'
        })
        
        with patch.object(mock_frappe, 'get_all') as mock_get_all:
            mock_get_all.return_value = [{
                'name': 'TEACHER_001',
                'first_name': 'John',
                'last_name': 'Doe',
                'teacher_role': 'Teacher',
                'school_id': 'SCHOOL_001'
            }]
            
            with patch.object(mock_frappe, 'get_doc') as mock_get_doc:
                mock_teacher = MockFrappeDocument('Teacher',
                    name='TEACHER_001',
                    first_name='John',
                    last_name='Doe',
                    teacher_role='Teacher',
                    school_id='SCHOOL_001')
                mock_teacher.save = Mock()
                mock_get_doc.return_value = mock_teacher
                
                with patch.object(mock_frappe.db, 'get_value') as mock_get_value:
                    mock_get_value.return_value = 'Test School'
                    
                    result = api_module.update_teacher_role()
                    
                    self.assert_success_response(result)
                    self.assertEqual(result['data']['new_role'], 'HM')
                    self.assertEqual(result['data']['old_role'], 'Teacher')
                    mock_teacher.save.assert_called_once()
    
    def test_invalid_role_value(self):
        """Test with invalid teacher role"""
        mock_frappe.request.data = json.dumps({
            'api_key': 'valid_key',
            'glific_id': 'glific_123',
            'teacher_role': 'InvalidRole'
        })
        
        result = api_module.update_teacher_role()
        
        self.assert_error_response(result, 400, "Invalid teacher_role")
    
    def test_teacher_not_found(self):
        """Test updating role for non-existent teacher"""
        mock_frappe.request.data = json.dumps({
            'api_key': 'valid_key',
            'glific_id': 'nonexistent',
            'teacher_role': 'HM'
        })
        
        with patch.object(mock_frappe, 'get_all') as mock_get_all:
            mock_get_all.return_value = []
            
            result = api_module.update_teacher_role()
            
            self.assert_error_response(result, 404, "No teacher found")


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == '__main__':
    # Run with verbose output
    unittest.main(verbosity=2)