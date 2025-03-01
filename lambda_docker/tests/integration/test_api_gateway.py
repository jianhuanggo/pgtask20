"""
Integration tests for the API Gateway REST API.
"""
import os
import sys
import json
import requests
import argparse
from datetime import datetime

# Add the project root to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

# Import the deployment config and logging
from lambda_docker.deployment.config import AWS_REGION
from _logging.pg_logger import get_logger, log_method, error_logger

# Configure the logger
logger = get_logger(
    name="api_gateway_test",
    log_level=os.environ.get("LOG_LEVEL", "INFO"),
    log_to_console=True,
    log_to_file=True,
    log_file_path=os.environ.get("LOG_FILE_PATH", "/tmp/api_gateway_test.log"),
    use_json_format=False
)

@log_method(level="info")
def test_get_endpoint(api_url):
    """Test the GET endpoint."""
    try:
        logger.info(f"Testing GET endpoint: {api_url}/api")
        response = requests.get(f"{api_url}/api")
        
        # Verify response status code
        assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
        
        # Verify response content
        data = response.json()
        assert "message" in data, "Response missing 'message' field"
        assert "timestamp" in data, "Response missing 'timestamp' field"
        assert "request_id" in data, "Response missing 'request_id' field"
        assert "environment" in data, "Response missing 'environment' field"
        
        logger.info("GET endpoint test passed")
        return True
    except Exception as e:
        error_logger(
            "test_get_endpoint",
            str(e),
            logger=logger,
            mode="error"
        )
        return False

@log_method(level="info")
def test_post_endpoint(api_url):
    """Test the POST endpoint."""
    try:
        logger.info(f"Testing POST endpoint: {api_url}/api")
        
        # Create test payload
        payload = {
            "name": "Test User",
            "email": "test@example.com",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Send POST request
        response = requests.post(
            f"{api_url}/api",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        # Verify response status code
        assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
        
        # Verify response content
        data = response.json()
        assert "message" in data, "Response missing 'message' field"
        assert "timestamp" in data, "Response missing 'timestamp' field"
        assert "request_id" in data, "Response missing 'request_id' field"
        assert "environment" in data, "Response missing 'environment' field"
        assert "received_data" in data, "Response missing 'received_data' field"
        
        # Verify received data
        received_data = data["received_data"]
        assert received_data["name"] == payload["name"], "Received data name mismatch"
        assert received_data["email"] == payload["email"], "Received data email mismatch"
        
        logger.info("POST endpoint test passed")
        return True
    except Exception as e:
        error_logger(
            "test_post_endpoint",
            str(e),
            logger=logger,
            mode="error"
        )
        return False

@log_method(level="info")
def test_put_endpoint(api_url):
    """Test the PUT endpoint."""
    try:
        logger.info(f"Testing PUT endpoint: {api_url}/api")
        
        # Create test payload
        payload = {
            "id": "12345",
            "name": "Updated User",
            "email": "updated@example.com",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Send PUT request
        response = requests.put(
            f"{api_url}/api",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        # Verify response status code
        assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
        
        # Verify response content
        data = response.json()
        assert "message" in data, "Response missing 'message' field"
        assert "timestamp" in data, "Response missing 'timestamp' field"
        assert "request_id" in data, "Response missing 'request_id' field"
        assert "environment" in data, "Response missing 'environment' field"
        assert "updated_data" in data, "Response missing 'updated_data' field"
        
        # Verify updated data
        updated_data = data["updated_data"]
        assert updated_data["id"] == payload["id"], "Updated data id mismatch"
        assert updated_data["name"] == payload["name"], "Updated data name mismatch"
        assert updated_data["email"] == payload["email"], "Updated data email mismatch"
        
        logger.info("PUT endpoint test passed")
        return True
    except Exception as e:
        error_logger(
            "test_put_endpoint",
            str(e),
            logger=logger,
            mode="error"
        )
        return False

@log_method(level="info")
def test_delete_endpoint(api_url):
    """Test the DELETE endpoint."""
    try:
        logger.info(f"Testing DELETE endpoint: {api_url}/api")
        
        # Send DELETE request
        response = requests.delete(f"{api_url}/api")
        
        # Verify response status code
        assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
        
        # Verify response content
        data = response.json()
        assert "message" in data, "Response missing 'message' field"
        assert "timestamp" in data, "Response missing 'timestamp' field"
        assert "request_id" in data, "Response missing 'request_id' field"
        assert "environment" in data, "Response missing 'environment' field"
        
        logger.info("DELETE endpoint test passed")
        return True
    except Exception as e:
        error_logger(
            "test_delete_endpoint",
            str(e),
            logger=logger,
            mode="error"
        )
        return False

@log_method(level="info")
def test_invalid_method(api_url):
    """Test an invalid HTTP method."""
    try:
        logger.info(f"Testing invalid HTTP method: {api_url}/api")
        
        # Send OPTIONS request (not implemented in the Lambda function)
        response = requests.options(f"{api_url}/api")
        
        # Verify response status code (should be 405 Method Not Allowed)
        assert response.status_code == 405, f"Expected status code 405, got {response.status_code}"
        
        # Verify response content
        data = response.json()
        assert "error" in data, "Response missing 'error' field"
        assert "message" in data, "Response missing 'message' field"
        
        logger.info("Invalid method test passed")
        return True
    except Exception as e:
        error_logger(
            "test_invalid_method",
            str(e),
            logger=logger,
            mode="error"
        )
        return False

@log_method(level="info")
def test_invalid_path(api_url):
    """Test an invalid path."""
    try:
        logger.info(f"Testing invalid path: {api_url}/invalid")
        
        # Send GET request to invalid path
        response = requests.get(f"{api_url}/invalid")
        
        # Verify response status code (should be 404 Not Found)
        assert response.status_code == 404, f"Expected status code 404, got {response.status_code}"
        
        logger.info("Invalid path test passed")
        return True
    except Exception as e:
        error_logger(
            "test_invalid_path",
            str(e),
            logger=logger,
            mode="error"
        )
        return False

@log_method(level="info")
def run_tests(api_url):
    """Run all API Gateway tests."""
    logger.info(f"Running API Gateway tests against URL: {api_url}")
    
    # Run tests
    tests = [
        ("GET Endpoint", test_get_endpoint),
        ("POST Endpoint", test_post_endpoint),
        ("PUT Endpoint", test_put_endpoint),
        ("DELETE Endpoint", test_delete_endpoint),
        ("Invalid Method", test_invalid_method),
        ("Invalid Path", test_invalid_path)
    ]
    
    # Track test results
    passed = 0
    failed = 0
    
    # Run each test
    for test_name, test_func in tests:
        logger.info(f"Running test: {test_name}")
        if test_func(api_url):
            logger.info(f"Test passed: {test_name}")
            passed += 1
        else:
            logger.error(f"Test failed: {test_name}")
            failed += 1
    
    # Print test summary
    logger.info(f"Test summary: {passed} passed, {failed} failed")
    
    # Return True if all tests passed
    return failed == 0

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Test API Gateway REST API")
    parser.add_argument("--api-url", type=str, required=True, help="API Gateway URL")
    return parser.parse_args()

if __name__ == "__main__":
    # Parse command-line arguments
    args = parse_args()
    
    # Run tests
    success = run_tests(args.api_url)
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1)
