"""
Script to delete an API Gateway REST API.
"""
import os
import sys
import boto3
from boto3.session import Session

# Add the project root to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

# Import the deployment config and logging
from lambda_docker.deployment.config import (
    AWS_REGION, get_boto3_session_args
)
from _logging.pg_logger import get_logger, log_method, error_logger

# Configure the logger
logger = get_logger(
    name="api_gateway_deployment",
    log_level=os.environ.get("LOG_LEVEL", "INFO"),
    log_to_console=True,
    log_to_file=True,
    log_file_path=os.environ.get("LOG_FILE_PATH", "/tmp/api_gateway_deployment.log"),
    use_json_format=False
)

# API Gateway Configuration
API_NAME = os.environ.get("API_GATEWAY_NAME", "lambda-docker-function-api")

@log_method(level="info")
def find_api_by_name():
    """Find an API Gateway REST API by name."""
    try:
        # Create a session with the profile if specified
        session = Session(**get_boto3_session_args())
        apigw_client = session.client('apigateway')
        
        response = apigw_client.get_rest_apis()
        for item in response['items']:
            if item['name'] == API_NAME:
                return item['id']
        
        logger.info(f"API Gateway REST API '{API_NAME}' not found")
        return None
    except Exception as e:
        error_logger(
            "find_api_by_name",
            str(e),
            logger=logger,
            mode="error"
        )
        return None

@log_method(level="info")
def delete_api(api_id):
    """Delete an API Gateway REST API."""
    try:
        # Create a session with the profile if specified
        session = Session(**get_boto3_session_args())
        apigw_client = session.client('apigateway')
        
        apigw_client.delete_rest_api(
            restApiId=api_id
        )
        
        logger.info(f"Deleted API Gateway REST API with ID: {api_id}")
        return True
    except Exception as e:
        error_logger(
            "delete_api",
            str(e),
            logger=logger,
            mode="error"
        )
        return False

@log_method(level="info")
def delete_api_gateway():
    """Delete the API Gateway REST API."""
    # Find the API by name
    api_id = find_api_by_name()
    if not api_id:
        logger.error(f"API Gateway REST API '{API_NAME}' not found")
        return False
    
    # Delete the API
    if not delete_api(api_id):
        logger.error(f"Failed to delete API Gateway REST API '{API_NAME}'")
        return False
    
    logger.info(f"API Gateway REST API '{API_NAME}' deleted successfully")
    return True

if __name__ == "__main__":
    delete_api_gateway()
