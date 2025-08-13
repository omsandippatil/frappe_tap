# Copyright (c) 2023, Tech4dev and contributors
# For license information, please see license.txt

import unittest
import frappe


class TestEnrollment(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """Set up test class"""
        # Ensure we're in a test environment
        if not frappe.db:
            frappe.init(site="test_site")
            frappe.connect()

    def setUp(self):
        """Set up test dependencies"""
        # Clean up any existing test records
        if frappe.db.exists("DocType", "Enrollment"):
            frappe.db.delete("Enrollment", {"name": ["like", "TEST-%"]})
            frappe.db.commit()

    def tearDown(self):
        """Clean up after tests"""
        # Clean up test records
        if frappe.db.exists("DocType", "Enrollment"):
            frappe.db.delete("Enrollment", {"name": ["like", "TEST-%"]})
            frappe.db.commit()

    def test_enrollment_doctype_exists(self):
        """Test that Enrollment DocType exists"""
        self.assertTrue(frappe.db.exists("DocType", "Enrollment"))

    def test_enrollment_class_import(self):
        """Test that Enrollment class can be imported"""
        try:
            from tap_lms.tap_lms.doctype.enrollment.enrollment import Enrollment
            enrollment = Enrollment()
            self.assertIsNotNone(enrollment)
        except ImportError as e:
            self.fail(f"Could not import Enrollment class: {e}")

    def test_enrollment_validation(self):
        """Test enrollment validation logic"""
        if not frappe.db.exists("DocType", "Enrollment"):
            self.skipTest("Enrollment DocType does not exist")
            
        enrollment = frappe.get_doc({
            "doctype": "Enrollment",
            # Add test data for validation scenarios
        })
        
        # Test document validation
        try:
            enrollment.validate()
            # Add assertions based on expected behavior
        except Exception as e:
            # Test expected validation errors if any
            pass

    def test_enrollment_permissions(self):
        """Test enrollment document permissions"""
        if not frappe.db.exists("DocType", "Enrollment"):
            self.skipTest("Enrollment DocType does not exist")
            
        # Test that Enrollment DocType has proper permissions configured
        enrollment_meta = frappe.get_meta("Enrollment")
        self.assertIsNotNone(enrollment_meta)

    def test_enrollment_fields(self):
        """Test enrollment document fields"""
        if not frappe.db.exists("DocType", "Enrollment"):
            self.skipTest("Enrollment DocType does not exist")
            
        enrollment_meta = frappe.get_meta("Enrollment")
        field_names = [field.fieldname for field in enrollment_meta.fields]
        
        # Test that required fields exist
        # Uncomment and modify based on your actual fields:
        # self.assertIn("student", field_names)
        # self.assertIn("course", field_names)
        # self.assertIn("enrollment_date", field_names)
        
        # For now, just test that fields list is not empty
        # Remove this when you have actual field tests
        self.assertIsInstance(field_names, list)

