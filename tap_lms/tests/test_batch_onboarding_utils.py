import pytest
import sys
from unittest.mock import Mock, patch, MagicMock

def test_generate_unique_batch_keyword_coverage():
    """
    Test to achieve 100% coverage for batch_onboarding_utils.py
    Tests the generate_unique_batch_keyword function with all code paths
    """
    
    # Use patch decorators to mock the imports at the function level
    with patch.dict('sys.modules', {
        'frappe': Mock(),
        'random': Mock(),
        'string': Mock(),
    }):
        # Mock the specific modules and functions we need
        mock_frappe = sys.modules['frappe']
        mock_random = sys.modules['random']
        mock_string = sys.modules['string']
        
        # Setup frappe mocks
        mock_frappe.get_doc = Mock()
        mock_frappe.db = Mock()
        mock_frappe.db.exists = Mock()
        
        # Setup random mocks
        mock_random.randint = Mock()
        mock_random.choices = Mock()
        
        # Setup string mocks
        mock_string.ascii_uppercase = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        
        # Import after mocking
        from tap_lms.batch_onboarding_utils import generate_unique_batch_keyword
        
        # Test Case 1: Basic keyword generation (covers lines 5-14)
        # Mock school and batch documents
        mock_school_doc = Mock()
        mock_school_doc.name1 = "Test School Name"
        mock_batch_doc = Mock()
        mock_batch_doc.name1 = "Test Batch Name"
        
        mock_frappe.get_doc.side_effect = [mock_school_doc, mock_batch_doc]
        
        # Mock random generation
        mock_random.randint.return_value = 42
        mock_random.choices.return_value = ['A', 'B']
        
        # Mock that keyword doesn't exist (first attempt succeeds)
        mock_frappe.db.exists.return_value = False
        
        result = generate_unique_batch_keyword("school_id", "batch_id")
        
        # Verify function calls
        assert mock_frappe.get_doc.call_count == 2
        mock_frappe.get_doc.assert_any_call("School", "school_id")
        mock_frappe.get_doc.assert_any_call("Batch", "batch_id")
        
        # Verify random generation calls
        mock_random.randint.assert_called_with(10, 99)
        mock_random.choices.assert_called_with(mock_string.ascii_uppercase, k=2)
        
        # Verify the keyword format
        expected_keyword = "TEST SCHOOL NAME{TEST BATCH NAME}{42}{AB}"
        assert result == expected_keyword
        
        # Verify uniqueness check
        mock_frappe.db.exists.assert_called_with("Batch Onboarding", {"batch_skeyword": expected_keyword})


def test_generate_unique_batch_keyword_collision_handling():
    """
    Test collision handling in while loop (covers lines 17-22)
    """
    
    with patch.dict('sys.modules', {
        'frappe': Mock(),
        'random': Mock(),
        'string': Mock(),
    }):
        mock_frappe = sys.modules['frappe']
        mock_random = sys.modules['random']
        mock_string = sys.modules['string']
        
        # Setup mocks
        mock_frappe.get_doc = Mock()
        mock_frappe.db = Mock()
        mock_string.ascii_uppercase = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        
        # Mock school and batch documents
        mock_school_doc = Mock()
        mock_school_doc.name1 = "Collision School"
        mock_batch_doc = Mock()
        mock_batch_doc.name1 = "Collision Batch"
        
        mock_frappe.get_doc.side_effect = [mock_school_doc, mock_batch_doc]
        
        # Mock random generation - simulate collision scenario
        mock_random.randint.side_effect = [11, 22, 33]  # Three attempts
        mock_random.choices.side_effect = [['X', 'Y'], ['Z', 'A'], ['B', 'C']]
        
        # Mock existence check: first two attempts exist, third doesn't
        mock_frappe.db.exists.side_effect = [True, True, False]
        
        from tap_lms.batch_onboarding_utils import generate_unique_batch_keyword
        
        result = generate_unique_batch_keyword("collision_school", "collision_batch")
        
        # Verify multiple attempts were made
        assert mock_random.randint.call_count == 3
        assert mock_random.choices.call_count == 3
        assert mock_frappe.db.exists.call_count == 3
        
        # Verify final result uses the third attempt
        expected_final_keyword = "COLLISION SCHOOL{COLLISION BATCH}{33}{BC}"
        assert result == expected_final_keyword


