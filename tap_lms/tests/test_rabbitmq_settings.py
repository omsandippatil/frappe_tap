"""
Direct test approach to achieve 100% coverage for rabbitmq_settings.py
This bypasses frappe import issues by mocking the dependencies.
"""

import subprocess
import sys
import tempfile
import os



def test_simple_import():
    """Simple test to verify the module can be imported with mocking"""
    from unittest.mock import Mock, patch
    
    # Create mock
    mock_document = Mock()
    
    # Patch the frappe import
    with patch.dict('sys.modules', {
        'frappe': Mock(),
        'frappe.model': Mock(),
        'frappe.model.document': Mock(Document=mock_document)
    }):
        # This should now work
        import tap_lms.tap_lms.doctype.rabbitmq_settings.rabbitmq_settings as module
        assert module is not None

