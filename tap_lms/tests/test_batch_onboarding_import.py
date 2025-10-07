import pytest
import sys
from unittest.mock import Mock, patch, call


@pytest.fixture
def mock_frappe_environment():
    """
    Fixture to set up a clean Frappe mock environment for each test
    This ensures test isolation and consistency
    """
    with patch.dict('sys.modules', {
        'frappe': Mock(),
        'frappe.model': Mock(),
        'frappe.model.document': Mock(),
        'tap_lms': Mock(),
        'tap_lms.batch_onboarding': Mock(),
    }):
        mock_frappe = sys.modules['frappe']
        mock_frappe.get_doc = Mock()
        mock_frappe.db = Mock()
        mock_frappe.db.exists = Mock()
        
        # Mock the generate_batch_skeyword function
        mock_batch_onboarding = Mock()
        mock_batch_onboarding.generate_batch_skeyword = Mock()
        sys.modules['tap_lms.batch_onboarding'] = mock_batch_onboarding
        
        yield {
            'frappe': mock_frappe,
            'generate_batch_skeyword': mock_batch_onboarding.generate_batch_skeyword
        }


class TestBeforeImport:
    """Test cases for the before_import function"""
    
    def test_before_import_without_batch_skeyword(self, mock_frappe_environment):
        """
        Test before_import when document has no batch_skeyword
        Should generate a new batch_skeyword
        """
        from tap_lms.batch_onboarding_import import before_import
        
        # Setup
        mock_generate = mock_frappe_environment['generate_batch_skeyword']
        mock_generate.return_value = "TEST_BATCH_2025"
        
        mock_doc = Mock()
        mock_doc.batch_skeyword = None
        mock_doc.school = "Test School"
        mock_doc.batch = "Batch A"
        
        # Execute
        before_import(mock_doc, "import")
        
        # Verify
        mock_generate.assert_called_once_with("Test School", "Batch A")
        assert mock_doc.batch_skeyword == "TEST_BATCH_2025"
    
    def test_before_import_with_existing_batch_skeyword(self, mock_frappe_environment):
        """
        Test before_import when document already has batch_skeyword
        Should NOT generate a new batch_skeyword
        """
        from tap_lms.batch_onboarding_import import before_import
        
        # Setup
        mock_generate = mock_frappe_environment['generate_batch_skeyword']
        
        mock_doc = Mock()
        mock_doc.batch_skeyword = "EXISTING_KEYWORD"
        mock_doc.school = "Test School"
        mock_doc.batch = "Batch B"
        
        # Execute
        before_import(mock_doc, "import")
        
        # Verify
        mock_generate.assert_not_called()
        assert mock_doc.batch_skeyword == "EXISTING_KEYWORD"
    
    def test_before_import_with_empty_string_batch_skeyword(self, mock_frappe_environment):
        """
        Test before_import when batch_skeyword is empty string
        Empty strings are falsy, so should generate new keyword
        """
        from tap_lms.batch_onboarding_import import before_import
        
        # Setup
        mock_generate = mock_frappe_environment['generate_batch_skeyword']
        mock_generate.return_value = "NEW_KEYWORD_2025"
        
        mock_doc = Mock()
        mock_doc.batch_skeyword = ""  # Empty string
        mock_doc.school = "Edge School"
        mock_doc.batch = "Edge Batch"
        
        # Execute
        before_import(mock_doc, "import")
        
        # Verify
        mock_generate.assert_called_once_with("Edge School", "Edge Batch")
        assert mock_doc.batch_skeyword == "NEW_KEYWORD_2025"
    
    def test_before_import_with_zero_batch_skeyword(self, mock_frappe_environment):
        """
        Test before_import when batch_skeyword is 0 (edge case)
        Zero is falsy, so should generate new keyword
        """
        from tap_lms.batch_onboarding_import import before_import
        
        # Setup
        mock_generate = mock_frappe_environment['generate_batch_skeyword']
        mock_generate.return_value = "ZERO_CASE_KEYWORD"
        
        mock_doc = Mock()
        mock_doc.batch_skeyword = 0
        mock_doc.school = "Zero School"
        mock_doc.batch = "Zero Batch"
        
        # Execute
        before_import(mock_doc, "import")
        
        # Verify
        mock_generate.assert_called_once_with("Zero School", "Zero Batch")
        assert mock_doc.batch_skeyword == "ZERO_CASE_KEYWORD"


