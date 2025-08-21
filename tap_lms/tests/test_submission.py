

# import json
# import unittest
# from unittest.mock import Mock, patch, MagicMock
# import sys
# from types import ModuleType

# # Create mock frappe module
# frappe = ModuleType('frappe')
# frappe.exceptions = ModuleType('frappe.exceptions')

# class DoesNotExistError(Exception):
#     pass

# frappe.exceptions.DoesNotExistError = DoesNotExistError
# frappe.DoesNotExistError = DoesNotExistError

# # Mock frappe functions
# frappe.db = Mock()
# frappe.new_doc = Mock()
# frappe.get_doc = Mock()
# frappe.set_user = Mock()
# frappe.throw = Mock()
# frappe.log_error = Mock()

# # Add frappe to sys.modules so imports work
# sys.modules['frappe'] = frappe
# sys.modules['frappe.exceptions'] = frappe.exceptions

# # Mock pika module
# pika = ModuleType('pika')
# pika.PlainCredentials = Mock()
# pika.ConnectionParameters = Mock()
# pika.BlockingConnection = Mock()
# sys.modules['pika'] = pika

# # Define the functions to test directly in this file
# def submit_artwork(api_key, assign_id, student_id, img_url):
#     """Submit artwork for evaluation"""
#     # Validate API key
#     api_key_doc = frappe.db.get_value("API Key", {"key": api_key}, ["user"])
#     if not api_key_doc:
#         frappe.throw("Invalid API key")
    
#     # Set user context
#     frappe.set_user(api_key_doc["user"])
    
#     # Create submission
#     submission = frappe.new_doc("ImgSubmission")
#     submission.assign_id = assign_id
#     submission.student_id = student_id
#     submission.img_url = img_url
#     submission.status = "Pending"
#     submission.insert()
    
#     # Commit to database
#     frappe.db.commit()
    
#     # Enqueue for processing
#     enqueue_submission(submission.name)
    
#     return {
#         "message": "Submission received",
#         "submission_id": submission.name
#     }

# def enqueue_submission(submission_id):
#     """Enqueue submission for processing via RabbitMQ"""
#     import pika
    
#     # Get submission details
#     submission = frappe.get_doc("ImgSubmission", submission_id)
    
#     # RabbitMQ connection setup
#     credentials = pika.PlainCredentials("user", "password")
#     parameters = pika.ConnectionParameters(
#         host="localhost",
#         port=5672,
#         virtual_host="/",
#         credentials=credentials
#     )
    
#     connection = pika.BlockingConnection(parameters)
#     channel = connection.channel()
    
#     # Declare queue
#     channel.queue_declare(queue="img_processing", durable=True)
    
#     # Prepare message
#     message = {
#         "submission_id": submission.name,
#         "assign_id": submission.assign_id,
#         "student_id": submission.student_id,
#         "img_url": submission.img_url
#     }
    
#     # Publish message
#     channel.basic_publish(
#         exchange="",
#         routing_key="img_processing",
#         body=json.dumps(message)
#     )
    
#     connection.close()

# def img_feedback(api_key, submission_id):
#     """Get feedback for image submission"""
#     # Validate API key
#     api_key_doc = frappe.db.get_value("API Key", {"key": api_key}, ["user"])
#     if not api_key_doc:
#         frappe.throw("Invalid API key")
    
#     # Set user context
#     frappe.set_user(api_key_doc["user"])
    
#     try:
#         # Get submission
#         submission = frappe.get_doc("ImgSubmission", submission_id)
        
#         result = {"status": submission.status}
        
#         if submission.status == "Completed":
#             result["overall_feedback"] = submission.overall_feedback
        
#         return result
        
#     except frappe.DoesNotExistError:
#         return {"error": "Submission not found"}
#     except Exception as e:
#         frappe.log_error(f"Error getting feedback: {str(e)}")
#         return {"error": "An error occurred while checking submission status"}

# def get_assignment_context(assign_id, student_id=None):
#     """Get assignment context for processing"""
#     try:
#         # Get assignment details
#         assignment = frappe.get_doc("Assignment", assign_id)
        
