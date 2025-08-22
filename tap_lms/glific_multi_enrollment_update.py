# # glific_multi_enrollment_update.py
# # New file to handle updating existing Glific contacts with multi_enrollment field for specific Backend Student Onboarding sets

# import frappe
# import requests
# import json
# from datetime import datetime, timezone
# from .glific_integration import get_glific_settings, get_glific_auth_headers
# import time
# from frappe.utils.background_jobs import enqueue


# def check_student_multi_enrollment(student_name):
#     """
#     Check if a student has multiple enrollments
#     Returns 'yes' if student has enrollments, 'no' otherwise
#     """
#     try:
#         # Check if student exists first to avoid transaction errors
#         if not frappe.db.exists("Student", student_name):
#             frappe.logger().error(f"Student document not found for multi_enrollment check: {student_name}")
#             return "no"
        
#         # Get the student document
#         student_doc = frappe.get_doc("Student", student_name)
        
#         # Check if the student has any enrollments in the enrollment child table
#         if student_doc.enrollment and len(student_doc.enrollment) > 1:
#             return "yes"
#         else:
#             return "no"
#     except Exception as e:
#         frappe.logger().error(f"Error checking multi_enrollment for student {student_name}: {str(e)}")
#         return "no"  # Default to "no" if there's an error

# def update_specific_set_contacts_with_multi_enrollment(onboarding_set_name, batch_size=50):
#     """
#     Update existing Glific contacts to add multi_enrollment field for a specific Backend Student Onboarding set
    
#     Args:
#         onboarding_set_name: Specific Backend Student Onboarding set name to process (required)
#     """
    
#     if not onboarding_set_name:
#         return {"error": "Backend Student Onboarding set name is required"}
    
#     # Get the specific Backend Student Onboarding set
#     try:
#         onboarding_set = frappe.get_doc("Backend Student Onboarding", onboarding_set_name)
#     except frappe.DoesNotExistError:
#         return {"error": f"Backend Student Onboarding set '{onboarding_set_name}' not found"}
    
#     if onboarding_set.status != "Processed":
#         return {"error": f"Set '{onboarding_set_name}' status is '{onboarding_set.status}', not 'Processed'"}
    
#     frappe.logger().info(f"Processing Backend Student Onboarding set: {onboarding_set.set_name}")
    
#     # Get all Backend Students from this set that were successfully processed
#     backend_students = frappe.get_all(
#         "Backend Students",
#         filters={
#             "parent": onboarding_set_name,
#             "processing_status": "Success",
#             "student_id": ["not in", ["", None]]  # Only students with valid student_id
#         },
#         fields=["student_name", "phone", "student_id", "batch_skeyword"],
#         limit=batch_size  # Add batch size limit
#     )
    
#     if not backend_students:
#         return {"message": f"No successfully processed students found in set {onboarding_set.set_name}"}
    
#     total_updated = 0
#     total_skipped = 0
#     total_errors = 0
#     total_processed = 0
    
#     # Process each backend student
#     for backend_student in backend_students:
#         try:
#             student_id = backend_student.student_id
#             student_name = backend_student.student_name
#             phone = backend_student.phone
            
#             # Get the actual Student document to get glific_id
#             try:
#                 # Check if student exists first to avoid transaction errors
#                 if not frappe.db.exists("Student", student_id):
#                     frappe.logger().error(f"Student document not found: {student_id}")
#                     total_errors += 1
#                     total_processed += 1
#                     continue
                
#                 student_doc = frappe.get_doc("Student", student_id)
#                 glific_id = student_doc.glific_id
#             except Exception as e:
#                 frappe.logger().error(f"Error getting student document {student_id}: {str(e)}")
#                 total_errors += 1
#                 total_processed += 1
#                 continue
            
#             if not glific_id:
#                 frappe.logger().warning(f"No Glific ID found for student {student_name} ({student_id})")
#                 total_errors += 1
#                 total_processed += 1
#                 continue
            
#             frappe.logger().info(f"Processing student: {student_name} (Glific ID: {glific_id})")
            
