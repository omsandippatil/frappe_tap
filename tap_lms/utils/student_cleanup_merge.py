"""
==============================================================================
STUDENT DATA CLEANUP & MERGE - COMPLETE WORKFLOW
==============================================================================

File Location: laplms/laplms/utils/student_cleanup_merge.py

PURPOSE:
    Complete student database cleanup workflow:
    STEP 1: Find students without phone numbers
    STEP 2: Show list (optional, with user confirmation)
    STEP 3: Delete students without phone (optional, with user confirmation)
    STEP 4: Find duplicate students by phone number
    STEP 5: Merge duplicate students

USAGE:
    # From Frappe console
    bench --site your-site console
    
    # Run complete interactive workflow
    from laplms.utils.student_cleanup_merge import run_complete_cleanup
    run_complete_cleanup()
    
    # Run specific steps only
    from laplms.utils.student_cleanup_merge import (
        step1_check_no_phone,
        step2_delete_no_phone,
        step3_merge_duplicates
    )

==============================================================================
"""

import frappe
from frappe.utils import getdate
from fuzzywuzzy import fuzz
from typing import List, Dict, Set, Tuple
import time


# ==============================================================================
# DATABASE CONNECTION HELPER
# ==============================================================================

def reset_db_connection():
    """
    Reset database connection if there's a failed transaction.
    Useful for PostgreSQL interactive console sessions.
    """
    try:
        frappe.db.rollback()
        print("✅ Database connection reset")
        return True
    except Exception as e:
        print(f"⚠️  Could not reset connection: {e}")
        return False


# ==============================================================================
# COMPLETE INTERACTIVE WORKFLOW
# ==============================================================================

