import pytest
import frappe
from unittest.mock import patch, MagicMock
import sys
import os

# Add your app path - update this to your actual app path
sys.path.append('/path/to/your/frappe/app/lms')  # Update this path
from api import authenticate_api_key  # Import from your actual api.py file


class TestAuthentication:
    """Test cases for authenticate_api_key function"""
    
    def test_authenticate_valid_api_key(self):
        """Test authentication with valid API key"""
        result = authenticate_api_key("test_api_key_123")
        assert result == "test_api_key_123"
        
    def test_authenticate_invalid_api_key(self):
        """Test authentication with invalid API key"""
        result = authenticate_api_key("invalid_api_key")
        assert result is None
        
    def test_authenticate_none_api_key(self):
        """Test authentication with None API key"""
        result = authenticate_api_key(None)
        assert result is None
        
    def test_authenticate_empty_api_key(self):
        """Test authentication with empty API key"""
        result = authenticate_api_key("")
        assert result is None
        
    def test_authenticate_disabled_api_key(self):
        """Test authentication with disabled API key"""
        # Create disabled API key
        disabled_key = "disabled_key_123"
        if not frappe.db.exists("API Key", {"key": disabled_key}):
            api_key_doc = frappe.get_doc({
                "doctype": "API Key",
                "key": disabled_key,
                "enabled": 0,
                "user": "Administrator"
            })
            api_key_doc.insert(ignore_permissions=True)
            frappe.db.commit()
            
        result = authenticate_api_key(disabled_key)
        assert result is None
        
    @patch('frappe.get_doc')
    def test_authenticate_api_key_does_not_exist_error(self, mock_get_doc):
        """Test authentication when DoesNotExistError occurs"""
        mock_get_doc.side_effect = frappe.DoesNotExistError()
        
        result = authenticate_api_key("some_key")
        assert result is None
        
    def test_authenticate_special_characters_api_key(self):
        """Test authentication with special characters in API key"""
        special_key = "test@#$%^&*()_+key"
        
        # Create API key with special characters
        if not frappe.db.exists("API Key", {"key": special_key}):
            api_key_doc = frappe.get_doc({
                "doctype": "API Key",
                "key": special_key,
                "enabled": 1,
                "user": "Administrator"
            })
            api_key_doc.insert(ignore_permissions=True)
            frappe.db.commit()
            
        result = authenticate_api_key(special_key)
        assert result == special_key
        
    def test_authenticate_very_long_api_key(self):
        """Test authentication with very long API key"""
        long_key = "a" * 1000  # Very long key
        
        result = authenticate_api_key(long_key)
        assert result is None  # Should not exist
        
    def test_authenticate_numeric_api_key(self):
        """Test authentication with numeric API key"""
        numeric_key = "123456789"
        
        # Create numeric API key
        if not frappe.db.exists("API Key", {"key": numeric_key}):
            api_key_doc = frappe.get_doc({
                "doctype": "API Key",
                "key": numeric_key,
                "enabled": 1,
                "user": "Administrator"
            })
            api_key_doc.insert(ignore_permissions=True)
            frappe.db.commit()
            
        result = authenticate_api_key(numeric_key)
        assert result == numeric_key