#             # Get current contact from Glific
#             settings = get_glific_settings()
#             url = f"{settings.api_url}/api"
#             headers = get_glific_auth_headers()
            
#             fetch_payload = {
#                 "query": """
#                 query contact($id: ID!) {
#                   contact(id: $id) {
#                     contact {
#                       id
#                       name
#                       phone
#                       fields
#                     }
#                   }
#                 }
#                 """,
#                 "variables": {
#                     "id": glific_id
#                 }
#             }
            
#             # Fetch current contact
#             response = requests.post(url, json=fetch_payload, headers=headers)
#             if response.status_code != 200:
#                 frappe.logger().error(f"Failed to fetch contact {glific_id} for student {student_name}")
#                 total_errors += 1
#                 total_processed += 1
#                 continue
                
#             data = response.json()
#             if "errors" in data:
#                 frappe.logger().error(f"Glific API Error fetching contact {glific_id}: {data['errors']}")
#                 total_errors += 1
#                 total_processed += 1
#                 continue
                
#             contact_data = data.get("data", {}).get("contact", {}).get("contact")
#             if not contact_data:
#                 frappe.logger().error(f"Contact not found for ID: {glific_id}")
#                 total_errors += 1
#                 total_processed += 1
#                 continue
            
#             # Parse existing fields
#             existing_fields = {}
#             if contact_data.get("fields"):
#                 try:
#                     existing_fields = json.loads(contact_data.get("fields", "{}"))
#                 except json.JSONDecodeError:
#                     frappe.logger().error(f"Failed to parse fields JSON for contact {glific_id}")
#                     existing_fields = {}
            
#             # Check if multi_enrollment field already exists
#             multi_enrollment_exists = "multi_enrollment" in existing_fields
#             if multi_enrollment_exists:
#                 old_value = existing_fields["multi_enrollment"]["value"]
#                 frappe.logger().info(f"multi_enrollment exists for contact {glific_id} with value: {old_value}")
#                 # We'll update it instead of skipping
            
#             # Get multi_enrollment value for this student
#             multi_enrollment_value = check_student_multi_enrollment(student_id)
            
#             # Log the enrollment check result
#             frappe.logger().info(f"Student {student_name} multi_enrollment value: {multi_enrollment_value}")
            
#             # Add or update multi_enrollment field
#             existing_fields["multi_enrollment"] = {
#                 "value": multi_enrollment_value,
#                 "type": "string",
#                 "inserted_at": datetime.now(timezone.utc).isoformat()
#             }
            
#             # Log what we're doing
#             if multi_enrollment_exists:
#                 if old_value != multi_enrollment_value:
#                     frappe.logger().info(f"Updating multi_enrollment for {student_name}: {old_value} → {multi_enrollment_value}")
#                 else:
#                     frappe.logger().info(f"Refreshing multi_enrollment for {student_name}: {multi_enrollment_value} (no change)")
#             else:
#                 frappe.logger().info(f"Adding multi_enrollment for {student_name}: {multi_enrollment_value}")
            
#             # Update contact with new fields
#             update_payload = {
#                 "query": """
#                 mutation updateContact($id: ID!, $input:ContactInput!) {
#                   updateContact(id: $id, input: $input) {
#                     contact {
#                       id
#                       name
#                       fields
#                     }
#                     errors {
#                       key
#                       message
#                     }
#                   }
#                 }
#                 """,
#                 "variables": {
#                     "id": glific_id,
#                     "input": {
#                         "name": contact_data.get("name", student_name),
#                         "fields": json.dumps(existing_fields)
#                     }
#                 }
#             }
            
#             # Execute update
#             update_response = requests.post(url, json=update_payload, headers=headers)
#             if update_response.status_code == 200:
#                 update_data = update_response.json()
#                 if "errors" not in update_data and update_data.get("data", {}).get("updateContact", {}).get("contact"):
#                     contact_updated = update_data.get("data", {}).get("updateContact", {}).get("contact")
                    
