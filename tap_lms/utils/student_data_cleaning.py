"""
==============================================================================
STUDENT CLEANUP - NO PHONE NUMBER HANDLER
==============================================================================

File Location: laplms/laplms/utils/cleanup_no_phone_students.py

PURPOSE:
    Find and optionally delete student records that don't have phone numbers.
    Optimized for large datasets (500k+ records).

USAGE:
    # From Frappe console
    bench --site your-site console
    
    # Import and use
    from laplms.utils.cleanup_no_phone_students import (
        check_students_without_phone,
        delete_students_without_phone
    )
    
    # Interactive check (with prompts)
    check_students_without_phone(interactive=True)
    
    # Just get the count
    result = check_students_without_phone(interactive=False)
    
    # Delete students without phone (with confirmation)
    delete_students_without_phone(batch_size=100, dry_run=True)

==============================================================================
"""

import frappe
from typing import Dict, List
from frappe.utils import cint


# ==============================================================================
# CHECK STUDENTS WITHOUT PHONE
# ==============================================================================

@frappe.whitelist()
def check_students_without_phone(interactive: bool = True, limit: int = 50) -> Dict:
    """
    Check how many students don't have phone numbers.
    
    Args:
        interactive: If True, prompts user for actions
        limit: Number of records to show in preview
    
    Returns:
        dict: Statistics and optional student list
    """
    
    # Convert string parameters (from web requests)
    if isinstance(interactive, str):
        interactive = interactive.lower() in ('true', '1', 'yes')
    if isinstance(limit, str):
        limit = int(limit)
    
    print("\n" + "=" * 80)
    print("STUDENT CLEANUP - PHONE NUMBER CHECK")
    print("=" * 80)
    
    # ========================================================================
    # STEP 1: COUNT STUDENTS WITHOUT PHONE
    # ========================================================================
    print("\n📊 Checking students without phone numbers...")
    
    count_result = frappe.db.sql("""
        SELECT COUNT(*) as total
        FROM `tabStudent`
        WHERE phone IS NULL 
           OR phone = '' 
           OR phone = '0'
    """, as_dict=True)
    
    total_without_phone = count_result[0].get('total', 0) if count_result else 0
    
    # Total students for context
    total_students = frappe.db.count('Student')
    percentage = (total_without_phone / total_students * 100) if total_students > 0 else 0
    
    print(f"\n📈 RESULTS:")
    print(f"   Total Students: {total_students:,}")
    print(f"   Without Phone: {total_without_phone:,} ({percentage:.2f}%)")
    print(f"   With Phone: {(total_students - total_without_phone):,}")
    
    result = {
        "total_students": total_students,
        "students_without_phone": total_without_phone,
        "students_with_phone": total_students - total_without_phone,
        "percentage_without_phone": round(percentage, 2),
        "students_list": []
    }
    
    if total_without_phone == 0:
        print("\n✅ All students have phone numbers!")
        print("=" * 80)
        return result
    
    # ========================================================================
    # STEP 2: INTERACTIVE PROMPT TO SHOW LIST
    # ========================================================================
    if interactive:
        print("\n" + "─" * 80)
        show_list = input(f"\n❓ Do you want to see a list of students without phone? (yes/no): ").strip().lower()
        
        if show_list in ('yes', 'y'):
            result["students_list"] = show_students_without_phone(limit)
    
    # ========================================================================
    # STEP 3: INTERACTIVE PROMPT TO DELETE
    # ========================================================================
    if interactive and total_without_phone > 0:
        print("\n" + "─" * 80)
        print("\n⚠️  WARNING: Deletion is permanent and will also delete related records!")
        print("   Recommended: Run with dry_run=True first to see what will be deleted.")
        
        delete_confirm = input(f"\n❓ Do you want to DELETE students without phone? (yes/no): ").strip().lower()
        
        if delete_confirm in ('yes', 'y'):
            dry_run_confirm = input("   Run as DRY RUN first (recommended)? (yes/no): ").strip().lower()
            
            if dry_run_confirm in ('yes', 'y'):
                print("\n🔍 Running DRY RUN (no changes will be made)...")
                delete_result = delete_students_without_phone(dry_run=True)
                result["deletion_preview"] = delete_result
                
                # Ask if they want to proceed with actual deletion
                print("\n" + "─" * 80)
                proceed = input("\n❓ Do you want to PROCEED with actual deletion? (yes/no): ").strip().lower()
                
                if proceed in ('yes', 'y'):
                    print("\n🗑️  Running LIVE DELETION...")
                    delete_result = delete_students_without_phone(dry_run=False)
                    result["deletion_result"] = delete_result
                else:
                    print("\n✅ Deletion cancelled.")
            else:
                print("\n🗑️  Running LIVE DELETION...")
                delete_result = delete_students_without_phone(dry_run=False)
                result["deletion_result"] = delete_result
        else:
            print("\n✅ No deletion performed.")
    
    print("\n" + "=" * 80)
    return result