#         context = {
#             "assignment": {
#                 "name": assignment.assignment_name,
#                 "description": assignment.description,
#                 "type": assignment.assignment_type,
#                 "subject": assignment.subject,
#                 "guidelines": assignment.submission_guidelines,
#                 "reference_image": assignment.reference_image,
#                 "max_score": assignment.max_score,
#                 "auto_feedback": assignment.enable_auto_feedback
#             }
#         }
        
#         # Get learning objectives
#         learning_objectives = []
#         for obj in assignment.learning_objectives:
#             obj_details = frappe.db.get_value(
#                 "Learning Objective", 
#                 obj.learning_objective, 
#                 "description"
#             )
#             learning_objectives.append({
#                 "objective": obj.learning_objective,
#                 "description": obj_details
#             })
        
#         context["learning_objectives"] = learning_objectives
        
#         # Get student details if provided
#         if student_id:
#             student = frappe.get_doc("Student", student_id)
#             context["student"] = {
#                 "grade": student.grade,
#                 "level": student.level,
#                 "language": student.language
#             }
        
#         # Add feedback prompt if auto feedback is enabled
#         if assignment.enable_auto_feedback and hasattr(assignment, 'feedback_prompt'):
#             context["feedback_prompt"] = assignment.feedback_prompt
        
#         return context
        
#     except Exception as e:
#         frappe.log_error(f"Error getting assignment context: {str(e)}")
#         return None


# class TestSubmission(unittest.TestCase):
    
#     def setUp(self):
#         """Set up test fixtures before each test method."""
#         # Reset all mocks
#         frappe.db.reset_mock()
#         frappe.new_doc.reset_mock()
#         frappe.get_doc.reset_mock()
#         frappe.set_user.reset_mock()
#         frappe.throw.reset_mock()
#         frappe.log_error.reset_mock()
    
#     # def test_submit_artwork_valid(self):
#     #     """Test submit_artwork with valid inputs - covers the happy path"""
#     #     # Setup mocks
#     #     frappe.db.get_value.return_value = {"user": "test_user"}
#     #     mock_submission = Mock()
#     #     mock_submission.name = "SUB-001"
#     #     frappe.new_doc.return_value = mock_submission
        
#     #     with patch('__main__.enqueue_submission') as mock_enqueue:
#     #         # Test the function
#     #         result = submit_artwork("valid_key", "ASSIGN-001", "STU-001", "http://example.com/image.jpg")
            
#     #         # Assertions
#     #         frappe.db.get_value.assert_called_with("API Key", {"key": "valid_key"}, ["user"])
#     #         frappe.set_user.assert_called_with("test_user")
#     #         frappe.new_doc.assert_called_with("ImgSubmission")
#     #         self.assertEqual(mock_submission.assign_id, "ASSIGN-001")
#     #         self.assertEqual(mock_submission.student_id, "STU-001")
#     #         self.assertEqual(mock_submission.img_url, "http://example.com/image.jpg")
#     #         self.assertEqual(mock_submission.status, "Pending")
#     #         mock_submission.insert.assert_called_once()
#     #         frappe.db.commit.assert_called_once()
#     #         mock_enqueue.assert_called_with("SUB-001")
#     #         self.assertEqual(result["message"], "Submission received")
#     #         self.assertEqual(result["submission_id"], "SUB-001")

#     def test_submit_artwork_invalid_api_key(self):
#         """Test submit_artwork with invalid API key - covers lines 43-44"""
#         # Setup mocks
#         frappe.db.get_value.return_value = None
#         frappe.throw.side_effect = Exception("Invalid API key")
        
#         # Test the function
#         with self.assertRaises(Exception) as context:
#             submit_artwork("invalid_key", "ASSIGN-001", "STU-001", "http://example.com/image.jpg")
        
#         self.assertEqual(str(context.exception), "Invalid API key")

#     @patch('pika.BlockingConnection')
#     @patch('pika.ConnectionParameters')
#     @patch('pika.PlainCredentials')
#     def test_enqueue_submission(self, mock_credentials, mock_params, mock_connection):
#         """Test enqueue_submission function - covers lines 70-105"""
#         # Setup mocks
#         mock_submission = Mock()
#         mock_submission.name = "SUB-001"
#         mock_submission.assign_id = "ASSIGN-001"
#         mock_submission.student_id = "STU-001"
#         mock_submission.img_url = "http://example.com/image.jpg"
        