#                     # Check if we actually updated vs refreshed the same value
#                     if multi_enrollment_exists and old_value == multi_enrollment_value:
#                         frappe.logger().info(f"Refreshed contact {glific_id} - value unchanged: {multi_enrollment_value}")
#                         # Count as updated since we processed it
#                         total_updated += 1
#                     elif multi_enrollment_exists and old_value != multi_enrollment_value:
#                         frappe.logger().info(f"Updated contact {glific_id} - value changed: {old_value} → {multi_enrollment_value}")
#                         total_updated += 1
#                     else:
#                         frappe.logger().info(f"Added multi_enrollment to contact {glific_id}: {multi_enrollment_value}")
#                         total_updated += 1
#                 else:
#                     frappe.logger().error(f"Failed to update contact {glific_id}: {update_data}")
#                     total_errors += 1
#             else:
#                 frappe.logger().error(f"Failed to update contact {glific_id}. Status: {update_response.status_code}")
#                 total_errors += 1
            
#             total_processed += 1
                
#         except Exception as e:
#             frappe.logger().error(f"Exception processing backend student {backend_student.student_name}: {str(e)}")
#             total_errors += 1
#             total_processed += 1
#             continue
    
#     result = {
#         "set_name": onboarding_set.set_name,
#         "updated": total_updated,
#         "skipped": total_skipped,  # This will now always be 0 since we don't skip
#         "errors": total_errors,
#         "total_processed": total_processed
#     }
    
#     frappe.logger().info(f"Multi-enrollment update completed for set {onboarding_set.set_name}. Updated: {total_updated}, Skipped: {total_skipped}, Errors: {total_errors}, Total Processed: {total_processed}")
#     return result

# @frappe.whitelist()
# def run_multi_enrollment_update_for_specific_set(onboarding_set_name, batch_size=10):
#     """
#     Whitelist function to run the multi-enrollment update process for a specific Backend Student Onboarding set
    
#     Args:
#         onboarding_set_name: Backend Student Onboarding set name to process (required)
#     """
#     if not onboarding_set_name:
#         return "Error: Backend Student Onboarding set name is required"
    
#     try:
#         # Start a new transaction to handle any database errors
#         frappe.db.begin()
#         result = update_specific_set_contacts_with_multi_enrollment(onboarding_set_name, int(batch_size))
#         frappe.db.commit()
        
#         if "error" in result:
#             return f"Error: {result['error']}"
#         elif "message" in result:
#             return result["message"]
#         else:
#             return f"Process completed for set '{result['set_name']}'. Updated: {result['updated']}, Skipped: {result['skipped']}, Errors: {result['errors']}, Total Processed: {result['total_processed']}"
#     except Exception as e:
#         frappe.db.rollback()
#         frappe.logger().error(f"Error in run_multi_enrollment_update_for_specific_set: {str(e)}")
#         return f"Error occurred: {str(e)}"

# @frappe.whitelist()
# def get_backend_onboarding_sets():
#     """
#     Get list of all processed Backend Student Onboarding sets
#     """
#     sets = frappe.get_all(
#         "Backend Student Onboarding",
#         filters={"status": "Processed"},
#         fields=["name", "set_name", "processed_student_count", "upload_date"],
#         order_by="upload_date desc"
#     )
#     return sets



# def process_multiple_sets_simple(set_names, batch_size=50):
#     """
#     Simple background processor for multiple sets
#     """
#     results = []

#     for i, set_name in enumerate(set_names, 1):
#         frappe.logger().info(f"Processing set {i}/{len(set_names)}: {set_name}")

#         try:
#             # Process all students in this set
#             total_updated = 0
#             total_errors = 0
#             batch_count = 0

#             while True:
#                 batch_count += 1
#                 result = update_specific_set_contacts_with_multi_enrollment(set_name, batch_size)

#                 if "error" in result:
#                     frappe.logger().error(f"Error in {set_name}: {result['error']}")
#                     break
#                 elif "message" in result:
#                     frappe.logger().info(f"Set {set_name}: {result['message']}")
#                     break
#                 else:
#                     total_updated += result['updated']
#                     total_errors += result['errors']

#                     # If no students processed, we're done
#                     if result['total_processed'] == 0:
#                         break

#                 time.sleep(1)  # Brief pause between batches

