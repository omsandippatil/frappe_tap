import json
from unittest.mock import Mock, patch, MagicMock

# Mock frappe module
frappe = Mock()
frappe.whitelist = lambda allow_guest=False: lambda func: func
frappe.db = Mock()
frappe.logger = Mock()
frappe.log_error = Mock()
frappe.throw = Mock(side_effect=Exception)
frappe.set_user = Mock()
frappe.new_doc = Mock()
frappe.get_doc = Mock()
frappe.DoesNotExistError = Exception

# Mock pika module
pika = Mock()
pika.PlainCredentials = Mock()
pika.ConnectionParameters = Mock()
pika.BlockingConnection = Mock()

# Import the functions to test (assuming they're in a file called artwork_api.py)
# For testing purposes, we'll define them here
def submit_artwork(api_key, assign_id, student_id, img_url):
    # Authenticate the API request using the provided api_key
    api_key_doc = frappe.db.get_value("API Key", {"key": api_key, "enabled": 1}, ["user"], as_dict=True)
    if not api_key_doc:
        frappe.throw("Invalid API key")

    # Switch to the user associated with the API key
    frappe.set_user(api_key_doc.user)

    try:
        # Create a new submission
        submission = frappe.new_doc("ImgSubmission")
        submission.assign_id = assign_id
        submission.student_id = student_id
        submission.img_url = img_url
        submission.status = "Pending"
        submission.insert()
        frappe.db.commit()

        # Log for debugging
        frappe.logger("submission").debug(f"Inserted submission: assign_id={submission.assign_id}, student_id={submission.student_id}, img_url={submission.img_url}")

        # Send the submission details to RabbitMQ
        enqueue_submission(submission.name)

        return {"message": "Submission received", "submission_id": submission.name}

    finally:
        # Switch back to the original user
        frappe.set_user("Administrator")

def enqueue_submission(submission_id):
    submission = frappe.get_doc("ImgSubmission", submission_id)
    payload = {
        "submission_id": submission.name,
        "assign_id": submission.assign_id,
        "student_id": submission.student_id,
        "img_url": submission.img_url
    }

    rabbitmq_config = {
        'host': 'armadillo.rmq.cloudamqp.com',
        'port': 5672,
        'virtual_host': 'fzdqidte',
        'username': 'fzdqidte',
        'password': '0SMrDogBVcWUcu9brWwp2QhET_kArl59',
        'queue': 'submission_queue'
    }

    # Establish a connection to RabbitMQ
    credentials = pika.PlainCredentials(rabbitmq_config['username'], rabbitmq_config['password'])
    parameters = pika.ConnectionParameters(
        rabbitmq_config['host'],
        rabbitmq_config['port'],
        rabbitmq_config['virtual_host'],
        credentials
    )
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()

    # Declare the queue
    channel.queue_declare(queue=rabbitmq_config['queue'])

    # Publish the message to the queue
    channel.basic_publish(
        exchange='',
        routing_key=rabbitmq_config['queue'],
        body=json.dumps(payload)
    )

    # Close the connection
    connection.close()

def img_feedback(api_key, submission_id):
    # Authenticate the API request using the provided api_key
    api_key_doc = frappe.db.get_value("API Key", {"key": api_key, "enabled": 1}, ["user"], as_dict=True)
    if not api_key_doc:
        frappe.throw("Invalid API key")

    # Switch to the user associated with the API key
    frappe.set_user(api_key_doc.user)

    try:
        # Get the submission document
        submission = frappe.get_doc("ImgSubmission", submission_id)
        
        # Prepare the response based on status
        if submission.status == "Completed":
            response = {
                "status": submission.status,
                "overall_feedback": submission.overall_feedback
            }
        else:
            response = {
                "status": submission.status
            }
        
        return response

    except frappe.DoesNotExistError:
        return {"error": "Submission not found"}
    
    except Exception as e:
        frappe.log_error(f"Error checking submission status: {str(e)}", "Submission Status Error")
        return {"error": "An error occurred while checking submission status"}

    finally:
        # Switch back to the original user
        frappe.set_user("Administrator")

