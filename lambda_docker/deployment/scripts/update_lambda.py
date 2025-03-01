"""
Script to update AWS Lambda function with the ECR image.
"""
import os
import sys
import boto3
import time
from boto3.session import Session

# Add the project root to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

# Import the deployment config and logging
from lambda_docker.deployment.config import (
    AWS_REGION, LAMBDA_FUNCTION_NAME, LAMBDA_MEMORY_SIZE,
    LAMBDA_TIMEOUT, LAMBDA_ENVIRONMENT, get_image_uri,
    get_boto3_session_args
)
from _logging.pg_logger import get_logger, log_method, error_logger

# Configure the logger
logger = get_logger(
    name="update_lambda",
    log_level=os.environ.get("LOG_LEVEL", "INFO"),
    log_to_console=True,
    log_to_file=True,
    log_file_path=os.environ.get("LOG_FILE_PATH", "/tmp/lambda_update.log")
)

@log_method(level="info")
def lambda_function_exists():
    """Check if the Lambda function exists."""
    try:
        # Create a session with the profile if specified
        session = Session(**get_boto3_session_args())
        lambda_client = session.client('lambda')
        lambda_client.get_function(FunctionName=LAMBDA_FUNCTION_NAME)
        logger.info(f"Lambda function {LAMBDA_FUNCTION_NAME} exists")
        return True
    except lambda_client.exceptions.ResourceNotFoundException:
        logger.info(f"Lambda function {LAMBDA_FUNCTION_NAME} does not exist")
        return False
    except Exception as e:
        error_logger(
            "lambda_function_exists",
            str(e),
            logger=logger,
            mode="error"
        )
        return False

@log_method(level="info")
def create_lambda_function():
    """Create a new Lambda function."""
    try:
        # Create a session with the profile if specified
        session = Session(**get_boto3_session_args())
        lambda_client = session.client('lambda')
        image_uri = get_image_uri()
        
        if not image_uri:
            logger.error("Failed to get ECR image URI")
            return False
        
        response = lambda_client.create_function(
            FunctionName=LAMBDA_FUNCTION_NAME,
            PackageType='Image',
            Code={
                'ImageUri': image_uri
            },
            Role=os.environ.get('LAMBDA_EXECUTION_ROLE'),
            Timeout=LAMBDA_TIMEOUT,
            MemorySize=LAMBDA_MEMORY_SIZE,
            Environment=LAMBDA_ENVIRONMENT
        )
        
        function_arn = response['FunctionArn']
        logger.info(f"Created Lambda function: {LAMBDA_FUNCTION_NAME} (ARN: {function_arn})")
        return True
    except Exception as e:
        error_logger(
            "create_lambda_function",
            str(e),
            logger=logger,
            mode="error"
        )
        return False

@log_method(level="info")
def update_lambda_function():
    """Update an existing Lambda function."""
    try:
        # Create a session with the profile if specified
        session = Session(**get_boto3_session_args())
        lambda_client = session.client('lambda')
        image_uri = get_image_uri()
        
        if not image_uri:
            logger.error("Failed to get ECR image URI")
            return False
        
        # Update function code
        lambda_client.update_function_code(
            FunctionName=LAMBDA_FUNCTION_NAME,
            ImageUri=image_uri
        )
        logger.info(f"Updated Lambda function code: {LAMBDA_FUNCTION_NAME} with image {image_uri}")
        
        # Update function configuration
        lambda_client.update_function_configuration(
            FunctionName=LAMBDA_FUNCTION_NAME,
            Timeout=LAMBDA_TIMEOUT,
            MemorySize=LAMBDA_MEMORY_SIZE,
            Environment=LAMBDA_ENVIRONMENT
        )
        logger.info(f"Updated Lambda function configuration: {LAMBDA_FUNCTION_NAME}")
        
        return True
    except Exception as e:
        error_logger(
            "update_lambda_function",
            str(e),
            logger=logger,
            mode="error"
        )
        return False

@log_method(level="info")
def wait_for_function_update():
    """Wait for the Lambda function update to complete."""
    try:
        # Create a session with the profile if specified
        session = Session(**get_boto3_session_args())
        lambda_client = session.client('lambda')
        
        logger.info(f"Waiting for Lambda function {LAMBDA_FUNCTION_NAME} update to complete...")
        waiter = lambda_client.get_waiter('function_updated')
        waiter.wait(
            FunctionName=LAMBDA_FUNCTION_NAME,
            WaiterConfig={
                'Delay': 5,
                'MaxAttempts': 30
            }
        )
        logger.info(f"Lambda function {LAMBDA_FUNCTION_NAME} update completed")
        return True
    except Exception as e:
        error_logger(
            "wait_for_function_update",
            str(e),
            logger=logger,
            mode="error"
        )
        return False

@log_method(level="info")
def update_lambda():
    """Main function to update the Lambda function."""
    start_time = time.time()
    logger.info(f"Starting Lambda function update: {LAMBDA_FUNCTION_NAME}")
    
    # Check if Lambda execution role is set
    if not os.environ.get('LAMBDA_EXECUTION_ROLE'):
        logger.error("LAMBDA_EXECUTION_ROLE environment variable is not set")
        return False
    
    # Check if function exists
    if lambda_function_exists():
        # Update existing function
        if not update_lambda_function():
            logger.error("Failed to update Lambda function")
            return False
        
        # Wait for update to complete
        if not wait_for_function_update():
            logger.error("Failed to wait for Lambda function update")
            return False
    else:
        # Create new function
        if not create_lambda_function():
            logger.error("Failed to create Lambda function")
            return False
    
    elapsed_time = time.time() - start_time
    logger.info(f"Lambda function update completed successfully in {elapsed_time:.2f} seconds")
    return True

if __name__ == "__main__":
    update_lambda()
