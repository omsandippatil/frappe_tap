# test_feedback_consumer.py

import pytest
import json
import frappe
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime
import pika

# Import the class under test
from tap_lms.feedback_consumer.feedback_consumer import FeedbackConsumer


class TestFeedbackConsumer:
    """Test cases for FeedbackConsumer class"""

    @pytest.fixture
    def consumer(self):
        """Create a FeedbackConsumer instance for testing"""
        return FeedbackConsumer()

    @pytest.fixture
    def mock_settings(self):
        """Mock RabbitMQ settings"""
        settings = Mock()
        settings.username = "test_user"
        settings.get_password.return_value = "test_password"
        settings.host = "localhost"
        settings.port = "5672"
        settings.virtual_host = "/"
        settings.feedback_results_queue = "test_feedback_queue"
        return settings

    @pytest.fixture
    def sample_message_data(self):
        """Sample message data for testing"""
        return {
            "submission_id": "SUB-001",
            "student_id": "STU-001",
            "feedback": {
                "grade_recommendation": "85.5",
                "overall_feedback": "Good work with minor improvements needed"
            },
            "plagiarism_score": 15.2,
            "summary": "Assignment completed successfully",
            "similar_sources": [
                {"source": "example.com", "similarity": 10.5}
            ]
        }

    @pytest.fixture
    def mock_submission(self):
        """Mock ImgSubmission document"""
        submission = Mock()
        submission.update = Mock()
        submission.save = Mock()
        return submission


class TestRabbitMQSetup:
    """Test RabbitMQ connection and setup"""

    @patch('tap_lms.feedback_consumer.feedback_consumer.frappe.get_single')
    @patch('tap_lms.feedback_consumer.feedback_consumer.pika.BlockingConnection')
    def test_setup_rabbitmq_success(self, mock_connection, mock_get_single, consumer, mock_settings):
        """Test successful RabbitMQ setup"""
        # Setup mocks
        mock_get_single.return_value = mock_settings
        mock_conn_instance = Mock()
        mock_channel = Mock()
        mock_conn_instance.channel.return_value = mock_channel
        mock_connection.return_value = mock_conn_instance

        # Execute
        consumer.setup_rabbitmq()

        # Assertions
        assert consumer.connection == mock_conn_instance
        assert consumer.channel == mock_channel
        mock_channel.exchange_declare.assert_called()
        mock_channel.queue_declare.assert_called()

    @patch('tap_lms.feedback_consumer.feedback_consumer.frappe.get_single')
    @patch('tap_lms.feedback_consumer.feedback_consumer.pika.BlockingConnection')
    def test_setup_rabbitmq_connection_failure(self, mock_connection, mock_get_single, consumer, mock_settings):
        """Test RabbitMQ setup with connection failure"""
        # Setup mocks
        mock_get_single.return_value = mock_settings
        mock_connection.side_effect = Exception("Connection failed")

        # Execute and assert
        with pytest.raises(Exception) as exc_info:
            consumer.setup_rabbitmq()
        
        assert "Connection failed" in str(exc_info.value)

    @patch('tap_lms.feedback_consumer.feedback_consumer.frappe.get_single')
    @patch('tap_lms.feedback_consumer.feedback_consumer.pika.BlockingConnection')
    def test_setup_rabbitmq_with_dead_letter_exchange_creation(self, mock_connection, mock_get_single, consumer, mock_settings):
        """Test RabbitMQ setup when dead letter exchange needs to be created"""
        # Setup mocks
        mock_get_single.return_value = mock_settings
        mock_conn_instance = Mock()
        mock_channel = Mock()
        mock_conn_instance.channel.return_value = mock_channel
        mock_connection.return_value = mock_conn_instance
        
        # Simulate exchange doesn't exist on first call, succeeds on second
        mock_channel.exchange_declare.side_effect = [
            pika.exceptions.ChannelClosedByBroker(200, "NOT_FOUND"),
            None  # Success on retry
        ]

        # Execute
        consumer.setup_rabbitmq()

        # Assertions
        assert mock_channel.exchange_declare.call_count >= 2

    def test_reconnect(self, consumer, mock_settings):
        """Test RabbitMQ reconnection functionality"""
        consumer.settings = mock_settings
        
        with patch('tap_lms.feedback_consumer.feedback_consumer.pika.BlockingConnection') as mock_connection:
            mock_conn_instance = Mock()
            mock_channel = Mock()
            mock_conn_instance.channel.return_value = mock_channel
            mock_connection.return_value = mock_conn_instance

            # Execute
            consumer._reconnect()

            # Assertions
            assert consumer.connection == mock_conn_instance
            assert consumer.channel == mock_channel


