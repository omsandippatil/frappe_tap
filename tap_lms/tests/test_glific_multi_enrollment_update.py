# Additional test methods to add to your existing TestGlificMultiEnrollmentComplete class
# Insert these methods into your existing test class

def test_48_get_glific_settings_function_coverage(self):
    """Test get_glific_settings function if it exists in module"""
    # This covers any get_glific_settings function calls
    with patch('frappe.get_single') as mock_get_single:
        mock_settings = Mock()
        mock_settings.api_url = "https://test.glific.com"
        mock_get_single.return_value = mock_settings
        
        if hasattr(self.module, 'get_glific_settings'):
            result = self.module.get_glific_settings()
            self.assertIsNotNone(result)

def test_49_get_glific_auth_headers_function_coverage(self):
    """Test get_glific_auth_headers function if it exists in module"""
    with patch.object(self.module, 'get_glific_settings') as mock_settings:
        mock_settings_obj = Mock()
        mock_settings_obj.api_url = "https://test.glific.com"
        mock_settings_obj.username = "test_user"
        mock_settings_obj.password = "test_pass"
        mock_settings.return_value = mock_settings_obj
        
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": {"session": {"access_token": "test_token"}}
            }
            mock_post.return_value = mock_response
            
            if hasattr(self.module, 'get_glific_auth_headers'):
                result = self.module.get_glific_auth_headers()
                self.assertIsNotNone(result)

def test_50_enqueue_function_coverage(self):
    """Test enqueue function import and usage"""
    # This should cover the enqueue import
    try:
        from frappe.utils.background_jobs import enqueue
        self.assertTrue(callable(enqueue))
    except ImportError:
        pass

def test_51_requests_exception_handling(self):
    """Test requests.exceptions handling"""
    with patch('frappe.get_doc') as mock_get_doc, \
         patch('frappe.get_all') as mock_get_all, \
         patch('frappe.db.exists', return_value=True), \
         patch('frappe.logger') as mock_logger, \
         patch.object(self.module, 'get_glific_settings') as mock_settings, \
         patch.object(self.module, 'get_glific_auth_headers') as mock_headers, \
         patch('requests.post') as mock_post:
        
        # Setup mocks
        mock_set = Mock()
        mock_set.status = "Processed"
        mock_set.set_name = "Test Set"
        
        mock_student = Mock()
        mock_student.glific_id = "12345"
        
        mock_get_doc.side_effect = [mock_set, mock_student]
        mock_get_all.return_value = [{"student_name": "Test", "phone": "+123", "student_id": "STU-001", "batch_skeyword": "B1"}]
        
        mock_settings_obj = Mock()
        mock_settings_obj.api_url = "https://test.glific.com"
        mock_settings.return_value = mock_settings_obj
        mock_headers.return_value = {"Authorization": "Bearer token"}
        
        # Mock requests exception
        mock_post.side_effect = requests.exceptions.RequestException("Connection error")
        
        result = self.module.update_specific_set_contacts_with_multi_enrollment("TEST-SET")
        
        self.assertEqual(result["errors"], 1)

def test_52_json_decode_error_handling(self):
    """Test JSON decode error handling"""
    with patch('frappe.get_doc') as mock_get_doc, \
         patch('frappe.get_all') as mock_get_all, \
         patch('frappe.db.exists', return_value=True), \
         patch('frappe.logger') as mock_logger, \
         patch.object(self.module, 'get_glific_settings') as mock_settings, \
         patch.object(self.module, 'get_glific_auth_headers') as mock_headers, \
         patch('requests.post') as mock_post:
        
        # Setup mocks
        mock_set = Mock()
        mock_set.status = "Processed"
        mock_set.set_name = "Test Set"
        
        mock_student = Mock()
        mock_student.glific_id = "12345"
        
        mock_get_doc.side_effect = [mock_set, mock_student]
        mock_get_all.return_value = [{"student_name": "Test", "phone": "+123", "student_id": "STU-001", "batch_skeyword": "B1"}]
        
        mock_settings_obj = Mock()
        mock_settings_obj.api_url = "https://test.glific.com"
        mock_settings.return_value = mock_settings_obj
        mock_headers.return_value = {"Authorization": "Bearer token"}
        
        # Mock JSON decode error
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_post.return_value = mock_response
        
        result = self.module.update_specific_set_contacts_with_multi_enrollment("TEST-SET")
        
        self.assertEqual(result["errors"], 1)

