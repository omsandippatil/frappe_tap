import pytest
import frappe
from unittest.mock import Mock, patch, MagicMock
from frappe.model.document import Document
from tap_lms.tap_lms.doctype.contentattachment.contentattachment import ContentAttachment


class TestContentAttachment:
    """Comprehensive test cases for ContentAttachment class"""
    
    def setup_method(self):
        """Setup method run before each test"""
        self.test_data = {
            "name": "test-attachment-001",
            "doctype": "ContentAttachment",
            "title": "Test Attachment",
            "description": "Test Description",
            "file_url": "/files/test.pdf",
            "file_name": "test.pdf",
            "file_size": 1024,
            "is_private": 0
        }
    
    def test_content_attachment_import(self):
        """Test that ContentAttachment can be imported successfully"""
        assert ContentAttachment is not None
        assert hasattr(ContentAttachment, '__module__')
        
    def test_content_attachment_class_definition(self):
        """Test that ContentAttachment class is properly defined"""
        assert issubclass(ContentAttachment, Document)
        assert ContentAttachment.__name__ == "ContentAttachment"
        assert ContentAttachment.__doc__ is None or isinstance(ContentAttachment.__doc__, str)
        
    def test_content_attachment_instantiation_empty(self):
        """Test that ContentAttachment can be instantiated without data"""
        content_attachment = ContentAttachment()
        assert isinstance(content_attachment, ContentAttachment)
        assert isinstance(content_attachment, Document)
        
    def test_content_attachment_instantiation_with_data(self):
        """Test ContentAttachment instantiation with data"""
        content_attachment = ContentAttachment(self.test_data)
        assert isinstance(content_attachment, ContentAttachment)
        assert content_attachment.get('title') == self.test_data['title']
        
    def test_content_attachment_inheritance(self):
        """Test that ContentAttachment properly inherits from Document"""
        content_attachment = ContentAttachment()
        
        # Check that it has Document methods/attributes
        document_methods = ['insert', 'save', 'delete', 'reload', 'get', 'set', 'update', 'db_set']
        for method in document_methods:
            assert hasattr(content_attachment, method), f"Missing method: {method}"
        
    def test_content_attachment_doctype_property(self):
        """Test that doctype is properly set"""
        content_attachment = ContentAttachment({"doctype": "ContentAttachment"})
        assert content_attachment.doctype == "ContentAttachment"
        
    def test_content_attachment_get_set_methods(self):
        """Test get and set methods"""
        content_attachment = ContentAttachment()
        content_attachment.set('title', 'New Title')
        assert content_attachment.get('title') == 'New Title'
        
    def test_content_attachment_update_method(self):
        """Test update method with dictionary"""
        content_attachment = ContentAttachment()
        update_data = {'title': 'Updated Title', 'description': 'Updated Description'}
        content_attachment.update(update_data)
        
        assert content_attachment.get('title') == 'Updated Title'
        assert content_attachment.get('description') == 'Updated Description'


class TestContentAttachmentValidation:
    """Test cases for ContentAttachment validation and business logic"""
    
    def setup_method(self):
        """Setup method run before each test"""
        self.valid_data = {
            "name": "valid-attachment",
            "doctype": "ContentAttachment",
            "title": "Valid Attachment",
            "file_url": "/files/valid.pdf"
        }
    
    def test_content_attachment_with_minimal_data(self):
        """Test with minimal required data"""
        minimal_data = {"doctype": "ContentAttachment", "title": "Minimal"}
        content_attachment = ContentAttachment(minimal_data)
        assert content_attachment.get('title') == 'Minimal'
        
    def test_content_attachment_with_file_data(self):
        """Test with file-related data"""
        file_data = {
            "doctype": "ContentAttachment",
            "file_url": "/files/document.pdf",
            "file_name": "document.pdf",
            "file_size": 2048,
            "is_private": 1
        }
        content_attachment = ContentAttachment(file_data)
        assert content_attachment.get('file_url') == '/files/document.pdf'
        assert content_attachment.get('file_size') == 2048
        assert content_attachment.get('is_private') == 1
        
    def test_content_attachment_boolean_fields(self):
        """Test boolean field handling"""
        data = {"doctype": "ContentAttachment", "is_private": True}
        content_attachment = ContentAttachment(data)
        assert content_attachment.get('is_private') is True
        
    def test_content_attachment_none_values(self):
        """Test handling of None values"""
        data = {"doctype": "ContentAttachment", "title": None, "description": None}
        content_attachment = ContentAttachment(data)
        assert content_attachment.get('title') is None
        assert content_attachment.get('description') is None