class TestMessageProcessing:
    """Test message processing functionality"""

    @patch('tap_lms.feedback_consumer.feedback_consumer.frappe.db')
    @patch('tap_lms.feedback_consumer.feedback_consumer.frappe.db.exists')
    def test_process_message_success(self, mock_exists, mock_db, consumer, sample_message_data):
        """Test successful message processing"""
        # Setup mocks
        mock_exists.return_value = True
        mock_method = Mock()
        mock_method.delivery_tag = "test_tag"
        mock_ch = Mock()
        
        with patch.object(consumer, 'update_submission') as mock_update, \
             patch.object(consumer, 'send_glific_notification') as mock_glific:
            
            # Execute
            body = json.dumps(sample_message_data).encode()
            consumer.process_message(mock_ch, mock_method, None, body)

            # Assertions
            mock_update.assert_called_once_with(sample_message_data)
            mock_glific.assert_called_once_with(sample_message_data)
            mock_ch.basic_ack.assert_called_once_with(delivery_tag="test_tag")
            mock_db.commit.assert_called_once()

    @patch('tap_lms.feedback_consumer.feedback_consumer.frappe.db')
    def test_process_message_invalid_json(self, mock_db, consumer):
        """Test processing message with invalid JSON"""
        mock_method = Mock()
        mock_method.delivery_tag = "test_tag"
        mock_ch = Mock()
        
        # Execute with invalid JSON
        body = b"invalid json"
        consumer.process_message(mock_ch, mock_method, None, body)

        # Assertions
        mock_ch.basic_reject.assert_called_once_with(delivery_tag="test_tag", requeue=False)

    @patch('tap_lms.feedback_consumer.feedback_consumer.frappe.db')
    def test_process_message_missing_submission_id(self, mock_db, consumer):
        """Test processing message without submission_id"""
        mock_method = Mock()
        mock_method.delivery_tag = "test_tag"
        mock_ch = Mock()
        
        # Execute with message missing submission_id
        message_data = {"feedback": {"grade_recommendation": "85"}}
        body = json.dumps(message_data).encode()
        consumer.process_message(mock_ch, mock_method, None, body)

        # Assertions
        mock_ch.basic_reject.assert_called_once_with(delivery_tag="test_tag", requeue=False)

    @patch('tap_lms.feedback_consumer.feedback_consumer.frappe.db')
    @patch('tap_lms.feedback_consumer.feedback_consumer.frappe.db.exists')
    def test_process_message_submission_not_found(self, mock_exists, mock_db, consumer, sample_message_data):
        """Test processing message when submission doesn't exist"""
        # Setup mocks
        mock_exists.return_value = False
        mock_method = Mock()
        mock_method.delivery_tag = "test_tag"
        mock_ch = Mock()
        
        # Execute
        body = json.dumps(sample_message_data).encode()
        consumer.process_message(mock_ch, mock_method, None, body)

        # Assertions
        mock_ch.basic_reject.assert_called_once_with(delivery_tag="test_tag", requeue=False)

    @patch('tap_lms.feedback_consumer.feedback_consumer.frappe.db')
    @patch('tap_lms.feedback_consumer.feedback_consumer.frappe.db.exists')
    def test_process_message_retryable_error(self, mock_exists, mock_db, consumer, sample_message_data):
        """Test processing message with retryable error"""
        # Setup mocks
        mock_exists.return_value = True
        mock_method = Mock()
        mock_method.delivery_tag = "test_tag"
        mock_ch = Mock()
        
        with patch.object(consumer, 'update_submission') as mock_update, \
             patch.object(consumer, 'is_retryable_error') as mock_retryable:
            
            mock_update.side_effect = Exception("Database lock error")
            mock_retryable.return_value = True
            
            # Execute
            body = json.dumps(sample_message_data).encode()
            consumer.process_message(mock_ch, mock_method, None, body)

            # Assertions
            mock_ch.basic_nack.assert_called_once_with(delivery_tag="test_tag", requeue=True)
            mock_db.rollback.assert_called_once()

    @patch('tap_lms.feedback_consumer.feedback_consumer.frappe.db')
    @patch('tap_lms.feedback_consumer.feedback_consumer.frappe.db.exists')
    def test_process_message_non_retryable_error(self, mock_exists, mock_db, consumer, sample_message_data):
        """Test processing message with non-retryable error"""
        # Setup mocks
        mock_exists.return_value = True
        mock_method = Mock()
        mock_method.delivery_tag = "test_tag"
        mock_ch = Mock()
        
        with patch.object(consumer, 'update_submission') as mock_update, \
             patch.object(consumer, 'is_retryable_error') as mock_retryable, \
             patch.object(consumer, 'mark_submission_failed') as mock_mark_failed:
            
            mock_update.side_effect = Exception("Validation error")
            mock_retryable.return_value = False
            
            # Execute
            body = json.dumps(sample_message_data).encode()
            consumer.process_message(mock_ch, mock_method, None, body)

            # Assertions
            mock_ch.basic_reject.assert_called_once_with(delivery_tag="test_tag", requeue=False)
            mock_mark_failed.assert_called_once()
            mock_db.rollback.assert_called()

    @patch('tap_lms.feedback_consumer.feedback_consumer.frappe.db')
    @patch('tap_lms.feedback_consumer.feedback_consumer.frappe.db.exists')
    def test_process_message_glific_notification_failure(self, mock_exists, mock_db, consumer, sample_message_data):
        """Test processing message when Glific notification fails (should not fail entire message)"""
        # Setup mocks
        mock_exists.return_value = True
        mock_method = Mock()
        mock_method.delivery_tag = "test_tag"
        mock_ch = Mock()
        
        with patch.object(consumer, 'update_submission') as mock_update, \
             patch.object(consumer, 'send_glific_notification') as mock_glific:
            
            mock_glific.side_effect = Exception("Glific API error")
            
            # Execute
            body = json.dumps(sample_message_data).encode()
            consumer.process_message(mock_ch, mock_method, None, body)

            # Assertions - message should still be acknowledged despite Glific failure
            mock_update.assert_called_once()
            mock_ch.basic_ack.assert_called_once_with(delivery_tag="test_tag")
            mock_db.commit.assert_called_once()


