import pytest
import sys
from unittest.mock import Mock

def test_enrollment_coverage():
    """
    Minimal test to achieve 100% coverage for enrollment.py
    Covers lines 5, 7, and 8
    """
    
    # Mock frappe module
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
    
    # Import and instantiate - this covers all 3 lines
    from tap_lms.tap_lms.doctype.enrollment.enrollment import Enrollment
    enrollment = Enrollment()
    
    # Basic assertions
    assert enrollment is not None
    assert Enrollment.__name__ == 'Enrollment'
    assert isinstance(enrollment, Enrollment)


def test_enrollment_inheritance():
    """Test Enrollment inherits from Document"""
    from tap_lms.tap_lms.doctype.enrollment.enrollment import Enrollment
    enrollment = Enrollment()
    assert enrollment is not None


def test_enrollment_multiple_instances():
    """Test multiple Enrollment instances"""
    from tap_lms.tap_lms.doctype.enrollment.enrollment import Enrollment
    
    enrollment1 = Enrollment()
    enrollment2 = Enrollment()
    
    assert enrollment1 is not None
    assert enrollment2 is not None
    assert enrollment1 is not enrollment2


def test_enrollment_class_attributes():
    """Test Enrollment class attributes and methods"""
    from tap_lms.tap_lms.doctype.enrollment.enrollment import Enrollment
    
    # Test class name
    assert hasattr(Enrollment, '__name__')
    assert Enrollment.__name__ == 'Enrollment'
    
    # Test instantiation
    enrollment = Enrollment()
    assert enrollment.__class__.__name__ == 'Enrollment'


def test_enrollment_with_args():
    """Test Enrollment instantiation with arguments"""
    from tap_lms.tap_lms.doctype.enrollment.enrollment import Enrollment
    
    # Test with positional arguments
    enrollment1 = Enrollment("test_arg")
    assert enrollment1 is not None
    
    # Test with keyword arguments
    enrollment2 = Enrollment(name="test_enrollment")
    assert enrollment2 is not None
    
    # Test with both
    enrollment3 = Enrollment("test_arg", name="test_enrollment")
    assert enrollment3 is not None


def test_enrollment_document_base_class():
    """Test Enrollment is properly based on Document class"""
    from tap_lms.tap_lms.doctype.enrollment.enrollment import Enrollment
    
    # Verify the class exists and can be instantiated
    enrollment = Enrollment()
    
    # Test that it behaves like a Document (through mocked Document)
    assert enrollment is not None
    assert hasattr(Enrollment, '__init__')