@frappe.whitelist()
def run_complete_cleanup(
    auto_mode: bool = False,
    batch_size: int = 100
) -> Dict:
    """
    Run complete student cleanup workflow with interactive prompts.
    
    Args:
        auto_mode: If True, runs without user prompts (uses defaults)
        batch_size: Batch size for processing
    
    Returns:
        dict: Complete statistics from all steps
    """
    
    # Convert string parameters
    if isinstance(auto_mode, str):
        auto_mode = auto_mode.lower() in ('true', '1', 'yes')
    if isinstance(batch_size, str):
        batch_size = int(batch_size)
    
    print("\n" + "=" * 80)
    print("STUDENT DATABASE CLEANUP - COMPLETE WORKFLOW")
    print("=" * 80)
    print(f"Mode: {'AUTOMATIC' if auto_mode else 'INTERACTIVE'}")
    print("=" * 80)
    
    # Reset any failed transactions
    try:
        frappe.db.rollback()
        print("✅ Database connection reset")
    except Exception:
        pass
    
    start_time = time.time()
    
    workflow_result = {
        "step1_check": {},
        "step2_cleanup": {},
        "step3_merge": {},
        "total_time": 0,
        "steps_completed": []
    }
    
    # ========================================================================
    # STEP 1: CHECK STUDENTS WITHOUT PHONE
    # ========================================================================
    print("\n" + "█" * 80)
    print("STEP 1: CHECKING STUDENTS WITHOUT PHONE NUMBERS")
    print("█" * 80)
    
    check_result = step1_check_no_phone(show_details=True)
    workflow_result["step1_check"] = check_result
    workflow_result["steps_completed"].append("step1_check")
    
    students_without_phone = check_result["students_without_phone"]
    
    # If no students without phone, skip to merge
    if students_without_phone == 0:
        print("\n✅ All students have phone numbers!")
        print("   Proceeding directly to duplicate merging...\n")
    else:
        # ====================================================================
        # STEP 1A: ASK TO SHOW LIST
        # ====================================================================
        show_list = False
        if not auto_mode:
            print("\n" + "─" * 80)
            user_input = input(f"\n❓ Found {students_without_phone:,} students without phone.\n   Do you want to see the list? (yes/no): ").strip().lower()
            show_list = user_input in ('yes', 'y')
        
        if show_list:
            print("\n📋 Showing students without phone numbers:\n")
            show_students_without_phone(limit=50)
        
        # ====================================================================
        # STEP 1B: ASK TO DELETE
        # ====================================================================
        delete_students = False
        if not auto_mode:
            print("\n" + "─" * 80)
            print("\n⚠️  WARNING: Deletion will permanently remove these students and all related records!")
            user_input = input(f"\n❓ Do you want to DELETE students without phone numbers? (yes/no): ").strip().lower()
            delete_students = user_input in ('yes', 'y')
        
        if delete_students:
            # Ask for dry run first
            dry_run = True
            if not auto_mode:
                user_input = input("   📝 Run as DRY RUN first (recommended)? (yes/no): ").strip().lower()
                dry_run = user_input in ('yes', 'y', '')  # Default to yes
            
            # ================================================================
            # STEP 2: DELETE STUDENTS WITHOUT PHONE
            # ================================================================
            print("\n" + "█" * 80)
            print("STEP 2: DELETING STUDENTS WITHOUT PHONE NUMBERS")
            print("█" * 80)
            
            if dry_run:
                print("\n🔍 Running DRY RUN (no changes will be made)...\n")
                cleanup_result = step2_delete_no_phone(
                    batch_size=batch_size,
                    dry_run=True
                )
                workflow_result["step2_cleanup"] = cleanup_result
                
                # Ask to proceed with actual deletion
                if not auto_mode:
                    print("\n" + "─" * 80)
                    user_input = input(f"\n❓ DRY RUN complete. Proceed with ACTUAL deletion? (yes/no): ").strip().lower()
                    if user_input in ('yes', 'y'):
                        print("\n🗑️  Running LIVE DELETION...\n")
                        cleanup_result = step2_delete_no_phone(
                            batch_size=batch_size,
                            dry_run=False
                        )
                        workflow_result["step2_cleanup"] = cleanup_result
                        workflow_result["steps_completed"].append("step2_cleanup")
                    else:
                        print("\n✅ Deletion cancelled. Proceeding to duplicate merge...\n")
            else:
                print("\n🗑️  Running LIVE DELETION...\n")
                cleanup_result = step2_delete_no_phone(
                    batch_size=batch_size,
                    dry_run=False
                )
                workflow_result["step2_cleanup"] = cleanup_result
                workflow_result["steps_completed"].append("step2_cleanup")
        else:
            print("\n✅ Skipping deletion. Proceeding to duplicate merge...\n")
    
    # ========================================================================
    # STEP 3: MERGE DUPLICATE STUDENTS
    # ========================================================================
    print("\n" + "█" * 80)
    print("STEP 3: MERGING DUPLICATE STUDENTS")
    print("█" * 80)
    
    if not auto_mode:
        print("\n📊 Checking for duplicate students...")
        preview_duplicates(limit=5)
        
        print("\n" + "─" * 80)
        user_input = input("\n❓ Do you want to MERGE duplicate students? (yes/no): ").strip().lower()
        
        if user_input in ('yes', 'y'):
            # Ask for dry run first
            user_input = input("   📝 Run as DRY RUN first (recommended)? (yes/no): ").strip().lower()
            dry_run = user_input in ('yes', 'y', '')  # Default to yes
            
            if dry_run:
                print("\n🔍 Running MERGE DRY RUN...\n")
                merge_result = step3_merge_duplicates(
                    batch_size=batch_size,
                    dry_run=True
                )
                workflow_result["step3_merge"] = merge_result
                
                # Ask to proceed with actual merge
                print("\n" + "─" * 80)
                user_input = input(f"\n❓ DRY RUN complete. Proceed with ACTUAL merge? (yes/no): ").strip().lower()
                if user_input in ('yes', 'y'):
                    print("\n🔄 Running LIVE MERGE...\n")
                    merge_result = step3_merge_duplicates(
                        batch_size=batch_size,
                        dry_run=False
                    )
                    workflow_result["step3_merge"] = merge_result
                    workflow_result["steps_completed"].append("step3_merge")
                else:
                    print("\n✅ Merge cancelled.")
            else:
                print("\n🔄 Running LIVE MERGE...\n")
                merge_result = step3_merge_duplicates(
                    batch_size=batch_size,
                    dry_run=False
                )
                workflow_result["step3_merge"] = merge_result
                workflow_result["steps_completed"].append("step3_merge")
        else:
            print("\n✅ Merge cancelled.")
    else:
        # Auto mode - run merge with dry_run=False
        merge_result = step3_merge_duplicates(
            batch_size=batch_size,
            dry_run=False
        )
        workflow_result["step3_merge"] = merge_result
        workflow_result["steps_completed"].append("step3_merge")
    
    # ========================================================================
    # FINAL SUMMARY
    # ========================================================================
    end_time = time.time()
    workflow_result["total_time"] = round(end_time - start_time, 2)
    
    print("\n" + "=" * 80)
    print("WORKFLOW COMPLETE - FINAL SUMMARY")
    print("=" * 80)
    print(f"Total Time: {workflow_result['total_time']} seconds")
    print(f"Steps Completed: {', '.join(workflow_result['steps_completed'])}")
    
    if "step2_cleanup" in workflow_result["steps_completed"]:
        cleanup = workflow_result["step2_cleanup"]
        print(f"\n✅ CLEANUP: Deleted {cleanup['students_deleted']:,} students without phone")
    
    if "step3_merge" in workflow_result["steps_completed"]:
        merge = workflow_result["step3_merge"]
        print(f"✅ MERGE: Merged {merge['students_merged']:,} duplicate students")
        print(f"✅ ENROLLMENTS: Moved {merge['enrollments_moved']:,} enrollments")
    
    print("=" * 80)
    
    return workflow_result


