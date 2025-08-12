# import unittest
# from unittest.mock import patch, MagicMock
# import sys


# class TestCompetency(unittest.TestCase):
    
#     def setUp(self):
#         """Set up test fixtures before each test method."""
#         # Mock frappe module to avoid import errors during testing
#         self.frappe_mock = MagicMock()
#         self.document_mock = MagicMock()
#         self.frappe_mock.model.document.Document = self.document_mock
        
#         # Add mocks to sys.modules
#         sys.modules['frappe'] = self.frappe_mock
#         sys.modules['frappe.model'] = self.frappe_mock.model
#         sys.modules['frappe.model.document'] = self.frappe_mock.model.document
    
#     def tearDown(self):
#         """Clean up after each test method."""
#         # Remove mocked modules
#         modules_to_remove = [
#             'frappe',
#             'frappe.model',
#             'frappe.model.document',
#             'tap_lms.tap_lms.doctype.competency.competency'
#         ]
#         for module in modules_to_remove:
#             if module in sys.modules:
#                 del sys.modules[module]
   

import unittest
from unittest.mock import patch, MagicMock
import sys


class TestCompetency(unittest.TestCase):
   
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Mock frappe module to avoid import errors during testing
        self.frappe_mock = MagicMock()
        self.document_mock = MagicMock()
        self.frappe_mock.model.document.Document = self.document_mock
       
        # Add mocks to sys.modules
        sys.modules['frappe'] = self.frappe_mock
        sys.modules['frappe.model'] = self.frappe_mock.model
        sys.modules['frappe.model.document'] = self.frappe_mock.model.document
   
    def tearDown(self):
        """Clean up after each test method."""
        # Remove mocked modules
        modules_to_remove = [
            'frappe',
            'frappe.model',
            'frappe.model.document',
            'tap_lms.tap_lms.doctype.competency.competency'
        ]
        for module in modules_to_remove:
            if module in sys.modules:
                del sys.modules[module]
   
    def test_competency_import_and_class_definition(self):
        """Test that covers all lines in competency.py for 100% coverage."""
        
        # This import statement covers the actual competency.py lines
        from tap_lms.tap_lms.doctype.competency.competency import Competency
        
        # Verify the class was imported successfully
        self.assertIsNotNone(Competency)
        
        # Verify it's a class
        self.assertTrue(isinstance(Competency, type))
        
        # Verify class name
        self.assertEqual(Competency.__name__, 'Competency')
        
        # Create an instance to ensure the class works
        instance = Competency()
        self.assertIsInstance(instance, Competency)
        
        # Verify inheritance from Document (mocked)
        self.assertTrue(issubclass(Competency, self.document_mock))
    
    def test_competency_multiple_instantiation(self):
        """Test multiple instantiation to ensure class definition is solid."""
        from tap_lms.tap_lms.doctype.competency.competency import Competency
        
        # Create multiple instances
        instance1 = Competency()
        instance2 = Competency()
        
        # Ensure they are different objects but same type
        self.assertIsNot(instance1, instance2)
        self.assertEqual(type(instance1), type(instance2))
        self.assertIsInstance(instance1, Competency)
        self.assertIsInstance(instance2, Competency)
    
    def test_competency_class_attributes(self):
        """Test class attributes and methods."""
        from tap_lms.tap_lms.doctype.competency.competency import Competency
        
        # Test basic class attributes
        self.assertTrue(hasattr(Competency, '__name__'))
        self.assertTrue(hasattr(Competency, '__module__'))
        self.assertTrue(hasattr(Competency, '__mro__'))
        
        # Test instance creation and basic attributes
        instance = Competency()
        self.assertTrue(hasattr(instance, '__class__'))
        self.assertEqual(instance.__class__.__name__, 'Competency')