def test_generate_unique_batch_keyword_string_processing():
    """
    Test string processing logic (covers lines 9-10)
    """
    
    with patch.dict('sys.modules', {
        'frappe': Mock(),
        'random': Mock(),
        'string': Mock(),
    }):
        mock_frappe = sys.modules['frappe']
        mock_random = sys.modules['random']
        mock_string = sys.modules['string']
        
        # Setup mocks
        mock_frappe.get_doc = Mock()
        mock_frappe.db = Mock()
        mock_frappe.db.exists = Mock(return_value=False)
        mock_string.ascii_uppercase = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        
        # Test with names that need processing (slicing and uppercasing)
        mock_school_doc = Mock()
        mock_school_doc.name1 = "Very Long School Name That Needs Slicing"  # Should be sliced to first 2 chars
        mock_batch_doc = Mock()
        mock_batch_doc.name1 = "long batch name"  # Should be uppercased and sliced
        
        mock_frappe.get_doc.side_effect = [mock_school_doc, mock_batch_doc]
        
        # Mock random generation
        mock_random.randint.return_value = 55
        mock_random.choices.return_value = ['P', 'Q']
        
        from tap_lms.batch_onboarding_utils import generate_unique_batch_keyword
        
        result = generate_unique_batch_keyword("long_school", "long_batch")
        
        # Verify string processing: first 2 characters, uppercased
        # "Very Long School Name That Needs Slicing"[:2].upper() = "VE"
        # "long batch name"[:2].upper() = "LO"
        expected_keyword = "VE{LO}{55}{PQ}"
        assert result == expected_keyword


def test_generate_unique_batch_keyword_edge_cases():
    """
    Test edge cases for string processing
    """
    
    with patch.dict('sys.modules', {
        'frappe': Mock(),
        'random': Mock(),
        'string': Mock(),
    }):
        mock_frappe = sys.modules['frappe']
        mock_random = sys.modules['random']
        mock_string = sys.modules['string']
        
        # Setup mocks
        mock_frappe.get_doc = Mock()
        mock_frappe.db = Mock()
        mock_frappe.db.exists = Mock(return_value=False)
        mock_string.ascii_uppercase = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        
        # Test with very short names
        mock_school_doc = Mock()
        mock_school_doc.name1 = "A"  # Single character
        mock_batch_doc = Mock()
        mock_batch_doc.name1 = "B"  # Single character
        
        mock_frappe.get_doc.side_effect = [mock_school_doc, mock_batch_doc]
        
        mock_random.randint.return_value = 77
        mock_random.choices.return_value = ['R', 'S']
        
        from tap_lms.batch_onboarding_utils import generate_unique_batch_keyword
        
        result = generate_unique_batch_keyword("short_school", "short_batch")
        
        # Should handle short names gracefully
        expected_keyword = "A{B}{77}{RS}"
        assert result == expected_keyword


def test_generate_unique_batch_keyword_empty_names():
    """
    Test with empty or None names
    """
    
    with patch.dict('sys.modules', {
        'frappe': Mock(),
        'random': Mock(),
        'string': Mock(),
    }):
        mock_frappe = sys.modules['frappe']
        mock_random = sys.modules['random']
        mock_string = sys.modules['string']
        
        # Setup mocks
        mock_frappe.get_doc = Mock()
        mock_frappe.db = Mock()
        mock_frappe.db.exists = Mock(return_value=False)
        mock_string.ascii_uppercase = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        
        # Test with empty names
        mock_school_doc = Mock()
        mock_school_doc.name1 = ""  # Empty string
        mock_batch_doc = Mock()
        mock_batch_doc.name1 = ""  # Empty string
        
        mock_frappe.get_doc.side_effect = [mock_school_doc, mock_batch_doc]
        
        mock_random.randint.return_value = 88
        mock_random.choices.return_value = ['T', 'U']
        
        from tap_lms.batch_onboarding_utils import generate_unique_batch_keyword
        
        result = generate_unique_batch_keyword("empty_school", "empty_batch")
        
        # Should handle empty names gracefully
        expected_keyword = "{}{88}{TU}"
        assert result == expected_keyword


def test_generate_unique_batch_keyword_multiple_collisions():
    """
    Test multiple collision scenarios to ensure while loop works correctly
    """
    
    with patch.dict('sys.modules', {
        'frappe': Mock(),
        'random': Mock(),
        'string': Mock(),
    }):
        mock_frappe = sys.modules['frappe']
        mock_random = sys.modules['random']
        mock_string = sys.modules['string']
        
        # Setup mocks
        mock_frappe.get_doc = Mock()
        mock_frappe.db = Mock()
        mock_string.ascii_uppercase = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        
        mock_school_doc = Mock()
        mock_school_doc.name1 = "Multi Collision School"
        mock_batch_doc = Mock()
        mock_batch_doc.name1 = "Multi Collision Batch"
        
        mock_frappe.get_doc.side_effect = [mock_school_doc, mock_batch_doc]
        
        # Simulate 5 collisions before finding unique keyword
        mock_random.randint.side_effect = [10, 20, 30, 40, 50, 60]
        mock_random.choices.side_effect = [
            ['A', 'A'], ['B', 'B'], ['C', 'C'], 
            ['D', 'D'], ['E', 'E'], ['F', 'F']
        ]
        
        # First 5 attempts exist, 6th doesn't
        mock_frappe.db.exists.side_effect = [True, True, True, True, True, False]
        
        from tap_lms.batch_onboarding_utils import generate_unique_batch_keyword
        
        result = generate_unique_batch_keyword("multi_school", "multi_batch")
        
        # Verify all attempts were made
        assert mock_random.randint.call_count == 6
        assert mock_random.choices.call_count == 6
        assert mock_frappe.db.exists.call_count == 6
        
        # Verify final successful result
        expected_final_keyword = "MU{MU}{60}{FF}"
        assert result == expected_final_keyword


