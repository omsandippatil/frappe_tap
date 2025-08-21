

import frappe
import unittest
from unittest.mock import patch, MagicMock


class TestGlificUtils(unittest.TestCase):
    """Test cases for glific_utils.py to achieve 100% code coverage"""

    def setUp(self):
        """Set up test fixtures before each test method."""
        pass

    def tearDown(self):
        """Tear down test fixtures after each test method."""
        pass

    @patch('tap_lms.glific_utils.update_student_glific_ids')
    @patch('frappe.enqueue')
    @patch('frappe.db.count')
    def test_run_glific_id_update_with_students_found(self, mock_count, mock_enqueue, mock_update):
        """Test run_glific_id_update when students are found"""
        from tap_lms.glific_utils import run_glific_id_update
        
        # Mock frappe.db.count to return students found
        mock_count.return_value = 5
        
        # Mock enqueue function
        mock_job = MagicMock()
        mock_job.name = "test_job_123"
        mock_enqueue.return_value = mock_job
        
        result = run_glific_id_update()
        
        # Verify frappe.db.count was called with correct parameters
        mock_count.assert_called_once_with(
            "Student", 
            {"glific_id": ["in", ["", None]]}
        )
        
        # Verify enqueue was called with correct parameters
        from tap_lms.glific_utils import process_glific_id_update
        mock_enqueue.assert_called_once_with(
            process_glific_id_update,
            queue='long',
            timeout=3600,
            total_students=5
        )
        
        # Verify return value
        self.assertEqual(result, "Glific ID update process started. Job ID: test_job_123")

    @patch('frappe.db.count')
    def test_run_glific_id_update_no_students_found(self, mock_count):
        """Test run_glific_id_update when no students are found"""
        from tap_lms.glific_utils import run_glific_id_update
        
        # Mock frappe.db.count to return 0 students
        mock_count.return_value = 0
        
        result = run_glific_id_update()
        
        # Verify frappe.db.count was called
        mock_count.assert_called_once_with(
            "Student", 
            {"glific_id": ["in", ["", None]]}
        )
        
        # Verify return value when no students found
        self.assertEqual(result, "No students found without Glific ID.")

    @patch('frappe.publish_realtime')
    @patch('frappe.db.commit')
    @patch('tap_lms.glific_utils.update_student_glific_ids')
    def test_process_glific_id_update_single_batch(self, mock_update, mock_commit, mock_publish):
        """Test process_glific_id_update with single batch (less than 100 students)"""
        from tap_lms.glific_utils import process_glific_id_update
        
        total_students = 50
        
        # Mock update_student_glific_ids to return updated count
        mock_update.return_value = 50
        
        process_glific_id_update(total_students)
        
        # Verify frappe.db.commit was called once
        mock_commit.assert_called_once()
        
        # Verify publish_realtime calls
        expected_calls = [
            unittest.mock.call("glific_id_update_progress", {"processed": 50, "total": 50}),
            unittest.mock.call("glific_id_update_complete", {"total_updated": 50})
        ]
        mock_publish.assert_has_calls(expected_calls)

    @patch('frappe.publish_realtime')
    @patch('frappe.db.commit')
    @patch('tap_lms.glific_utils.update_student_glific_ids')
    def test_process_glific_id_update_multiple_batches(self, mock_update, mock_commit, mock_publish):
        """Test process_glific_id_update with multiple batches"""
        from tap_lms.glific_utils import process_glific_id_update
        
        total_students = 250  # More than one batch
        
        # Mock update_student_glific_ids to return different values for different calls
        mock_update.side_effect = [100, 100, 50]
        
        process_glific_id_update(total_students)
        
        # Verify frappe.db.commit was called 3 times (once per batch)
        self.assertEqual(mock_commit.call_count, 3)
        
        # Verify update_student_glific_ids was called 3 times
        self.assertEqual(mock_update.call_count, 3)
        
        # Verify publish_realtime was called for progress updates
        expected_calls = [
            unittest.mock.call("glific_id_update_progress", {"processed": 100, "total": 250}),
            unittest.mock.call("glific_id_update_progress", {"processed": 200, "total": 250}),
            unittest.mock.call("glific_id_update_progress", {"processed": 250, "total": 250}),
            unittest.mock.call("glific_id_update_complete", {"total_updated": 250})
        ]
        mock_publish.assert_has_calls(expected_calls)

    @patch('frappe.publish_realtime')
    @patch('frappe.db.commit')
    @patch('tap_lms.glific_utils.update_student_glific_ids')
    def test_process_glific_id_update_exact_batch_size(self, mock_update, mock_commit, mock_publish):
        """Test process_glific_id_update with exactly 100 students (one complete batch)"""
        from tap_lms.glific_utils import process_glific_id_update
        
        total_students = 100
        
        # Mock update_student_glific_ids to return updated count
        mock_update.return_value = 100
        
        process_glific_id_update(total_students)
        
        # Verify frappe.db.commit was called once
        mock_commit.assert_called_once()
        
        # Verify publish_realtime calls
        expected_calls = [
            unittest.mock.call("glific_id_update_progress", {"processed": 100, "total": 100}),
            unittest.mock.call("glific_id_update_complete", {"total_updated": 100})
        ]
        mock_publish.assert_has_calls(expected_calls)

    @patch('frappe.publish_realtime')
    @patch('frappe.db.commit')
    @patch('tap_lms.glific_utils.update_student_glific_ids')
    def test_process_glific_id_update_with_zero_students(self, mock_update, mock_commit, mock_publish):
        """Test process_glific_id_update with zero total students"""
        from tap_lms.glific_utils import process_glific_id_update
        
        total_students = 0
        
        process_glific_id_update(total_students)
        
        # Verify no database operations were performed
        mock_commit.assert_not_called()
        mock_update.assert_not_called()
        
        # Verify only completion call was made
        mock_publish.assert_called_once_with(
            "glific_id_update_complete", 
            {"total_updated": 0}
        )

    @patch('frappe.publish_realtime')
    @patch('frappe.db.commit')
    @patch('tap_lms.glific_utils.update_student_glific_ids')
    def test_process_glific_id_update_partial_update_in_batch(self, mock_update, mock_commit, mock_publish):
        """Test process_glific_id_update when update_student_glific_ids returns less than batch size"""
        from tap_lms.glific_utils import process_glific_id_update
        
        total_students = 300
        
        # Mock update_student_glific_ids to return partial updates
        mock_update.side_effect = [80, 90, 70]  # Total: 240 < 300
        
        process_glific_id_update(total_students)
        
        # Verify progress tracking with actual processed counts
        expected_calls = [
            unittest.mock.call("glific_id_update_progress", {"processed": 80, "total": 300}),
            unittest.mock.call("glific_id_update_progress", {"processed": 170, "total": 300}),
            unittest.mock.call("glific_id_update_progress", {"processed": 240, "total": 300}),
            unittest.mock.call("glific_id_update_complete", {"total_updated": 240})
        ]
        mock_publish.assert_has_calls(expected_calls)

    @patch('tap_lms.glific_utils.update_student_glific_ids')
    @patch('frappe.enqueue')
    @patch('frappe.db.count')
    def test_complete_workflow_integration(self, mock_count, mock_enqueue, mock_update):
        """Test the complete workflow from run_glific_id_update to process_glific_id_update"""
        from tap_lms.glific_utils import run_glific_id_update, process_glific_id_update
        
        # Setup
        mock_count.return_value = 150
        mock_job = MagicMock()
        mock_job.name = "integration_test_job"
        mock_enqueue.return_value = mock_job
        
        # Test run_glific_id_update
        result = run_glific_id_update()
        
        # Verify enqueue was called
        self.assertTrue(mock_enqueue.called)
        args, kwargs = mock_enqueue.call_args
        self.assertEqual(args[0], process_glific_id_update)
        self.assertEqual(kwargs['total_students'], 150)
        self.assertEqual(kwargs['queue'], 'long')
        self.assertEqual(kwargs['timeout'], 3600)
        
        # Verify result
        self.assertEqual(result, "Glific ID update process started. Job ID: integration_test_job")

    @patch('frappe.publish_realtime')
    @patch('frappe.db.commit')  
    @patch('tap_lms.glific_utils.update_student_glific_ids')
    def test_large_student_count(self, mock_update, mock_commit, mock_publish):
        """Test with very large student count"""
        from tap_lms.glific_utils import process_glific_id_update
        
        total_students = 1000  # 10 batches
        
        # Mock consistent returns
        mock_update.return_value = 100
        
        process_glific_id_update(total_students)
        
        # Verify correct number of commits (10 batches)
        self.assertEqual(mock_commit.call_count, 10)
        
        # Verify final completion call exists
        completion_calls = [call for call in mock_publish.call_args_list 
                          if call[0][0] == "glific_id_update_complete"]
        self.assertEqual(len(completion_calls), 1)
        self.assertEqual(completion_calls[0], unittest.mock.call("glific_id_update_complete", {"total_updated": 1000}))

    @patch('frappe.publish_realtime')
    @patch('frappe.db.commit')
    @patch('tap_lms.glific_utils.update_student_glific_ids')
    def test_batch_size_boundary(self, mock_update, mock_commit, mock_publish):
        """Test exactly at batch size boundaries"""
        from tap_lms.glific_utils import process_glific_id_update
        
        test_cases = [99, 100, 101, 199, 200, 201]
        
        for total_students in test_cases:
            # Reset mocks for each iteration
            mock_commit.reset_mock()
            mock_update.reset_mock()
            mock_publish.reset_mock()
            
            mock_update.return_value = min(100, total_students)
            
            process_glific_id_update(total_students)
            
            expected_batches = (total_students + 99) // 100  # Ceiling division
            self.assertEqual(mock_commit.call_count, expected_batches)