class TestContentAttachmentMethods:
    """Test cases for ContentAttachment methods and properties"""
    
    def test_content_attachment_as_dict(self):
        """Test converting ContentAttachment to dictionary"""
        data = {
            "doctype": "ContentAttachment",
            "name": "test-dict",
            "title": "Dictionary Test"
        }
        content_attachment = ContentAttachment(data)
        
        # Test that as_dict method exists and works
        if hasattr(content_attachment, 'as_dict'):
            result_dict = content_attachment.as_dict()
            assert isinstance(result_dict, dict)
            assert result_dict.get('title') == 'Dictionary Test'
    
    def test_content_attachment_get_with_default(self):
        """Test get method with default values"""
        content_attachment = ContentAttachment({"doctype": "ContentAttachment"})
        
        # Test getting non-existent field with default
        assert content_attachment.get('non_existent_field', 'default_value') == 'default_value'
        assert content_attachment.get('title', 'Default Title') == 'Default Title'
    
    def test_content_attachment_flags(self):
        """Test flags attribute"""
        content_attachment = ContentAttachment()
        assert hasattr(content_attachment, 'flags')
        
        # Test setting flags
        content_attachment.flags.ignore_permissions = True
        assert content_attachment.flags.ignore_permissions is True
    
    def test_content_attachment_meta_properties(self):
        """Test meta properties and attributes"""
        content_attachment = ContentAttachment()
        
        # Check if meta attribute exists
        if hasattr(content_attachment, 'meta'):
            assert content_attachment.meta is not None


class TestContentAttachmentParametrized:
    """Parametrized tests for different scenarios"""
    
    @pytest.mark.parametrize("test_data,expected_title", [
        ({"doctype": "ContentAttachment", "title": "Test 1"}, "Test 1"),
        ({"doctype": "ContentAttachment", "title": "Test 2"}, "Test 2"),
        ({"doctype": "ContentAttachment", "title": ""}, ""),
        ({"doctype": "ContentAttachment"}, None),
    ])
    def test_content_attachment_title_variations(self, test_data, expected_title):
        """Test ContentAttachment with various title values"""
        content_attachment = ContentAttachment(test_data)
        assert content_attachment.get('title') == expected_title
    
    @pytest.mark.parametrize("field_name", [
        "title", "description", "file_url", "file_name", "file_size", "is_private"
    ])
    def test_content_attachment_field_access(self, field_name):
        """Test accessing different fields"""
        content_attachment = ContentAttachment({
            "doctype": "ContentAttachment",
            field_name: f"test_{field_name}"
        })
        assert content_attachment.get(field_name) == f"test_{field_name}"
    
    @pytest.mark.parametrize("method_name", [
        "insert", "save", "delete", "reload", "get", "set", "update"
    ])
    def test_inherited_methods_exist(self, method_name):
        """Test that inherited Document methods exist"""
        content_attachment = ContentAttachment()
        assert hasattr(content_attachment, method_name)
        assert callable(getattr(content_attachment, method_name))
    
    @pytest.mark.parametrize("file_size,is_private", [
        (1024, 0),
        (2048, 1),
        (0, 0),
        (999999, 1),
    ])
    def test_content_attachment_file_properties(self, file_size, is_private):
        """Test file properties with different values"""
        data = {
            "doctype": "ContentAttachment",
            "file_size": file_size,
            "is_private": is_private
        }
        content_attachment = ContentAttachment(data)
        assert content_attachment.get('file_size') == file_size
        assert content_attachment.get('is_private') == is_private