#                 if batch_count > 20:  # Safety limit
#                     frappe.logger().warning(f"Reached batch limit for {set_name}")
#                     break

#             results.append({
#                 "set_name": set_name,
#                 "updated": total_updated,
#                 "errors": total_errors,
#                 "status": "completed"
#             })

#             frappe.logger().info(f"Completed {set_name}: {total_updated} updated, {total_errors} errors")

#         except Exception as e:
#             frappe.logger().error(f"Exception in {set_name}: {str(e)}")
#             results.append({
#                 "set_name": set_name,
#                 "updated": 0,
#                 "errors": 1,
#                 "status": "error",
#                 "error": str(e)
#             })

#     # Log final summary
#     total_updated = sum(r['updated'] for r in results)
#     total_errors = sum(r['errors'] for r in results)
#     frappe.logger().info(f"All sets completed: {total_updated} updated, {total_errors} errors")

#     return results

# @frappe.whitelist()
# def process_my_sets(set_names):
#     """
#     Simple function to process your list of sets in background

#     Args:
#         set_names: List of set names (can be list or comma-separated string)
#     """

#     # Handle string input
#     if isinstance(set_names, str):
#         set_names = [name.strip() for name in set_names.split(',')]

#     # Start background job
#     job = enqueue(
#         process_multiple_sets_simple,
#         queue='long',
#         timeout=7200,  # 2 hours
#         set_names=set_names,
#         batch_size=50
#     )

#     return f"Started processing {len(set_names)} sets in background. Job ID: {job.id}"



# coverage_analysis.py
# Script to identify and create tests for missing coverage

import coverage
import ast
import inspect
import sys
import os

def analyze_missing_coverage(file_path):
    """
    Analyze which lines are missing coverage and suggest test cases
    """
    
    # Create coverage instance
    cov = coverage.Coverage()
    cov.start()
    
    # Import and analyze the module
    try:
        # Import your module here
        import glific_multi_enrollment_update
        
        # Stop coverage
        cov.stop()
        cov.save()
        
        # Get missing lines
        missing_lines = cov.analysis(file_path)[3]
        
        print(f"Missing lines in {file_path}:")
        for line_num in missing_lines:
            print(f"Line {line_num}")
            
        return missing_lines
        
    except Exception as e:
        print(f"Error analyzing coverage: {e}")
        return []

