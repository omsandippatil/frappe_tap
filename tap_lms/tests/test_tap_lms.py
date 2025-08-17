import unittest
import json
from unittest.mock import patch, MagicMock


class TestTapLmsConfig(unittest.TestCase):
    """Test cases for tap_lms.config.tap_lms module"""

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Import here to avoid import issues during test discovery
        try:
            from apps.tap_lms.tap_lms.config.tap_lms import get_data
            self.get_data = get_data
        except ImportError:
            # Alternative import path
            from tap_lms.config.tap_lms import get_data
            self.get_data = get_data

    def test_get_data_returns_dict(self):
        """Test that get_data returns a dictionary"""
        result = self.get_data()
        self.assertIsInstance(result, dict)

    def test_get_data_has_required_keys(self):
        """Test that get_data returns dictionary with expected keys"""
        result = self.get_data()
        self.assertIn('label', result)
        self.assertIn('items', result)

    def test_get_data_label_value(self):
        """Test that the label has the expected value"""
        result = self.get_data()
        self.assertEqual(result['label'], '_("School")')

    def test_get_data_items_count(self):
        """Test that items list has expected number of elements"""
        result = self.get_data()
        items = result['items']
        self.assertIsInstance(items, list)
        self.assertEqual(len(items), 1)

    def test_get_data_items_structure(self):
        """Test the structure of items array"""
        result = self.get_data()
        items = result['items']
        
        self.assertIsInstance(items, list)
        self.assertGreater(len(items), 0)
        self.assertIsInstance(items[0], dict)

    def test_get_data_school_item_properties(self):
        """Test all properties of the school item"""
        result = self.get_data()
        school_item = result['items'][0]
        
        # Test each property individually
        self.assertEqual(school_item['type'], 'doctype')
        self.assertEqual(school_item['name'], 'School')
        self.assertEqual(school_item['label'], '_("School")')
        self.assertEqual(school_item['description'], '_("Manage School")')
        self.assertEqual(school_item['onboard'], 1)

    def test_get_data_school_item_onboard_flag(self):
        """Test that onboard flag is set correctly"""
        result = self.get_data()
        school_item = result['items'][0]
        self.assertEqual(school_item['onboard'], 1)

    def test_get_data_school_item_type_doctype(self):
        """Test that item type is doctype"""
        result = self.get_data()
        school_item = result['items'][0]
        self.assertEqual(school_item['type'], 'doctype')

    def test_get_data_returns_dict(self):
        """Test function returns dictionary type"""
        result = self.get_data()
        self.assertIsInstance(result, dict)

    @patch('frappe.import_module')
    def test_get_data_with_frappe_import(self, mock_frappe):
        """Test that function works with frappe mocked"""
        result = self.get_data()
        self.assertIsInstance(result, dict)
        self.assertIn('label', result)
        self.assertIn('items', result)


class TestTapLmsConfigIntegration(unittest.TestCase):
    """Integration tests for configuration"""

    def setUp(self):
        """Set up test fixtures"""
        try:
            from apps.tap_lms.tap_lms.config.tap_lms import get_data
            self.get_data = get_data
        except ImportError:
            from tap_lms.config.tap_lms import get_data
            self.get_data = get_data

    def test_config_can_be_serialized(self):
        """Test that configuration can be converted to JSON"""
        result = self.get_data()
        
        # Should not raise an exception
        json_string = json.dumps(result)
        self.assertIsInstance(json_string, str)
        
        # Should be deserializable
        deserialized = json.loads(json_string)
        self.assertEqual(result, deserialized)


# Alternative simple test file if the above doesn't work
class SimpleTestTapLms(unittest.TestCase):
    """Simplified test cases"""
    
    def test_import_and_call_get_data(self):
        """Test basic import and function call"""
        # Try different import paths
        get_data_func = None
        
        try:
            from apps.tap_lms.tap_lms.config.tap_lms import get_data
            get_data_func = get_data
        except ImportError:
            try:
                from tap_lms.config.tap_lms import get_data
                get_data_func = get_data
            except ImportError:
                self.fail("Could not import get_data function")
        
        # Call the function
        result = get_data_func()
        
        # Basic assertions
        self.assertIsNotNone(result)
        self.assertIsInstance(result, dict)

    def test_function_output_structure(self):
        """Test the basic structure of output"""
        # Import
        try:
            from apps.tap_lms.tap_lms.config.tap_lms import get_data
        except ImportError:
            from tap_lms.config.tap_lms import get_data
        
        result = get_data()
        
        # Check structure
        self.assertTrue('label' in result)
        self.assertTrue('items' in result)
        self.assertTrue(isinstance(result['items'], list))