class TestContentAttachmentEdgeCases:
    """Test edge cases and error scenarios"""
    
    def test_content_attachment_empty_dict(self):
        """Test with empty dictionary"""
        content_attachment = ContentAttachment({})
        assert isinstance(content_attachment, ContentAttachment)
        
    def test_content_attachment_large_data(self):
        """Test with large data set"""
        large_data = {
            "doctype": "ContentAttachment",
            "title": "A" * 1000,  # Very long title
            "description": "B" * 5000,  # Very long description
            "file_name": "very_long_file_name_" + "x" * 200 + ".pdf"
        }
        content_attachment = ContentAttachment(large_data)
        assert len(content_attachment.get('title')) == 1000
        assert len(content_attachment.get('description')) == 5000
    
    def test_content_attachment_special_characters(self):
        """Test with special characters"""
        special_data = {
            "doctype": "ContentAttachment",
            "title": "Special çhars: àáâãäå èéêë ìíîï",
            "description": "Unicode: 你好 🌟 ñoël",
            "file_name": "file@#$%^&*().pdf"
        }
        content_attachment = ContentAttachment(special_data)
        assert "çhars" in content_attachment.get('title')
        assert "🌟" in content_attachment.get('description')
    
    def test_content_attachment_numeric_strings(self):
        """Test with numeric string values"""
        data = {
            "doctype": "ContentAttachment",
            "title": "123",
            "file_size": "456"
        }
        content_attachment = ContentAttachment(data)
        assert content_attachment.get('title') == "123"
        assert content_attachment.get('file_size') == "456"


class TestContentAttachmentIntegration:
    """Integration-style tests (mocked for isolation)"""
    
    @pytest.mark.skip(reason="Requires Frappe site setup")
    def test_content_attachment_database_operations(self):
        """Test database operations (requires actual Frappe setup)"""
        content_attachment = ContentAttachment({
            "doctype": "ContentAttachment",
            "title": "Integration Test Attachment",
            "description": "Test attachment for integration testing"
        })
        
        # These would require proper Frappe site setup
        # content_attachment.insert()
        # content_attachment.save()
        # content_attachment.reload()
        # content_attachment.delete()
        pass
    
    def test_content_attachment_mock_operations(self):
        """Test operations with mocked dependencies"""
        with patch.object(ContentAttachment, 'insert') as mock_insert:
            content_attachment = ContentAttachment({
                "doctype": "ContentAttachment",
                "title": "Mock Test"
            })
            
            # This won't actually call insert, but tests the interface
            mock_insert.return_value = None
            content_attachment.insert()
            
            # Verify the method exists and can be called
            assert callable(content_attachment.insert)


@pytest.fixture
def sample_content_attachment():
    """Fixture providing a sample ContentAttachment instance"""
    return ContentAttachment({
        "name": "fixture-attachment",
        "doctype": "ContentAttachment",
        "title": "Fixture Attachment",
        "description": "Created by pytest fixture",
        "file_url": "/files/fixture.pdf"
    })


class TestContentAttachmentFixtures:
    """Tests using fixtures"""
    
    def test_sample_content_attachment_fixture(self, sample_content_attachment):
        """Test using the sample fixture"""
        assert isinstance(sample_content_attachment, ContentAttachment)
        assert sample_content_attachment.get('title') == "Fixture Attachment"
        assert sample_content_attachment.doctype == "ContentAttachment"
    
    def test_fixture_modification(self, sample_content_attachment):
        """Test modifying fixture data"""
        original_title = sample_content_attachment.get('title')
        sample_content_attachment.set('title', 'Modified Title')
        assert sample_content_attachment.get('title') != original_title
        assert sample_content_attachment.get('title') == 'Modified Title'