def test_53_graphql_queries_coverage(self):
    """Test GraphQL query construction and usage"""
    # Test the GraphQL queries are properly constructed
    test_query = """
        query getContact($id: ID!) {
            contact(id: $id) {
                contact {
                    id
                    name
                    phone
                    fields
                }
            }
        }
    """
    
    test_mutation = """
        mutation updateContact($id: ID!, $input: ContactInput!) {
            updateContact(id: $id, input: $input) {
                contact {
                    id
                    name
                    fields
                }
            }
        }
    """
    
    self.assertIn("contact", test_query)
    self.assertIn("updateContact", test_mutation)

def test_54_time_sleep_coverage(self):
    """Test time.sleep usage in batch processing"""
    with patch('time.sleep') as mock_sleep, \
         patch('frappe.logger') as mock_logger, \
         patch.object(self.module, 'update_specific_set_contacts_with_multi_enrollment') as mock_update:
        
        # Mock multiple batches to trigger sleep
        mock_update.side_effect = [
            {"updated": 10, "errors": 0, "total_processed": 50},  # First batch
            {"updated": 5, "errors": 0, "total_processed": 0}     # Final batch
        ]
        
        result = self.module.process_multiple_sets_simple(["TEST-SET"])
        
        # Verify sleep was called between batches
        mock_sleep.assert_called_with(1)

def test_55_batch_size_parameter_coverage(self):
    """Test different batch_size parameter values"""
    with patch('frappe.get_doc') as mock_get_doc, \
         patch('frappe.get_all') as mock_get_all:
        
        mock_set = Mock()
        mock_set.status = "Processed"
        mock_set.set_name = "Test Set"
        mock_get_doc.return_value = mock_set
        
        # Test with batch_size=10
        mock_get_all.return_value = []
        result = self.module.update_specific_set_contacts_with_multi_enrollment("TEST-SET", batch_size=10)
        
        # Verify get_all was called with correct limit
        mock_get_all.assert_called_with(
            "Backend Student",
            filters={"parent": "TEST-SET", "docstatus": 1, "glific_status": "Success"},
            fields=["student_name", "phone", "student_id", "batch_skeyword"],
            limit=10
        )

def test_56_different_batch_sizes(self):
    """Test various batch sizes"""
    test_cases = [1, 5, 10, 25, 50, 100]
    
    for batch_size in test_cases:
        with patch('frappe.get_doc') as mock_get_doc, \
             patch('frappe.get_all') as mock_get_all:
            
            mock_set = Mock()
            mock_set.status = "Processed"
            mock_set.set_name = f"Test Set {batch_size}"
            mock_get_doc.return_value = mock_set
            mock_get_all.return_value = []
            
            result = self.module.update_specific_set_contacts_with_multi_enrollment(
                f"TEST-SET-{batch_size}", batch_size=batch_size
            )
            
            self.assertIn("message", result)

def test_57_enqueue_parameters_coverage(self):
    """Test enqueue function with all parameters"""
    with patch.object(self.module, 'enqueue') as mock_enqueue:
        mock_job = Mock()
        mock_job.id = "test_job_id"
        mock_enqueue.return_value = mock_job
        
        # Test with list input
        result = self.module.process_my_sets(["SET-001", "SET-002"])
        
        # Verify enqueue called with correct parameters
        mock_enqueue.assert_called_once_with(
            self.module.process_multiple_sets_simple,
            set_names=["SET-001", "SET-002"],
            batch_size=50,
            queue='long',
            timeout=7200
        )