def get_assignment_context(assignment_id, student_id=None):
    """Get complete assignment context for RAG service"""
    try:
        assignment = frappe.get_doc("Assignment", assignment_id)
        
        context = {
            "assignment": {
                "name": assignment.assignment_name,
                "description": assignment.description,
                "type": assignment.assignment_type,
                "subject": assignment.subject,
                "submission_guidelines": assignment.submission_guidelines,
                "reference_image": assignment.reference_image,
                "max_score": assignment.max_score
            },
            "learning_objectives": [
                {
                    "objective": obj.learning_objective,
                    "description": frappe.db.get_value(
                        "Learning Objective",
                        obj.learning_objective,
                        "description"
                    )
                }
                for obj in assignment.learning_objectives
            ]
        }
        
        # Add student context if provided
        if student_id:
            student = frappe.get_doc("Student", student_id)
            context["student"] = {
                "grade": student.grade,
                "level": student.level,
                "language": student.language
            }
        
        # Add custom feedback prompt if enabled
        if assignment.enable_auto_feedback and assignment.feedback_prompt:
            context["feedback_prompt"] = assignment.feedback_prompt
            
        return context
        
    except Exception as e:
        frappe.log_error(
            f"Error getting assignment context: {str(e)}",
            "RAG Context Error"
        )
        return None

# TEST CASES

def test_submit_artwork_valid_api_key():
    """Test submit_artwork with valid API key"""
    print("Testing submit_artwork with valid API key...")
    
    # Setup mocks
    frappe.db.get_value.return_value = {"user": "test_user"}
    
    mock_submission = Mock()
    mock_submission.name = "SUB-001"
    mock_submission.assign_id = "ASSIGN-001"
    mock_submission.student_id = "STU-001"
    mock_submission.img_url = "http://example.com/image.jpg"
    mock_submission.status = "Pending"
    
    frappe.new_doc.return_value = mock_submission
    frappe.get_doc.return_value = mock_submission
    frappe.db.commit = Mock()
    
    # Mock RabbitMQ
    mock_connection = Mock()
    mock_channel = Mock()
    mock_connection.channel.return_value = mock_channel
    pika.BlockingConnection.return_value = mock_connection
    
    # Test
    result = submit_artwork("valid_key", "ASSIGN-001", "STU-001", "http://example.com/image.jpg")
    
    # Assertions
    assert result["message"] == "Submission received"
    assert result["submission_id"] == "SUB-001"
    frappe.db.get_value.assert_called_once()
    frappe.set_user.assert_called()
    mock_submission.insert.assert_called_once()
    frappe.db.commit.assert_called_once()
    
    print("✓ Test passed: submit_artwork with valid API key")

def test_submit_artwork_invalid_api_key():
    """Test submit_artwork with invalid API key"""
    print("Testing submit_artwork with invalid API key...")
    
    # Setup mocks
    frappe.db.get_value.return_value = None
    frappe.throw.side_effect = Exception("Invalid API key")
    
    # Test
    try:
        submit_artwork("invalid_key", "ASSIGN-001", "STU-001", "http://example.com/image.jpg")
        assert False, "Should have thrown an exception"
    except Exception as e:
        assert str(e) == "Invalid API key"
    
    print("✓ Test passed: submit_artwork with invalid API key")

def test_enqueue_submission():
    """Test enqueue_submission function"""
    print("Testing enqueue_submission...")
    
    # Setup mocks
    mock_submission = Mock()
    mock_submission.name = "SUB-001"
    mock_submission.assign_id = "ASSIGN-001"
    mock_submission.student_id = "STU-001"
    mock_submission.img_url = "http://example.com/image.jpg"
    
    frappe.get_doc.return_value = mock_submission
    
    # Mock RabbitMQ
    mock_connection = Mock()
    mock_channel = Mock()
    mock_connection.channel.return_value = mock_channel
    pika.BlockingConnection.return_value = mock_connection
    
    # Test
    enqueue_submission("SUB-001")
    
    # Assertions
    frappe.get_doc.assert_called_with("ImgSubmission", "SUB-001")
    pika.BlockingConnection.assert_called_once()
    mock_channel.queue_declare.assert_called_once()
    mock_channel.basic_publish.assert_called_once()
    mock_connection.close.assert_called_once()
    
    print("✓ Test passed: enqueue_submission")

