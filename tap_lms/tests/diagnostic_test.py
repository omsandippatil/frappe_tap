"""
Diagnostic test to find what functions actually exist and can be imported
Run this first to understand the API module structure
"""

import frappe
import unittest
import sys
import os

class DiagnosticTest(unittest.TestCase):
    """Diagnostic test to check what's available"""
    
    def setUp(self):
        frappe.set_user("Administrator")
    
    def test_find_api_functions(self):
        """Find all available API functions"""
        try:
            # Try different import methods
            print("\n=== DIAGNOSTIC TEST RESULTS ===")
            
            # Method 1: Direct import
            try:
                import tap_lms.api as api_module
                print("✅ Successfully imported tap_lms.api")
                print(f"Module file: {api_module.__file__}")
                
                # List all functions
                functions = []
                for name in dir(api_module):
                    if not name.startswith('_'):
                        attr = getattr(api_module, name)
                        if callable(attr):
                            functions.append(name)
                            print(f"✅ Function found: {name}")
                
                print(f"\nTotal functions found: {len(functions)}")
                
                # Test calling a simple function
                if 'authenticate_api_key' in functions:
                    print("\nTesting authenticate_api_key:")
                    result = api_module.authenticate_api_key(None)
                    print(f"✅ authenticate_api_key(None) returned: {result}")
                
                return functions
                
            except Exception as e:
                print(f"❌ Direct import failed: {e}")
                print(f"Python path: {sys.path}")
                
            # Method 2: Try frappe.get_attr
            try:
                auth_func = frappe.get_attr('tap_lms.api.authenticate_api_key')
                print("✅ frappe.get_attr worked for authenticate_api_key")
                result = auth_func(None)
                print(f"✅ Function call returned: {result}")
            except Exception as e:
                print(f"❌ frappe.get_attr failed: {e}")
                
            # Method 3: Check if functions are whitelisted
            try:
                frappe.call('tap_lms.api.authenticate_api_key', api_key=None)
                print("✅ frappe.call worked")
            except Exception as e:
                print(f"❌ frappe.call failed: {e}")
                
        except Exception as e:
            print(f"❌ Overall diagnostic failed: {e}")
            import traceback
            traceback.print_exc()
            
        # This test should always pass to show results
        self.assertTrue(True, "Diagnostic completed")

if __name__ == '__main__':
    unittest.main()