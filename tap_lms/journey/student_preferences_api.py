import frappe
import json
from frappe import _
import traceback
from datetime import datetime


@frappe.whitelist(allow_guest=False)
def update_student_preferences(student_id=None, glific_id=None, phone=None, name=None, preferred_day=None, preferred_time=None):
    """
    Update student's preferred day and time for receiving messages
    
    Args:
        student_id (str, optional): Student ID (name field)
        glific_id (str, optional): Glific ID of student  
        phone (str, optional): Phone number of student
        name (str, optional): Student name to help identify unique student
        preferred_day (str, optional): Preferred day (Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday, Daily)
        preferred_time (str, optional): Preferred time in HH:MM format (e.g., "14:30")
        
    Returns:
        dict: Success status with updated preferences information
    """
    try:
        # Authentication check
        if frappe.session.user == 'Guest':
            frappe.throw(_("Authentication required"), frappe.AuthenticationError)
        
        # Validate that at least one identifier is provided
        if not student_id and not glific_id and not phone:
            frappe.local.response.http_status_code = 400
            return {
                "success": False, 
                "error": "At least one of student_id, glific_id, or phone must be provided"
            }
        
        # Validate that at least one preference field is provided
        if preferred_day is None and preferred_time is None:
            frappe.local.response.http_status_code = 400
            return {
                "success": False,
                "error": "At least one of preferred_day or preferred_time must be provided"
            }
        
        # Validate preferred_day options
        valid_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday", "Daily"]
        if preferred_day is not None and preferred_day not in valid_days:
            frappe.local.response.http_status_code = 400
            return {
                "success": False,
                "error": f"Invalid preferred_day. Allowed values: {', '.join(valid_days)}"
            }
        
        # Validate preferred_time format (HH:MM)
        if preferred_time is not None:
            try:
                # Try to parse the time to validate format
                datetime.strptime(preferred_time, "%H:%M")
            except ValueError:
                frappe.local.response.http_status_code = 400
                return {
                    "success": False,
                    "error": "Invalid preferred_time format. Use HH:MM format (e.g., '14:30')"
                }
        
        # Find the student using the same logic as other student APIs
        student_records = find_student_records(student_id, glific_id, phone, name)
        
        if not student_records:
            frappe.local.response.http_status_code = 404
            return {
                "success": False,
                "error": "Student not found"
            }
        
        # Get the student document
        student = frappe.get_doc("Student", student_records[0].name)
        
        # Track what was updated
        updated_fields = {}
        
        # Update preferred_day if provided
        if preferred_day is not None:
            student.preferred_day = preferred_day
            updated_fields["preferred_day"] = preferred_day
        
        # Update preferred_time if provided  
        if preferred_time is not None:
            student.preferred_time = preferred_time
            updated_fields["preferred_time"] = preferred_time
        
        # Save the student document
        student.save()
        
        # Build response with current values
        response = {
            "success": True,
            "message": "Student preferences updated successfully",
            "student_id": student.name,
            "student_name": student.name1,
            "updated_fields": updated_fields,
            "current_preferences": {
                "preferred_day": student.preferred_day,
                "preferred_time": str(student.preferred_time) if student.preferred_time else None
            }
        }
        
        # Add warning if multiple students were found
        if len(student_records) > 1:
            response["_warning"] = f"Multiple students found. Updated the most recently created one. Count: {len(student_records)}"
        
        # Add search parameters used for debugging
        response["_search_params"] = {
            "student_id": student_id,
            "glific_id": glific_id, 
            "phone": phone,
            "name": name
        }
        
        return response
        
    except frappe.ValidationError as e:
        frappe.local.response.http_status_code = 400
        frappe.log_error(
            f"Validation error in update_student_preferences: {str(e)}",
            "Student Preferences Update API Validation Error"
        )
        return {
            "success": False,
            "error": str(e)
        }
    
    except frappe.AuthenticationError as e:
        frappe.local.response.http_status_code = 401
        frappe.log_error(
            f"Authentication error in update_student_preferences: {str(e)}",
            "Student Preferences Update API Error"
        )
        return {
            "success": False,
            "error": str(e)
        }
    
    except Exception as e:
        frappe.local.response.http_status_code = 500
        error_traceback = traceback.format_exc()
        frappe.log_error(
            f"Error updating student preferences: {str(e)}\n{error_traceback}",
            "Student Preferences Update API Error"
        )
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist(allow_guest=False)
def get_student_preferences(student_id=None, glific_id=None, phone=None, name=None):
    """
    Get student's current preferences for day and time
    
    Args:
        student_id (str, optional): Student ID (name field)
        glific_id (str, optional): Glific ID of student  
        phone (str, optional): Phone number of student
        name (str, optional): Student name to help identify unique student
        
    Returns:
        dict: Student's current preferences
    """
    try:
        # Authentication check
        if frappe.session.user == 'Guest':
            frappe.throw(_("Authentication required"), frappe.AuthenticationError)
        
        # Validate that at least one identifier is provided
        if not student_id and not glific_id and not phone:
            frappe.local.response.http_status_code = 400
            return {
                "success": False, 
                "error": "At least one of student_id, glific_id, or phone must be provided"
            }
        
        # Find the student
        student_records = find_student_records(student_id, glific_id, phone, name)
        
        if not student_records:
            frappe.local.response.http_status_code = 404
            return {
                "success": False,
                "error": "Student not found"
            }
        
        # Get the student document
        student = frappe.get_doc("Student", student_records[0].name)
        
        # Build response
        response = {
            "success": True,
            "student_id": student.name,
            "student_name": student.name1,
            "preferences": {
                "preferred_day": student.preferred_day,
                "preferred_time": str(student.preferred_time) if student.preferred_time else None
            }
        }
        
        # Add warning if multiple students were found
        if len(student_records) > 1:
            response["_warning"] = f"Multiple students found. Showing preferences for the most recently created one. Count: {len(student_records)}"
        
        return response
        
    except frappe.AuthenticationError as e:
        frappe.local.response.http_status_code = 401
        return {"success": False, "error": str(e)}
    
    except Exception as e:
        frappe.local.response.http_status_code = 500
        error_traceback = traceback.format_exc()
        frappe.log_error(
            f"Error getting student preferences: {str(e)}\n{error_traceback}",
            "Student Preferences Get API Error"
        )
        return {"success": False, "error": str(e)}


