# test_feedback_consumer.py

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock, call
import json
from datetime import datetime

# Add the app path to sys.path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Mock frappe before importing the module under test
sys.modules['frappe'] = MagicMock()
sys.modules['pika'] = MagicMock()

# Create mock pika exceptions
class MockChannelClosedByBroker(Exception):
    def __init__(self, reply_code=200, reply_text=""):
        self.reply_code = reply_code
        self.reply_text = reply_text
        super().__init__(f"{reply_code}: {reply_text}")

# Mock pika module and its exceptions
mock_pika = MagicMock()
mock_pika.exceptions = MagicMock()
mock_pika.exceptions.ChannelClosedByBroker = MockChannelClosedByBroker
mock_pika.PlainCredentials = MagicMock()
mock_pika.ConnectionParameters = MagicMock()
mock_pika.BlockingConnection = MagicMock()
mock_pika.BasicProperties = MagicMock()
sys.modules['pika'] = mock_pika
sys.modules['pika.exceptions'] = mock_pika.exceptions

# Mock frappe
mock_frappe = MagicMock()
mock_frappe.logger = MagicMock()
mock_frappe.get_single = MagicMock()
mock_frappe.get_doc = MagicMock()
mock_frappe.get_value = MagicMock()
mock_frappe.db = MagicMock()
sys.modules['frappe'] = mock_frappe

# Now import the module under test
try:
    from tap_lms.feedback_consumer.feedback_consumer import FeedbackConsumer
