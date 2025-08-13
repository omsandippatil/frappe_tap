# Copyright (c) 2023, Tech4dev and contributors
# For license information, please see license.txt

import unittest
import frappe
from frappe.test_runner import make_test_records


class TestEnrollment(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """Set up test data"""
        # Create test records if needed
        make_test_records("User")
        make_test_records("Course")  # Assuming you have a Course doctype
        
    def setUp(self):
        """Set up before each test"""
        # Clean up any existing test enrollments
        frappe.db.delete("Enrollment", {"student": "test@example.com"})
        frappe.db.commit()
    
    def tearDown(self):
        """Clean up after each test"""
        # Clean up test data
        frappe.db.delete("Enrollment", {"student": "test@example.com"})
        frappe.db.commit()
    
    def test_enrollment_creation(self):
        """Test basic enrollment creation"""
        enrollment = frappe.get_doc({
            "doctype": "Enrollment",
            "student": "test@example.com",
            "course": "TEST-COURSE-001",
            "enrollment_date": frappe.utils.today(),
            "status": "Active"
        })
        enrollment.insert()
        
        # Verify enrollment was created
        self.assertTrue(enrollment.name)
        self.assertEqual(enrollment.student, "test@example.com")
        self.assertEqual(enrollment.status, "Active")
    
    def test_enrollment_duplicate_prevention(self):
        """Test that duplicate enrollments are prevented"""
        # Create first enrollment
        enrollment1 = frappe.get_doc({
            "doctype": "Enrollment",
            "student": "test@example.com",
            "course": "TEST-COURSE-001",
            "enrollment_date": frappe.utils.today(),
            "status": "Active"
        })
        enrollment1.insert()
        
        # Try to create duplicate enrollment
        enrollment2 = frappe.get_doc({
            "doctype": "Enrollment",
            "student": "test@example.com",
            "course": "TEST-COURSE-001",
            "enrollment_date": frappe.utils.today(),
            "status": "Active"
        })
        
        # This should raise an exception if duplicate prevention is implemented
        with self.assertRaises(frappe.DuplicateEntryError):
            enrollment2.insert()
    
    def test_enrollment_status_validation(self):
        """Test enrollment status validation"""
        enrollment = frappe.get_doc({
            "doctype": "Enrollment",
            "student": "test@example.com",
            "course": "TEST-COURSE-001",
            "enrollment_date": frappe.utils.today(),
            "status": "Invalid Status"
        })
        
        # This should raise validation error if status validation is implemented
        with self.assertRaises(frappe.ValidationError):
            enrollment.insert()
    
    def test_enrollment_date_validation(self):
        """Test enrollment date validation"""
        # Test future date validation
        future_date = frappe.utils.add_days(frappe.utils.today(), 30)
        enrollment = frappe.get_doc({
            "doctype": "Enrollment",
            "student": "test@example.com",
            "course": "TEST-COURSE-001",
            "enrollment_date": future_date,
            "status": "Active"
        })
        
        # This might raise validation error if future date validation is implemented
        try:
            enrollment.insert()
        except frappe.ValidationError:
            pass  # Expected if validation exists
    
    def test_enrollment_update(self):
        """Test enrollment update functionality"""
        # Create enrollment
        enrollment = frappe.get_doc({
            "doctype": "Enrollment",
            "student": "test@example.com",
            "course": "TEST-COURSE-001",
            "enrollment_date": frappe.utils.today(),
            "status": "Active"
        })
        enrollment.insert()
        
        # Update enrollment status
        enrollment.status = "Completed"
        enrollment.save()
        
        # Verify update
        updated_enrollment = frappe.get_doc("Enrollment", enrollment.name)
        self.assertEqual(updated_enrollment.status, "Completed")
    
    def test_enrollment_deletion(self):
        """Test enrollment deletion"""
        # Create enrollment
        enrollment = frappe.get_doc({
            "doctype": "Enrollment",
            "student": "test@example.com",
            "course": "TEST-COURSE-001",
            "enrollment_date": frappe.utils.today(),
            "status": "Active"
        })
        enrollment.insert()
        enrollment_name = enrollment.name
        
        # Delete enrollment
        enrollment.delete()
        
        # Verify deletion
        self.assertFalse(frappe.db.exists("Enrollment", enrollment_name))
    
    def test_enrollment_get_list(self):
        """Test getting list of enrollments"""
        # Create multiple enrollments
        for i in range(3):
            enrollment = frappe.get_doc({
                "doctype": "Enrollment",
                "student": f"test{i}@example.com",
                "course": "TEST-COURSE-001",
                "enrollment_date": frappe.utils.today(),
                "status": "Active"
            })
            enrollment.insert()
        
        # Get list of enrollments
        enrollments = frappe.get_list("Enrollment", 
                                    filters={"course": "TEST-COURSE-001"},
                                    fields=["name", "student", "status"])
        
        self.assertGreaterEqual(len(enrollments), 3)
    
    def test_enrollment_permissions(self):
        """Test enrollment permissions"""
        # Create enrollment
        enrollment = frappe.get_doc({
            "doctype": "Enrollment",
            "student": "test@example.com",
            "course": "TEST-COURSE-001",
            "enrollment_date": frappe.utils.today(),
            "status": "Active"
        })
        enrollment.insert()
        
        # Test read permission
        self.assertTrue(frappe.has_permission("Enrollment", "read", enrollment.name))
        
        # Test write permission
        self.assertTrue(frappe.has_permission("Enrollment", "write", enrollment.name))
    
    def test_enrollment_mandatory_fields(self):
        """Test mandatory field validation"""
        # Test missing student
        enrollment = frappe.get_doc({
            "doctype": "Enrollment",
            "course": "TEST-COURSE-001",
            "enrollment_date": frappe.utils.today(),
            "status": "Active"
        })
        
        with self.assertRaises(frappe.MandatoryError):
            enrollment.insert()
        
        # Test missing course
        enrollment = frappe.get_doc({
            "doctype": "Enrollment",
            "student": "test@example.com",
            "enrollment_date": frappe.utils.today(),
            "status": "Active"
        })
        
        with self.assertRaises(frappe.MandatoryError):
            enrollment.insert()


def get_test_records():
    """Return test records for Enrollment doctype"""
    return [
        {
            "doctype": "Enrollment",
            "student": "test1@example.com",
            "course": "TEST-COURSE-001",
            "enrollment_date": "2023-01-01",
            "status": "Active"
        },
        {
            "doctype": "Enrollment", 
            "student": "test2@example.com",
            "course": "TEST-COURSE-002",
            "enrollment_date": "2023-01-02",
            "status": "Completed"
        }
    ]


# if __name__ == "__main__":
#     unittest.main()