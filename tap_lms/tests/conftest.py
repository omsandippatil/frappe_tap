"""
Pytest configuration and global fixtures for TAP LMS tests
"""

import sys
import os
from unittest.mock import MagicMock

# CRITICAL: Mock modules BEFORE any test discovery
# This ensures Jenkins doesn't try to import real frappe
def pytest_configure(config):
    """Called before test collection"""
    # Mock all external dependencies globally
    sys.modules['frappe'] = MagicMock()
    sys.modules['frappe.utils'] = MagicMock()
    sys.modules['frappe.model'] = MagicMock()
    sys.modules['frappe.model.document'] = MagicMock()
    sys.modules['requests'] = MagicMock()
    sys.modules['dateutil'] = MagicMock()
    sys.modules['dateutil.parser'] = MagicMock()
    
    # Register custom markers
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )

# Add parent directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)