# ==============================================================================
# STEP 1: CHECK STUDENTS WITHOUT PHONE
# ==============================================================================

@frappe.whitelist()
def step1_check_no_phone(show_details: bool = True) -> Dict:
    """
    STEP 1: Check how many students don't have phone numbers.
    
    Args:
        show_details: If True, prints detailed statistics
    
    Returns:
        dict: Statistics about students without phone
    """
    
    if isinstance(show_details, str):
        show_details = show_details.lower() in ('true', '1', 'yes')
    
    # Reset any failed transactions
    try:
        frappe.db.rollback()
    except Exception:
        pass
    
    if show_details:
        print("\n📊 Analyzing student records...")
    
    # Count students without phone
    count_result = frappe.db.sql("""
        SELECT COUNT(*) as total
        FROM `tabStudent`
        WHERE phone IS NULL 
           OR phone = '' 
           OR phone = '0'
    """, as_dict=True)
    
    total_without_phone = count_result[0].get('total', 0) if count_result else 0
    total_students = frappe.db.count('Student')
    percentage = (total_without_phone / total_students * 100) if total_students > 0 else 0
    
    result = {
        "total_students": total_students,
        "students_without_phone": total_without_phone,
        "students_with_phone": total_students - total_without_phone,
        "percentage_without_phone": round(percentage, 2)
    }
    
    if show_details:
        print(f"\n📈 RESULTS:")
        print(f"   Total Students: {total_students:,}")
        print(f"   Without Phone: {total_without_phone:,} ({percentage:.2f}%)")
        print(f"   With Phone: {(total_students - total_without_phone):,}")
    
    return result


def show_students_without_phone(limit: int = 50) -> List[Dict]:
    """
    Display students who don't have phone numbers.
    
    Args:
        limit: Maximum number of students to display
    
    Returns:
        list: List of student records
    """
    
    students = frappe.db.sql("""
        SELECT 
            name as student_id,
            name1 as student_name,
            joined_on,
            school,
            creation
        FROM `tabStudent`
        WHERE phone IS NULL 
           OR phone = '' 
           OR phone = '0'
        ORDER BY creation DESC
        LIMIT %s
    """, (limit,), as_dict=True)
    
    if not students:
        print("   No students found without phone numbers.")
        return []
    
    print(f"{'#':<5} {'Student ID':<20} {'Student Name':<30} {'Joined On':<15} {'School':<20}")
    print("─" * 95)
    
    for idx, student in enumerate(students, 1):
        print(f"{idx:<5} {student.student_id:<20} {student.student_name:<30} {str(student.joined_on or 'N/A'):<15} {(student.school or 'N/A'):<20}")
    
    total_count = frappe.db.sql("""
        SELECT COUNT(*) as total
        FROM `tabStudent`
        WHERE phone IS NULL OR phone = '' OR phone = '0'
    """, as_dict=True)[0]['total']
    
    if total_count > limit:
        print(f"\n... and {total_count - limit:,} more students")
    
    print()
    return students