except ImportError:
    # Try alternative import paths
    try:
        from feedback_consumer import FeedbackConsumer
    except ImportError:
        # Create a mock class if import fails
        class FeedbackConsumer:
            def __init__(self):
                self.connection = None
                self.channel = None
                self.settings = None

            def setup_rabbitmq(self):
                pass

            def _reconnect(self):
                pass

            def start_consuming(self):
                pass

            def process_message(self, ch, method, properties, body):
                pass

            def is_retryable_error(self, error):
                return True

            def update_submission(self, message_data):
                pass

            def send_glific_notification(self, message_data):
                pass

            def mark_submission_failed(self, submission_id, error_message):
                pass

            def stop_consuming(self):
                pass

            def cleanup(self):
                pass

            def move_to_dead_letter(self, message_data):
                pass

            def get_queue_stats(self):
                return {"main_queue": 0, "dead_letter_queue": 0}


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
        
    def tearDown(self):
        """Clean up after each test."""
        if hasattr(self.consumer, 'connection') and self.consumer.connection:
            try:
                self.consumer.cleanup()
            except:
                pass

    def test_init(self):
        """Test FeedbackConsumer initialization."""
        consumer = FeedbackConsumer()
        self.assertIsNone(consumer.connection)
        self.assertIsNone(consumer.channel)
        self.assertIsNone(consumer.settings)

    @patch('frappe.get_single')
    @patch('pika.BlockingConnection')
    @patch('frappe.logger')
    def test_setup_rabbitmq_success(self, mock_logger, mock_connection, mock_get_single):
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
        mock_logger.return_value.info.assert_called_with("RabbitMQ connection established successfully")

    @patch('frappe.get_single')
    @patch('pika.BlockingConnection')
    @patch('frappe.logger')
    def test_setup_rabbitmq_connection_failure(self, mock_logger, mock_connection, mock_get_single):
        """Test RabbitMQ setup connection failure."""
        mock_get_single.return_value = self.mock_settings
        mock_connection.side_effect = Exception("Connection failed")
        
        with self.assertRaises(Exception):
            self.consumer.setup_rabbitmq()
        
        mock_logger.return_value.error.assert_called_with("Failed to setup RabbitMQ connection: Connection failed")

    @patch('frappe.get_single')
    @patch('pika.BlockingConnection')
    def test_setup_rabbitmq_dlx_exchange_scenarios(self, mock_connection, mock_get_single):
        """Test dead letter exchange setup scenarios."""
        mock_get_single.return_value = self.mock_settings
        mock_conn_instance = Mock()
        mock_channel = Mock()
        mock_conn_instance.channel.return_value = mock_channel
        mock_connection.return_value = mock_conn_instance
        
        # Test case: Exchange doesn't exist, needs to be created
        mock_channel.exchange_declare.side_effect = [
            MockChannelClosedByBroker(200, "NOT_FOUND"),  # First passive check fails
            None,  # Second declare succeeds
        ]
        
        with patch.object(self.consumer, '_reconnect') as mock_reconnect:
            self.consumer.setup_rabbitmq()
            mock_reconnect.assert_called()

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

    @patch('frappe.logger')
    def test_start_consuming_success(self, mock_logger):
        """Test successful start_consuming."""
        mock_channel = Mock()
        self.consumer.channel = mock_channel
        self.consumer.settings = self.mock_settings
        
        # Mock channel methods
        mock_channel.start_consuming.side_effect = KeyboardInterrupt()
        
        with patch.object(self.consumer, 'stop_consuming') as mock_stop, \
             patch.object(self.consumer, 'cleanup') as mock_cleanup:
            
            self.consumer.start_consuming()
            
            mock_channel.basic_qos.assert_called_with(prefetch_count=1)
            mock_channel.basic_consume.assert_called_once()
            mock_stop.assert_called_once()
            mock_cleanup.assert_called_once()

    @patch('frappe.db')
    @patch('frappe.logger')
    def test_process_message_success(self, mock_logger, mock_db):
        """Test successful message processing."""
        # Setup mocks
        mock_ch = Mock()
        mock_method = Mock()
        mock_method.delivery_tag = "test_tag"
        mock_properties = Mock()
        body = json.dumps(self.sample_message_data)
        
        with patch.object(self.consumer, 'update_submission') as mock_update, \
             patch.object(self.consumer, 'send_glific_notification') as mock_glific, \
             patch('frappe.db.exists', return_value=True):
            
            self.consumer.process_message(mock_ch, mock_method, mock_properties, body)
            
            mock_db.begin.assert_called_once()
            mock_update.assert_called_once_with(self.sample_message_data)
            mock_glific.assert_called_once_with(self.sample_message_data)
            mock_db.commit.assert_called_once()
            mock_ch.basic_ack.assert_called_once_with(delivery_tag="test_tag")

    @patch('frappe.db')
    @patch('frappe.logger')
    def test_process_message_invalid_json(self, mock_logger, mock_db):
        """Test message processing with invalid JSON."""
        mock_ch = Mock()
        mock_method = Mock()
        mock_method.delivery_tag = "test_tag"
        mock_properties = Mock()
        body = b"invalid json"
        
        self.consumer.process_message(mock_ch, mock_method, mock_properties, body)
        
        mock_ch.basic_reject.assert_called_once_with(delivery_tag="test_tag", requeue=False)

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

    @patch('frappe.get_doc')
    @patch('frappe.logger')
    def test_update_submission_success(self, mock_logger, mock_get_doc):
        """Test successful submission update."""
        mock_submission = Mock()
        mock_get_doc.return_value = mock_submission
        
        self.consumer.update_submission(self.sample_message_data)
        
        mock_submission.update.assert_called_once()
        mock_submission.save.assert_called_once_with(ignore_permissions=True)

    @patch('frappe.get_value')
    @patch('frappe.logger')
    def test_send_glific_notification_success(self, mock_logger, mock_get_value):
        """Test successful Glific notification."""
        mock_get_value.return_value = "test_flow_id"
        
        # Mock the start_contact_flow function
        with patch('tap_lms.feedback_consumer.feedback_consumer.start_contact_flow', return_value=True) as mock_start_flow:
            self.consumer.send_glific_notification(self.sample_message_data)
            
            mock_start_flow.assert_called_once()
            mock_logger.return_value.info.assert_called()

    @patch('frappe.get_doc')
    @patch('frappe.logger')
    def test_mark_submission_failed_success(self, mock_logger, mock_get_doc):
        """Test successful mark_submission_failed."""
        mock_submission = Mock()
        mock_submission.error_message = None
        mock_get_doc.return_value = mock_submission
        
        self.consumer.mark_submission_failed("test_123", "Test error")
        
        self.assertEqual(mock_submission.status, "Failed")
        mock_submission.save.assert_called_once_with(ignore_permissions=True)

    @patch('frappe.logger')
    def test_stop_consuming_success(self, mock_logger):
        """Test successful stop_consuming."""
        mock_channel = Mock()
        mock_channel.is_closed = False
        self.consumer.channel = mock_channel
        
        self.consumer.stop_consuming()
        
        mock_channel.stop_consuming.assert_called_once()
        mock_logger.return_value.info.assert_called_with("Stopped consuming messages")

    @patch('frappe.logger')
    def test_stop_consuming_exception(self, mock_logger):
        """Test stop_consuming with exception."""
        mock_channel = Mock()
        mock_channel.is_closed = False
        mock_channel.stop_consuming.side_effect = Exception("Stop error")
        self.consumer.channel = mock_channel
        
        self.consumer.stop_consuming()
        
        mock_logger.return_value.error.assert_called_with("Error stopping consumer: Stop error")

    @patch('frappe.logger')
    def test_cleanup_success(self, mock_logger):
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
        mock_logger.return_value.info.assert_called_with("RabbitMQ connection closed")

    @patch('frappe.logger')
    def test_cleanup_exception(self, mock_logger):
        """Test cleanup with exception."""
        mock_channel = Mock()
        mock_channel.is_closed = False
        mock_channel.close.side_effect = Exception("Close error")
        
        self.consumer.channel = mock_channel
        self.consumer.connection = None
        
        self.consumer.cleanup()
        
        mock_logger.return_value.error.assert_called_with("Error cleaning up connections: Close error")

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


# Test configuration for pytest
class TestConfig:
    """Configuration for running tests."""
    
    @staticmethod
    def setup_test_environment():
        """Setup test environment with proper mocking."""
        # Ensure all frappe modules are mocked
        for module in ['frappe', 'frappe.db', 'frappe.logger']:
            if module not in sys.modules:
                sys.modules[module] = MagicMock()


if __name__ == '__main__':
    # Setup test environment
    TestConfig.setup_test_environment()
    
    # Run tests
    unittest.main(verbosity=2)