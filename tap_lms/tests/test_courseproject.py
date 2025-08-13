import unittest
from unittest.mock import patch
import sys
import os

# Add the doctype path to sys.path so we can import from doctype/courseproject
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'doctype', 'courseproject'))

class TestCourseProjectCoverage(unittest.TestCase):
    """Minimal test to achieve 100% coverage for courseproject.py"""
    
    @patch('frappe.model.document.Document')
    def test_full_module_coverage(self, mock_document):
        """Single test that covers all 3 statements in courseproject.py"""
        
        # This import will execute:
        # 1. Line 5: from frappe.model.document import Document
        # 2. Line 7: class CourseProject(Document):
        # 3. Line 8: pass
        from courseproject import CourseProject
        
        # Verify the class was created successfully
        self.assertEqual(CourseProject.__name__, 'CourseProject')
        
        # Create an instance to ensure everything works
        instance = CourseProject()
        self.assertIsInstance(instance, CourseProject)