#         frappe.get_doc.return_value = mock_submission
        
#         # Mock RabbitMQ components
#         mock_channel = Mock()
#         mock_conn_instance = Mock()
#         mock_conn_instance.channel.return_value = mock_channel
#         mock_connection.return_value = mock_conn_instance
        
#         # Test the function
#         enqueue_submission("SUB-001")
        
#         # Assertions
#         frappe.get_doc.assert_called_with("ImgSubmission", "SUB-001")
#         mock_credentials.assert_called_once()
#         mock_params.assert_called_once()
#         mock_connection.assert_called_once()
#         mock_channel.queue_declare.assert_called_once()
#         mock_channel.basic_publish.assert_called_once()
#         mock_conn_instance.close.assert_called_once()

#     def test_img_feedback_invalid_api_key(self):
#         """Test img_feedback with invalid API key - covers lines 111-112"""
#         # Setup mocks
#         frappe.db.get_value.return_value = None
#         frappe.throw.side_effect = Exception("Invalid API key")
        
#         # Test the function
#         with self.assertRaises(Exception) as context:
#             img_feedback("invalid_key", "SUB-001")
        
#         self.assertEqual(str(context.exception), "Invalid API key")

#     # def test_img_feedback_valid_pending(self):
#     #     """Test img_feedback with valid submission in pending status"""
#     #     # Setup mocks
#     #     frappe.db.get_value.return_value = {"user": "test_user"}
#     #     mock_submission = Mock()
#     #     mock_submission.status = "Pending"
#     #     frappe.get_doc.return_value = mock_submission
        
#     #     # Test the function
#     #     result = img_feedback("valid_key", "SUB-001")
        
#     #     # Assertions
#     #     frappe.db.get_value.assert_called_with("API Key", {"key": "valid_key"}, ["user"])
#     #     frappe.set_user.assert_called_with("test_user")
#     #     frappe.get_doc.assert_called_with("ImgSubmission", "SUB-001")
#     #     self.assertEqual(result["status"], "Pending")
#     #     self.assertNotIn("overall_feedback", result)

#     def test_img_feedback_submission_not_found(self):
#         """Test img_feedback with non-existent submission - covers lines 128-129"""
#         # Setup mocks
#         frappe.db.get_value.return_value = {"user": "test_user"}
#         frappe.get_doc.side_effect = DoesNotExistError("Submission not found")
        
#         # Test the function
#         result = img_feedback("valid_key", "NONEXISTENT")
        
#         # Assertions
#         self.assertEqual(result["error"], "Submission not found")

#     def test_img_feedback_general_exception(self):
#         """Test img_feedback with general exception - covers lines 130-132"""
#         # Setup mocks
#         frappe.db.get_value.return_value = {"user": "test_user"}
#         frappe.get_doc.side_effect = Exception("Database error")
        
#         # Test the function
#         result = img_feedback("valid_key", "SUB-001")
        
#         # Assertions
#         self.assertEqual(result["error"], "An error occurred while checking submission status")
#         frappe.log_error.assert_called_once()

#     def test_get_assignment_context_basic(self):
#         """Test get_assignment_context without student - covers lines 136-166"""
#         # Setup mocks
#         mock_assignment = Mock()
#         mock_assignment.assignment_name = "Math Test"
#         mock_assignment.description = "Basic math assignment"
#         mock_assignment.assignment_type = "Quiz"
#         mock_assignment.subject = "Mathematics"
#         mock_assignment.submission_guidelines = "Submit your answers"
#         mock_assignment.reference_image = "ref.jpg"
#         mock_assignment.max_score = 100
#         mock_assignment.enable_auto_feedback = False
        
#         mock_objective = Mock()
#         mock_objective.learning_objective = "LO-001"
#         mock_assignment.learning_objectives = [mock_objective]
        
#         frappe.get_doc.return_value = mock_assignment
#         frappe.db.get_value.return_value = "Understand basic math"
        
#         # Test the function
#         result = get_assignment_context("ASSIGN-001")
        