# ==============================================================================
# SHOW STUDENTS WITHOUT PHONE
# ==============================================================================

def show_students_without_phone(limit: int = 50) -> List[Dict]:
    """
    Display students who don't have phone numbers.
    
    Args:
        limit: Maximum number of students to display
    
    Returns:
        list: List of student records
    """
    
    print(f"\n📋 Showing up to {limit} students without phone numbers:\n")
    
    students = frappe.db.sql("""
        SELECT 
            name as student_id,
            name1 as student_name,
            joined_on,
            school,
            creation,
            modified
        FROM `tabStudent`
        WHERE phone IS NULL 
           OR phone = '' 
           OR phone = '0'
        ORDER BY modified DESC
        LIMIT %s
    """, (limit,), as_dict=True)
    
    if not students:
        print("   No students found without phone numbers.")
        return []
    
    print(f"{'#':<5} {'Student ID':<20} {'Student Name':<30} {'Joined On':<15} {'School':<20}")
    print("─" * 100)
    
    for idx, student in enumerate(students, 1):
        print(f"{idx:<5} {student.student_id:<20} {student.student_name:<30} {str(student.joined_on or 'N/A'):<15} {(student.school or 'N/A'):<20}")
    
    total_count = frappe.db.count('Student', {
        'phone': ['in', [None, '', '0']]
    })
    
    if total_count > limit:
        print(f"\n... and {total_count - limit} more students")
    
    print()
    return students


# ==============================================================================
# DELETE STUDENTS WITHOUT PHONE
# ==============================================================================