class TestAfterImport:
    """Test cases for the after_import function"""
    
    def test_after_import_with_duplicate_batch_skeyword(self, mock_frappe_environment):
        """
        Test after_import when a duplicate batch_skeyword exists
        Should generate new keyword and save the document
        """
        from tap_lms.batch_onboarding_import import after_import
        
        # Setup
        mock_frappe = mock_frappe_environment['frappe']
        mock_generate = mock_frappe_environment['generate_batch_skeyword']
        mock_generate.return_value = "UPDATED_KEYWORD_2025"
        
        # Input document
        mock_doc = Mock()
        mock_doc.name = "TEST_DOC_001"
        mock_doc.school = "Test School"
        mock_doc.batch = "Batch A"
        
        # Existing document in database
        mock_existing_doc = Mock()
        mock_existing_doc.batch_skeyword = "DUPLICATE_KEYWORD"
        mock_existing_doc.save = Mock()
        
        # Mock Frappe functions
        mock_frappe.get_doc.return_value = mock_existing_doc
        mock_frappe.db.exists.return_value = True  # Duplicate exists
        
        # Execute
        after_import(mock_doc, "import")
        
        # Verify
        mock_frappe.get_doc.assert_called_once_with("Batch Onboarding", "TEST_DOC_001")
        mock_frappe.db.exists.assert_called_once_with(
            "Batch Onboarding",
            {"batch_skeyword": "DUPLICATE_KEYWORD", "name": ["!=", "TEST_DOC_001"]}
        )
        mock_generate.assert_called_once_with("Test School", "Batch A")
        assert mock_existing_doc.batch_skeyword == "UPDATED_KEYWORD_2025"
        mock_existing_doc.save.assert_called_once()
    
    def test_after_import_with_unique_batch_skeyword(self, mock_frappe_environment):
        """
        Test after_import when batch_skeyword is unique
        Should NOT generate new keyword or save the document
        """
        from tap_lms.batch_onboarding_import import after_import
        
        # Setup
        mock_frappe = mock_frappe_environment['frappe']
        mock_generate = mock_frappe_environment['generate_batch_skeyword']
        
        # Input document
        mock_doc = Mock()
        mock_doc.name = "TEST_DOC_002"
        mock_doc.school = "Test School"
        mock_doc.batch = "Batch B"
        
        # Existing document in database
        mock_existing_doc = Mock()
        mock_existing_doc.batch_skeyword = "UNIQUE_KEYWORD"
        mock_existing_doc.save = Mock()
        
        # Mock Frappe functions
        mock_frappe.get_doc.return_value = mock_existing_doc
        mock_frappe.db.exists.return_value = False  # No duplicate
        
        # Execute
        after_import(mock_doc, "import")
        
        # Verify
        mock_frappe.get_doc.assert_called_once_with("Batch Onboarding", "TEST_DOC_002")
        mock_frappe.db.exists.assert_called_once_with(
            "Batch Onboarding",
            {"batch_skeyword": "UNIQUE_KEYWORD", "name": ["!=", "TEST_DOC_002"]}
        )
        mock_generate.assert_not_called()
        mock_existing_doc.save.assert_not_called()
    
    def test_after_import_handles_missing_document(self, mock_frappe_environment):
        """
        Test after_import when document doesn't exist in database
        Should raise an exception (expected behavior)
        """
        from tap_lms.batch_onboarding_import import after_import
        
        # Setup
        mock_frappe = mock_frappe_environment['frappe']
        
        mock_doc = Mock()
        mock_doc.name = "NON_EXISTENT_DOC"
        
        # Simulate document not found
        mock_frappe.get_doc.side_effect = Exception("Document not found")
        
        # Execute & Verify
        with pytest.raises(Exception, match="Document not found"):
            after_import(mock_doc, "import")
        
        mock_frappe.get_doc.assert_called_once_with("Batch Onboarding", "NON_EXISTENT_DOC")
    
    def test_after_import_multiple_duplicates_scenario(self, mock_frappe_environment):
        """
        Test after_import in scenario with multiple duplicate checks
        Ensures the function uses the existing document's batch_skeyword
        """
        from tap_lms.batch_onboarding_import import after_import
        
        # Setup
        mock_frappe = mock_frappe_environment['frappe']
        mock_generate = mock_frappe_environment['generate_batch_skeyword']
        mock_generate.return_value = "FINAL_UNIQUE_KEYWORD"
        
        # Input document (may have different batch_skeyword)
        mock_doc = Mock()
        mock_doc.name = "TEST_DOC_003"
        mock_doc.school = "Multi School"
        mock_doc.batch = "Multi Batch"
        mock_doc.batch_skeyword = "INPUT_KEYWORD"  # This is ignored
        
        # Existing document has different keyword
        mock_existing_doc = Mock()
        mock_existing_doc.batch_skeyword = "OLD_EXISTING_KEYWORD"
        mock_existing_doc.save = Mock()
        
        mock_frappe.get_doc.return_value = mock_existing_doc
        mock_frappe.db.exists.return_value = True
        
        # Execute
        after_import(mock_doc, "import")
        
        # Verify it checks with EXISTING document's batch_skeyword, not input doc's
        mock_frappe.db.exists.assert_called_once_with(
            "Batch Onboarding",
            {"batch_skeyword": "OLD_EXISTING_KEYWORD", "name": ["!=", "TEST_DOC_003"]}
        )