def test_generate_unique_batch_keyword_function_signature():
    """
    Test function signature and parameter handling
    """
    
    with patch.dict('sys.modules', {
        'frappe': Mock(),
        'random': Mock(),
        'string': Mock(),
    }):
        from tap_lms.batch_onboarding_utils import generate_unique_batch_keyword
        
        # Test function exists and is callable
        assert callable(generate_unique_batch_keyword)
        
        # Test function signature
        import inspect
        sig = inspect.signature(generate_unique_batch_keyword)
        assert len(sig.parameters) == 2  # school, batch
        
        param_names = list(sig.parameters.keys())
        assert param_names == ['school', 'batch']


def test_import_coverage():
    """
    Test import statements coverage (covers lines 1-3)
    """
    
    with patch.dict('sys.modules', {
        'frappe': Mock(),
        'random': Mock(),
        'string': Mock(),
    }):
        # This test ensures the import statements are executed
        try:
            from tap_lms.batch_onboarding_utils import generate_unique_batch_keyword
            assert True  # Import successful
        except ImportError:
            pytest.fail("Import failed")


def test_complete_workflow_integration():
    """
    Test complete workflow to ensure all lines are covered
    """
    
    with patch.dict('sys.modules', {
        'frappe': Mock(),
        'random': Mock(),
        'string': Mock(),
    }):
        mock_frappe = sys.modules['frappe']
        mock_random = sys.modules['random']
        mock_string = sys.modules['string']
        
        # Setup comprehensive mocks
        mock_frappe.get_doc = Mock()
        mock_frappe.db = Mock()
        mock_string.ascii_uppercase = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        
        # Create realistic test data
        mock_school_doc = Mock()
        mock_school_doc.name1 = "Integration Test School"
        mock_batch_doc = Mock()
        mock_batch_doc.name1 = "Integration Test Batch"
        
        mock_frappe.get_doc.side_effect = [mock_school_doc, mock_batch_doc]
        
        # Test one collision, then success
        mock_random.randint.side_effect = [15, 25]
        mock_random.choices.side_effect = [['G', 'H'], ['I', 'J']]
        mock_frappe.db.exists.side_effect = [True, False]
        
        from tap_lms.batch_onboarding_utils import generate_unique_batch_keyword
        
        result = generate_unique_batch_keyword("integration_school", "integration_batch")
        
        # Verify all components worked together
        assert mock_frappe.get_doc.call_count == 2
        assert mock_random.randint.call_count == 2
        assert mock_random.choices.call_count == 2
        assert mock_frappe.db.exists.call_count == 2
        
        # Verify final result format
        expected_result = "IN{IN}{25}{IJ}"
        assert result == expected_result


def test_all_lines_executed():
    """
    Comprehensive test to ensure every single line is executed
    """
    
    with patch.dict('sys.modules', {
        'frappe': Mock(),
        'random': Mock(),
        'string': Mock(),
    }):
        mock_frappe = sys.modules['frappe']
        mock_random = sys.modules['random']
        mock_string = sys.modules['string']
        
        # Line 1-3: Import statements (covered by import)
        from tap_lms.batch_onboarding_utils import generate_unique_batch_keyword
        
        # Line 5: Function definition (covered by calling function)
        # Line 6-7: frappe.get_doc calls
        mock_school = Mock()
        mock_school.name1 = "Complete Test School"
        mock_batch = Mock()
        mock_batch.name1 = "Complete Test Batch"
        
        mock_frappe.get_doc.side_effect = [mock_school, mock_batch]
        mock_frappe.db = Mock()
        mock_frappe.db.exists = Mock(return_value=False)
        
        # Line 9-10: String processing
        mock_string.ascii_uppercase = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        
        # Line 11-12: Random generation
        mock_random.randint = Mock(return_value=99)
        mock_random.choices = Mock(return_value=['Z', 'Z'])
        
        # Line 14: Initial keyword formation
        # Line 16: Comment (no execution needed)
        # Line 17: While loop condition (will be False, so loop body not executed)
        # Line 22: Return statement
        
        result = generate_unique_batch_keyword("complete_school", "complete_batch")
        
        # Verify the result follows expected pattern
        expected = "CO{CO}{99}{ZZ}"
        assert result == expected
        
        # Now test the while loop execution (lines 18-21)
        mock_frappe.db.exists.side_effect = [True, False]  # First exists, second doesn't
        mock_random.randint.side_effect = [11, 22]
        mock_random.choices.side_effect = [['A', 'B'], ['C', 'D']]
        
        # Reset get_doc for second call
        mock_frappe.get_doc.side_effect = [mock_school, mock_batch]
        
        result2 = generate_unique_batch_keyword("loop_school", "loop_batch")
        
        # This should have executed the while loop body (lines 18-21)
        expected2 = "CO{CO}{22}{CD}"
        assert result2 == expected2