class TestErrorHandling:
    """Test error handling and retry logic"""

    def test_is_retryable_error_non_retryable(self, consumer):
        """Test identification of non-retryable errors"""
        non_retryable_errors = [
            Exception("Record does not exist"),
            Exception("Entity not found"),
            Exception("Invalid data format"),
            Exception("Permission denied"),
            Exception("Duplicate entry"),
            Exception("Missing submission_id"),
            Exception("Validation error occurred")
        ]
        
        for error in non_retryable_errors:
            assert not consumer.is_retryable_error(error)

    def test_is_retryable_error_retryable(self, consumer):
        """Test identification of retryable errors"""
        retryable_errors = [
            Exception("Database lock timeout"),
            Exception("Connection timeout"),
            Exception("Network error"),
            Exception("Temporary service unavailable"),
            Exception("Unknown database error")
        ]
        
        for error in retryable_errors:
            assert consumer.is_retryable_error(error)


class TestSubmissionUpdate:
    """Test submission update functionality"""

    @patch('tap_lms.feedback_consumer.feedback_consumer.frappe.get_doc')
    def test_update_submission_success(self, mock_get_doc, consumer, sample_message_data, mock_submission):
        """Test successful submission update"""
        # Setup mocks
        mock_get_doc.return_value = mock_submission
        
        # Execute
        consumer.update_submission(sample_message_data)

        # Assertions
        mock_get_doc.assert_called_once_with("ImgSubmission", "SUB-001")
        mock_submission.update.assert_called_once()
        mock_submission.save.assert_called_once_with(ignore_permissions=True)
        
        # Check update data
        update_call = mock_submission.update.call_args[0][0]
        assert update_call["status"] == "Completed"
        assert update_call["grade"] == 85.5
        assert update_call["plagiarism_result"] == 15.2

    @patch('tap_lms.feedback_consumer.feedback_consumer.frappe.get_doc')
    def test_update_submission_invalid_grade(self, mock_get_doc, consumer, mock_submission):
        """Test submission update with invalid grade data"""
        # Setup test data with invalid grade
        message_data = {
            "submission_id": "SUB-001",
            "feedback": {
                "grade_recommendation": "invalid_grade",
                "overall_feedback": "Test feedback"
            },
            "plagiarism_score": 10
        }
        
        mock_get_doc.return_value = mock_submission
        
        # Execute
        consumer.update_submission(message_data)

        # Assertions - should use 0.0 as default grade
        update_call = mock_submission.update.call_args[0][0]
        assert update_call["grade"] == 0.0

    @patch('tap_lms.feedback_consumer.feedback_consumer.frappe.get_doc')
    def test_update_submission_missing_fields(self, mock_get_doc, consumer, mock_submission):
        """Test submission update with missing optional fields"""
        # Setup minimal message data
        message_data = {
            "submission_id": "SUB-001",
            "feedback": {}
        }
        
        mock_get_doc.return_value = mock_submission
        
        # Execute
        consumer.update_submission(message_data)

        # Assertions - should handle missing fields gracefully
        update_call = mock_submission.update.call_args[0][0]
        assert update_call["status"] == "Completed"
        assert update_call["grade"] == 0.0
        assert update_call["overall_feedback"] == ""


