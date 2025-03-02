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
    get_boto3_session_args, get_lambda_role_arn,
    VPC_ENABLED, VPC_ID, VPC_SUBNETS, VPC_SECURITY_GROUPS,
    IAM_ROLE_NAME, IAM_ROLE_DESCRIPTION, IAM_ROLE_RECREATE
)
from lambda_docker.deployment.scripts.manage_iam_role import (
    check_role_exists, create_role, recreate_role, get_role_arn
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
        
        # Get or create the IAM role
        role_arn = get_lambda_role_arn()
        if not role_arn:
            logger.info(f"IAM role not found, creating new role: {IAM_ROLE_NAME}")
            if IAM_ROLE_RECREATE:
                logger.info(f"Recreating IAM role: {IAM_ROLE_NAME}")
                role_arn = recreate_role(IAM_ROLE_NAME, IAM_ROLE_DESCRIPTION, VPC_ENABLED)
            else:
                logger.info(f"Creating IAM role: {IAM_ROLE_NAME}")
                role_arn = create_role(IAM_ROLE_NAME, IAM_ROLE_DESCRIPTION, VPC_ENABLED)
            
            if not role_arn:
                logger.error(f"Failed to create IAM role: {IAM_ROLE_NAME}")
                return False
        
        # Prepare function arguments
        function_args = {
            'FunctionName': LAMBDA_FUNCTION_NAME,
            'PackageType': 'Image',
            'Code': {
                'ImageUri': image_uri
            },
            'Role': role_arn,
            'Timeout': LAMBDA_TIMEOUT,
            'MemorySize': LAMBDA_MEMORY_SIZE,
            'Environment': LAMBDA_ENVIRONMENT
        }
        
        # Add VPC configuration if enabled
        if VPC_ENABLED and VPC_ID and VPC_SUBNETS and VPC_SECURITY_GROUPS:
            function_args['VpcConfig'] = {
                'SubnetIds': VPC_SUBNETS,
                'SecurityGroupIds': VPC_SECURITY_GROUPS
            }
            logger.info(f"Adding VPC configuration: VPC_ID={VPC_ID}, Subnets={VPC_SUBNETS}, Security Groups={VPC_SECURITY_GROUPS}")
        
        # Create the Lambda function
        response = lambda_client.create_function(**function_args)
        
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
        
        # Get or update the IAM role
        role_arn = get_lambda_role_arn()
        if not role_arn:
            logger.info(f"IAM role not found, creating new role: {IAM_ROLE_NAME}")
            if IAM_ROLE_RECREATE:
                logger.info(f"Recreating IAM role: {IAM_ROLE_NAME}")
                role_arn = recreate_role(IAM_ROLE_NAME, IAM_ROLE_DESCRIPTION, VPC_ENABLED)
            else:
                logger.info(f"Creating IAM role: {IAM_ROLE_NAME}")
                role_arn = create_role(IAM_ROLE_NAME, IAM_ROLE_DESCRIPTION, VPC_ENABLED)
            
            if not role_arn:
                logger.error(f"Failed to create IAM role: {IAM_ROLE_NAME}")
                return False
        elif IAM_ROLE_RECREATE:
            logger.info(f"Recreating IAM role: {IAM_ROLE_NAME}")
            role_arn = recreate_role(IAM_ROLE_NAME, IAM_ROLE_DESCRIPTION, VPC_ENABLED)
            if not role_arn:
                logger.error(f"Failed to recreate IAM role: {IAM_ROLE_NAME}")
                return False
        
        # Update function code
        lambda_client.update_function_code(
            FunctionName=LAMBDA_FUNCTION_NAME,
            ImageUri=image_uri
        )
        logger.info(f"Updated Lambda function code: {LAMBDA_FUNCTION_NAME} with image {image_uri}")
        
        # Prepare configuration arguments
        config_args = {
            'FunctionName': LAMBDA_FUNCTION_NAME,
            'Role': role_arn,
            'Timeout': LAMBDA_TIMEOUT,
            'MemorySize': LAMBDA_MEMORY_SIZE,
            'Environment': LAMBDA_ENVIRONMENT
        }
        
        # Add VPC configuration if enabled
        if VPC_ENABLED and VPC_ID and VPC_SUBNETS and VPC_SECURITY_GROUPS:
            config_args['VpcConfig'] = {
                'SubnetIds': VPC_SUBNETS,
                'SecurityGroupIds': VPC_SECURITY_GROUPS
            }
            logger.info(f"Adding VPC configuration: VPC_ID={VPC_ID}, Subnets={VPC_SUBNETS}, Security Groups={VPC_SECURITY_GROUPS}")
        
        # Update function configuration
        lambda_client.update_function_configuration(**config_args)
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
def delete_lambda_function():
    """Delete a Lambda function if it exists."""
    try:
        # Check if function exists
        if not lambda_function_exists():
            logger.info(f"Lambda function {LAMBDA_FUNCTION_NAME} does not exist, nothing to delete")
            return True
        
        # Create a session with the profile if specified
        session = Session(**get_boto3_session_args())
        lambda_client = session.client('lambda')
        
        # Delete the function
        lambda_client.delete_function(FunctionName=LAMBDA_FUNCTION_NAME)
        logger.info(f"Deleted Lambda function: {LAMBDA_FUNCTION_NAME}")
        
        # Wait for the function to be deleted
        logger.info(f"Waiting for Lambda function {LAMBDA_FUNCTION_NAME} to be deleted...")
        time.sleep(10)  # Lambda deletions can take time to propagate
        
        return True
    except Exception as e:
        error_logger(
            "delete_lambda_function",
            str(e),
            logger=logger,
            mode="error"
        )
        return False

@log_method(level="info")
def recreate_lambda_function():
    """Delete and recreate a Lambda function."""
    try:
        # Delete the function if it exists
        if not delete_lambda_function():
            logger.error(f"Failed to delete Lambda function: {LAMBDA_FUNCTION_NAME}")
            return False
        
        # Create the function
        if not create_lambda_function():
            logger.error(f"Failed to create Lambda function: {LAMBDA_FUNCTION_NAME}")
            return False
        
        logger.info(f"Successfully recreated Lambda function: {LAMBDA_FUNCTION_NAME}")
        return True
    except Exception as e:
        error_logger(
            "recreate_lambda_function",
            str(e),
            logger=logger,
            mode="error"
        )
        return False

@log_method(level="info")
def update_lambda(recreate=False):
    """Main function to update the Lambda function."""
    start_time = time.time()
    logger.info(f"Starting Lambda function update: {LAMBDA_FUNCTION_NAME}")
    
    # If recreate is requested, delete and recreate the function
    if recreate:
        logger.info(f"Recreating Lambda function: {LAMBDA_FUNCTION_NAME}")
        if not recreate_lambda_function():
            logger.error("Failed to recreate Lambda function")
            return False
    else:
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
    import argparse
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Update AWS Lambda function with ECR image")
    parser.add_argument("--recreate", action="store_true", help="Delete and recreate the Lambda function")
    parser.add_argument("--env-file", type=str, help="Path to .env file")
    args = parser.parse_args()
    
    # Load environment variables from .env file if specified
    if args.env_file:
        from dotenv import load_dotenv
        load_dotenv(args.env_file)
    
    # Update Lambda function
    update_lambda(recreate=args.recreate)