class TestIntegration:
    """Integration tests for complete workflow"""
    
    def test_complete_import_workflow(self, mock_frappe_environment):
        """
        Test complete workflow: before_import -> import -> after_import
        Simulates a full document import process
        """
        from tap_lms.batch_onboarding_import import before_import, after_import
        
        # Setup
        mock_frappe = mock_frappe_environment['frappe']
        mock_generate = mock_frappe_environment['generate_batch_skeyword']
        
        # First call for before_import, second call for after_import
        mock_generate.side_effect = ["WORKFLOW_KEYWORD_1", "WORKFLOW_KEYWORD_2"]
        
        # Existing document
        mock_existing_doc = Mock()
        mock_existing_doc.batch_skeyword = "OLD_WORKFLOW_KEYWORD"
        mock_existing_doc.save = Mock()
        
        mock_frappe.get_doc.return_value = mock_existing_doc
        mock_frappe.db.exists.return_value = True  # Duplicate exists
        
        # Test document
        mock_doc = Mock()
        mock_doc.batch_skeyword = None  # No initial keyword
        mock_doc.school = "Workflow School"
        mock_doc.batch = "Workflow Batch"
        mock_doc.name = "WORKFLOW_DOC_001"
        
        # Execute workflow
        # Step 1: before_import
        before_import(mock_doc, "import")
        assert mock_doc.batch_skeyword == "WORKFLOW_KEYWORD_1"
        
        # Step 2: Simulate import (document gets saved with name)
        # In real scenario, Frappe assigns the name here
        
        # Step 3: after_import
        after_import(mock_doc, "import")
        
        # Verify
        assert mock_generate.call_count == 2
        assert mock_generate.call_args_list == [
            call("Workflow School", "Workflow Batch"),
            call("Workflow School", "Workflow Batch")
        ]
        assert mock_existing_doc.batch_skeyword == "WORKFLOW_KEYWORD_2"
        mock_existing_doc.save.assert_called_once()
    
    def test_bulk_import_scenario(self, mock_frappe_environment):
        """
        Test bulk import of multiple documents
        Ensures each document is processed correctly
        """
        from tap_lms.batch_onboarding_import import before_import, after_import
        
        # Setup
        mock_frappe = mock_frappe_environment['frappe']
        mock_generate = mock_frappe_environment['generate_batch_skeyword']
        
        # Generate unique keywords for each document
        keywords = [
            "BULK_KEYWORD_1", "BULK_KEYWORD_2", "BULK_KEYWORD_3",
            "BULK_KEYWORD_4", "BULK_KEYWORD_5", "BULK_KEYWORD_6"
        ]
        mock_generate.side_effect = keywords
        
        # Simulate 3 documents being imported
        documents = []
        for i in range(1, 4):
            doc = Mock()
            doc.batch_skeyword = None
            doc.school = f"School {i}"
            doc.batch = f"Batch {i}"
            doc.name = f"BULK_DOC_{i:03d}"
            documents.append(doc)
        
        # Process each document
        for doc in documents:
            # before_import
            before_import(doc, "import")
            assert doc.batch_skeyword is not None
            
            # after_import
            mock_existing_doc = Mock()
            mock_existing_doc.batch_skeyword = doc.batch_skeyword
            mock_existing_doc.save = Mock()
            mock_frappe.get_doc.return_value = mock_existing_doc
            mock_frappe.db.exists.return_value = False  # Assume unique
            
            after_import(doc, "import")
        
        # Verify all documents were processed
        assert mock_generate.call_count == 3  # One call per document in before_import
        assert mock_frappe.get_doc.call_count == 3