#         # Assertions
#         self.assertEqual(result["assignment"]["name"], "Math Test")
#         self.assertEqual(result["assignment"]["description"], "Basic math assignment")
#         self.assertEqual(len(result["learning_objectives"]), 1)
#         self.assertNotIn("student", result)

#     def test_get_assignment_context_with_student(self):
#         """Test get_assignment_context with student - covers lines 168-175"""
#         # Setup mocks
#         mock_assignment = Mock()
#         mock_assignment.assignment_name = "Math Test"
#         mock_assignment.description = "Basic math assignment"
#         mock_assignment.assignment_type = "Quiz"
#         mock_assignment.subject = "Mathematics"
#         mock_assignment.submission_guidelines = "Submit your answers"
#         mock_assignment.reference_image = "ref.jpg"
#         mock_assignment.max_score = 100
#         mock_assignment.enable_auto_feedback = False
#         mock_assignment.learning_objectives = []
        
#         mock_student = Mock()
#         mock_student.grade = "10"
#         mock_student.level = "Intermediate"
#         mock_student.language = "English"
        
#         def mock_get_doc(doctype, doc_id):
#             if doctype == "Assignment":
#                 return mock_assignment
#             elif doctype == "Student":
#                 return mock_student
        
#         frappe.get_doc.side_effect = mock_get_doc
        
#         # Test the function
#         result = get_assignment_context("ASSIGN-001", "STU-001")
        
#         # Assertions
#         self.assertEqual(result["assignment"]["name"], "Math Test")
#         self.assertEqual(result["student"]["grade"], "10")
#         self.assertEqual(result["student"]["level"], "Intermediate")
#         self.assertEqual(result["student"]["language"], "English")

#     def test_get_assignment_context_exception(self):
#         """Test get_assignment_context with exception - covers lines 183-185"""
#         # Setup mocks
#         frappe.get_doc.side_effect = Exception("Database error")
        
#         # Test the function
#         result = get_assignment_context("INVALID-ASSIGN")
        
#         # Assertions
#         self.assertIsNone(result)
#         frappe.log_error.assert_called_once()

import unittest
from unittest.mock import Mock, patch, MagicMock
import json
import frappe
from frappe.exceptions import ValidationError
import pika


