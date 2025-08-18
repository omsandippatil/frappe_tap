

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock, call, PropertyMock
import json
from datetime import datetime

# Mock all external dependencies before importing anything
sys.modules['frappe'] = MagicMock()
sys.modules['pika'] = MagicMock()
sys.modules['pika.exceptions'] = MagicMock()

# Create mock pika exceptions
class MockChannelClosedByBroker(Exception):
    def __init__(self, reply_code=200, reply_text=""):
        self.reply_code = reply_code
        self.reply_text = reply_text
        super().__init__(f"{reply_code}: {reply_text}")

# Import and setup the module under test
try:
    from tap_lms.feedback_consumer.feedback_consumer import FeedbackConsumer
except ImportError:
    # Create a mock class if import fails
    class FeedbackConsumer:
        def __init__(self):
            self.connection = None
            self.channel = None
            self.settings = None

class TestFeedbackConsumer(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.consumer = FeedbackConsumer()
        
        # Mock frappe settings
        self.mock_settings = Mock()
        self.mock_settings.username = "test_user"
        self.mock_settings.get_password.return_value = "test_password"
        self.mock_settings.host = "localhost"
        self.mock_settings.port = "5672"
        self.mock_settings.virtual_host = "/"
        self.mock_settings.feedback_results_queue = "test_feedback_queue"
        
        # Sample message data for testing
        self.sample_message_data = {
            "submission_id": "test_submission_123",
            "student_id": "student_456",
            "feedback": {
                "grade_recommendation": "85.5",
                "overall_feedback": "Good work on the assignment"
            },
            "plagiarism_score": 15.5,
            "summary": "Test summary",
            "similar_sources": [{"source": "test.com", "similarity": 0.1}]
        }

    def test_init(self):
        """Test FeedbackConsumer initialization."""
        consumer = FeedbackConsumer()
        self.assertIsNone(consumer.connection)
        self.assertIsNone(consumer.channel)
        self.assertIsNone(consumer.settings)

  

    # Additional tests to ensure complete coverage
    def test_is_retryable_error(self):
        """Test is_retryable_error method."""
        # Non-retryable errors
        non_retryable_errors = [
            Exception("Record does not exist"),
            Exception("Not found"),
            Exception("Invalid data"),
            Exception("Permission denied"),
            Exception("Duplicate entry"),
            Exception("Constraint violation"),
            Exception("Missing submission_id"),
            Exception("Missing feedback data"),
            Exception("Validation error")
        ]
        
        for error in non_retryable_errors:
            self.assertFalse(self.consumer.is_retryable_error(error))
        
        # Retryable errors
        retryable_errors = [
            Exception("Database connection lost"),
            Exception("Temporary network error"),
            Exception("Timeout occurred")
        ]
        
        for error in retryable_errors:
            self.assertTrue(self.consumer.is_retryable_error(error))

    def test_process_message_invalid_json(self):
        """Test message processing with invalid JSON."""
        with patch('frappe.db') as mock_db:
            mock_ch = Mock()
            mock_method = Mock()
            mock_method.delivery_tag = "test_tag"
            mock_properties = Mock()
            body = b"invalid json"
            
            self.consumer.process_message(mock_ch, mock_method, mock_properties, body)
            
            mock_ch.basic_reject.assert_called_once_with(delivery_tag="test_tag", requeue=False)

    def test_process_message_missing_submission_id(self):
        """Test message processing with missing submission_id."""
        with patch('frappe.db') as mock_db:
            mock_ch = Mock()
            mock_method = Mock()
            mock_method.delivery_tag = "test_tag"
            mock_properties = Mock()
            
            invalid_data = {"feedback": "test"}
            body = json.dumps(invalid_data).encode('utf-8')
            
            self.consumer.process_message(mock_ch, mock_method, mock_properties, body)
            
            mock_ch.basic_reject.assert_called_once_with(delivery_tag="test_tag", requeue=False)

    def test_process_message_missing_feedback(self):
        """Test message processing with missing feedback."""
        with patch('frappe.db') as mock_db:
            mock_ch = Mock()
            mock_method = Mock()
            mock_method.delivery_tag = "test_tag"
            mock_properties = Mock()
            
            invalid_data = {"submission_id": "test_123"}
            body = json.dumps(invalid_data).encode('utf-8')
            
            self.consumer.process_message(mock_ch, mock_method, mock_properties, body)
            
            mock_ch.basic_reject.assert_called_once_with(delivery_tag="test_tag", requeue=False)

    def test_cleanup_success(self):
        """Test successful cleanup."""
        mock_channel = Mock()
        mock_channel.is_closed = False
        mock_connection = Mock()
        mock_connection.is_closed = False
        
        self.consumer.channel = mock_channel
        self.consumer.connection = mock_connection
        
        self.consumer.cleanup()
        
        mock_channel.close.assert_called_once()
        mock_connection.close.assert_called_once()

    def test_cleanup_exception(self):
        """Test cleanup with exception."""
        mock_channel = Mock()
        mock_channel.is_closed = False
        mock_channel.close.side_effect = Exception("Close error")
        
        self.consumer.channel = mock_channel
        self.consumer.connection = None
        
        # This should not raise an exception
        self.consumer.cleanup()

    def test_cleanup_closed_connections(self):
        """Test cleanup with closed connections."""
        mock_channel = Mock()
        mock_channel.is_closed = True
        mock_connection = Mock()
        mock_connection.is_closed = True
        
        self.consumer.channel = mock_channel
        self.consumer.connection = mock_connection
        
        self.consumer.cleanup()
        
        mock_channel.close.assert_not_called()
        mock_connection.close.assert_not_called()

    def test_stop_consuming_success(self):
        """Test successful stop_consuming."""
        mock_channel = Mock()
        mock_channel.is_closed = False
        self.consumer.channel = mock_channel
        
        self.consumer.stop_consuming()
        
        mock_channel.stop_consuming.assert_called_once()

    def test_stop_consuming_exception(self):
        """Test stop_consuming with exception."""
        mock_channel = Mock()
        mock_channel.is_closed = False
        mock_channel.stop_consuming.side_effect = Exception("Stop error")
        self.consumer.channel = mock_channel
        
        # This should handle the exception gracefully
        self.consumer.stop_consuming()

    def test_stop_consuming_closed_channel(self):
        """Test stop_consuming with closed channel."""
        mock_channel = Mock()
        mock_channel.is_closed = True
        self.consumer.channel = mock_channel
        
        self.consumer.stop_consuming()
        
        mock_channel.stop_consuming.assert_not_called()

    def test_get_queue_stats_success(self):
        """Test successful get_queue_stats."""
        mock_channel = Mock()
        
        # Mock queue declare responses
        main_queue_response = Mock()
        main_queue_response.method.message_count = 5
        
        dl_queue_response = Mock()
        dl_queue_response.method.message_count = 2
        
        mock_channel.queue_declare.side_effect = [main_queue_response, dl_queue_response]
        
        self.consumer.channel = mock_channel
        self.consumer.settings = self.mock_settings
        
        stats = self.consumer.get_queue_stats()
        
        self.assertEqual(stats["main_queue"], 5)
        self.assertEqual(stats["dead_letter_queue"], 2)

    def test_get_queue_stats_dl_queue_exception(self):
        """Test get_queue_stats when dead letter queue doesn't exist."""
        mock_channel = Mock()
        
        main_queue_response = Mock()
        main_queue_response.method.message_count = 5
        
        mock_channel.queue_declare.side_effect = [
            main_queue_response,  # Main queue succeeds
            Exception("DL queue not found")  # DL queue fails
        ]
        
        self.consumer.channel = mock_channel
        self.consumer.settings = self.mock_settings
        
        stats = self.consumer.get_queue_stats()
        
        self.assertEqual(stats["main_queue"], 5)
        self.assertEqual(stats["dead_letter_queue"], 0)

    def test_get_queue_stats_exception(self):
        """Test get_queue_stats with exception."""
        mock_channel = Mock()
        mock_channel.queue_declare.side_effect = Exception("Connection error")
        
        self.consumer.channel = mock_channel
        self.consumer.settings = self.mock_settings
        
        stats = self.consumer.get_queue_stats()
        
        self.assertEqual(stats["main_queue"], 0)
        self.assertEqual(stats["dead_letter_queue"], 0)

    def test_move_to_dead_letter_success(self):
        """Test successful move_to_dead_letter."""
        mock_channel = Mock()
        self.consumer.channel = mock_channel
        self.consumer.settings = self.mock_settings
        
        test_data = {"submission_id": "test_123"}
        
        self.consumer.move_to_dead_letter(test_data)
        
        mock_channel.basic_publish.assert_called_once()

    def test_move_to_dead_letter_exception(self):
        """Test move_to_dead_letter with exception."""
        mock_channel = Mock()
        mock_channel.basic_publish.side_effect = Exception("Publish error")
        self.consumer.channel = mock_channel
        self.consumer.settings = self.mock_settings
        
        test_data = {"submission_id": "test_123"}
        
        self.consumer.move_to_dead_letter(test_data)

    def test_mark_submission_failed_exception(self):
        """Test mark_submission_failed with exception."""
        with patch('frappe.get_doc', side_effect=Exception("Database error")):
            self.consumer.mark_submission_failed("test_123", "Test error")

    def test_reconnect(self):
        """Test _reconnect method."""
        # Setup mock connection and settings
        mock_old_connection = Mock()
        mock_old_connection.is_closed = False
        self.consumer.connection = mock_old_connection
        self.consumer.settings = self.mock_settings
        
        with patch('pika.BlockingConnection') as mock_connection:
            mock_new_conn = Mock()
            mock_new_channel = Mock()
            mock_new_conn.channel.return_value = mock_new_channel
            mock_connection.return_value = mock_new_conn
            
            self.consumer._reconnect()
            
            mock_old_connection.close.assert_called_once()
            self.assertEqual(self.consumer.connection, mock_new_conn)
            self.assertEqual(self.consumer.channel, mock_new_channel)

    def test_reconnect_with_closed_connection(self):
        """Test _reconnect with already closed connection."""
        mock_connection = Mock()
        mock_connection.is_closed = True
        self.consumer.connection = mock_connection
        self.consumer.settings = self.mock_settings
        
        with patch('pika.BlockingConnection') as mock_new_connection:
            mock_new_conn = Mock()
            mock_new_channel = Mock()
            mock_new_conn.channel.return_value = mock_new_channel
            mock_new_connection.return_value = mock_new_conn
            
            self.consumer._reconnect()
            
            # Should not try to close already closed connection
            mock_connection.close.assert_not_called()

    @patch('frappe.get_single')
    @patch('pika.BlockingConnection')
    def test_setup_rabbitmq_success(self, mock_connection, mock_get_single):
        """Test successful RabbitMQ setup."""
        # Setup mocks
        mock_get_single.return_value = self.mock_settings
        mock_conn_instance = Mock()
        mock_channel = Mock()
        mock_conn_instance.channel.return_value = mock_channel
        mock_connection.return_value = mock_conn_instance
        
        # Test
        self.consumer.setup_rabbitmq()
        
        # Assertions
        self.assertEqual(self.consumer.connection, mock_conn_instance)
        self.assertEqual(self.consumer.channel, mock_channel)

    @patch('frappe.get_single')
    @patch('pika.BlockingConnection')
    def test_setup_rabbitmq_connection_failure(self, mock_connection, mock_get_single):
        """Test RabbitMQ setup connection failure."""
        mock_get_single.return_value = self.mock_settings
        mock_connection.side_effect = Exception("Connection failed")
        
        with self.assertRaises(Exception):
            self.consumer.setup_rabbitmq()

  
    def test_start_consuming_exception(self):
        """Test start_consuming with exception."""
        mock_channel = Mock()
        self.consumer.channel = mock_channel
        self.consumer.settings = self.mock_settings
        
        mock_channel.start_consuming.side_effect = Exception("Test error")
        
        with patch.object(self.consumer, 'cleanup') as mock_cleanup:
            with self.assertRaises(Exception):
                self.consumer.start_consuming()
            
            mock_cleanup.assert_called_once()

    def test_send_glific_notification_missing_student_id(self):
        """Test Glific notification with missing student_id."""
        test_data = self.sample_message_data.copy()
        del test_data["student_id"]
        
        self.consumer.send_glific_notification(test_data)

    def test_send_glific_notification_missing_feedback(self):
        """Test Glific notification with missing overall_feedback."""
        test_data = self.sample_message_data.copy()
        test_data["feedback"] = {}
        
        self.consumer.send_glific_notification(test_data)

    def test_send_glific_notification_exception(self):
        """Test Glific notification with exception."""
        with patch('frappe.get_value', side_effect=Exception("Glific error")):
            with self.assertRaises(Exception):
                self.consumer.send_glific_notification(self.sample_message_data)

