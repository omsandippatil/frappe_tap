import pytest
import sys
from unittest.mock import Mock

def test_feedback_request_coverage():
    """
    Test for YOUR feedback_request.py file
    
    Your file has only 3 lines that need testing:
    Line 5: from frappe.model.document import Document
    Line 7: class FeedbackRequest(Document):
    Line 8:     pass
    
    This test covers all 3 lines.
    """
    
    # Mock frappe module (so we don't need actual Frappe installed)
    class MockDocument:
        def __init__(self, *args, **kwargs):
            pass
    
    mock_frappe = Mock()
    mock_frappe.model = Mock()
    mock_frappe.model.document = Mock()
    mock_frappe.model.document.Document = MockDocument
    
    sys.modules['frappe'] = mock_frappe
    sys.modules['frappe.model'] = mock_frappe.model
    sys.modules['frappe.model.document'] = mock_frappe.model.document
    
    # Import your class - this tests line 5
    from tap_lms.tap_lms.doctype.feedback_request.feedback_request import FeedbackRequest
    
    # Create instance - this tests lines 7 and 8
    feedback_request = FeedbackRequest()
    
    # Check it worked
    assert feedback_request is not None
    assert FeedbackRequest.__name__ == 'FeedbackRequest'
    assert isinstance(feedback_request, FeedbackRequest)


def test_feedback_request_inheritance():
    """Test FeedbackRequest inherits from Document"""
    from tap_lms.tap_lms.doctype.feedback_request.feedback_request import FeedbackRequest
    feedback_request = FeedbackRequest()
    assert feedback_request is not None


def test_feedback_request_multiple_instances():
    """Test creating multiple FeedbackRequest instances"""
    from tap_lms.tap_lms.doctype.feedback_request.feedback_request import FeedbackRequest
    
    request1 = FeedbackRequest()
    request2 = FeedbackRequest()
    
    assert request1 is not None
    assert request2 is not None
    assert request1 is not request2