# ==============================================================================
# STEP 2: DELETE STUDENTS WITHOUT PHONE
# ==============================================================================

@frappe.whitelist()
def step2_delete_no_phone(
    batch_size: int = 100,
    dry_run: bool = True
) -> Dict:
    """
    STEP 2: Delete students who don't have phone numbers.
    
    Args:
        batch_size: Number of students to process per batch
        dry_run: If True, only shows what would be deleted
    
    Returns:
        dict: Deletion statistics
    """
    
    # Convert string parameters
    if isinstance(dry_run, str):
        dry_run = dry_run.lower() in ('true', '1', 'yes')
    if isinstance(batch_size, str):
        batch_size = int(batch_size)
    
    # Reset any failed transactions
    try:
        frappe.db.rollback()
    except Exception:
        pass
    
    print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'LIVE RUN (deleting data)'}")
    print(f"Batch Size: {batch_size}")
    print("─" * 80)
    
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
        # Get students without phone
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
        print(f"   Found {total_students:,} students to process\n")
        
        if total_students == 0:
            print("✅ No students found without phone numbers.")
            return stats
        
        # Process in batches
        batch_counter = 0
        
        for idx, student in enumerate(students, 1):
            try:
                # Progress indicator
                if idx % 100 == 0 or idx == 1:
                    progress = (idx / total_students) * 100
                    print(f"Progress: {idx:,}/{total_students:,} ({progress:.1f}%)")
                
                stats["students_processed"] += 1
                
                # Delete linked records
                linked_stats = delete_student_linked_records(
                    student["student_id"],
                    dry_run
                )
                
                for key in stats["records_deleted"]:
                    stats["records_deleted"][key] += linked_stats.get(key, 0)
                
                # Delete student
                if not dry_run:
                    frappe.delete_doc(
                        "Student",
                        student["student_id"],
                        ignore_permissions=True,
                        force=True
                    )
                
                stats["students_deleted"] += 1
                
                # Batch commit
                batch_counter += 1
                if not dry_run and batch_counter >= batch_size:
                    frappe.db.commit()
                    print(f"   💾 Committed batch of {batch_counter} students")
                    batch_counter = 0
                
            except Exception as e:
                error_msg = f"Error deleting student {student['student_id']}: {str(e)}"
                print(f"   ❌ {error_msg}")
                stats["errors"].append(error_msg)
                # Don't log to database during error as transaction may be aborted
                
                if not dry_run:
                    frappe.db.rollback()
        
        # Final commit
        if not dry_run and batch_counter > 0:
            frappe.db.commit()
            print(f"   💾 Final commit of {batch_counter} students")
        
        # Print summary
        print("\n" + "─" * 80)
        print("CLEANUP SUMMARY")
        print("─" * 80)
        print(f"Students Processed: {stats['students_processed']:,}")
        print(f"Students Deleted: {stats['students_deleted']:,}")
        
        if sum(stats['records_deleted'].values()) > 0:
            print(f"\nLinked Records Deleted:")
            for key, value in stats['records_deleted'].items():
                if value > 0:
                    print(f"  - {key.replace('_', ' ').title()}: {value:,}")
        
        if stats["errors"]:
            print(f"\n⚠️  Errors: {len(stats['errors'])}")
        
        if dry_run:
            print("\n✅ DRY RUN COMPLETE - No changes were made")
        else:
            print("\n✅ CLEANUP COMPLETE - Students removed from database")
        
        return stats
        
    except Exception as e:
        error_msg = f"FATAL ERROR: {str(e)}"
        print(f"\n❌ {error_msg}")
        # Don't log to database during error as transaction may be aborted
        
        if not dry_run:
            frappe.db.rollback()
            print("🔄 All changes rolled back")
        
        stats["errors"].append(error_msg)
        return stats


