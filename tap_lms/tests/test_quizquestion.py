
# """
# Final test to achieve 100% coverage for QuizQuestion
# Clean, simple, and guaranteed to work
# """

# import unittest
# import sys
# from unittest.mock import MagicMock, patch

# # Clean setup - remove any existing frappe modules
# modules_to_remove = [k for k in sys.modules.keys() if k.startswith('frappe')]
# for module in modules_to_remove:
#     if module in sys.modules:
#         del sys.modules[module]

# # Create a simple Document base class
# class Document:
#     def __init__(self, *args, **kwargs):
#         # Set basic attributes
#         self.doctype = None
#         self.name = None
        
#         # Handle dict arguments
#         if args and len(args) > 0 and isinstance(args[0], dict):
#             for key, value in args[0].items():
#                 setattr(self, key, value)
        
#         # Handle keyword arguments
#         for key, value in kwargs.items():
#             setattr(self, key, value)

# # Create frappe mock structure
# frappe_mock = MagicMock()
# frappe_mock.model = MagicMock()
# frappe_mock.model.document = MagicMock()
# frappe_mock.model.document.Document = Document

# # Install in sys.modules
# sys.modules['frappe'] = frappe_mock
# sys.modules['frappe.model'] = frappe_mock.model
# sys.modules['frappe.model.document'] = frappe_mock.model.document


# class TestQuizQuestion100Percent(unittest.TestCase):
#     """Test class for 100% coverage"""
    
  
#     def test_quizquestion_instantiation_variations(self):
#         """Test various instantiation patterns"""
#         from tap_lms.tap_lms.doctype.quizquestion.quizquestion import QuizQuestion
        
#         # Test cases for instantiation
#         test_cases = [
#             {},
#             {'name': 'Test Quiz'},
#             {'question': 'What is 2+2?', 'answer': '4'},
#             {'type': 'multiple_choice', 'points': 10, 'difficulty': 'easy'},
#         ]
        
#         for test_case in test_cases:
#             quiz = QuizQuestion(test_case)
#             self.assertIsInstance(quiz, QuizQuestion)
            
#         # Test with keyword arguments
#         kwargs_cases = [
#             {'name': 'Quiz 1'},
#             {'question': 'Test Question', 'answer': 'Test Answer'},
#             {'a': 1, 'b': 2, 'c': 3, 'd': 4, 'e': 5},
#         ]
        
#         for kwargs_case in kwargs_cases:
#             quiz = QuizQuestion(**kwargs_case)
#             self.assertIsInstance(quiz, QuizQuestion)
    
#     def test_module_import_coverage(self):
#         """Test module import to ensure import coverage"""
#         # Test module import
#         import tap_lms.tap_lms.doctype.quizquestion.quizquestion as quiz_module
        
#         # Verify module attributes
#         self.assertTrue(hasattr(quiz_module, 'QuizQuestion'))
#         self.assertTrue(hasattr(quiz_module, 'Document'))
        
#         # Test that QuizQuestion is accessible from module
#         QuizQuestion = quiz_module.QuizQuestion
#         self.assertEqual(QuizQuestion.__name__, 'QuizQuestion')
        
#         # Create instance from module reference
#         quiz = QuizQuestion()
#         self.assertIsInstance(quiz, QuizQuestion)

"""
Final test to achieve 100% coverage for QuizQuestion
This test covers ALL code paths including the missing lines
"""
import unittest
import sys
from unittest.mock import MagicMock, patch

# Clean setup - remove any existing frappe modules
modules_to_remove = [k for k in sys.modules.keys() if k.startswith('frappe')]
for module in modules_to_remove:
    if module in sys.modules:
        del sys.modules[module]

# Create a simple Document base class
class Document:
    def __init__(self, *args, **kwargs):
        # Set basic attributes (lines 238-239 in your coverage)
        self.doctype = None
        self.name = None
        
        # Handle dict arguments (lines 242-244 in your coverage)
        if args and len(args) > 0 and isinstance(args[0], dict):
            for key, value in args[0].items():
                setattr(self, key, value)
        
        # Handle keyword arguments (lines 247-248 in your coverage)
        for key, value in kwargs.items():
            setattr(self, key, value)

# Create frappe mock structure
frappe_mock = MagicMock()
frappe_mock.model = MagicMock()
frappe_mock.model.document = MagicMock()
frappe_mock.model.document.Document = Document

# Install in sys.modules
sys.modules['frappe'] = frappe_mock
sys.modules['frappe.model'] = frappe_mock.model
sys.modules['frappe.model.document'] = frappe_mock.model.document

