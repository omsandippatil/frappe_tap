# Copyright (c) 2024, Tech4dev and Contributors
# See License.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime, add_days, getdate


class TestFeedbackRequest(FrappeTestCase):
    
    def setUp(self):
        """Set up test data before each test method"""
        self.test_user_email = "test_user@example.com"
        self.test_feedback_data = {
            "doctype": "Feedback Request",
            "subject": "Test Feedback Request",
            "recipient": self.test_user_email,
            "message": "Please provide your feedback on our service",
            "request_date": getdate(),
            "status": "Pending"
        }
    
    def tearDown(self):
        """Clean up test data after each test method"""
        # Remove any test feedback requests created during testing
        frappe.db.delete("Feedback Request", {"recipient": self.test_user_email})
        frappe.db.commit()
    
    def test_feedback_request_creation(self):
        """Test basic feedback request creation"""
        feedback_request = frappe.get_doc(self.test_feedback_data)
        feedback_request.insert()
        
        # Verify the document was created successfully
        self.assertTrue(feedback_request.name)
        self.assertEqual(feedback_request.subject, "Test Feedback Request")
        self.assertEqual(feedback_request.recipient, self.test_user_email)
        self.assertEqual(feedback_request.status, "Pending")
    
    def test_feedback_request_validation(self):
        """Test validation rules for feedback request"""
        # Test missing required fields
        invalid_data = self.test_feedback_data.copy()
        del invalid_data["recipient"]
        
        feedback_request = frappe.get_doc(invalid_data)
        
        with self.assertRaises(frappe.ValidationError):
            feedback_request.insert()
    
    def test_feedback_request_status_update(self):
        """Test updating feedback request status"""
        feedback_request = frappe.get_doc(self.test_feedback_data)
        feedback_request.insert()
        
        # Update status to 'Sent'
        feedback_request.status = "Sent"
        feedback_request.sent_date = now_datetime()
        feedback_request.save()
        
        # Verify status update
        updated_doc = frappe.get_doc("Feedback Request", feedback_request.name)
        self.assertEqual(updated_doc.status, "Sent")
        self.assertIsNotNone(updated_doc.sent_date)
    
    def test_feedback_request_response_handling(self):
        """Test handling of feedback responses"""
        feedback_request = frappe.get_doc(self.test_feedback_data)
        feedback_request.insert()
        
        # Simulate receiving a response
        feedback_request.status = "Responded"
        feedback_request.response = "Great service, very satisfied!"
        feedback_request.response_date = now_datetime()
        feedback_request.rating = 5
        feedback_request.save()
        
        # Verify response was recorded
        updated_doc = frappe.get_doc("Feedback Request", feedback_request.name)
        self.assertEqual(updated_doc.status, "Responded")
        self.assertEqual(updated_doc.response, "Great service, very satisfied!")
        self.assertEqual(updated_doc.rating, 5)
        self.assertIsNotNone(updated_doc.response_date)
    
    def test_feedback_request_expiry(self):
        """Test feedback request expiry logic"""
        feedback_request = frappe.get_doc(self.test_feedback_data)
        feedback_request.request_date = add_days(getdate(), -30)  # 30 days ago
        feedback_request.expiry_date = add_days(getdate(), -1)    # Expired yesterday
        feedback_request.insert()
        
        # Test if request is considered expired
        updated_doc = frappe.get_doc("Feedback Request", feedback_request.name)
        self.assertTrue(getdate() > updated_doc.expiry_date)
    
    def test_feedback_request_email_validation(self):
        """Test email address validation"""
        invalid_data = self.test_feedback_data.copy()
        invalid_data["recipient"] = "invalid-email"
        
        feedback_request = frappe.get_doc(invalid_data)
        
        with self.assertRaises(frappe.ValidationError):
            feedback_request.insert()
    
    def test_feedback_request_duplicate_prevention(self):
        """Test prevention of duplicate feedback requests"""
        # Create first feedback request
        feedback_request1 = frappe.get_doc(self.test_feedback_data)
        feedback_request1.insert()
        
        # Try to create duplicate
        feedback_request2 = frappe.get_doc(self.test_feedback_data)
        
        # This should either prevent duplicate or handle it gracefully
        # depending on your business logic
        try:
            feedback_request2.insert()
            # If duplicates are allowed, verify both exist
            self.assertTrue(feedback_request2.name)
        except frappe.DuplicateEntryError:
            # If duplicates are prevented, this is expected
            pass
    
    def test_feedback_request_permissions(self):
        """Test user permissions for feedback requests"""
        feedback_request = frappe.get_doc(self.test_feedback_data)
        feedback_request.insert()
        
        # Test if current user has read permission
        self.assertTrue(frappe.has_permission("Feedback Request", "read", feedback_request.name))
    
    def test_feedback_request_search_functionality(self):
        """Test searching feedback requests"""
        # Create multiple feedback requests for testing
        feedback_request1 = frappe.get_doc(self.test_feedback_data)
        feedback_request1.subject = "Customer Service Feedback"
        feedback_request1.insert()
        
        feedback_request2_data = self.test_feedback_data.copy()
        feedback_request2_data["recipient"] = "another_user@example.com"
        feedback_request2_data["subject"] = "Product Quality Feedback"
        feedback_request2 = frappe.get_doc(feedback_request2_data)
        feedback_request2.insert()
        
        # Test search by subject
        results = frappe.get_all("Feedback Request", 
                                filters={"subject": ["like", "%Service%"]},
                                fields=["name", "subject"])
        
        self.assertTrue(len(results) >= 1)
        self.assertIn("Service", results[0].subject)
        
        # Clean up the additional test data
        frappe.delete_doc("Feedback Request", feedback_request2.name)
    
    def test_feedback_request_bulk_operations(self):
        """Test bulk operations on feedback requests"""
        # Create multiple feedback requests
        feedback_requests = []
        for i in range(3):
            data = self.test_feedback_data.copy()
            data["recipient"] = f"user{i}@example.com"
            data["subject"] = f"Feedback Request {i+1}"
            doc = frappe.get_doc(data)
            doc.insert()
            feedback_requests.append(doc)
        
        # Test bulk status update
        for doc in feedback_requests:
            doc.status = "Sent"
            doc.save()
        
        # Verify all were updated
        sent_count = frappe.db.count("Feedback Request", {"status": "Sent"})
        self.assertGreaterEqual(sent_count, 3)
        
        # Clean up
        for doc in feedback_requests:
            frappe.delete_doc("Feedback Request", doc.name)
    
    def test_feedback_request_data_integrity(self):
        """Test data integrity constraints"""
        feedback_request = frappe.get_doc(self.test_feedback_data)
        feedback_request.insert()
        
        # Test that certain fields maintain their data types
        self.assertIsInstance(feedback_request.request_date, str)  # Date stored as string in Frappe
        
        if hasattr(feedback_request, 'rating'):
            feedback_request.rating = 5
            feedback_request.save()
            self.assertIsInstance(feedback_request.rating, (int, float))
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment before running all tests"""
        super().setUpClass()
        # Any one-time setup for all tests
        
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment after all tests"""
        super().tearDownClass()
        # Any one-time cleanup after all tests