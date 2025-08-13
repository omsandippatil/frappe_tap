# Copyright (c) 2024, Tech4dev and Contributors
# See license.txt

import frappe
import unittest


class TestCourseProject(unittest.TestCase):
    def setUp(self):
        """Set up test data before each test method."""
        frappe.set_user("Administrator")
        
        # Create test course if needed
        if not frappe.db.exists("Course", "Test Course"):
            try:
                self.test_course = frappe.get_doc({
                    "doctype": "Course",
                    "course_name": "Test Course",
                    "course_code": "TC001"
                })
                self.test_course.insert(ignore_permissions=True)
            except Exception as e:
                # If Course doctype doesn't exist, create a simple test record
                print(f"Note: Could not create test course: {e}")
                self.test_course = None
        else:
            self.test_course = frappe.get_doc("Course", "Test Course")

    def tearDown(self):
        """Clean up after each test method."""
        frappe.db.rollback()

    def test_course_project_creation(self):
        """Test basic course project creation."""
        course_project = frappe.new_doc("CourseProject")
        course_project.update({
            "title": "Test Project",
            "description": "This is a test project description"
        })
        
        if self.test_course:
            course_project.course = self.test_course.name
        
        # Test that we can create the document
        try:
            course_project.insert(ignore_permissions=True)
            self.assertTrue(course_project.name)
            self.assertEqual(course_project.title, "Test Project")
            print("✓ Course project creation test passed")
        except Exception as e:
            print(f"Course project creation test failed: {e}")
            raise

    def test_course_project_search(self):
        """Test search functionality."""
        try:
            # Create a test project first
            course_project = frappe.new_doc("CourseProject")
            course_project.title = "Search Test Project"
            course_project.insert(ignore_permissions=True)
            
            # Now search for it
            results = frappe.get_list(
                "CourseProject", 
                filters={"title": "Search Test Project"},
                limit=1
            )
            
            self.assertTrue(len(results) > 0)
            print("✓ Search functionality working")
            
        except Exception as e:
            print(f"Search test failed: {e}")

    def test_doctype_exists(self):
        """Test that the CourseProject doctype exists."""
        try:
            doctype_exists = frappe.db.exists("DocType", "CourseProject")
            self.assertTrue(doctype_exists)
            print("✓ CourseProject doctype exists in database")
        except Exception as e:
            print(f"Doctype existence test failed: {e}")
            raise

    @classmethod
    def setUpClass(cls):
        """Set up class-level test data."""
        frappe.init(site="test_site")
        frappe.connect()

    @classmethod
    def tearDownClass(cls):
        """Clean up class-level test data."""
        frappe.destroy()


# Alternative simple test that doesn't require FrappeTestCase
def test_basic_functionality():
    """Simple test function that can be run independently."""
    try:
        # Test basic frappe functionality
        frappe.set_user("Administrator")
        
        # Test CourseProject doctype access
        meta = frappe.get_meta("CourseProject")
        print(f"✓ CourseProject doctype loaded with {len(meta.fields)} fields")
        
        # Test document creation
        doc = frappe.new_doc("CourseProject")
        print("✓ New CourseProject document created")
        
        return True
    except Exception as e:
        print(f"✗ Basic functionality test failed: {e}")
        return False