def create_additional_tests():
    """
    Create additional test methods for edge cases
    """
    
    additional_tests = """
    
    # Additional test methods to add to your test class:
    
    def test_json_parsing_error(self):
        '''Test JSON parsing error in contact fields'''
        with patch('requests.post') as mock_post, \\
             patch('frappe.get_all') as mock_get_all, \\
             patch('frappe.get_doc') as mock_get_doc, \\
             patch('frappe.db.exists') as mock_exists, \\
             patch('frappe.logger') as mock_logger:
            
            # Setup mocks for invalid JSON scenario
            mock_logger_instance = Mock()
            mock_logger.return_value = mock_logger_instance
            
            mock_onboarding_set = Mock()
            mock_onboarding_set.status = "Processed"
            mock_onboarding_set.set_name = "Test Set"
            
            mock_get_all.return_value = [{"student_name": "Test", "phone": "123", "student_id": "STU001", "batch_skeyword": "TEST"}]
            
            mock_student_doc = Mock()
            mock_student_doc.glific_id = "12345"
            mock_get_doc.side_effect = [mock_onboarding_set, mock_student_doc]
            mock_exists.return_value = True
            
            # Mock response with invalid JSON in fields
            fetch_response = Mock()
            fetch_response.status_code = 200
            fetch_response.json.return_value = {
                "data": {
                    "contact": {
                        "contact": {
                            "id": "12345",
                            "name": "Test Student", 
                            "phone": "1234567890",
                            "fields": "invalid_json_string"  # This will cause JSON decode error
                        }
                    }
                }
            }
            mock_post.return_value = fetch_response
            
            with patch('glific_multi_enrollment_update.get_glific_settings') as mock_settings, \\
                 patch('glific_multi_enrollment_update.get_glific_auth_headers') as mock_headers:
                
                mock_settings.return_value = Mock(api_url="http://test.com")
                mock_headers.return_value = {"Authorization": "Bearer test"}
                
                from glific_multi_enrollment_update import update_specific_set_contacts_with_multi_enrollment
                result = update_specific_set_contacts_with_multi_enrollment("Test Set")
                
                # Should handle JSON error gracefully
                self.assertEqual(result["errors"], 1)

    def test_contact_not_found_in_response(self):
        '''Test when contact is not found in Glific response'''
        with patch('requests.post') as mock_post, \\
             patch('frappe.get_all') as mock_get_all, \\
             patch('frappe.get_doc') as mock_get_doc, \\
             patch('frappe.db.exists') as mock_exists, \\
             patch('frappe.logger') as mock_logger:
            
            mock_logger_instance = Mock()
            mock_logger.return_value = mock_logger_instance
            
            mock_onboarding_set = Mock()
            mock_onboarding_set.status = "Processed"
            mock_onboarding_set.set_name = "Test Set"
            
            mock_get_all.return_value = [{"student_name": "Test", "phone": "123", "student_id": "STU001", "batch_skeyword": "TEST"}]
            
            mock_student_doc = Mock()
            mock_student_doc.glific_id = "12345"
            mock_get_doc.side_effect = [mock_onboarding_set, mock_student_doc]
            mock_exists.return_value = True
            
            # Mock response with no contact data
            fetch_response = Mock()
            fetch_response.status_code = 200
            fetch_response.json.return_value = {
                "data": {
                    "contact": {
                        "contact": None  # Contact not found
                    }
                }
            }
            mock_post.return_value = fetch_response
            
            with patch('glific_multi_enrollment_update.get_glific_settings') as mock_settings, \\
                 patch('glific_multi_enrollment_update.get_glific_auth_headers') as mock_headers:
                
                mock_settings.return_value = Mock(api_url="http://test.com")
                mock_headers.return_value = {"Authorization": "Bearer test"}
                
                from glific_multi_enrollment_update import update_specific_set_contacts_with_multi_enrollment
                result = update_specific_set_contacts_with_multi_enrollment("Test Set")
                
                self.assertEqual(result["errors"], 1)
                mock_logger_instance.error.assert_called()

    def test_glific_api_errors_in_response(self):
        '''Test when Glific API returns errors in response'''
        with patch('requests.post') as mock_post, \\
             patch('frappe.get_all') as mock_get_all, \\
             patch('frappe.get_doc') as mock_get_doc, \\
             patch('frappe.db.exists') as mock_exists, \\
             patch('frappe.logger') as mock_logger:
            
            mock_logger_instance = Mock()
            mock_logger.return_value = mock_logger_instance
            
            mock_onboarding_set = Mock()
            mock_onboarding_set.status = "Processed"
            mock_onboarding_set.set_name = "Test Set"
            
            mock_get_all.return_value = [{"student_name": "Test", "phone": "123", "student_id": "STU001", "batch_skeyword": "TEST"}]
            
            mock_student_doc = Mock()
            mock_student_doc.glific_id = "12345"
            mock_get_doc.side_effect = [mock_onboarding_set, mock_student_doc]
            mock_exists.return_value = True
            
            # Mock response with errors
            fetch_response = Mock()
            fetch_response.status_code = 200
            fetch_response.json.return_value = {
                "errors": [{"message": "Contact not found", "code": "NOT_FOUND"}]
            }
            mock_post.return_value = fetch_response
            
            with patch('glific_multi_enrollment_update.get_glific_settings') as mock_settings, \\
                 patch('glific_multi_enrollment_update.get_glific_auth_headers') as mock_headers:
                
                mock_settings.return_value = Mock(api_url="http://test.com")
                mock_headers.return_value = {"Authorization": "Bearer test"}
                
                from glific_multi_enrollment_update import update_specific_set_contacts_with_multi_enrollment
                result = update_specific_set_contacts_with_multi_enrollment("Test Set")
                
                self.assertEqual(result["errors"], 1)

    def test_update_contact_api_errors(self):
        '''Test errors during contact update API call'''
        with patch('requests.post') as mock_post, \\
             patch('frappe.get_all') as mock_get_all, \\
             patch('frappe.get_doc') as mock_get_doc, \\
             patch('frappe.db.exists') as mock_exists, \\
             patch('frappe.logger') as mock_logger:
            
            mock_logger_instance = Mock()
            mock_logger.return_value = mock_logger_instance
            
            mock_onboarding_set = Mock()
            mock_onboarding_set.status = "Processed"
            mock_onboarding_set.set_name = "Test Set"
            
            mock_get_all.return_value = [{"student_name": "Test", "phone": "123", "student_id": "STU001", "batch_skeyword": "TEST"}]
            
            mock_student_doc = Mock()
            mock_student_doc.glific_id = "12345"
            mock_get_doc.side_effect = [mock_onboarding_set, mock_student_doc]
            mock_exists.return_value = True
            
            # Mock successful fetch but failed update
            fetch_response = Mock()
            fetch_response.status_code = 200
            fetch_response.json.return_value = {
                "data": {
                    "contact": {
                        "contact": {
                            "id": "12345",
                            "name": "Test Student",
                            "phone": "1234567890", 
                            "fields": "{}"
                        }
                    }
                }
            }
            
            update_response = Mock()
            update_response.status_code = 500  # Server error
            
            mock_post.side_effect = [fetch_response, update_response]
            
            with patch('glific_multi_enrollment_update.get_glific_settings') as mock_settings, \\
                 patch('glific_multi_enrollment_update.get_glific_auth_headers') as mock_headers:
                
                mock_settings.return_value = Mock(api_url="http://test.com")
                mock_headers.return_value = {"Authorization": "Bearer test"}
                
                from glific_multi_enrollment_update import update_specific_set_contacts_with_multi_enrollment
                result = update_specific_set_contacts_with_multi_enrollment("Test Set")
                
                self.assertEqual(result["errors"], 1)

    def test_existing_multi_enrollment_field_same_value(self):
        '''Test when multi_enrollment field exists with same value'''
        with patch('requests.post') as mock_post, \\
             patch('frappe.get_all') as mock_get_all, \\
             patch('frappe.get_doc') as mock_get_doc, \\
             patch('frappe.db.exists') as mock_exists, \\
             patch('frappe.logger') as mock_logger:
            
            mock_logger_instance = Mock()
            mock_logger.return_value = mock_logger_instance
            
            mock_onboarding_set = Mock()
            mock_onboarding_set.status = "Processed"
            mock_onboarding_set.set_name = "Test Set"
            
            mock_get_all.return_value = [{"student_name": "Test", "phone": "123", "student_id": "STU001", "batch_skeyword": "TEST"}]
            
            mock_student_doc = Mock()
            mock_student_doc.glific_id = "12345"
            mock_student_doc.enrollment = [Mock()]  # Single enrollment = "no"
            mock_get_doc.side_effect = [mock_onboarding_set, mock_student_doc]
            mock_exists.return_value = True
            
            # Mock contact with existing multi_enrollment field
            fetch_response = Mock()
            fetch_response.status_code = 200
            fetch_response.json.return_value = {
                "data": {
                    "contact": {
                        "contact": {
                            "id": "12345",
                            "name": "Test Student",
                            "phone": "1234567890",
                            "fields": '{"multi_enrollment": {"value": "no", "type": "string"}}'  # Same value
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
                            "id": "12345",
                            "name": "Test Student",
                            "fields": '{"multi_enrollment": {"value": "no", "type": "string"}}'
                        }
                    }
                }
            }
            
            mock_post.side_effect = [fetch_response, update_response]
            
            with patch('glific_multi_enrollment_update.get_glific_settings') as mock_settings, \\
                 patch('glific_multi_enrollment_update.get_glific_auth_headers') as mock_headers:
                
                mock_settings.return_value = Mock(api_url="http://test.com")
                mock_headers.return_value = {"Authorization": "Bearer test"}
                
                from glific_multi_enrollment_update import update_specific_set_contacts_with_multi_enrollment
                result = update_specific_set_contacts_with_multi_enrollment("Test Set")
                
                self.assertEqual(result["updated"], 1)  # Should still count as updated
                mock_logger_instance.info.assert_called()

    def test_batch_limit_reached(self):
        '''Test when batch processing limit is reached'''
        with patch('time.sleep') as mock_sleep, \\
             patch('frappe.logger') as mock_logger:
            
            mock_logger_instance = Mock()
            mock_logger.return_value = mock_logger_instance
            
            call_count = 0
            def mock_update_function(set_name, batch_size):
                nonlocal call_count
                call_count += 1
                if call_count <= 20:  # Simulate continued processing
                    return {"updated": 1, "errors": 0, "total_processed": 1}
                else:
                    return {"updated": 0, "errors": 0, "total_processed": 0}
            
            with patch('glific_multi_enrollment_update.update_specific_set_contacts_with_multi_enrollment', side_effect=mock_update_function):
                from glific_multi_enrollment_update import process_multiple_sets_simple
                result = process_multiple_sets_simple(["Set1"], 50)
                
                # Should hit batch limit and log warning
                self.assertEqual(len(result), 1)
                mock_logger_instance.warning.assert_called()

    def test_update_contact_response_errors(self):
        '''Test when update contact response contains errors'''
        with patch('requests.post') as mock_post, \\
             patch('frappe.get_all') as mock_get_all, \\
             patch('frappe.get_doc') as mock_get_doc, \\
             patch('frappe.db.exists') as mock_exists, \\
             patch('frappe.logger') as mock_logger:
            
            mock_logger_instance = Mock()
            mock_logger.return_value = mock_logger_instance
            
            mock_onboarding_set = Mock()
            mock_onboarding_set.status = "Processed"
            mock_onboarding_set.set_name = "Test Set"
            
            mock_get_all.return_value = [{"student_name": "Test", "phone": "123", "student_id": "STU001", "batch_skeyword": "TEST"}]
            
            mock_student_doc = Mock()
            mock_student_doc.glific_id = "12345"
            mock_get_doc.side_effect = [mock_onboarding_set, mock_student_doc]
            mock_exists.return_value = True
            
            fetch_response = Mock()
            fetch_response.status_code = 200
            fetch_response.json.return_value = {
                "data": {
                    "contact": {
                        "contact": {
                            "id": "12345",
                            "name": "Test Student",
                            "phone": "1234567890",
                            "fields": "{}"
                        }
                    }
                }
            }
            
            # Update response with errors
            update_response = Mock()
            update_response.status_code = 200
            update_response.json.return_value = {
                "errors": [{"message": "Update failed", "key": "fields"}]
            }
            
            mock_post.side_effect = [fetch_response, update_response]
            
            with patch('glific_multi_enrollment_update.get_glific_settings') as mock_settings, \\
                 patch('glific_multi_enrollment_update.get_glific_auth_headers') as mock_headers:
                
                mock_settings.return_value = Mock(api_url="http://test.com")
                mock_headers.return_value = {"Authorization": "Bearer test"}
                
                from glific_multi_enrollment_update import update_specific_set_contacts_with_multi_enrollment
                result = update_specific_set_contacts_with_multi_enrollment("Test Set")
                
                self.assertEqual(result["errors"], 1)
    """
    
    return additional_tests

# Command to run coverage and identify missing lines
def run_coverage_analysis():
    """
    Run this to see exactly which lines need tests
    """
    
    commands = '''
    # Run these commands to identify missing coverage:
    
    1. Install coverage:
    pip install coverage
    
    2. Run tests with coverage:
    coverage run -m unittest test_glific_webhook.py
    
    3. Generate coverage report:
    coverage report -m tap_lms/tests/test_glific_webhook.py
    
    4. Generate HTML coverage report (more detailed):
    coverage html
    
    5. View missing lines:
    coverage report --show-missing
    '''
    
    print(commands)

if __name__ == "__main__":
    print("Additional test methods to achieve 100% coverage:")
    print(create_additional_tests())
    print("\\n" + "="*50)
    run_coverage_analysis()