class TestSubmitArtwork(unittest.TestCase):
    """Test cases for submit_artwork function"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.valid_api_key = "test_api_key_123"
        self.assign_id = "ASSIGN-001"
        self.student_id = "STU-001"
        self.img_url = "https://example.com/image.jpg"
        
    @patch('frappe.db.get_value')
    @patch('frappe.set_user')
    @patch('frappe.new_doc')
    @patch('frappe.db.commit')
    @patch('submission.enqueue_submission')
    def test_submit_artwork_success(self, mock_enqueue, mock_commit, mock_new_doc, mock_set_user, mock_get_value):
        """Test successful artwork submission"""
        # Mock API key validation
        mock_get_value.return_value = {"user": "test_user"}
        
        # Mock submission document
        mock_submission = Mock()
        mock_submission.name = "SUB-001"
        mock_submission.assign_id = self.assign_id
        mock_submission.student_id = self.student_id
        mock_submission.img_url = self.img_url
        mock_new_doc.return_value = mock_submission
        
        # Import and test the function
        from submission import submit_artwork
        
        result = submit_artwork(self.valid_api_key, self.assign_id, self.student_id, self.img_url)
        
        # Assertions
        mock_get_value.assert_called_once_with("API Key", {"key": self.valid_api_key, "enabled": 1}, ["user"], as_dict=True)
        mock_set_user.assert_any_call("test_user")
        mock_set_user.assert_any_call("Administrator")
        mock_new_doc.assert_called_once_with("ImgSubmission")
        mock_submission.insert.assert_called_once()
        mock_commit.assert_called_once()
        mock_enqueue.assert_called_once_with("SUB-001")
        
        self.assertEqual(result["message"], "Submission received")
        self.assertEqual(result["submission_id"], "SUB-001")
        self.assertEqual(mock_submission.status, "Pending")

    @patch('frappe.db.get_value')
    @patch('frappe.throw')
    def test_submit_artwork_invalid_api_key(self, mock_throw, mock_get_value):
        """Test submission with invalid API key"""
        mock_get_value.return_value = None
        
        from submission import submit_artwork
        
        submit_artwork("invalid_key", self.assign_id, self.student_id, self.img_url)
        
        mock_throw.assert_called_once_with("Invalid API key")

    @patch('frappe.db.get_value')
    @patch('frappe.set_user')
    @patch('frappe.new_doc')
    @patch('submission.enqueue_submission')
    def test_submit_artwork_database_error(self, mock_enqueue, mock_new_doc, mock_set_user, mock_get_value):
        """Test submission with database error"""
        mock_get_value.return_value = {"user": "test_user"}
        mock_submission = Mock()
        mock_submission.insert.side_effect = Exception("Database error")
        mock_new_doc.return_value = mock_submission
        
        from submission import submit_artwork
        
        with self.assertRaises(Exception):
            submit_artwork(self.valid_api_key, self.assign_id, self.student_id, self.img_url)
        
        # Ensure user is switched back to Administrator even on error
        mock_set_user.assert_any_call("Administrator")

    @patch('frappe.db.get_value')
    @patch('frappe.set_user')
    @patch('frappe.new_doc')
    @patch('frappe.db.commit')
    @patch('submission.enqueue_submission')
    def test_submit_artwork_with_empty_values(self, mock_enqueue, mock_commit, mock_new_doc, mock_set_user, mock_get_value):
        """Test submission with empty/null values"""
        mock_get_value.return_value = {"user": "test_user"}
        mock_submission = Mock()
        mock_submission.name = "SUB-002"
        mock_new_doc.return_value = mock_submission
        
        from submission import submit_artwork
        
        # Test with empty strings
        result = submit_artwork(self.valid_api_key, "", "", "")
        
        self.assertEqual(mock_submission.assign_id, "")
        self.assertEqual(mock_submission.student_id, "")
        self.assertEqual(mock_submission.img_url, "")


class TestEnqueueSubmission(unittest.TestCase):
    """Test cases for enqueue_submission function"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.submission_id = "SUB-001"
        
    @patch('frappe.get_doc')
    @patch('pika.BlockingConnection')
    @patch('pika.PlainCredentials')
    @patch('pika.ConnectionParameters')
    def test_enqueue_submission_success(self, mock_params, mock_creds, mock_connection, mock_get_doc):
        """Test successful submission enqueueing"""
        # Mock submission document
        mock_submission = Mock()
        mock_submission.name = "SUB-001"
        mock_submission.assign_id = "ASSIGN-001"
        mock_submission.student_id = "STU-001"
        mock_submission.img_url = "https://example.com/image.jpg"
        mock_get_doc.return_value = mock_submission
        
        # Mock RabbitMQ connection
        mock_channel = Mock()
        mock_conn_instance = Mock()
        mock_conn_instance.channel.return_value = mock_channel
        mock_connection.return_value = mock_conn_instance
        
        from submission import enqueue_submission
        
        enqueue_submission(self.submission_id)
        
        # Verify RabbitMQ setup
        mock_creds.assert_called_once_with('fzdqidte', '0SMrDogBVcWUcu9brWwp2QhET_kArl59')
        mock_params.assert_called_once()
        mock_connection.assert_called_once()
        mock_channel.queue_declare.assert_called_once_with(queue='submission_queue')
        
        # Verify message publishing
        expected_payload = {
            "submission_id": "SUB-001",
            "assign_id": "ASSIGN-001",
            "student_id": "STU-001",
            "img_url": "https://example.com/image.jpg"
        }
        mock_channel.basic_publish.assert_called_once_with(
            exchange='',
            routing_key='submission_queue',
            body=json.dumps(expected_payload)
        )
        mock_conn_instance.close.assert_called_once()

    @patch('frappe.get_doc')
    @patch('pika.BlockingConnection')
    def test_enqueue_submission_connection_error(self, mock_connection, mock_get_doc):
        """Test enqueueing with RabbitMQ connection error"""
        mock_submission = Mock()
        mock_submission.name = "SUB-001"
        mock_get_doc.return_value = mock_submission
        
        mock_connection.side_effect = pika.exceptions.AMQPConnectionError("Connection failed")
        
        from submission import enqueue_submission
        
        with self.assertRaises(pika.exceptions.AMQPConnectionError):
            enqueue_submission(self.submission_id)

    @patch('frappe.get_doc')
    def test_enqueue_submission_invalid_document(self, mock_get_doc):
        """Test enqueueing with invalid submission document"""
        mock_get_doc.side_effect = frappe.DoesNotExistError("Document not found")
        
        from submission import enqueue_submission
        
        with self.assertRaises(frappe.DoesNotExistError):
            enqueue_submission("INVALID-ID")