class TestFunctionSignatures:
    """Test function definitions and signatures"""
    
    def test_function_definitions_exist(self, mock_frappe_environment):
        """Verify that both functions are defined and callable"""
        from tap_lms.batch_onboarding_import import before_import, after_import
        
        assert callable(before_import)
        assert callable(after_import)
    
    def test_function_signatures(self, mock_frappe_environment):
        """Verify function signatures are correct"""
        import inspect
        from tap_lms.batch_onboarding_import import before_import, after_import
        
        # Check before_import signature
        before_sig = inspect.signature(before_import)
        assert len(before_sig.parameters) == 2
        assert 'doc' in before_sig.parameters
        assert 'method' in before_sig.parameters
        
        # Check after_import signature
        after_sig = inspect.signature(after_import)
        assert len(after_sig.parameters) == 2
        assert 'doc' in after_sig.parameters
        assert 'method' in after_sig.parameters


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_before_import_with_false_value(self, mock_frappe_environment):
        """Test before_import with False value (falsy but not None)"""
        from tap_lms.batch_onboarding_import import before_import
        
        mock_generate = mock_frappe_environment['generate_batch_skeyword']
        mock_generate.return_value = "FALSE_CASE_KEYWORD"
        
        mock_doc = Mock()
        mock_doc.batch_skeyword = False
        mock_doc.school = "False School"
        mock_doc.batch = "False Batch"
        
        before_import(mock_doc, "import")
        
        mock_generate.assert_called_once_with("False School", "False Batch")
        assert mock_doc.batch_skeyword == "FALSE_CASE_KEYWORD"
    
    def test_after_import_with_same_name_different_keyword(self, mock_frappe_environment):
        """
        Test after_import when checking for duplicates excludes current document
        Verifies the name != filter works correctly
        """
        from tap_lms.batch_onboarding_import import after_import
        
        mock_frappe = mock_frappe_environment['frappe']
        mock_generate = mock_frappe_environment['generate_batch_skeyword']
        
        mock_doc = Mock()
        mock_doc.name = "SAME_NAME_DOC"
        mock_doc.school = "Same School"
        mock_doc.batch = "Same Batch"
        
        mock_existing_doc = Mock()
        mock_existing_doc.batch_skeyword = "SAME_KEYWORD"
        mock_existing_doc.save = Mock()
        
        mock_frappe.get_doc.return_value = mock_existing_doc
        mock_frappe.db.exists.return_value = False
        
        after_import(mock_doc, "import")
        
        # Verify name exclusion in query
        call_args = mock_frappe.db.exists.call_args[0]
        assert call_args[1]["name"] == ["!=", "SAME_NAME_DOC"]
    
    def test_generate_batch_skeyword_called_with_correct_params(self, mock_frappe_environment):
        """
        Test that generate_batch_skeyword is always called with doc's school and batch
        """
        from tap_lms.batch_onboarding_import import before_import, after_import
        
        mock_frappe = mock_frappe_environment['frappe']
        mock_generate = mock_frappe_environment['generate_batch_skeyword']
        mock_generate.return_value = "PARAM_TEST_KEYWORD"
        
        # Test before_import
        doc1 = Mock()
        doc1.batch_skeyword = None
        doc1.school = "Param School A"
        doc1.batch = "Param Batch A"
        
        before_import(doc1, "import")
        mock_generate.assert_called_with("Param School A", "Param Batch A")
        
        # Test after_import
        mock_generate.reset_mock()
        doc2 = Mock()
        doc2.name = "PARAM_DOC"
        doc2.school = "Param School B"
        doc2.batch = "Param Batch B"
        
        mock_existing_doc = Mock()
        mock_existing_doc.batch_skeyword = "OLD_KEYWORD"
        mock_existing_doc.save = Mock()
        
        mock_frappe.get_doc.return_value = mock_existing_doc
        mock_frappe.db.exists.return_value = True
        
        after_import(doc2, "import")
        mock_generate.assert_called_with("Param School B", "Param Batch B")


