# test_onboardingstage.py
"""
Simple test for OnboardingStage to achieve 100% coverage
No external dependencies except the module itself
"""

import unittest
import sys
import os

# Add the app path to sys.path if needed
sys.path.insert(0, '/home/frappe/frappe-bench/apps/tap_lms')


class TestOnboardingStage(unittest.TestCase):
    """Simple unittest class for OnboardingStage coverage"""
    
    
    def test_class_attributes(self):
        """Test class attributes and inheritance"""
        from tap_lms.tap_lms.doctype.onboardingstage.onboardingstage import OnboardingStage
        
        # Check inheritance
        self.assertTrue(hasattr(OnboardingStage, '__bases__'))
        
        # The class should have Document as base class
        base_class_names = [base.__name__ for base in OnboardingStage.__bases__]
        self.assertIn('Document', base_class_names)