class TestImgFeedback(unittest.TestCase):
    """Test cases for img_feedback function"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.valid_api_key = "test_api_key_123"
        self.submission_id = "SUB-001"
        
    @patch('frappe.db.get_value')
    @patch('frappe.set_user')
    @patch('frappe.get_doc')
    def test_img_feedback_completed_submission(self, mock_get_doc, mock_set_user, mock_get_value):
        """Test feedback for completed submission"""
        mock_get_value.return_value = {"user": "test_user"}
        
        mock_submission = Mock()
        mock_submission.status = "Completed"
        mock_submission.overall_feedback = "Great work! The artwork shows excellent understanding."
        mock_get_doc.return_value = mock_submission
        
        from submission import img_feedback
        
        result = img_feedback(self.valid_api_key, self.submission_id)
        
        expected_response = {
            "status": "Completed",
            "overall_feedback": "Great work! The artwork shows excellent understanding."
        }
        
        self.assertEqual(result, expected_response)
        mock_set_user.assert_any_call("test_user")
        mock_set_user.assert_any_call("Administrator")

    @patch('frappe.db.get_value')
    @patch('frappe.set_user')
    @patch('frappe.get_doc')
    def test_img_feedback_pending_submission(self, mock_get_doc, mock_set_user, mock_get_value):
        """Test feedback for pending submission"""
        mock_get_value.return_value = {"user": "test_user"}
        
        mock_submission = Mock()
        mock_submission.status = "Pending"
        mock_get_doc.return_value = mock_submission
        
        from submission import img_feedback
        
        result = img_feedback(self.valid_api_key, self.submission_id)
        
        expected_response = {"status": "Pending"}
        
        self.assertEqual(result, expected_response)

    @patch('frappe.db.get_value')
    @patch('frappe.throw')
    def test_img_feedback_invalid_api_key(self, mock_throw, mock_get_value):
        """Test feedback with invalid API key"""
        mock_get_value.return_value = None
        
        from submission import img_feedback
        
        img_feedback("invalid_key", self.submission_id)
        
        mock_throw.assert_called_once_with("Invalid API key")

    @patch('frappe.db.get_value')
    @patch('frappe.set_user')
    @patch('frappe.get_doc')
    def test_img_feedback_submission_not_found(self, mock_get_doc, mock_set_user, mock_get_value):
        """Test feedback for non-existent submission"""
        mock_get_value.return_value = {"user": "test_user"}
        mock_get_doc.side_effect = frappe.DoesNotExistError("Document not found")
        
        from submission import img_feedback
        
        result = img_feedback(self.valid_api_key, "INVALID-ID")
        
        self.assertEqual(result, {"error": "Submission not found"})
        mock_set_user.assert_any_call("Administrator")

    @patch('frappe.db.get_value')
    @patch('frappe.set_user')
    @patch('frappe.get_doc')
    @patch('frappe.log_error')
    def test_img_feedback_general_error(self, mock_log_error, mock_get_doc, mock_set_user, mock_get_value):
        """Test feedback with general error"""
        mock_get_value.return_value = {"user": "test_user"}
        mock_get_doc.side_effect = Exception("Database connection error")
        
        from submission import img_feedback
        
        result = img_feedback(self.valid_api_key, self.submission_id)
        
        self.assertEqual(result, {"error": "An error occurred while checking submission status"})
        mock_log_error.assert_called_once()
        mock_set_user.assert_any_call("Administrator")


class TestGetAssignmentContext(unittest.TestCase):
    """Test cases for get_assignment_context function"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.assignment_id = "ASSIGN-001"
        self.student_id = "STU-001"
        
    @patch('frappe.get_doc')
    @patch('frappe.db.get_value')
    def test_get_assignment_context_success(self, mock_get_value, mock_get_doc):
        """Test successful assignment context retrieval"""
        # Mock assignment document
        mock_assignment = Mock()
        mock_assignment.assignment_name = "Art Fundamentals"
        mock_assignment.description = "Basic art assignment"
        mock_assignment.assignment_type = "Drawing"
        mock_assignment.subject = "Art"
        mock_assignment.submission_guidelines = "Submit in JPEG format"
        mock_assignment.reference_image = "ref_image.jpg"
        mock_assignment.max_score = 100
        mock_assignment.enable_auto_feedback = False
        mock_assignment.feedback_prompt = None
        
        # Mock learning objectives
        mock_obj1 = Mock()
        mock_obj1.learning_objective = "LO-001"
        mock_obj2 = Mock()
        mock_obj2.learning_objective = "LO-002"
        mock_assignment.learning_objectives = [mock_obj1, mock_obj2]
        
        mock_get_doc.return_value = mock_assignment
        mock_get_value.side_effect = ["Understand color theory", "Master perspective drawing"]
        
        from submission import get_assignment_context
        
        result = get_assignment_context(self.assignment_id)
        
        # Verify assignment data
        self.assertEqual(result["assignment"]["name"], "Art Fundamentals")
        self.assertEqual(result["assignment"]["max_score"], 100)
        
        # Verify learning objectives
        self.assertEqual(len(result["learning_objectives"]), 2)
        self.assertEqual(result["learning_objectives"][0]["objective"], "LO-001")
        self.assertEqual(result["learning_objectives"][0]["description"], "Understand color theory")

    @patch('frappe.get_doc')
    @patch('frappe.db.get_value')
    def test_get_assignment_context_with_student(self, mock_get_value, mock_get_doc):
        """Test assignment context with student information"""
        # Mock assignment
        mock_assignment = Mock()
        mock_assignment.assignment_name = "Art Fundamentals"
        mock_assignment.description = "Basic art assignment"
        mock_assignment.assignment_type = "Drawing"
        mock_assignment.subject = "Art"
        mock_assignment.submission_guidelines = "Submit in JPEG format"
        mock_assignment.reference_image = "ref_image.jpg"
        mock_assignment.max_score = 100
        mock_assignment.enable_auto_feedback = False
        mock_assignment.learning_objectives = []
        
        # Mock student
        mock_student = Mock()
        mock_student.grade = "Grade 10"
        mock_student.level = "Intermediate"
        mock_student.language = "English"
        
        mock_get_doc.side_effect = [mock_assignment, mock_student]
        
        from submission import get_assignment_context
        
        result = get_assignment_context(self.assignment_id, self.student_id)
        
        # Verify student data is included
        self.assertIn("student", result)
        self.assertEqual(result["student"]["grade"], "Grade 10")
        self.assertEqual(result["student"]["level"], "Intermediate")
        self.assertEqual(result["student"]["language"], "English")

    @patch('frappe.get_doc')
    @patch('frappe.db.get_value')
    def test_get_assignment_context_with_feedback_prompt(self, mock_get_value, mock_get_doc):
        """Test assignment context with custom feedback prompt"""
        mock_assignment = Mock()
        mock_assignment.assignment_name = "Art Fundamentals"
        mock_assignment.description = "Basic art assignment"
        mock_assignment.assignment_type = "Drawing"
        mock_assignment.subject = "Art"
        mock_assignment.submission_guidelines = "Submit in JPEG format"
        mock_assignment.reference_image = "ref_image.jpg"
        mock_assignment.max_score = 100
        mock_assignment.enable_auto_feedback = True
        mock_assignment.feedback_prompt = "Focus on color composition and technique"
        mock_assignment.learning_objectives = []
        
        mock_get_doc.return_value = mock_assignment
        
        from submission import get_assignment_context
        
        result = get_assignment_context(self.assignment_id)
        
        # Verify feedback prompt is included
        self.assertIn("feedback_prompt", result)
        self.assertEqual(result["feedback_prompt"], "Focus on color composition and technique")

    @patch('frappe.get_doc')
    @patch('frappe.log_error')
    def test_get_assignment_context_error(self, mock_log_error, mock_get_doc):
        """Test assignment context with error"""
        mock_get_doc.side_effect = Exception("Database error")
        
        from submission import get_assignment_context
        
        result = get_assignment_context("INVALID-ID")
        
        self.assertIsNone(result)
        mock_log_error.assert_called_once()


