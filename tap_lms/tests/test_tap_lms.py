import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add the path to your module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

class TestTapLmsConfig(unittest.TestCase):
    
    @patch('frappe._')
    def test_import_frappe_underscore(self, mock_frappe_underscore):
        """Test that frappe._ is imported successfully"""
        # Mock the frappe._ function
        mock_frappe_underscore.return_value = "Mocked translation"
        
        # Import the module to trigger the import statement
        from tap_lms.config import tap_lms
        
        # Verify the module was imported without errors
        self.assertTrue(hasattr(tap_lms, 'get_data'))
    
    @patch('frappe._')
    def test_get_data_function_exists_and_callable(self, mock_frappe_underscore):
        """Test that get_data function exists and is callable"""
        # Mock the frappe._ function
        mock_frappe_underscore.return_value = "School"
        
        # Import the module
        from tap_lms.config import tap_lms
        
        # Test that get_data function exists
        self.assertTrue(hasattr(tap_lms, 'get_data'))
        self.assertTrue(callable(tap_lms.get_data))
    
    @patch('frappe._')
    def test_get_data_returns_expected_structure(self, mock_frappe_underscore):
        """Test that get_data returns the expected data structure"""
        # Mock the frappe._ function to return expected translations
        def mock_translate(text):
            translations = {
                "School": "School",
                "Manage School": "Manage School"
            }
            return translations.get(text, text)
        
        mock_frappe_underscore.side_effect = mock_translate
        
        # Import and call the function
        from tap_lms.config import tap_lms
        result = tap_lms.get_data()
        
        # Verify the structure
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        
        # Check the main structure
        main_item = result[0]
        self.assertIn("label", main_item)
        self.assertIn("items", main_item)
        
        # Check the nested items structure
        items = main_item["items"]
        self.assertIsInstance(items, list)
        self.assertEqual(len(items), 1)
        
        school_item = items[0]
        expected_keys = ["type", "name", "label", "description", "onboard"]
        for key in expected_keys:
            self.assertIn(key, school_item)
    
   
    @patch('frappe._')
    def test_frappe_underscore_called_with_correct_arguments(self, mock_frappe_underscore):
        """Test that frappe._ is called with the correct arguments"""
        # Import and call the function
        from tap_lms.config import tap_lms
        tap_lms.get_data()
        
        # Verify frappe._ was called with expected arguments
        expected_calls = ["School", "Manage School"]
        actual_calls = [call[0][0] for call in mock_frappe_underscore.call_args_list]
        
        for expected_call in expected_calls:
            self.assertIn(expected_call, actual_calls)
    
    @patch('frappe._')
    def test_module_level_import_coverage(self, mock_frappe_underscore):
        """Test to ensure module-level imports are covered"""
        # This test ensures that when we import the module,
        # all module-level code is executed
        mock_frappe_underscore.return_value = "Test"
        
        # Force reimport to ensure coverage of import statements
        if 'tap_lms.config.tap_lms' in sys.modules:
            del sys.modules['tap_lms.config.tap_lms']
        
        # Import the module
        from tap_lms.config import tap_lms
        
        # Verify module was imported successfully
        self.assertTrue(hasattr(tap_lms, 'get_data'))