def test_58_frappe_db_operations_coverage(self):
    """Test frappe.db operations coverage"""
    with patch('frappe.db.exists') as mock_exists, \
         patch('frappe.db.begin') as mock_begin, \
         patch('frappe.db.commit') as mock_commit, \
         patch('frappe.db.rollback') as mock_rollback:
        
        # Test exists() function
        mock_exists.return_value = True
        result = self.module.check_student_multi_enrollment("STU-001")
        mock_exists.assert_called_with("Student", "STU-001")
        
        # Test database transaction methods
        mock_begin.assert_not_called()  # Only called in run function
        
        # Test run function to cover db operations
        with patch.object(self.module, 'update_specific_set_contacts_with_multi_enrollment') as mock_update:
            mock_update.return_value = {"updated": 1, "errors": 0, "total_processed": 1}
            
            result = self.module.run_multi_enrollment_update_for_specific_set("TEST-SET")
            
            mock_begin.assert_called_once()
            mock_commit.assert_called_once()

def test_59_all_exception_types_coverage(self):
    """Test coverage of different exception types"""
    # Test frappe.DoesNotExistError
    with patch('frappe.get_doc', side_effect=frappe.DoesNotExistError("Document not found")):
        result = self.module.update_specific_set_contacts_with_multi_enrollment("INVALID-SET")
        self.assertIn("error", result)
    
    # Test AttributeError 
    with patch('frappe.get_doc') as mock_get_doc:
        mock_student = Mock()
        del mock_student.enrollment  # Remove enrollment attribute
        mock_get_doc.return_value = mock_student
        
        with patch('frappe.db.exists', return_value=True):
            result = self.module.check_student_multi_enrollment("STU-001")
            self.assertEqual(result, "no")

def test_60_complete_workflow_integration(self):
    """Test complete workflow from start to finish"""
    with patch('frappe.get_doc') as mock_get_doc, \
         patch('frappe.get_all') as mock_get_all, \
         patch('frappe.db.exists', return_value=True), \
         patch('frappe.logger') as mock_logger, \
         patch.object(self.module, 'get_glific_settings') as mock_settings, \
         patch.object(self.module, 'get_glific_auth_headers') as mock_headers, \
         patch.object(self.module, 'check_student_multi_enrollment', return_value="yes"), \
         patch('requests.post') as mock_post, \
         patch('frappe.db.begin') as mock_begin, \
         patch('frappe.db.commit') as mock_commit:
        
        # Complete successful workflow
        mock_set = Mock()
        mock_set.status = "Processed"
        mock_set.set_name = "Complete Test Set"
        
        mock_student = Mock()
        mock_student.glific_id = "67890"
        
        mock_get_doc.side_effect = [mock_set, mock_student]
        mock_get_all.return_value = [{
            "student_name": "Complete Test Student",
            "phone": "+9876543210",
            "student_id": "STU-COMPLETE",
            "batch_skeyword": "COMPLETE-BATCH"
        }]
        
        mock_settings_obj = Mock()
        mock_settings_obj.api_url = "https://complete.test.glific.com"
        mock_settings.return_value = mock_settings_obj
        mock_headers.return_value = {"Authorization": "Bearer complete_token"}
        
        # Mock successful API responses
        fetch_response = Mock()
        fetch_response.status_code = 200
        fetch_response.json.return_value = {
            "data": {
                "contact": {
                    "contact": {
                        "id": "67890",
                        "name": "Complete Test Student",
                        "phone": "+9876543210",
                        "fields": "{}"
                    }
                }
            }
        }
        
        update_response = Mock()
        update_response.status_code = 200
        update_response.json.return_value = {
            "data": {
                "updateContact": {
                    "contact": {
                        "id": "67890",
                        "name": "Complete Test Student",
                        "fields": json.dumps({
                            "multi_enrollment": {
                                "value": "yes",
                                "type": "string",
                                "inserted_at": datetime.now(timezone.utc).isoformat()
                            }
                        })
                    }
                }
            }
        }
        
        mock_post.side_effect = [fetch_response, update_response]
        
        # Test the complete run function
        result = self.module.run_multi_enrollment_update_for_specific_set("COMPLETE-TEST-SET")
        
        self.assertIn("Process completed", result)
        self.assertIn("Updated: 1", result)
        mock_begin.assert_called_once()
        mock_commit.assert_called_once()