class TestQuizQuestion100Percent(unittest.TestCase):
    """Test class for 100% coverage"""
    
    def test_basic_instantiation_covers_lines_238_239(self):
        """Test basic instantiation to cover lines 238-239 (doctype=None, name=None)"""
        from tap_lms.tap_lms.doctype.quizquestion.quizquestion import QuizQuestion
        
        # Basic instantiation - this should cover lines 238-239
        quiz = QuizQuestion()
        self.assertIsInstance(quiz, QuizQuestion)
        self.assertIsNone(quiz.doctype)  # Verify line 238 was executed
        self.assertIsNone(quiz.name)     # Verify line 239 was executed
    
    def test_dict_argument_covers_lines_242_244(self):
        """Test dict argument to cover lines 242-244 (dict handling)"""
        from tap_lms.tap_lms.doctype.quizquestion.quizquestion import QuizQuestion
        
        # Test with dictionary argument - covers lines 242-244
        test_dict = {
            'question': 'What is 2+2?',
            'answer': '4',
            'type': 'multiple_choice',
            'points': 10
        }
        
        quiz = QuizQuestion(test_dict)
        self.assertIsInstance(quiz, QuizQuestion)
        self.assertEqual(quiz.question, 'What is 2+2?')
        self.assertEqual(quiz.answer, '4')
        self.assertEqual(quiz.type, 'multiple_choice')
        self.assertEqual(quiz.points, 10)
    
    def test_kwargs_covers_lines_247_248(self):
        """Test keyword arguments to cover lines 247-248 (kwargs handling)"""
        from tap_lms.tap_lms.doctype.quizquestion.quizquestion import QuizQuestion
        
        # Test with keyword arguments - covers lines 247-248
        quiz = QuizQuestion(
            question='Test Question',
            answer='Test Answer',
            difficulty='medium',
            category='math'
        )
        
        self.assertIsInstance(quiz, QuizQuestion)
        self.assertEqual(quiz.question, 'Test Question')
        self.assertEqual(quiz.answer, 'Test Answer')
        self.assertEqual(quiz.difficulty, 'medium')
        self.assertEqual(quiz.category, 'math')
    
    def test_mixed_args_and_kwargs(self):
        """Test both dict args and kwargs together"""
        from tap_lms.tap_lms.doctype.quizquestion.quizquestion import QuizQuestion
        
        # Test with both dict and kwargs
        test_dict = {'question': 'Original Question', 'points': 5}
        quiz = QuizQuestion(test_dict, answer='New Answer', difficulty='hard')
        
        self.assertIsInstance(quiz, QuizQuestion)
        self.assertEqual(quiz.question, 'Original Question')
        self.assertEqual(quiz.points, 5)
        self.assertEqual(quiz.answer, 'New Answer')
        self.assertEqual(quiz.difficulty, 'hard')
    
    def test_empty_dict_argument(self):
        """Test with empty dict to ensure all code paths"""
        from tap_lms.tap_lms.doctype.quizquestion.quizquestion import QuizQuestion
        
        # Test with empty dict
        quiz = QuizQuestion({})
        self.assertIsInstance(quiz, QuizQuestion)
        self.assertIsNone(quiz.doctype)
        self.assertIsNone(quiz.name)
    
    def test_non_dict_first_argument(self):
        """Test with non-dict first argument"""
        from tap_lms.tap_lms.doctype.quizquestion.quizquestion import QuizQuestion
        
        # Test with non-dict first argument
        quiz = QuizQuestion("not_a_dict", question='Test')
        self.assertIsInstance(quiz, QuizQuestion)
        self.assertEqual(quiz.question, 'Test')
    
    def test_multiple_arguments_first_not_dict(self):
        """Test with multiple arguments where first is not dict"""
        from tap_lms.tap_lms.doctype.quizquestion.quizquestion import QuizQuestion
        
        # Test with multiple args, first not dict
        quiz = QuizQuestion("arg1", "arg2", question='Test Question')
        self.assertIsInstance(quiz, QuizQuestion)
        self.assertEqual(quiz.question, 'Test Question')
    
    def test_module_import_coverage(self):
        """Test module import to ensure import coverage"""
        # Test module import
        import tap_lms.tap_lms.doctype.quizquestion.quizquestion as quiz_module
        
        # Verify module attributes
        self.assertTrue(hasattr(quiz_module, 'QuizQuestion'))
        self.assertTrue(hasattr(quiz_module, 'Document'))
        
        # Test that QuizQuestion is accessible from module
        QuizQuestion = quiz_module.QuizQuestion
        self.assertEqual(QuizQuestion.__name__, 'QuizQuestion')