class TestGlificIntegration:
    """Test Glific notification functionality"""

    @patch('tap_lms.feedback_consumer.feedback_consumer.frappe.get_value')
    @patch('tap_lms.feedback_consumer.feedback_consumer.start_contact_flow')
    def test_send_glific_notification_success(self, mock_start_flow, mock_get_value, consumer, sample_message_data):
        """Test successful Glific notification"""
        # Setup mocks
        mock_get_value.return_value = "FLOW-123"
        mock_start_flow.return_value = True
        
        # Execute
        consumer.send_glific_notification(sample_message_data)

        # Assertions
        mock_start_flow.assert_called_once_with(
            flow_id="FLOW-123",
            contact_id="STU-001",
            default_results={
                "submission_id": "SUB-001",
                "feedback": "Good work with minor improvements needed"
            }
        )

    @patch('tap_lms.feedback_consumer.feedback_consumer.frappe.get_value')
    def test_send_glific_notification_no_student_id(self, mock_get_value, consumer):
        """Test Glific notification with missing student_id"""
        message_data = {
            "submission_id": "SUB-001",
            "feedback": {"overall_feedback": "Test feedback"}
        }
        
        # Execute - should not raise exception
        consumer.send_glific_notification(message_data)
        
        # Should complete without error (just log warning)

    @patch('tap_lms.feedback_consumer.feedback_consumer.frappe.get_value')
    def test_send_glific_notification_no_flow_configured(self, mock_get_value, consumer, sample_message_data):
        """Test Glific notification when flow is not configured"""
        # Setup mocks
        mock_get_value.return_value = None
        
        # Execute - should not raise exception
        consumer.send_glific_notification(sample_message_data)
        
        # Should complete without error (just log warning)


