import pytest
from frappe.model.document import Document
from tap_lms.tap_lms.doctype.rabbitmq_settings.rabbitmq_settings import RabbitmqSettings


class TestRabbitmqSettings:
    """Test cases for RabbitmqSettings doctype"""
    
    def test_rabbitmq_settings_creation(self):
        """Test that RabbitmqSettings can be instantiated"""
        # Test basic instantiation
        settings = RabbitmqSettings()
        assert isinstance(settings, Document)
        assert isinstance(settings, RabbitmqSettings)
    
    def test_rabbitmq_settings_inheritance(self):
        """Test that RabbitmqSettings properly inherits from Document"""
        settings = RabbitmqSettings()
        
        # Verify it has Document methods
        assert hasattr(settings, 'save')
        assert hasattr(settings, 'delete')
        assert hasattr(settings, 'insert')
        
    def test_rabbitmq_settings_pass_statement(self):
        """Test that the pass statement executes without error"""
        # This will execute the __init__ method and the pass statement
        settings = RabbitmqSettings()
        
        # If we get here without exception, the pass statement executed successfully
        assert settings is not None
        
    def test_rabbitmq_settings_with_data(self):
        """Test RabbitmqSettings with sample data"""
        # Create with some typical RabbitMQ configuration data
        data = {
            'doctype': 'RabbitmqSettings',
            'host': 'localhost',
            'port': 5672,
            'username': 'guest',
            'password': 'guest',
            'virtual_host': '/'
        }
        
        settings = RabbitmqSettings(data)
        assert settings.doctype == 'RabbitmqSettings'
        
    def test_rabbitmq_settings_empty_init(self):
        """Test RabbitmqSettings with empty initialization"""
        settings = RabbitmqSettings({})
        assert isinstance(settings, RabbitmqSettings)


# Additional test for import coverage
def test_import_statement():
    """Test that the import statement is covered"""
    from frappe.model.document import Document
    assert Document is not None


# Test to ensure class definition is covered
def test_class_definition():
    """Test that the class definition line is covered"""
    assert hasattr(RabbitmqSettings, '__bases__')
    assert Document in RabbitmqSettings.__bases__