def delete_student_linked_records(student_id: str, dry_run: bool) -> Dict:
    """Delete all child records linked to a student (PostgreSQL compatible)."""
    
    stats = {
        "backend_students": 0,
        "engagement_states": 0,
        "stage_progress": 0,
        "learning_states": 0,
        "onboarding_progress": 0
    }
    
    # Backend Students
    if not dry_run:
        # Count first, then delete (works for both MySQL and PostgreSQL)
        count = frappe.db.count("Backend Students", {"student_id": student_id})
        frappe.db.sql("DELETE FROM `tabBackend Students` WHERE student_id = %s", (student_id,))
        stats["backend_students"] = count
    else:
        stats["backend_students"] = frappe.db.count("Backend Students", {"student_id": student_id})
    
    # EngagementState
    if not dry_run:
        count = frappe.db.count("EngagementState", {"student": student_id})
        frappe.db.sql("DELETE FROM `tabEngagementState` WHERE student = %s", (student_id,))
        stats["engagement_states"] = count
    else:
        stats["engagement_states"] = frappe.db.count("EngagementState", {"student": student_id})
    
    # StudentStageProgress
    if not dry_run:
        count = frappe.db.count("StudentStageProgress", {"student": student_id})
        frappe.db.sql("DELETE FROM `tabStudentStageProgress` WHERE student = %s", (student_id,))
        stats["stage_progress"] = count
    else:
        stats["stage_progress"] = frappe.db.count("StudentStageProgress", {"student": student_id})
    
    # LearningState
    if not dry_run:
        count = frappe.db.count("LearningState", {"student": student_id})
        frappe.db.sql("DELETE FROM `tabLearningState` WHERE student = %s", (student_id,))
        stats["learning_states"] = count
    else:
        stats["learning_states"] = frappe.db.count("LearningState", {"student": student_id})
    
    # StudentOnboardingProgress
    if not dry_run:
        count = frappe.db.count("StudentOnboardingProgress", {"student": student_id})
        frappe.db.sql("DELETE FROM `tabStudentOnboardingProgress` WHERE student = %s", (student_id,))
        stats["onboarding_progress"] = count
    else:
        stats["onboarding_progress"] = frappe.db.count("StudentOnboardingProgress", {"student": student_id})
    
    return stats


# ==============================================================================
# STEP 3: MERGE DUPLICATE STUDENTS
# ==============================================================================