def find_student_records(student_id=None, glific_id=None, phone=None, name=None):
    """
    Helper function to find student records using the EXACT same logic as get_student_minimal_details
    
    Returns:
        list: List of student records found
    """
    student_records = []
    
    # If student_id is provided, use it directly
    if student_id:
        student_records = frappe.get_all(
            "Student",
            filters={"name": student_id},
            fields=["name", "name1", "phone", "glific_id", "creation"],
            limit=1
        )
    else:
        # Build filters for other identifiers
        filters = {}
        
        if glific_id:
            filters["glific_id"] = glific_id
        
        if phone:
            filters["phone"] = str(phone).strip()
        
        # Find students with current filters
        student_records = frappe.get_all(
            "Student",
            filters=filters,
            fields=["name", "name1", "phone", "glific_id", "creation"],
            order_by="creation desc"
        )
        
        # Phone fallback logic (if original search failed) - SAME AS get_student_minimal_details
        if not student_records and phone and str(phone).strip().startswith('91') and len(str(phone).strip()) == 12:
            phone_without_prefix = str(phone).strip()[2:]
            filters["phone"] = phone_without_prefix
            
            student_records = frappe.get_all(
                "Student",
                filters=filters,
                fields=["name", "name1", "phone", "glific_id", "creation"],
                order_by="creation desc"
            )
        
        # Name filtering logic (if multiple students found)
        if name and len(student_records) > 1:
            normalized_name = str(name).strip().lower()
            exact_matches = [s for s in student_records if s.name1 and s.name1.strip().lower() == normalized_name]
            
            if not exact_matches:
                partial_matches = [s for s in student_records if s.name1 and normalized_name in s.name1.strip().lower()]
                if partial_matches:
                    student_records = partial_matches
            else:
                student_records = exact_matches
    
    return student_records