class TestUtilityMethods:
    """Test utility and helper methods"""

    @patch('tap_lms.feedback_consumer.feedback_consumer.frappe.get_doc')
    def test_mark_submission_failed(self, mock_get_doc, consumer, mock_submission):
        """Test marking submission as failed"""
        # Setup mocks
        mock_submission.error_message = None  # Simulate field exists
        mock_get_doc.return_value = mock_submission
        
        # Execute
        consumer.mark_submission_failed("SUB-001", "Test error message")

        # Assertions
        assert mock_submission.status == "Failed"
        mock_submission.save.assert_called_once_with(ignore_permissions=True)

    def test_stop_consuming(self, consumer):
        """Test stopping message consumption"""
        # Setup mock channel
        mock_channel = Mock()
        consumer.channel = mock_channel
        
        # Execute
        consumer.stop_consuming()

        # Assertions
        mock_channel.stop_consuming.assert_called_once()

    def test_cleanup(self, consumer):
        """Test cleanup of connections"""
        # Setup mock connections
        mock_channel = Mock()
        mock_connection = Mock()
        consumer.channel = mock_channel
        consumer.connection = mock_connection
        
        # Execute
        consumer.cleanup()

        # Assertions
        mock_channel.close.assert_called_once()
        mock_connection.close.assert_called_once()

    @patch.object(FeedbackConsumer, 'setup_rabbitmq')
    def test_get_queue_stats_success(self, mock_setup, consumer):
        """Test getting queue statistics"""
        # Setup mock channel
        mock_channel = Mock()
        consumer.channel = mock_channel
        consumer.settings = Mock()
        consumer.settings.feedback_results_queue = "test_queue"
        
        # Mock queue declare responses
        main_queue_response = Mock()
        main_queue_response.method.message_count = 5
        dl_queue_response = Mock()
        dl_queue_response.method.message_count = 2
        
        mock_channel.queue_declare.side_effect = [main_queue_response, dl_queue_response]
        
        # Execute
        stats = consumer.get_queue_stats()

        # Assertions
        assert stats["main_queue"] == 5
        assert stats["dead_letter_queue"] == 2

    def test_move_to_dead_letter(self, consumer, sample_message_data):
        """Test moving message to dead letter queue"""
        # Setup mock channel and settings
        mock_channel = Mock()
        consumer.channel = mock_channel
        consumer.settings = Mock()
        consumer.settings.feedback_results_queue = "test_queue"
        
        # Execute
        consumer.move_to_dead_letter(sample_message_data)

        # Assertions
        mock_channel.basic_publish.assert_called_once()
        call_args = mock_channel.basic_publish.call_args
        assert call_args[1]["routing_key"] == "test_queue_dead_letter"


class TestConsumerLifecycle:
    """Test consumer lifecycle and integration"""

    @patch.object(FeedbackConsumer, 'setup_rabbitmq')
    @patch.object(FeedbackConsumer, 'cleanup')
    def test_start_consuming_keyboard_interrupt(self, mock_cleanup, mock_setup, consumer):
        """Test handling keyboard interrupt during consumption"""
        # Setup mock channel
        mock_channel = Mock()
        mock_channel.start_consuming.side_effect = KeyboardInterrupt()
        consumer.channel = mock_channel
        consumer.settings = Mock()
        consumer.settings.feedback_results_queue = "test_queue"
        
        with patch.object(consumer, 'stop_consuming') as mock_stop:
            # Execute
            consumer.start_consuming()

            # Assertions
            mock_stop.assert_called_once()
            mock_cleanup.assert_called_once()

    @patch.object(FeedbackConsumer, 'setup_rabbitmq')
    @patch.object(FeedbackConsumer, 'cleanup')
    def test_start_consuming_exception(self, mock_cleanup, mock_setup, consumer):
        """Test handling exceptions during consumption"""
        # Setup mock channel
        mock_channel = Mock()
        mock_channel.start_consuming.side_effect = Exception("Consumer error")
        consumer.channel = mock_channel
        consumer.settings = Mock()
        consumer.settings.feedback_results_queue = "test_queue"
        
        # Execute and assert
        with pytest.raises(Exception) as exc_info:
            consumer.start_consuming()
        
        assert "Consumer error" in str(exc_info.value)
        mock_cleanup.assert_called_once()


# Integration test fixtures and helpers
@pytest.fixture
def frappe_test_context():
    """Setup Frappe test context"""
    with patch('tap_lms.feedback_consumer.feedback_consumer.frappe') as mock_frappe:
        mock_frappe.db.begin = Mock()
        mock_frappe.db.commit = Mock()
        mock_frappe.db.rollback = Mock()
        mock_frappe.logger.return_value = Mock()
        yield mock_frappe


# Example of how to run specific test categories
if __name__ == "__main__":
    # Run all tests
    pytest.main([__file__, "-v"])
    
    # Run specific test categories
    # pytest.main([__file__ + "::TestMessageProcessing", "-v"])
    # pytest.main([__file__ + "::TestRabbitMQSetup", "-v"])