@frappe.whitelist()
def step3_merge_duplicates(
    batch_size: int = 50,
    dry_run: bool = True,
    strict_name_matching: bool = True
) -> Dict:
    """
    STEP 3: Merge duplicate students based on phone numbers.
    
    Args:
        batch_size: Number of phone groups to process before committing
        dry_run: If True, only shows what would be merged
        strict_name_matching: If True, uses strict first-name validation
    
    Returns:
        dict: Merge statistics
    """
    
    # Convert string parameters
    if isinstance(dry_run, str):
        dry_run = dry_run.lower() in ('true', '1', 'yes')
    if isinstance(strict_name_matching, str):
        strict_name_matching = strict_name_matching.lower() in ('true', '1', 'yes')
    if isinstance(batch_size, str):
        batch_size = int(batch_size)
    
    # Reset any failed transactions
    try:
        frappe.db.rollback()
    except Exception:
        pass
    
    print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'LIVE RUN (merging data)'}")
    print(f"Batch Size: {batch_size}")
    print(f"Strict Name Matching: {strict_name_matching}")
    print("─" * 80)
    
    stats = {
        "duplicate_phones": 0,
        "students_processed": 0,
        "students_merged": 0,
        "enrollments_moved": 0,
        "records_deleted": {
            "backend_students": 0,
            "engagement_states": 0,
            "stage_progress": 0,
            "learning_states": 0,
            "onboarding_progress": 0,
            "duplicate_students": 0
        },
        "names_fixed": 0,
        "errors": []
    }
    
    try:
        # Find duplicate phone numbers
        print("\n🔍 Finding duplicate phone numbers...")
        
        duplicates = frappe.db.sql("""
            SELECT phone, COUNT(*) AS cnt
            FROM `tabStudent`
            WHERE phone IS NOT NULL 
              AND phone <> ''
              AND phone <> '0'
            GROUP BY phone
            HAVING COUNT(*) > 1
            ORDER BY cnt DESC
        """, as_dict=True)
        
        stats["duplicate_phones"] = len(duplicates)
        print(f"   Found {len(duplicates):,} duplicate phone numbers\n")
        
        if len(duplicates) == 0:
            print("   ✅ No duplicates found.")
            return stats
        
        # Process each duplicate phone group
        batch_counter = 0
        total_groups = len(duplicates)
        
        for idx, d in enumerate(duplicates, 1):
            if idx % 10 == 0 or idx == 1:
                progress = (idx / total_groups) * 100
                print(f"Progress: {idx:,}/{total_groups:,} ({progress:.1f}%)")
            
            try:
                result = process_duplicate_phone_group(
                    phone=d.phone,
                    dry_run=dry_run,
                    strict_name_matching=strict_name_matching,
                    show_details=(idx <= 5)  # Show details for first 5 groups
                )
                
                # Update statistics
                stats["students_processed"] += result["students_processed"]
                stats["students_merged"] += result["students_merged"]
                stats["enrollments_moved"] += result["enrollments_moved"]
                stats["names_fixed"] += result["names_fixed"]
                
                for key in stats["records_deleted"]:
                    stats["records_deleted"][key] += result["records_deleted"].get(key, 0)
                
                # Commit in batches
                batch_counter += 1
                if not dry_run and batch_counter >= batch_size:
                    frappe.db.commit()
                    print(f"   💾 Committed batch of {batch_counter} phone groups")
                    batch_counter = 0
                    
            except Exception as e:
                error_msg = f"Error processing phone {d.phone}: {str(e)}"
                print(f"   ❌ {error_msg}")
                stats["errors"].append(error_msg)
                # Don't log to database during error as transaction may be aborted
                
                if not dry_run:
                    frappe.db.rollback()
        
        # Final commit
        if not dry_run and batch_counter > 0:
            frappe.db.commit()
            print(f"   💾 Final commit of {batch_counter} phone groups")
        
        # Print summary
        print("\n" + "─" * 80)
        print("MERGE SUMMARY")
        print("─" * 80)
        print(f"Duplicate Phone Numbers: {stats['duplicate_phones']:,}")
        print(f"Students Processed: {stats['students_processed']:,}")
        print(f"Students Merged: {stats['students_merged']:,}")
        print(f"Enrollments Moved: {stats['enrollments_moved']:,}")
        print(f"Names Fixed (Camel Case): {stats['names_fixed']:,}")
        
        if sum(stats['records_deleted'].values()) > 0:
            print(f"\nRecords Deleted:")
            for key, value in stats['records_deleted'].items():
                if value > 0:
                    print(f"  - {key.replace('_', ' ').title()}: {value:,}")
        
        if stats["errors"]:
            print(f"\n⚠️  Errors: {len(stats['errors'])}")
        
        if dry_run:
            print("\n✅ MERGE DRY RUN COMPLETE - No changes were made")
        else:
            print("\n✅ MERGE COMPLETE - Changes saved to database")
        
        return stats
        
    except Exception as e:
        error_msg = f"FATAL ERROR: {str(e)}"
        print(f"\n❌ {error_msg}")
        # Don't log to database during error as transaction may be aborted
        
        if not dry_run:
            frappe.db.rollback()
            print("🔄 All changes rolled back")
        
        stats["errors"].append(error_msg)
        return stats


# ==============================================================================
# HELPER FUNCTIONS FOR MERGE
# ==============================================================================

def names_are_really_similar(name1: str, name2: str, strict: bool = True) -> bool:
    """Check if two names are similar enough to be considered the same person."""
    
    name1_clean = name1.strip().lower()
    name2_clean = name2.strip().lower()

    # Exact match
    if name1_clean == name2_clean:
        return True

    # Substring match
    if name1_clean in name2_clean or name2_clean in name1_clean:
        return True

    # Fuzzy matching
    ratio = fuzz.token_set_ratio(name1_clean, name2_clean)
    words1 = name1_clean.split()
    words2 = name2_clean.split()
    
    if not words1 or not words2:
        return False
    
    first1 = words1[0]
    first2 = words2[0]
    first_ratio = fuzz.ratio(first1, first2)
    
    if strict:
        if first1 == first2 or first_ratio >= 90:
            return ratio >= 85
        return False
    else:
        return ratio >= 80


def to_camel_case(text: str) -> str:
    """Convert a name to proper Camel Case."""
    
    if not text:
        return ""
    
    words = text.strip().split()
    new_words = []

    for w in words:
        if len(w) == 2 and w[1] == ".":  # Initial like 'T.'
            new_words.append(w[0].upper() + ".")
        elif w:
            new_words.append(w[0].upper() + w[1:].lower())
    
    return " ".join(new_words)