class TestIntegration(unittest.TestCase):
    """Integration test cases"""
    
    @patch('frappe.db.get_value')
    @patch('frappe.set_user')
    @patch('frappe.new_doc')
    @patch('frappe.db.commit')
    @patch('frappe.get_doc')
    @patch('pika.BlockingConnection')
    def test_submit_and_check_feedback_workflow(self, mock_connection, mock_get_doc, 
                                               mock_commit, mock_new_doc, mock_set_user, mock_get_value):
        """Test complete workflow from submission to feedback"""
        # Setup mocks for submission
        mock_get_value.return_value = {"user": "test_user"}
        mock_submission = Mock()
        mock_submission.name = "SUB-001"
        mock_submission.assign_id = "ASSIGN-001"
        mock_submission.student_id = "STU-001"
        mock_submission.img_url = "https://example.com/image.jpg"
        mock_new_doc.return_value = mock_submission
        
        # Mock RabbitMQ
        mock_channel = Mock()
        mock_conn_instance = Mock()
        mock_conn_instance.channel.return_value = mock_channel
        mock_connection.return_value = mock_conn_instance
        
        from submission import submit_artwork, img_feedback
        
        # Test submission
        submit_result = submit_artwork("valid_key", "ASSIGN-001", "STU-001", "https://example.com/image.jpg")
        self.assertEqual(submit_result["submission_id"], "SUB-001")
        
        # Test feedback check (pending)
        mock_submission.status = "Pending"
        mock_get_doc.return_value = mock_submission
        
        feedback_result = img_feedback("valid_key", "SUB-001")
        self.assertEqual(feedback_result["status"], "Pending")
        
        # Test feedback check (completed)
        mock_submission.status = "Completed"
        mock_submission.overall_feedback = "Excellent work!"
        
        feedback_result = img_feedback("valid_key", "SUB-001")
        self.assertEqual(feedback_result["status"], "Completed")
        self.assertEqual(feedback_result["overall_feedback"], "Excellent work!")