def test_img_feedback_completed_status():
    """Test img_feedback with completed submission"""
    print("Testing img_feedback with completed submission...")
    
    # Setup mocks
    frappe.db.get_value.return_value = {"user": "test_user"}
    
    mock_submission = Mock()
    mock_submission.status = "Completed"
    mock_submission.overall_feedback = "Great work!"
    
    frappe.get_doc.return_value = mock_submission
    
    # Test
    result = img_feedback("valid_key", "SUB-001")
    
    # Assertions
    assert result["status"] == "Completed"
    assert result["overall_feedback"] == "Great work!"
    
    print("✓ Test passed: img_feedback with completed status")

def test_img_feedback_pending_status():
    """Test img_feedback with pending submission"""
    print("Testing img_feedback with pending submission...")
    
    # Setup mocks
    frappe.db.get_value.return_value = {"user": "test_user"}
    
    mock_submission = Mock()
    mock_submission.status = "Pending"
    
    frappe.get_doc.return_value = mock_submission
    
    # Test
    result = img_feedback("valid_key", "SUB-001")
    
    # Assertions
    assert result["status"] == "Pending"
    assert "overall_feedback" not in result
    
    print("✓ Test passed: img_feedback with pending status")

def test_img_feedback_submission_not_found():
    """Test img_feedback with non-existent submission"""
    print("Testing img_feedback with non-existent submission...")
    
    # Setup mocks
    frappe.db.get_value.return_value = {"user": "test_user"}
    frappe.get_doc.side_effect = frappe.DoesNotExistError("Submission not found")
    
    # Test
    result = img_feedback("valid_key", "NONEXISTENT")
    
    # Assertions
    assert result["error"] == "Submission not found"
    
    print("✓ Test passed: img_feedback with non-existent submission")

def test_img_feedback_invalid_api_key():
    """Test img_feedback with invalid API key"""
    print("Testing img_feedback with invalid API key...")
    
    # Setup mocks
    frappe.db.get_value.return_value = None
    frappe.throw.side_effect = Exception("Invalid API key")
    
    # Test
    try:
        img_feedback("invalid_key", "SUB-001")
        assert False, "Should have thrown an exception"
    except Exception as e:
        assert str(e) == "Invalid API key"
    
    print("✓ Test passed: img_feedback with invalid API key")

def test_get_assignment_context_basic():
    """Test get_assignment_context without student"""
    print("Testing get_assignment_context basic...")
    
    # Setup mocks
    mock_assignment = Mock()
    mock_assignment.assignment_name = "Math Test"
    mock_assignment.description = "Basic math assignment"
    mock_assignment.assignment_type = "Quiz"
    mock_assignment.subject = "Mathematics"
    mock_assignment.submission_guidelines = "Submit your answers"
    mock_assignment.reference_image = "ref.jpg"
    mock_assignment.max_score = 100
    mock_assignment.enable_auto_feedback = False
    
    mock_objective = Mock()
    mock_objective.learning_objective = "LO-001"
    mock_assignment.learning_objectives = [mock_objective]
    
    frappe.get_doc.return_value = mock_assignment
    frappe.db.get_value.return_value = "Understand basic math"
    
    # Test
    result = get_assignment_context("ASSIGN-001")
    
    # Assertions
    assert result["assignment"]["name"] == "Math Test"
    assert result["assignment"]["description"] == "Basic math assignment"
    assert len(result["learning_objectives"]) == 1
    assert "student" not in result
    
    print("✓ Test passed: get_assignment_context basic")

