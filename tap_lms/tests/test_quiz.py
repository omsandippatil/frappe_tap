import unittest
import frappe
from tap_lms.tap_lms.doctype.quiz.quiz import Quiz


class TestQuiz(unittest.TestCase):
    """Test cases for Quiz doctype to achieve 100% code coverage"""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a test quiz document
        self.quiz_data = {
            "doctype": "Quiz",
            "name": "Test Quiz 1",
            "title": "Sample Quiz for Testing"
        }
    
    def tearDown(self):
        """Clean up after each test method."""
        # Delete any test documents created
        try:
            if frappe.db.exists("Quiz", "Test Quiz 1"):
                frappe.delete_doc("Quiz", "Test Quiz 1", force=True)
        except:
            pass
    
    def test_quiz_class_import(self):
        """Test that Quiz class can be imported successfully"""
        # This test ensures the import statement is executed
        from tap_lms.tap_lms.doctype.quiz.quiz import Quiz
        self.assertTrue(Quiz)
        
    def test_quiz_class_inheritance(self):
        """Test that Quiz class inherits from Document"""
        # This test ensures the class definition line is executed
        self.assertTrue(issubclass(Quiz, frappe.model.document.Document))
    
    def test_quiz_instantiation(self):
        """Test Quiz class can be instantiated"""
        # This test ensures the class definition and pass statement are executed
        quiz = Quiz()
        self.assertIsInstance(quiz, Quiz)
        self.assertIsInstance(quiz, frappe.model.document.Document)
    
    def test_quiz_creation_with_data(self):
        """Test Quiz document creation with data"""
        # Create quiz with data to ensure all code paths are covered
        quiz = Quiz(self.quiz_data)
        self.assertEqual(quiz.doctype, "Quiz")
        self.assertEqual(quiz.name, "Test Quiz 1")
    
    def test_quiz_document_methods(self):
        """Test inherited Document methods work correctly"""
        # This ensures the inheritance works and covers the class definition
        quiz = Quiz(self.quiz_data)
        
        # Test that inherited methods are accessible
        self.assertTrue(hasattr(quiz, 'insert'))
        self.assertTrue(hasattr(quiz, 'save'))
        self.assertTrue(hasattr(quiz, 'delete'))
    
    def test_quiz_with_frappe_new_doc(self):
        """Test Quiz creation using frappe.new_doc"""
        # Another way to ensure class instantiation is covered
        quiz = frappe.new_doc("Quiz")
        quiz.update(self.quiz_data)
        self.assertIsInstance(quiz, Quiz)
    
    def test_multiple_quiz_instances(self):
        """Test creating multiple Quiz instances"""
        # Ensure class definition is executed multiple times
        quiz1 = Quiz({"doctype": "Quiz", "name": "Quiz 1"})
        quiz2 = Quiz({"doctype": "Quiz", "name": "Quiz 2"})
        
        self.assertIsInstance(quiz1, Quiz)
        self.assertIsInstance(quiz2, Quiz)
        self.assertNotEqual(id(quiz1), id(quiz2))


# Additional test class for edge cases
class TestQuizEdgeCases(unittest.TestCase):
    """Additional test cases to ensure complete coverage"""
    
    def test_quiz_empty_initialization(self):
        """Test Quiz with no parameters"""
        quiz = Quiz()
        self.assertIsInstance(quiz, Quiz)
    
    def test_quiz_class_attributes(self):
        """Test Quiz class has expected attributes"""
        # Verify class definition is properly executed
        self.assertTrue(hasattr(Quiz, '__module__'))
        self.assertTrue(hasattr(Quiz, '__doc__'))
    
    def test_import_statement_coverage(self):
        """Explicit test to cover import statement"""
        # Import the module to ensure import line is executed
        import tap_lms.tap_lms.doctype.quiz.quiz as quiz_module
        self.assertTrue(hasattr(quiz_module, 'Document'))
        self.assertTrue(hasattr(quiz_module, 'Quiz'))


if __name__ == '__main__':
    # Run the tests
    unittest.main()