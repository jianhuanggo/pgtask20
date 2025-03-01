"""
Unit tests for the Lambda function.
"""
import os
import sys
import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import datetime
import boto3
from boto3.session import Session
import importlib

# Add the project root to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

# Import the Lambda handler
from lambda_docker.app.lambda_function.app import handler

# Mock the PGLogger to avoid side effects during testing
@pytest.fixture
def mock_logger():
    """Mock the logger to avoid side effects during testing."""
    with patch('lambda_docker.app.lambda_function.app.logger') as mock_logger:
        yield mock_logger

@pytest.fixture
def mock_event():
    """Create a mock API Gateway event."""
    return {
        "httpMethod": "GET",
        "path": "/test",
        "headers": {
            "Content-Type": "application/json",
            "User-Agent": "Test Agent"
        },
        "queryStringParameters": {
            "param1": "value1",
            "param2": "value2"
        },
        "body": json.dumps({
            "test": "data"
        })
    }

@pytest.fixture
def mock_context():
    """Create a mock Lambda context."""
    context = MagicMock()
    context.aws_request_id = "test-request-id"
    context.function_name = "test-function"
    context.memory_limit_in_mb = 128
    return context

@pytest.fixture
def mock_boto3_session():
    """Mock boto3 Session for AWS profile-based authentication."""
    with patch('boto3.session.Session') as mock_session:
        # Create a mock session instance
        session_instance = MagicMock()
        mock_session.return_value = session_instance
        
        # Mock the clients that will be created from this session
        mock_clients = {}
        
        def get_client(service_name, **kwargs):
            if service_name not in mock_clients:
                mock_clients[service_name] = MagicMock()
            return mock_clients[service_name]
        
        session_instance.client.side_effect = get_client
        
        yield mock_session

def test_handler_success(mock_event, mock_context, mock_logger, mock_boto3_session):
    """Test that the handler returns a successful response."""
    # Call the handler
    response = handler(mock_event, mock_context)
    
    # Verify the response
    assert response["statusCode"] == 200
    assert "body" in response
    assert "Content-Type" in response["headers"]
    
    # Parse the response body
    body = json.loads(response["body"])
    assert "message" in body
    assert "timestamp" in body
    assert "request_id" in body
    assert "environment" in body
    assert body["request_id"] == mock_context.aws_request_id

def test_handler_exception(mock_event, mock_context, mock_logger, mock_boto3_session):
    """Test that the handler handles exceptions properly."""
    # Mock the logger.info to raise an exception
    mock_logger.info.side_effect = Exception("Test exception")
    
    # Call the handler
    response = handler(mock_event, mock_context)
    
    # Verify the response
    assert response["statusCode"] == 500
    assert "body" in response
    
    # Parse the response body
    body = json.loads(response["body"])
    assert "error" in body
    assert "message" in body
    assert "timestamp" in body
    assert "request_id" in body
    assert body["error"] == "Internal server error"
    assert "Test exception" in body["message"]

def test_aws_profile_authentication(mock_boto3_session):
    """Test AWS profile-based authentication."""
    # Import the config module
    from lambda_docker.deployment.config import get_boto3_session_args
    
    # Test with AWS_PROFILE set
    with patch.dict('os.environ', {'AWS_PROFILE': 'production'}):
        session_args = get_boto3_session_args()
        assert 'profile_name' in session_args
        assert session_args['profile_name'] == 'production'
    
    # Test without AWS_PROFILE set
    with patch.dict('os.environ', {'AWS_PROFILE': ''}):
        session_args = get_boto3_session_args()
        assert 'profile_name' not in session_args

def test_custom_app_location():
    """Test custom application location."""
    # Import the config module
    from lambda_docker.deployment import config
    
    # Save original environment
    original_app_location = os.environ.get('APP_LOCATION', '')
    
    try:
        # Create a temporary directory with a Dockerfile
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a Dockerfile in the temporary directory
            dockerfile_path = Path(temp_dir) / "Dockerfile"
            with open(dockerfile_path, "w") as f:
                f.write("FROM python:3.11-slim\n")
            
            # Test with APP_LOCATION set
            with patch.dict('os.environ', {'APP_LOCATION': temp_dir}):
                # Reload the config module to apply the new APP_LOCATION
                importlib.reload(config)
                
                # Validate the application location
                assert config.APP_LOCATION == temp_dir
                assert config.DOCKERFILE_PATH == dockerfile_path
                assert config.validate_app_location() == True
        
        # Test with invalid APP_LOCATION
        with patch.dict('os.environ', {'APP_LOCATION': '/invalid/path'}):
            # Reload the config module to apply the new APP_LOCATION
            importlib.reload(config)
            
            # Validate the application location
            assert config.validate_app_location() == False
        
        # Test with APP_LOCATION not set
        with patch.dict('os.environ', {'APP_LOCATION': ''}):
            # Reload the config module to apply the new APP_LOCATION
            importlib.reload(config)
            
            # Validate the application location
            assert config.APP_LOCATION is None
            assert config.validate_app_location() == True
    
    finally:
        # Restore original environment
        if original_app_location:
            os.environ['APP_LOCATION'] = original_app_location
        else:
            os.environ.pop('APP_LOCATION', None)
        
        # Reload the config module to restore original state
        importlib.reload(config)
