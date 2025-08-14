import pytest
import sys
from unittest.mock import Mock, patch, MagicMock

def setup_frappe_mocks():
    """Setup comprehensive frappe mocks"""
    mock_frappe = Mock()
    mock_frappe.db = Mock()
    mock_frappe.logger = Mock()
    mock_frappe.logger.return_value = Mock()
    
    # Mock enqueue
    mock_enqueue = Mock()
    
    sys.modules['frappe'] = mock_frappe
    sys.modules['frappe.utils'] = Mock()
    sys.modules['frappe.utils.background_jobs'] = Mock()
    sys.modules['frappe.utils.background_jobs'].enqueue = mock_enqueue
    
    return mock_frappe, mock_enqueue

def setup_glific_mocks():
    """Setup glific integration mocks"""
    mock_glific = Mock()
    mock_glific.optin_contact = Mock()
    mock_glific.start_contact_flow = Mock()
    mock_glific.create_or_get_teacher_group_for_batch = Mock()
    mock_glific.add_contact_to_group = Mock()
    
    sys.modules['tap_lms.background_jobs.glific_integration'] = mock_glific
    
    return mock_glific

class TestProcessGlificActions:
    
    def setup_method(self):
        """Setup before each test"""
        self.mock_frappe, self.mock_enqueue = setup_frappe_mocks()
        self.mock_glific = setup_glific_mocks()
        
        # Clear any existing modules
        if 'tap_lms.background_jobs' in sys.modules:
            del sys.modules['tap_lms.background_jobs']

    def test_process_glific_actions_optin_failure(self):
        """Test process_glific_actions when optin fails"""
        with patch('tap_lms.background_jobs.optin_contact', return_value=False):
            from tap_lms.background_jobs import process_glific_actions
            
            process_glific_actions(
                "teacher_1", "1234567890", "John", "school_1", 
                "Test School", "en", "model_1", "Batch A", "batch_1"
            )
            
            # Verify error was logged for optin failure
            self.mock_frappe.logger().error.assert_called()

    def test_process_glific_actions_no_glific_id(self):
        """Test process_glific_actions when glific_id not found"""
        with patch('tap_lms.background_jobs.optin_contact', return_value=True):
            self.mock_frappe.db.get_value.return_value = None
            
            from tap_lms.background_jobs import process_glific_actions
            
            process_glific_actions(
                "teacher_1", "1234567890", "John", "school_1", 
                "Test School", "en", "model_1", "Batch A", "batch_1"
            )
            
            # Verify error was logged for missing glific_id
            self.mock_frappe.logger().error.assert_called()

    def test_process_glific_actions_no_valid_batch(self):
        """Test process_glific_actions with no valid batch_id"""
        with patch('tap_lms.background_jobs.optin_contact', return_value=True):
            self.mock_frappe.db.get_value.side_effect = ["glific_123", "flow_456"]
            
            from tap_lms.background_jobs import process_glific_actions
            
            # Test with no_active_batch_id
            process_glific_actions(
                "teacher_1", "1234567890", "John", "school_1", 
                "Test School", "en", "model_1", "Batch A", "no_active_batch_id"
            )
            
            # Verify info was logged for skipping group assignment
            self.mock_frappe.logger().info.assert_called()

    def test_process_glific_actions_add_contact_failure(self):
        """Test add contact to group failure - covers line 38"""
        with patch('tap_lms.background_jobs.optin_contact', return_value=True), \
             patch('tap_lms.background_jobs.create_or_get_teacher_group_for_batch', 
                   return_value={"group_id": "group_789", "label": "Test Group"}), \
             patch('tap_lms.background_jobs.add_contact_to_group', return_value=False), \
             patch('tap_lms.background_jobs.start_contact_flow', return_value=True):
            
            self.mock_frappe.db.get_value.side_effect = ["glific_123", "flow_456"]
            
            from tap_lms.background_jobs import process_glific_actions
            
            process_glific_actions(
                "teacher_1", "1234567890", "John", "school_1", 
                "Test School", "en", "model_1", "Batch A", "batch_1"
            )
            
            # Verify warning was logged for failed group addition
            warning_calls = self.mock_frappe.logger().warning.call_args_list
            assert len(warning_calls) > 0, "Expected warning to be logged for failed group addition"

    def test_process_glific_actions_flow_start_failure(self):
        """Test flow start failure - covers line 62"""
        with patch('tap_lms.background_jobs.optin_contact', return_value=True), \
             patch('tap_lms.background_jobs.create_or_get_teacher_group_for_batch', 
                   return_value={"group_id": "group_789", "label": "Test Group"}), \
             patch('tap_lms.background_jobs.add_contact_to_group', return_value=True), \
             patch('tap_lms.background_jobs.start_contact_flow', return_value=False):
            
            self.mock_frappe.db.get_value.side_effect = ["glific_123", "flow_456"]
            
            from tap_lms.background_jobs import process_glific_actions
            
            process_glific_actions(
                "teacher_1", "1234567890", "John", "school_1", 
                "Test School", "en", "model_1", "Batch A", "batch_1"
            )
            
            # Verify error was logged for flow start failure
            error_calls = self.mock_frappe.logger().error.call_args_list
            flow_error_found = any("Failed to start onboarding flow" in str(call) for call in error_calls)
            assert flow_error_found, "Expected flow start failure error to be logged"

    def test_process_glific_actions_success_flow(self):
        """Test successful process_glific_actions execution"""
        with patch('tap_lms.background_jobs.optin_contact', return_value=True), \
             patch('tap_lms.background_jobs.create_or_get_teacher_group_for_batch', 
                   return_value={"group_id": "group_789", "label": "Test Group"}), \
             patch('tap_lms.background_jobs.add_contact_to_group', return_value=True), \
             patch('tap_lms.background_jobs.start_contact_flow', return_value=True):
            
            self.mock_frappe.db.get_value.side_effect = ["glific_123", "flow_456"]
            
            from tap_lms.background_jobs import process_glific_actions
            
            process_glific_actions(
                "teacher_1", "1234567890", "John", "school_1", 
                "Test School", "en", "model_1", "Batch A", "batch_1"
            )
            
            # Verify info was logged for successful operations
            self.mock_frappe.logger().info.assert_called()

    def test_process_glific_actions_no_flow_found(self):
        """Test process_glific_actions when flow not found"""
        with patch('tap_lms.background_jobs.optin_contact', return_value=True):
            self.mock_frappe.db.get_value.side_effect = ["glific_123", None]  # No flow found
            
            from tap_lms.background_jobs import process_glific_actions
            
            process_glific_actions(
                "teacher_1", "1234567890", "John", "school_1", 
                "Test School", "en", "model_1", "Batch A", "batch_1"
            )
            
            # Verify error was logged for missing flow
            error_calls = self.mock_frappe.logger().error.call_args_list
            flow_error_found = any("Glific flow not found" in str(call) for call in error_calls)
            assert flow_error_found, "Expected flow not found error to be logged"

    def test_process_glific_actions_exception_handling(self):
        """Test process_glific_actions exception handling"""
        with patch('tap_lms.background_jobs.optin_contact', side_effect=Exception("Test exception")):
            from tap_lms.background_jobs import process_glific_actions
            
            process_glific_actions(
                "teacher_1", "1234567890", "John", "school_1", 
                "Test School", "en", "model_1", "Batch A", "batch_1"
            )
            
            # Verify exception was logged
            error_calls = self.mock_frappe.logger().error.call_args_list
            exception_error_found = any("Error in process_glific_actions" in str(call) for call in error_calls)
            assert exception_error_found, "Expected exception error to be logged"