if __name__ == '__main__':
    # Test configuration
    unittest.main(verbosity=2)


# Additional test utility functions
class TestUtilities:
    """Utility functions for testing"""
    
    @staticmethod
    def create_mock_submission(submission_id="SUB-001", status="Pending", feedback=None):
        """Create a mock submission document"""
        mock_submission = Mock()
        mock_submission.name = submission_id
        mock_submission.assign_id = "ASSIGN-001"
        mock_submission.student_id = "STU-001"
        mock_submission.img_url = "https://example.com/image.jpg"
        mock_submission.status = status
        mock_submission.overall_feedback = feedback
        return mock_submission
    
    @staticmethod
    def create_mock_assignment(enable_feedback=False, feedback_prompt=None):
        """Create a mock assignment document"""
        mock_assignment = Mock()
        mock_assignment.assignment_name = "Test Assignment"
        mock_assignment.description = "Test Description"
        mock_assignment.assignment_type = "Drawing"
        mock_assignment.subject = "Art"
        mock_assignment.submission_guidelines = "Submit in JPEG format"
        mock_assignment.reference_image = "ref_image.jpg"
        mock_assignment.max_score = 100
        mock_assignment.enable_auto_feedback = enable_feedback
        mock_assignment.feedback_prompt = feedback_prompt
        mock_assignment.learning_objectives = []
        return mock_assignment


# Test data constants
TEST_DATA = {
    "VALID_API_KEY": "test_api_key_123",
    "INVALID_API_KEY": "invalid_key",
    "ASSIGNMENT_ID": "ASSIGN-001",
    "STUDENT_ID": "STU-001",
    "SUBMISSION_ID": "SUB-001",
    "IMG_URL": "https://example.com/test_image.jpg",
    "RABBITMQ_QUEUE": "submission_queue"
}