def test_get_assignment_context_with_student():
    """Test get_assignment_context with student"""
    print("Testing get_assignment_context with student...")
    
    # Setup mocks
    mock_assignment = Mock()
    mock_assignment.assignment_name = "Math Test"
    mock_assignment.description = "Basic math assignment"
    mock_assignment.assignment_type = "Quiz"
    mock_assignment.subject = "Mathematics"
    mock_assignment.submission_guidelines = "Submit your answers"
    mock_assignment.reference_image = "ref.jpg"
    mock_assignment.max_score = 100
    mock_assignment.enable_auto_feedback = False
    mock_assignment.learning_objectives = []
    
    mock_student = Mock()
    mock_student.grade = "10"
    mock_student.level = "Intermediate"
    mock_student.language = "English"
    
    def mock_get_doc(doctype, doc_id):
        if doctype == "Assignment":
            return mock_assignment
        elif doctype == "Student":
            return mock_student
    
    frappe.get_doc.side_effect = mock_get_doc
    
    # Test
    result = get_assignment_context("ASSIGN-001", "STU-001")
    
    # Assertions
    assert result["assignment"]["name"] == "Math Test"
    assert result["student"]["grade"] == "10"
    assert result["student"]["level"] == "Intermediate"
    assert result["student"]["language"] == "English"
    
    print("✓ Test passed: get_assignment_context with student")

def test_get_assignment_context_with_feedback_prompt():
    """Test get_assignment_context with feedback prompt"""
    print("Testing get_assignment_context with feedback prompt...")
    
    # Setup mocks
    mock_assignment = Mock()
    mock_assignment.assignment_name = "Math Test"
    mock_assignment.description = "Basic math assignment"
    mock_assignment.assignment_type = "Quiz"
    mock_assignment.subject = "Mathematics"
    mock_assignment.submission_guidelines = "Submit your answers"
    mock_assignment.reference_image = "ref.jpg"
    mock_assignment.max_score = 100
    mock_assignment.enable_auto_feedback = True
    mock_assignment.feedback_prompt = "Provide detailed feedback"
    mock_assignment.learning_objectives = []
    
    frappe.get_doc.return_value = mock_assignment
    
    # Test
    result = get_assignment_context("ASSIGN-001")
    
    # Assertions
    assert result["assignment"]["name"] == "Math Test"
    assert result["feedback_prompt"] == "Provide detailed feedback"
    
    print("✓ Test passed: get_assignment_context with feedback prompt")

def test_get_assignment_context_exception():
    """Test get_assignment_context with exception"""
    print("Testing get_assignment_context with exception...")
    
    # Setup mocks
    frappe.get_doc.side_effect = Exception("Database error")
    
    # Test
    result = get_assignment_context("INVALID-ASSIGN")
    
    # Assertions
    assert result is None
    frappe.log_error.assert_called_once()
    
    print("✓ Test passed: get_assignment_context with exception")

def run_all_tests():
    """Run all test cases"""
    print("=" * 50)
    print("RUNNING ALL TEST CASES")
    print("=" * 50)
    
    # Reset mocks before each test
    frappe.reset_mock()
    pika.reset_mock()
    
    try:
        test_submit_artwork_valid_api_key()
        
        # Reset for next test
        frappe.reset_mock()
        test_submit_artwork_invalid_api_key()
        
        frappe.reset_mock()
        test_enqueue_submission()
        
        frappe.reset_mock()
        test_img_feedback_completed_status()
        
        frappe.reset_mock()
        test_img_feedback_pending_status()
        
        frappe.reset_mock()
        test_img_feedback_submission_not_found()
        
        frappe.reset_mock()
        test_img_feedback_invalid_api_key()
        
        frappe.reset_mock()
        test_get_assignment_context_basic()
        
        frappe.reset_mock()
        test_get_assignment_context_with_student()
        
        frappe.reset_mock()
        test_get_assignment_context_with_feedback_prompt()
        
        frappe.reset_mock()
        test_get_assignment_context_exception()
        
        print("\n" + "=" * 50)
        print("ALL TESTS PASSED! ✓")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        raise