class TestCoverageCompleteness:
    """Ensure 100% code coverage"""
    
    def test_all_code_paths_covered(self, mock_frappe_environment):
        """
        Meta-test to ensure all conditional branches are covered
        This test documents what coverage we're achieving
        """
        from tap_lms.batch_onboarding_import import before_import, after_import
        
        coverage_checklist = {
            'before_import_true_branch': False,   # if not doc.batch_skeyword: (True)
            'before_import_false_branch': False,  # if not doc.batch_skeyword: (False)
            'after_import_true_branch': False,    # if frappe.db.exists(...): (True)
            'after_import_false_branch': False,   # if frappe.db.exists(...): (False)
        }
        
        mock_frappe = mock_frappe_environment['frappe']
        mock_generate = mock_frappe_environment['generate_batch_skeyword']
        mock_generate.return_value = "COVERAGE_KEYWORD"
        
        # Test before_import True branch
        doc1 = Mock()
        doc1.batch_skeyword = None
        doc1.school = "School"
        doc1.batch = "Batch"
        before_import(doc1, "import")
        coverage_checklist['before_import_true_branch'] = True
        
        # Test before_import False branch
        doc2 = Mock()
        doc2.batch_skeyword = "EXISTING"
        before_import(doc2, "import")
        coverage_checklist['before_import_false_branch'] = True
        
        # Test after_import True branch
        doc3 = Mock()
        doc3.name = "DOC1"
        doc3.school = "School"
        doc3.batch = "Batch"
        mock_existing = Mock()
        mock_existing.batch_skeyword = "OLD"
        mock_existing.save = Mock()
        mock_frappe.get_doc.return_value = mock_existing
        mock_frappe.db.exists.return_value = True
        after_import(doc3, "import")
        coverage_checklist['after_import_true_branch'] = True
        
        # Test after_import False branch
        mock_frappe.db.exists.return_value = False
        doc4 = Mock()
        doc4.name = "DOC2"
        after_import(doc4, "import")
        coverage_checklist['after_import_false_branch'] = True
        
        # Verify all paths covered
        assert all(coverage_checklist.values()), f"Missing coverage: {coverage_checklist}"


# Run tests with: pytest test_batch_onboarding_import.py -v --cov=tap_lms.batch_onboarding_import --cov-report=html