def get_enrollment_key(enrollment: Dict) -> Tuple:
    """Create a unique key for an enrollment."""
    
    return (
        enrollment.get("batch"),
        enrollment.get("course"),
        enrollment.get("grade"),
        enrollment.get("date_of_joining"),
        enrollment.get("school")
    )


def process_duplicate_phone_group(
    phone: str,
    dry_run: bool,
    strict_name_matching: bool,
    show_details: bool = False
) -> Dict:
    """Process all students with the same phone number."""
    
    stats = {
        "students_processed": 0,
        "students_merged": 0,
        "enrollments_moved": 0,
        "names_fixed": 0,
        "records_deleted": {
            "backend_students": 0,
            "engagement_states": 0,
            "stage_progress": 0,
            "learning_states": 0,
            "onboarding_progress": 0,
            "duplicate_students": 0
        }
    }
    
    # Get all students with this phone
    students = frappe.get_all(
        "Student",
        filters={"phone": phone},
        fields=["name", "name1", "joined_on"],
        order_by="joined_on DESC"
    )
    
    stats["students_processed"] = len(students)
    
    if len(students) < 2:
        return stats
    
    if show_details:
        print(f"\n   Phone: {phone} ({len(students)} students)")
        for s in students:
            print(f"      - {s.name1} (ID: {s.name}, Joined: {s.joined_on})")
    
    # Group by similar names
    processed = set()
    
    for i, base in enumerate(students):
        if base["name"] in processed:
            continue
        
        # Find similar names
        similar_group = [base]
        for j, other in enumerate(students):
            if i == j or other["name"] in processed:
                continue
            
            if names_are_really_similar(base["name1"], other["name1"], strict=strict_name_matching):
                similar_group.append(other)
                processed.add(other["name"])
        
        if len(similar_group) < 2:
            continue
        
        # Sort by join date (latest = primary)
        similar_group.sort(
            key=lambda x: getdate(x.get("joined_on") or "1900-01-01"),
            reverse=True
        )
        
        primary = similar_group[0]
        duplicates_to_remove = similar_group[1:]
        
        if show_details:
            print(f"      PRIMARY: {primary['name1']}")
            print(f"      DUPLICATES: {len(duplicates_to_remove)}")
        
        # Merge enrollments
        merge_result = merge_enrollments(primary, duplicates_to_remove, dry_run, show_details)
        stats["enrollments_moved"] += merge_result["enrollments_moved"]
        stats["names_fixed"] += merge_result["names_fixed"]
        
        # Delete child records
        for dup in duplicates_to_remove:
            delete_result = delete_linked_records(dup["name"], dry_run, show_details)
            
            for key in stats["records_deleted"]:
                stats["records_deleted"][key] += delete_result.get(key, 0)
            
            stats["students_merged"] += 1
    
    return stats


def merge_enrollments(
    primary: Dict,
    duplicates: List[Dict],
    dry_run: bool,
    show_details: bool = False
) -> Dict:
    """Merge enrollments from duplicate students to primary student."""
    
    stats = {
        "enrollments_moved": 0,
        "names_fixed": 0
    }
    
    # Load primary student document
    primary_doc = frappe.get_doc("Student", primary["name"])
    
    # Fix name to Camel Case
    proper_name = to_camel_case(primary_doc.name1)
    if primary_doc.name1 != proper_name:
        if show_details:
            print(f"         🔤 Fixing name: '{primary_doc.name1}' → '{proper_name}'")
        if not dry_run:
            primary_doc.name1 = proper_name
        stats["names_fixed"] += 1
    
    # Get existing enrollments
    existing_enrollments = set()
    for e in primary_doc.get("enrollments") or []:
        key = get_enrollment_key(e)
        existing_enrollments.add(key)
    
    # Process each duplicate
    for dup in duplicates:
        dup_doc = frappe.get_doc("Student", dup["name"])
        added = 0
        
        for enroll in dup_doc.get("enrollments") or []:
            key = get_enrollment_key(enroll)
            
            if key not in existing_enrollments:
                if not dry_run:
                    primary_doc.append("enrollments", {
                        "batch": enroll.batch,
                        "course": enroll.course,
                        "grade": enroll.grade,
                        "date_of_joining": enroll.date_of_joining,
                        "school": enroll.school
                    })
                existing_enrollments.add(key)
                added += 1
        
        if added > 0:
            stats["enrollments_moved"] += added
    
    # Save primary document
    if (stats["enrollments_moved"] > 0 or stats["names_fixed"] > 0) and not dry_run:
        primary_doc.save(ignore_permissions=True)
    
    return stats


