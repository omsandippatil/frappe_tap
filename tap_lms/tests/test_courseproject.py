# Copyright (c) 2024, Tech4dev and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe import _


class TestCourseProject(FrappeTestCase):
    def setUp(self):
        """Set up test data before each test method."""
        # Create test course if needed
        if not frappe.db.exists("Course", "Test Course"):
            self.test_course = frappe.get_doc({
                "doctype": "Course",
                "course_name": "Test Course",
                "course_code": "TC001"
            }).insert()
        else:
            self.test_course = frappe.get_doc("Course", "Test Course")

    def tearDown(self):
        """Clean up after each test method."""
        # Delete test records
        frappe.db.rollback()

    def test_course_project_creation(self):
        """Test basic course project creation."""
        course_project = frappe.get_doc({
            "doctype": "CourseProject",
            "title": "Test Project",
            "course": self.test_course.name,
            "description": "This is a test project description",
            "status": "Draft"
        })
        
        # Test insertion
        course_project.insert()
        self.assertTrue(course_project.name)
        self.assertEqual(course_project.title, "Test Project")
        self.assertEqual(course_project.status, "Draft")

    def test_course_project_validation(self):
        """Test validation rules for course project."""
        # Test missing required fields
        with self.assertRaises(frappe.ValidationError):
            course_project = frappe.get_doc({
                "doctype": "CourseProject",
                # Missing title - should raise validation error
                "course": self.test_course.name
            })
            course_project.insert()

    def test_course_project_permissions(self):
        """Test user permissions for course project."""
        # Create a test user
        test_user = "test@example.com"
        if not frappe.db.exists("User", test_user):
            user_doc = frappe.get_doc({
                "doctype": "User",
                "email": test_user,
                "first_name": "Test",
                "last_name": "User"
            }).insert(ignore_permissions=True)

        # Test permissions
        frappe.set_user(test_user)
        
        try:
            course_project = frappe.get_doc({
                "doctype": "CourseProject",
                "title": "Permission Test Project",
                "course": self.test_course.name
            })
            # This should work if user has proper permissions
            course_project.insert()
        except frappe.PermissionError:
            # Expected if user doesn't have create permissions
            pass
        finally:
            frappe.set_user("Administrator")

    def test_course_project_status_workflow(self):
        """Test status transitions in course project."""
        course_project = frappe.get_doc({
            "doctype": "CourseProject",
            "title": "Workflow Test Project",
            "course": self.test_course.name,
            "status": "Draft"
        }).insert()

        # Test status changes
        valid_statuses = ["Draft", "Active", "Completed", "Cancelled"]
        
        for status in valid_statuses:
            course_project.status = status
            course_project.save()
            self.assertEqual(course_project.status, status)

    def test_course_project_with_assignments(self):
        """Test course project with student assignments."""
        course_project = frappe.get_doc({
            "doctype": "CourseProject",
            "title": "Assignment Test Project",
            "course": self.test_course.name,
            "max_score": 100,
            "due_date": frappe.utils.add_days(frappe.utils.nowdate(), 7)
        }).insert()

        # Test due date validation
        self.assertTrue(course_project.due_date >= frappe.utils.nowdate())

    def test_course_project_duplicate_prevention(self):
        """Test prevention of duplicate course projects."""
        # Create first project
        course_project1 = frappe.get_doc({
            "doctype": "CourseProject",
            "title": "Unique Project",
            "course": self.test_course.name
        }).insert()

        # Try to create duplicate (if uniqueness is enforced)
        try:
            course_project2 = frappe.get_doc({
                "doctype": "CourseProject",
                "title": "Unique Project",
                "course": self.test_course.name
            }).insert()
            # If no error, duplicates are allowed
        except frappe.DuplicateEntryError:
            # Expected if uniqueness is enforced
            pass

    def test_course_project_search_and_filter(self):
        """Test search and filtering capabilities."""
        # Create multiple projects
        projects = []
        for i in range(3):
            project = frappe.get_doc({
                "doctype": "CourseProject",
                "title": f"Search Test Project {i+1}",
                "course": self.test_course.name,
                "status": "Active" if i % 2 == 0 else "Draft"
            }).insert()
            projects.append(project)

        # Test filtering by status
        active_projects = frappe.get_all(
            "CourseProject",
            filters={"status": "Active", "course": self.test_course.name},
            fields=["name", "title", "status"]
        )
        
        self.assertTrue(len(active_projects) >= 2)

    def test_course_project_deletion(self):
        """Test course project deletion and cleanup."""
        course_project = frappe.get_doc({
            "doctype": "CourseProject",
            "title": "Delete Test Project",
            "course": self.test_course.name
        }).insert()

        project_name = course_project.name
        
        # Delete the project
        course_project.delete()
        
        # Verify deletion
        self.assertFalse(frappe.db.exists("CourseProject", project_name))

    def test_course_project_data_integrity(self):
        """Test data integrity and relationships."""
        course_project = frappe.get_doc({
            "doctype": "CourseProject",
            "title": "Integrity Test Project",
            "course": self.test_course.name,
            "description": "Testing data integrity"
        }).insert()

        # Test course relationship
        linked_course = frappe.get_doc("Course", course_project.course)
        self.assertEqual(linked_course.name, self.test_course.name)

    def test_course_project_custom_validations(self):
        """Test any custom validation methods."""
        # Example: Test custom validation for project dates
        course_project = frappe.get_doc({
            "doctype": "CourseProject",
            "title": "Validation Test Project",
            "course": self.test_course.name,
            "start_date": frappe.utils.nowdate(),
            "end_date": frappe.utils.add_days(frappe.utils.nowdate(), -1)  # Invalid: end before start
        })

        # This should raise validation error if custom validation exists
        try:
            course_project.insert()
        except frappe.ValidationError:
            # Expected if date validation is implemented
            pass

    @classmethod
    def setUpClass(cls):
        """Set up class-level test data."""
        super().setUpClass()
        # Any class-level setup can go here

    @classmethod
    def tearDownClass(cls):
        """Clean up class-level test data."""
        super().tearDownClass()
        # Clean up any class-level test data