@frappe.whitelist()
def delete_students_without_phone(
    batch_size: int = 100,
    dry_run: bool = True,
    delete_linked_records: bool = True
) -> Dict:
    """
    Delete students who don't have phone numbers.
    
    Args:
        batch_size: Number of students to process per batch
        dry_run: If True, only shows what would be deleted
        delete_linked_records: If True, also deletes related child records
    
    Returns:
        dict: Deletion statistics
    """
    
    # Convert string parameters
    if isinstance(dry_run, str):
        dry_run = dry_run.lower() in ('true', '1', 'yes')
    if isinstance(batch_size, str):
        batch_size = int(batch_size)
    if isinstance(delete_linked_records, str):
        delete_linked_records = delete_linked_records.lower() in ('true', '1', 'yes')
    
    print("\n" + "=" * 80)
    print("STUDENT DELETION - NO PHONE NUMBERS")
    print("=" * 80)
    print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'LIVE RUN (will delete data)'}")
    print(f"Batch Size: {batch_size}")
    print(f"Delete Linked Records: {delete_linked_records}")
    print("=" * 80)
    
    stats = {
        "students_deleted": 0,
        "students_processed": 0,
        "records_deleted": {
            "backend_students": 0,
            "engagement_states": 0,
            "stage_progress": 0,
            "learning_states": 0,
            "onboarding_progress": 0
        },
        "errors": []
    }
    
    try:
        # ====================================================================
        # GET STUDENTS WITHOUT PHONE
        # ====================================================================
        print("\n🔍 Finding students without phone numbers...")
        
        students = frappe.db.sql("""
            SELECT name as student_id, name1 as student_name
            FROM `tabStudent`
            WHERE phone IS NULL 
               OR phone = '' 
               OR phone = '0'
            ORDER BY creation ASC
        """, as_dict=True)
        
        total_students = len(students)
        print(f"   Found {total_students:,} students to delete\n")
        
        if total_students == 0:
            print("✅ No students found without phone numbers.")
            return stats
        
        # ====================================================================
        # PROCESS IN BATCHES
        # ====================================================================
        batch_counter = 0
        
        for idx, student in enumerate(students, 1):
            try:
                # Progress indicator
                if idx % 100 == 0 or idx == 1:
                    progress = (idx / total_students) * 100
                    print(f"Progress: {idx}/{total_students} ({progress:.1f}%)")
                    
                    # Publish progress for web interface
                    frappe.publish_realtime(
                        "cleanup_progress",
                        {
                            "message": f"Processing {idx}/{total_students} students...",
                            "progress": int(progress)
                        },
                        user=frappe.session.user
                    )
                
                stats["students_processed"] += 1
                
                # ============================================================
                # DELETE LINKED RECORDS
                # ============================================================
                if delete_linked_records:
                    linked_stats = delete_student_linked_records(
                        student["student_id"],
                        dry_run
                    )
                    
                    for key in stats["records_deleted"]:
                        stats["records_deleted"][key] += linked_stats.get(key, 0)
                
                # ============================================================
                # DELETE STUDENT
                # ============================================================
                if not dry_run:
                    frappe.delete_doc(
                        "Student",
                        student["student_id"],
                        ignore_permissions=True,
                        force=True
                    )
                
                stats["students_deleted"] += 1
                
                # ============================================================
                # BATCH COMMIT
                # ============================================================
                batch_counter += 1
                if not dry_run and batch_counter >= batch_size:
                    frappe.db.commit()
                    print(f"   💾 Committed batch of {batch_counter} students")
                    batch_counter = 0
                
            except Exception as e:
                error_msg = f"Error deleting student {student['student_id']}: {str(e)}"
                print(f"   ❌ {error_msg}")
                stats["errors"].append(error_msg)
                frappe.log_error(error_msg, "Student Deletion Error")
                
                if not dry_run:
                    frappe.db.rollback()
        
        # Final commit
        if not dry_run and batch_counter > 0:
            frappe.db.commit()
            print(f"   💾 Final commit of {batch_counter} students")
        
        # ====================================================================
        # PRINT SUMMARY
        # ====================================================================
        print("\n" + "=" * 80)
        print("DELETION SUMMARY")
        print("=" * 80)
        print(f"Students Processed: {stats['students_processed']:,}")
        print(f"Students Deleted: {stats['students_deleted']:,}")
        
        if delete_linked_records:
            print(f"\nLinked Records Deleted:")
            for key, value in stats['records_deleted'].items():
                if value > 0:
                    print(f"  - {key.replace('_', ' ').title()}: {value:,}")
        
        if stats["errors"]:
            print(f"\n⚠️  Errors: {len(stats['errors'])}")
            for error in stats["errors"][:10]:
                print(f"  - {error}")
        
        print("=" * 80)
        
        if dry_run:
            print("\n✅ DRY RUN COMPLETE - No changes were made")
            print("   Run with dry_run=False to delete students")
        else:
            print("\n✅ DELETION COMPLETE - Students removed from database")
        
        # Publish completion
        frappe.publish_realtime(
            "cleanup_progress",
            {
                "message": "Cleanup complete!",
                "progress": 100,
                "stats": stats
            },
            user=frappe.session.user
        )
        
        return stats
        
    except Exception as e:
        error_msg = f"FATAL ERROR: {str(e)}"
        print(f"\n❌ {error_msg}")
        frappe.log_error(error_msg, "Student Deletion Fatal Error")
        
        if not dry_run:
            frappe.db.rollback()
            print("🔄 All changes rolled back")
        
        stats["errors"].append(error_msg)
        return stats


# ==============================================================================
# DELETE LINKED CHILD RECORDS
# ==============================================================================