def delete_linked_records(student_id: str, dry_run: bool, show_details: bool = False) -> Dict:
    """Delete all child records linked to a duplicate student (PostgreSQL compatible)."""
    
    stats = {
        "backend_students": 0,
        "engagement_states": 0,
        "stage_progress": 0,
        "learning_states": 0,
        "onboarding_progress": 0,
        "duplicate_students": 0
    }
    
    # Backend Students - count first, then delete
    if not dry_run:
        count = frappe.db.count("Backend Students", {"student_id": student_id})
        frappe.db.sql("DELETE FROM `tabBackend Students` WHERE student_id = %s", (student_id,))
        stats["backend_students"] = count
    else:
        stats["backend_students"] = frappe.db.count("Backend Students", {"student_id": student_id})
    
    # EngagementState
    linked_states = frappe.get_all("EngagementState", filters={"student": student_id}, fields=["name"])
    stats["engagement_states"] = len(linked_states)
    if not dry_run:
        for state in linked_states:
            frappe.delete_doc("EngagementState", state["name"], ignore_permissions=True, force=True)
    
    # StudentStageProgress
    linked_progress = frappe.get_all("StudentStageProgress", filters={"student": student_id}, fields=["name"])
    stats["stage_progress"] = len(linked_progress)
    if not dry_run:
        for progress in linked_progress:
            frappe.delete_doc("StudentStageProgress", progress["name"], ignore_permissions=True, force=True)
    
    # LearningState
    linked_learning = frappe.get_all("LearningState", filters={"student": student_id}, fields=["name"])
    stats["learning_states"] = len(linked_learning)
    if not dry_run:
        for state in linked_learning:
            frappe.delete_doc("LearningState", state["name"], ignore_permissions=True, force=True)
    
    # StudentOnboardingProgress
    linked_onboarding = frappe.get_all("StudentOnboardingProgress", filters={"student": student_id}, fields=["name"])
    stats["onboarding_progress"] = len(linked_onboarding)
    if not dry_run:
        for progress in linked_onboarding:
            frappe.delete_doc("StudentOnboardingProgress", progress["name"], ignore_permissions=True, force=True)
    
    # Delete the duplicate student itself
    if not dry_run:
        frappe.delete_doc("Student", student_id, ignore_permissions=True, force=True)
    stats["duplicate_students"] = 1
    
    return stats


# ==============================================================================
# UTILITY FUNCTIONS
# ==============================================================================

@frappe.whitelist()
def preview_duplicates(limit: int = 10) -> Dict:
    """Preview duplicate students without making any changes."""
    
    if isinstance(limit, str):
        limit = int(limit)
    
    duplicates = frappe.db.sql("""
        SELECT phone, COUNT(*) AS cnt
        FROM `tabStudent`
        WHERE phone IS NOT NULL 
          AND phone <> ''
          AND phone <> '0'
        GROUP BY phone
        HAVING COUNT(*) > 1
        ORDER BY cnt DESC
        LIMIT %s
    """, (limit,), as_dict=True)
    
    print(f"\nShowing top {limit} duplicate phone numbers:\n")
    
    preview_data = []
    
    for idx, d in enumerate(duplicates, 1):
        students = frappe.get_all(
            "Student",
            filters={"phone": d.phone},
            fields=["name", "name1", "joined_on"],
            order_by="joined_on DESC"
        )
        
        print(f"{idx}. Phone: {d.phone} ({d.cnt} students)")
        student_list = []
        for s in students:
            print(f"   - {s.name1} (ID: {s.name}, Joined: {s.joined_on or 'Unknown'})")
            student_list.append({
                "name": s.name,
                "name1": s.name1,
                "joined_on": s.joined_on
            })
        print()
        
        preview_data.append({
            "phone": d.phone,
            "count": d.cnt,
            "students": student_list
        })
    
    return {
        "total_duplicate_phones": len(duplicates),
        "preview": preview_data
    }