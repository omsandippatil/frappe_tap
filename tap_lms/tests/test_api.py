"""
High-Coverage Test Suite for tap_lms/api.py
Targets specific uncovered line ranges to achieve 90%+ coverage
"""

import sys
import unittest
from unittest.mock import Mock, patch, MagicMock
import json
from datetime import datetime, timedelta

# Import the real API module - this is critical for coverage
import tap_lms.api as api


class TestAPIHighCoverage(unittest.TestCase):
    """Tests designed to cover specific missing line ranges"""
    
    def setUp(self):
        """Reset before each test"""
        pass
    
    # =========================================================================
    # LINES 351-469: create_teacher function
    # =========================================================================
    
    def test_create_teacher_success(self):
        """Test create_teacher with valid data"""
        with patch('tap_lms.api.authenticate_api_key', return_value='valid_key'):
            with patch('tap_lms.api.frappe.db.get_value', return_value='SCHOOL_001'):
                with patch('tap_lms.api.frappe.new_doc') as mock_new_doc:
                    mock_teacher = Mock()
                    mock_teacher.name = 'TEACHER_001'
                    mock_teacher.insert = Mock()
                    mock_new_doc.return_value = mock_teacher
                    
                    with patch('tap_lms.api.frappe.db.commit'):
                        result = api.create_teacher(
                            api_key='valid_key',
                            keyword='test_school',
                            first_name='John',
                            phone_number='9876543210',
                            glific_id='glific_123',
                            last_name='Doe',
                            email='john@test.com',
                            language='LANG_001'
                        )
                        
                        self.assertIn('teacher_id', result)
                        self.assertEqual(result['teacher_id'], 'TEACHER_001')
    
    def test_create_teacher_invalid_api_key(self):
        """Test create_teacher with invalid API key"""
        with patch('tap_lms.api.authenticate_api_key', return_value=None):
            with patch('tap_lms.api.frappe.throw', side_effect=Exception("Invalid API key")):
                with self.assertRaises(Exception):
                    api.create_teacher(
                        api_key='invalid',
                        keyword='test',
                        first_name='John',
                        phone_number='9876543210',
                        glific_id='test'
                    )
    
    def test_create_teacher_school_not_found(self):
        """Test create_teacher when school doesn't exist"""
        with patch('tap_lms.api.authenticate_api_key', return_value='valid_key'):
            with patch('tap_lms.api.frappe.db.get_value', return_value=None):
                result = api.create_teacher(
                    api_key='valid_key',
                    keyword='nonexistent',
                    first_name='John',
                    phone_number='9876543210',
                    glific_id='test'
                )
                
                self.assertIn('error', result)
    
    def test_create_teacher_duplicate_phone(self):
        """Test create_teacher with duplicate phone number"""
        with patch('tap_lms.api.authenticate_api_key', return_value='valid_key'):
            with patch('tap_lms.api.frappe.db.get_value', return_value='SCHOOL_001'):
                with patch('tap_lms.api.frappe.new_doc') as mock_new_doc:
                    mock_teacher = Mock()
                    mock_teacher.insert = Mock(side_effect=api.frappe.DuplicateEntryError())
                    mock_new_doc.return_value = mock_teacher
                    
                    result = api.create_teacher(
                        api_key='valid_key',
                        keyword='test',
                        first_name='John',
                        phone_number='9876543210',
                        glific_id='test'
                    )
                    
                    self.assertIn('error', result)
    
    def test_create_teacher_general_exception(self):
        """Test create_teacher with general exception"""
        with patch('tap_lms.api.authenticate_api_key', return_value='valid_key'):
            with patch('tap_lms.api.frappe.db.get_value', side_effect=Exception("DB Error")):
                result = api.create_teacher(
                    api_key='valid_key',
                    keyword='test',
                    first_name='John',
                    phone_number='9876543210',
                    glific_id='test'
                )
                
                self.assertIn('error', result)
    
    # =========================================================================
    # LINES 1327-1493: send_otp variants
    # =========================================================================
    
    def test_send_otp_v0_new_teacher(self):
        """Test send_otp_v0 for new teacher"""
        with patch('tap_lms.api.authenticate_api_key', return_value='valid_key'):
            with patch('tap_lms.api.frappe.request') as mock_request:
                mock_request.get_json.return_value = {
                    'api_key': 'valid_key',
                    'phone': '9876543210'
                }
                
                with patch('tap_lms.api.frappe.get_all', return_value=[]):
                    with patch('tap_lms.api.frappe.get_doc') as mock_get_doc:
                        mock_otp = Mock()
                        mock_otp.insert = Mock()
                        mock_get_doc.return_value = mock_otp
                        
                        with patch('tap_lms.api.requests.get') as mock_req_get:
                            mock_response = Mock()
                            mock_response.json.return_value = {'status': 'success', 'id': 'msg_123'}
                            mock_req_get.return_value = mock_response
                            
                            with patch('tap_lms.api.frappe.response') as mock_resp:
                                mock_resp.http_status_code = 200
                                result = api.send_otp_v0()
                                
                                self.assertEqual(result['status'], 'success')
    
    def test_send_otp_v0_existing_teacher(self):
        """Test send_otp_v0 with existing teacher"""
        with patch('tap_lms.api.authenticate_api_key', return_value='valid_key'):
            with patch('tap_lms.api.frappe.request') as mock_request:
                mock_request.get_json.return_value = {
                    'api_key': 'valid_key',
                    'phone': '9876543210'
                }
                
                with patch('tap_lms.api.frappe.get_all', return_value=[{'name': 'TEACHER_001'}]):
                    with patch('tap_lms.api.frappe.response') as mock_resp:
                        mock_resp.http_status_code = 409
                        result = api.send_otp_v0()
                        
                        self.assertEqual(result['status'], 'failure')
    
    def test_send_otp_v0_invalid_api_key(self):
        """Test send_otp_v0 with invalid API key"""
        with patch('tap_lms.api.authenticate_api_key', return_value=None):
            with patch('tap_lms.api.frappe.request') as mock_request:
                mock_request.get_json.return_value = {
                    'api_key': 'invalid',
                    'phone': '9876543210'
                }
                
                with patch('tap_lms.api.frappe.response') as mock_resp:
                    mock_resp.http_status_code = 401
                    result = api.send_otp_v0()
                    
                    self.assertEqual(result['status'], 'failure')
    
    def test_send_otp_v0_missing_phone(self):
        """Test send_otp_v0 without phone number"""
        with patch('tap_lms.api.authenticate_api_key', return_value='valid_key'):
            with patch('tap_lms.api.frappe.request') as mock_request:
                mock_request.get_json.return_value = {
                    'api_key': 'valid_key'
                }
                
                with patch('tap_lms.api.frappe.response') as mock_resp:
                    mock_resp.http_status_code = 400
                    result = api.send_otp_v0()
                    
                    self.assertEqual(result['status'], 'failure')
    
    def test_send_otp_v0_whatsapp_api_error(self):
        """Test send_otp_v0 when WhatsApp API fails"""
        with patch('tap_lms.api.authenticate_api_key', return_value='valid_key'):
            with patch('tap_lms.api.frappe.request') as mock_request:
                mock_request.get_json.return_value = {
                    'api_key': 'valid_key',
                    'phone': '9876543210'
                }
                
                with patch('tap_lms.api.frappe.get_all', return_value=[]):
                    with patch('tap_lms.api.frappe.get_doc') as mock_get_doc:
                        mock_otp = Mock()
                        mock_otp.insert = Mock()
                        mock_get_doc.return_value = mock_otp
                        
                        with patch('tap_lms.api.requests.get') as mock_req_get:
                            mock_response = Mock()
                            mock_response.json.return_value = {'status': 'failure', 'message': 'API Error'}
                            mock_req_get.return_value = mock_response
                            
                            with patch('tap_lms.api.frappe.response') as mock_resp:
                                mock_resp.http_status_code = 500
                                result = api.send_otp_v0()
                                
                                self.assertEqual(result['status'], 'failure')
    
    def test_send_otp_mock_variant(self):
        """Test send_otp_mock function"""
        with patch('tap_lms.api.authenticate_api_key', return_value='valid_key'):
            with patch('tap_lms.api.frappe.request') as mock_request:
                mock_request.get_json.return_value = {
                    'api_key': 'valid_key',
                    'phone': '9876543210'
                }
                
                with patch('tap_lms.api.frappe.get_all', return_value=[]):
                    with patch('tap_lms.api.frappe.get_doc') as mock_get_doc:
                        mock_otp = Mock()
                        mock_otp.insert = Mock()
                        mock_get_doc.return_value = mock_otp
                        
                        with patch('tap_lms.api.frappe.response') as mock_resp:
                            mock_resp.http_status_code = 200
                            result = api.send_otp_mock()
                            
                            self.assertEqual(result['status'], 'success')
                            self.assertIn('mock_otp', result)
    
    # =========================================================================
    # LINES 2112-2167: get_teacher_by_glific_id
    # =========================================================================
    
    def test_get_teacher_by_glific_id_success(self):
        """Test get_teacher_by_glific_id with valid data"""
        with patch('tap_lms.api.authenticate_api_key', return_value='valid_key'):
            with patch('tap_lms.api.frappe.request') as mock_request:
                mock_request.data = json.dumps({
                    'api_key': 'valid_key',
                    'glific_id': 'glific_123'
                })
                
                with patch('tap_lms.api.frappe.get_all') as mock_get_all:
                    mock_get_all.return_value = [{
                        'name': 'TEACHER_001',
                        'first_name': 'John',
                        'last_name': 'Doe',
                        'teacher_role': 'Teacher',
                        'school_id': 'SCHOOL_001',
                        'phone_number': '9876543210',
                        'email_id': 'test@test.com',
                        'department': 'Math',
                        'language': 'LANG_001',
                        'gender': 'Male',
                        'course_level': 'COURSE_001'
                    }]
                    
                    with patch('tap_lms.api.frappe.db.get_value', return_value='Test School'):
                        with patch('tap_lms.api.frappe.db.sql', return_value=[]):
                            with patch('tap_lms.api.frappe.response') as mock_resp:
                                mock_resp.http_status_code = 200
                                result = api.get_teacher_by_glific_id()
                                
                                self.assertEqual(result['status'], 'success')
                                self.assertIn('data', result)
    
    def test_get_teacher_by_glific_id_not_found(self):
        """Test get_teacher_by_glific_id when teacher not found"""
        with patch('tap_lms.api.authenticate_api_key', return_value='valid_key'):
            with patch('tap_lms.api.frappe.request') as mock_request:
                mock_request.data = json.dumps({
                    'api_key': 'valid_key',
                    'glific_id': 'nonexistent'
                })
                
                with patch('tap_lms.api.frappe.get_all', return_value=[]):
                    with patch('tap_lms.api.frappe.response') as mock_resp:
                        mock_resp.http_status_code = 404
                        result = api.get_teacher_by_glific_id()
                        
                        self.assertEqual(result['status'], 'error')
    
    def test_get_teacher_by_glific_id_missing_params(self):
        """Test get_teacher_by_glific_id with missing parameters"""
        with patch('tap_lms.api.authenticate_api_key', return_value='valid_key'):
            with patch('tap_lms.api.frappe.request') as mock_request:
                mock_request.data = json.dumps({
                    'api_key': 'valid_key'
                })
                
                with patch('tap_lms.api.frappe.response') as mock_resp:
                    mock_resp.http_status_code = 400
                    result = api.get_teacher_by_glific_id()
                    
                    self.assertEqual(result['status'], 'error')
    
    # =========================================================================
    # LINES 2250-2271: get_school_city and search_schools_by_city
    # =========================================================================
    
    def test_get_school_city_success(self):
        """Test get_school_city with valid school"""
        with patch('tap_lms.api.authenticate_api_key', return_value='valid_key'):
            with patch('tap_lms.api.frappe.request') as mock_request:
                mock_request.data = json.dumps({
                    'api_key': 'valid_key',
                    'school_name': 'Test School'
                })
                
                with patch('tap_lms.api.frappe.get_all') as mock_get_all:
                    mock_get_all.return_value = [{
                        'name': 'SCHOOL_001',
                        'name1': 'Test School',
                        'city': 'CITY_001',
                        'state': 'STATE_001',
                        'country': 'COUNTRY_001',
                        'address': '123 Main St',
                        'pin': '123456'
                    }]
                    
                    with patch('tap_lms.api.frappe.get_doc') as mock_get_doc:
                        mock_city = Mock()
                        mock_city.city_name = 'Test City'
                        mock_city.district = 'DISTRICT_001'
                        mock_get_doc.return_value = mock_city
                        
                        with patch('tap_lms.api.frappe.db.get_value', return_value='Test State'):
                            with patch('tap_lms.api.frappe.response') as mock_resp:
                                mock_resp.http_status_code = 200
                                result = api.get_school_city()
                                
                                self.assertEqual(result['status'], 'success')
    
    def test_get_school_city_no_city_assigned(self):
        """Test get_school_city when school has no city"""
        with patch('tap_lms.api.authenticate_api_key', return_value='valid_key'):
            with patch('tap_lms.api.frappe.request') as mock_request:
                mock_request.data = json.dumps({
                    'api_key': 'valid_key',
                    'school_name': 'Test School'
                })
                
                with patch('tap_lms.api.frappe.get_all') as mock_get_all:
                    mock_get_all.return_value = [{
                        'name': 'SCHOOL_001',
                        'name1': 'Test School',
                        'city': None,
                        'state': None,
                        'country': None,
                        'address': '123 Main St',
                        'pin': '123456'
                    }]
                    
                    with patch('tap_lms.api.frappe.response') as mock_resp:
                        mock_resp.http_status_code = 200
                        result = api.get_school_city()
                        
                        self.assertEqual(result['status'], 'success')
                        self.assertIsNone(result['city'])
    
    def test_search_schools_by_city_success(self):
        """Test search_schools_by_city with valid city"""
        with patch('tap_lms.api.authenticate_api_key', return_value='valid_key'):
            with patch('tap_lms.api.frappe.request') as mock_request:
                mock_request.data = json.dumps({
                    'api_key': 'valid_key',
                    'city_name': 'Test City'
                })
                
                with patch('tap_lms.api.frappe.get_all') as mock_get_all:
                    mock_get_all.side_effect = [
                        [{'name': 'CITY_001', 'city_name': 'Test City', 'district': 'DISTRICT_001'}],
                        [{'name': 'SCHOOL_001', 'name1': 'School 1'}]
                    ]
                    
                    with patch('tap_lms.api.frappe.get_doc') as mock_get_doc:
                        mock_district = Mock()
                        mock_district.district_name = 'Test District'
                        mock_district.state = 'STATE_001'
                        mock_get_doc.return_value = mock_district
                        
                        with patch('tap_lms.api.frappe.response') as mock_resp:
                            mock_resp.http_status_code = 200
                            result = api.search_schools_by_city()
                            
                            self.assertEqual(result['status'], 'success')
    
    # =========================================================================
    # ADDITIONAL UNCOVERED FUNCTIONS
    # =========================================================================
    
    def test_send_whatsapp_message_success(self):
        """Test send_whatsapp_message function"""
        with patch('tap_lms.api.frappe.get_single') as mock_get_single:
            mock_settings = Mock()
            mock_settings.api_key = 'test_key'
            mock_settings.source_number = '1234567890'
            mock_settings.app_name = 'TestApp'
            mock_settings.api_endpoint = 'https://api.test.com'
            mock_get_single.return_value = mock_settings
            
            with patch('tap_lms.api.requests.post') as mock_post:
                mock_response = Mock()
                mock_response.raise_for_status = Mock()
                mock_post.return_value = mock_response
                
                result = api.send_whatsapp_message('9876543210', 'Test message')
                
                self.assertTrue(result)
    
    def test_send_whatsapp_message_no_settings(self):
        """Test send_whatsapp_message when settings not found"""
        with patch('tap_lms.api.frappe.get_single', return_value=None):
            with patch('tap_lms.api.frappe.log_error'):
                result = api.send_whatsapp_message('9876543210', 'Test')
                
                self.assertFalse(result)
    
    def test_send_whatsapp_message_incomplete_settings(self):
        """Test send_whatsapp_message with incomplete settings"""
        with patch('tap_lms.api.frappe.get_single') as mock_get_single:
            mock_settings = Mock()
            mock_settings.api_key = None
            mock_settings.source_number = None
            mock_get_single.return_value = mock_settings
            
            with patch('tap_lms.api.frappe.log_error'):
                result = api.send_whatsapp_message('9876543210', 'Test')
                
                self.assertFalse(result)
    
    def test_send_whatsapp_message_request_exception(self):
        """Test send_whatsapp_message with request exception"""
        with patch('tap_lms.api.frappe.get_single') as mock_get_single:
            mock_settings = Mock()
            mock_settings.api_key = 'test'
            mock_settings.source_number = '1234567890'
            mock_settings.app_name = 'TestApp'
            mock_settings.api_endpoint = 'https://api.test.com'
            mock_get_single.return_value = mock_settings
            
            with patch('tap_lms.api.requests.post', side_effect=Exception("Network error")):
                with patch('tap_lms.api.frappe.log_error'):
                    result = api.send_whatsapp_message('9876543210', 'Test')
                    
                    self.assertFalse(result)
    
    def test_get_course_level_api_success(self):
        """Test get_course_level_api function"""
        with patch('tap_lms.api.authenticate_api_key', return_value='valid_key'):
            with patch('tap_lms.api.frappe.form_dict') as mock_form_dict:
                mock_form_dict.get.side_effect = lambda key: {
                    'api_key': 'valid_key',
                    'grade': '5',
                    'vertical': 'Math',
                    'batch_skeyword': 'test_batch'
                }.get(key)
                
                with patch('tap_lms.api.frappe.get_all') as mock_get_all:
                    mock_get_all.side_effect = [
                        [{'name': 'BO_001', 'kit_less': 1}],
                        [{'name': 'VERT_001'}]
                    ]
                    
                    with patch('tap_lms.api.get_course_level', return_value='COURSE_001'):
                        result = api.get_course_level_api()
                        
                        self.assertEqual(result['status'], 'success')
    
    def test_course_vertical_list_count_success(self):
        """Test course_vertical_list_count function"""
        with patch('tap_lms.api.authenticate_api_key', return_value='valid_key'):
            with patch('tap_lms.api.frappe.local.form_dict', {'api_key': 'valid_key', 'keyword': 'test'}):
                with patch('tap_lms.api.frappe.get_all') as mock_get_all:
                    mock_get_all.side_effect = [
                        [{'name': 'BO_001'}],
                        [{'course_vertical': 'VERT_001'}]
                    ]
                    
                    with patch('tap_lms.api.frappe.get_doc') as mock_get_doc:
                        mock_vertical = Mock()
                        mock_vertical.name2 = 'Math'
                        mock_get_doc.return_value = mock_vertical
                        
                        result = api.course_vertical_list_count()
                        
                        self.assertIsInstance(result, dict)
                        self.assertIn('count', result)
    
    def test_get_course_level_original_success(self):
        """Test get_course_level_original function"""
        with patch('tap_lms.api.frappe.db.sql') as mock_sql:
            mock_sql.return_value = [{'name': 'STAGE_001'}]
            
            with patch('tap_lms.api.frappe.get_all') as mock_get_all:
                mock_get_all.return_value = [{'name': 'COURSE_001'}]
                
                result = api.get_course_level_original('VERT_001', '5', 1)
                
                self.assertEqual(result, 'COURSE_001')
    
    def test_get_course_level_original_no_stage(self):
        """Test get_course_level_original when no stage found"""
        with patch('tap_lms.api.frappe.db.sql', return_value=[]):
            with patch('tap_lms.api.frappe.throw', side_effect=Exception("No stage")):
                with self.assertRaises(Exception):
                    api.get_course_level_original('VERT_001', '99', 1)
    
    def test_get_course_level_original_kitless_fallback(self):
        """Test get_course_level_original with kitless fallback"""
        with patch('tap_lms.api.frappe.db.sql') as mock_sql:
            mock_sql.return_value = [{'name': 'STAGE_001'}]
            
            with patch('tap_lms.api.frappe.get_all') as mock_get_all:
                mock_get_all.side_effect = [
                    [],  # No result with kit_less
                    [{'name': 'COURSE_FALLBACK'}]  # Result without kit_less
                ]
                
                result = api.get_course_level_original('VERT_001', '5', 1)
                
                self.assertEqual(result, 'COURSE_FALLBACK')
    
    def test_send_otp_gs_function(self):
        """Test send_otp_gs function"""
        with patch('tap_lms.api.authenticate_api_key', return_value='valid_key'):
            with patch('tap_lms.api.frappe.request') as mock_request:
                mock_request.get_json.return_value = {
                    'api_key': 'valid_key',
                    'phone': '9876543210'
                }
                
                with patch('tap_lms.api.frappe.get_all', return_value=[]):
                    with patch('tap_lms.api.frappe.get_doc') as mock_get_doc:
                        mock_otp = Mock()
                        mock_otp.insert = Mock()
                        mock_get_doc.return_value = mock_otp
                        
                        with patch('tap_lms.api.send_whatsapp_message', return_value=True):
                            with patch('tap_lms.api.frappe.response') as mock_resp:
                                mock_resp.http_status_code = 200
                                result = api.send_otp_gs()
                                
                                self.assertEqual(result['status'], 'success')


if __name__ == '__main__':
    unittest.main(verbosity=2)