def delete_student_linked_records(student_id: str, dry_run: bool) -> Dict:
    """
    Delete all child records linked to a student.
    
    Args:
        student_id: Student ID to delete records for
        dry_run: If True, only counts records without deleting
    
    Returns:
        dict: Count of deleted records
    """
    
    stats = {
        "backend_students": 0,
        "engagement_states": 0,
        "stage_progress": 0,
        "learning_states": 0,
        "onboarding_progress": 0
    }
    
    # Backend Students (bulk delete for efficiency)
    if not dry_run:
        frappe.db.sql("""
            DELETE FROM `tabBackend Students`
            WHERE student_id = %s
        """, (student_id,))
        count = frappe.db.sql("""
            SELECT ROW_COUNT() as count
        """, as_dict=True)[0].get('count', 0)
        stats["backend_students"] = count
    else:
        count = frappe.db.count("Backend Students", {"student_id": student_id})
        stats["backend_students"] = count
    
    # EngagementState
    if not dry_run:
        frappe.db.sql("""
            DELETE FROM `tabEngagementState`
            WHERE student = %s
        """, (student_id,))
        count = frappe.db.sql("SELECT ROW_COUNT() as count", as_dict=True)[0].get('count', 0)
        stats["engagement_states"] = count
    else:
        stats["engagement_states"] = frappe.db.count("EngagementState", {"student": student_id})
    
    # StudentStageProgress
    if not dry_run:
        frappe.db.sql("""
            DELETE FROM `tabStudentStageProgress`
            WHERE student = %s
        """, (student_id,))
        count = frappe.db.sql("SELECT ROW_COUNT() as count", as_dict=True)[0].get('count', 0)
        stats["stage_progress"] = count
    else:
        stats["stage_progress"] = frappe.db.count("StudentStageProgress", {"student": student_id})
    
    # LearningState
    if not dry_run:
        frappe.db.sql("""
            DELETE FROM `tabLearningState`
            WHERE student = %s
        """, (student_id,))
        count = frappe.db.sql("SELECT ROW_COUNT() as count", as_dict=True)[0].get('count', 0)
        stats["learning_states"] = count
    else:
        stats["learning_states"] = frappe.db.count("LearningState", {"student": student_id})
    
    # StudentOnboardingProgress
    if not dry_run:
        frappe.db.sql("""
            DELETE FROM `tabStudentOnboardingProgress`
            WHERE student = %s
        """, (student_id,))
        count = frappe.db.sql("SELECT ROW_COUNT() as count", as_dict=True)[0].get('count', 0)
        stats["onboarding_progress"] = count
    else:
        stats["onboarding_progress"] = frappe.db.count("StudentOnboardingProgress", {"student": student_id})
    
    return stats


# ==============================================================================
# COMBINED WORKFLOW
# ==============================================================================

@frappe.whitelist()
def cleanup_and_merge_workflow(
    skip_cleanup: bool = False,
    skip_merge: bool = False,
    cleanup_batch_size: int = 100,
    merge_batch_size: int = 50
) -> Dict:
    """
    Complete workflow: Clean up students without phone, then merge duplicates.
    
    Args:
        skip_cleanup: Skip the cleanup step
        skip_merge: Skip the merge step
        cleanup_batch_size: Batch size for cleanup
        merge_batch_size: Batch size for merge
    
    Returns:
        dict: Combined statistics
    """
    
    result = {
        "cleanup_stats": {},
        "merge_stats": {},
        "total_time": 0
    }
    
    import time
    start_time = time.time()
    
    print("\n" + "=" * 80)
    print("COMPLETE STUDENT DATA CLEANUP WORKFLOW")
    print("=" * 80)
    
    # ========================================================================
    # STEP 1: CLEANUP STUDENTS WITHOUT PHONE
    # ========================================================================
    if not skip_cleanup:
        print("\n📍 STEP 1: Removing students without phone numbers...")
        print("─" * 80)
        
        cleanup_stats = delete_students_without_phone(
            batch_size=cleanup_batch_size,
            dry_run=False,
            delete_linked_records=True
        )
        result["cleanup_stats"] = cleanup_stats
        
        print(f"\n✅ Cleanup complete: {cleanup_stats['students_deleted']:,} students removed")
    else:
        print("\n⏭️  STEP 1: Skipped (cleanup disabled)")
    
    # ========================================================================
    # STEP 2: MERGE DUPLICATE STUDENTS
    # ========================================================================
    if not skip_merge:
        print("\n📍 STEP 2: Merging duplicate students...")
        print("─" * 80)
        
        # Import the merge function from the other file
        from tap_lms.utils.optimized_merge_stud_v2 import merge_duplicate_students
        
        merge_stats = merge_duplicate_students(
            dry_run=False,
            batch_size=merge_batch_size,
            strict_name_matching=True
        )
        result["merge_stats"] = merge_stats
        
        print(f"\n✅ Merge complete: {merge_stats['students_merged']:,} duplicates merged")
    else:
        print("\n⏭️  STEP 2: Skipped (merge disabled)")
    
    # ========================================================================
    # FINAL SUMMARY
    # ========================================================================
    end_time = time.time()
    result["total_time"] = round(end_time - start_time, 2)
    
    print("\n" + "=" * 80)
    print("WORKFLOW COMPLETE")
    print("=" * 80)
    print(f"Total Time: {result['total_time']} seconds")
    print("=" * 80)
    
    return result