class TestEnqueueGlificActions:
    
    def setup_method(self):
        """Setup before each test"""
        self.mock_frappe, self.mock_enqueue = setup_frappe_mocks()

    def test_enqueue_glific_actions_basic(self):
        """Test basic enqueue_glific_actions function"""
        from tap_lms.background_jobs import enqueue_glific_actions
        
        enqueue_glific_actions(
            "teacher_1", "1234567890", "John", "school_1",
            "Test School", "en", "model_1", "Batch A", "batch_1"
        )
        
        # Verify enqueue was called
        self.mock_enqueue.assert_called_once()
        
        # Check that correct parameters were passed
        call_args = self.mock_enqueue.call_args
        kwargs = call_args[1]
        
        assert kwargs['queue'] == "short"
        assert kwargs['timeout'] == 300
        assert kwargs['teacher_id'] == "teacher_1"
        assert kwargs['phone'] == "1234567890"

class TestImportStatements:
    
    def test_import_coverage(self):
        """Test all import statements are covered"""
        # Setup mocks
        setup_frappe_mocks()
        setup_glific_mocks()
        
        # Import the module to cover import statements
        import tap_lms.background_jobs
        
        # Verify module was imported successfully
        assert tap_lms.background_jobs is not None
        assert hasattr(tap_lms.background_jobs, 'process_glific_actions')
        assert hasattr(tap_lms.background_jobs, 'enqueue_glific_actions')