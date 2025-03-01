"""
Script to create an API Gateway REST API for the Lambda function.
"""
import os
import sys
import json
import boto3
from boto3.session import Session

# Add the project root to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

# Import the deployment config and logging
from lambda_docker.deployment.config import (
    AWS_REGION, LAMBDA_FUNCTION_NAME, get_boto3_session_args
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
API_NAME = os.environ.get("API_GATEWAY_NAME", f"{LAMBDA_FUNCTION_NAME}-api")
API_DESCRIPTION = os.environ.get("API_GATEWAY_DESCRIPTION", f"REST API for {LAMBDA_FUNCTION_NAME}")
API_STAGE_NAME = os.environ.get("API_GATEWAY_STAGE_NAME", "prod")

@log_method(level="info")
def create_rest_api():
    """Create a new REST API in API Gateway."""
    try:
        # Create a session with the profile if specified
        session = Session(**get_boto3_session_args())
        apigw_client = session.client('apigateway')
        
        # Check if API already exists
        existing_api = find_existing_api(apigw_client)
        if existing_api:
            logger.info(f"API Gateway REST API '{API_NAME}' already exists with ID: {existing_api['id']}")
            return existing_api['id']
        
        # Create a new REST API
        response = apigw_client.create_rest_api(
            name=API_NAME,
            description=API_DESCRIPTION,
            endpointConfiguration={
                'types': ['REGIONAL']
            }
        )
        
        api_id = response['id']
        logger.info(f"Created API Gateway REST API '{API_NAME}' with ID: {api_id}")
        return api_id
    except Exception as e:
        error_logger(
            "create_rest_api",
            str(e),
            logger=logger,
            mode="error"
        )
        return None

@log_method(level="info")
def find_existing_api(apigw_client):
    """Find an existing API Gateway REST API by name."""
    try:
        response = apigw_client.get_rest_apis()
        for item in response['items']:
            if item['name'] == API_NAME:
                return item
        return None
    except Exception as e:
        error_logger(
            "find_existing_api",
            str(e),
            logger=logger,
            mode="error"
        )
        return None

@log_method(level="info")
def get_root_resource_id(api_id):
    """Get the root resource ID for the API."""
    try:
        # Create a session with the profile if specified
        session = Session(**get_boto3_session_args())
        apigw_client = session.client('apigateway')
        
        response = apigw_client.get_resources(
            restApiId=api_id
        )
        
        for resource in response['items']:
            if resource['path'] == '/':
                return resource['id']
        
        return None
    except Exception as e:
        error_logger(
            "get_root_resource_id",
            str(e),
            logger=logger,
            mode="error"
        )
        return None

@log_method(level="info")
def create_resource(api_id, parent_id, path_part):
    """Create a new resource in the API."""
    try:
        # Create a session with the profile if specified
        session = Session(**get_boto3_session_args())
        apigw_client = session.client('apigateway')
        
        response = apigw_client.create_resource(
            restApiId=api_id,
            parentId=parent_id,
            pathPart=path_part
        )
        
        resource_id = response['id']
        logger.info(f"Created resource '{path_part}' with ID: {resource_id}")
        return resource_id
    except Exception as e:
        error_logger(
            "create_resource",
            str(e),
            logger=logger,
            mode="error"
        )
        return None

@log_method(level="info")
def create_method(api_id, resource_id, http_method="GET"):
    """Create a method for the resource."""
    try:
        # Create a session with the profile if specified
        session = Session(**get_boto3_session_args())
        apigw_client = session.client('apigateway')
        
        response = apigw_client.put_method(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod=http_method,
            authorizationType='NONE',
            apiKeyRequired=False
        )
        
        logger.info(f"Created {http_method} method for resource ID: {resource_id}")
        return True
    except Exception as e:
        error_logger(
            "create_method",
            str(e),
            logger=logger,
            mode="error"
        )
        return False

@log_method(level="info")
def create_lambda_integration(api_id, resource_id, http_method="GET"):
    """Create a Lambda integration for the method."""
    try:
        # Create a session with the profile if specified
        session = Session(**get_boto3_session_args())
        apigw_client = session.client('apigateway')
        lambda_client = session.client('lambda')
        
        # Get the Lambda function ARN
        lambda_response = lambda_client.get_function(
            FunctionName=LAMBDA_FUNCTION_NAME
        )
        lambda_arn = lambda_response['Configuration']['FunctionArn']
        
        # Create the integration
        response = apigw_client.put_integration(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod=http_method,
            type='AWS_PROXY',
            integrationHttpMethod='POST',
            uri=f"arn:aws:apigateway:{AWS_REGION}:lambda:path/2015-03-31/functions/{lambda_arn}/invocations"
        )
        
        logger.info(f"Created Lambda integration for {http_method} method on resource ID: {resource_id}")
        return True
    except Exception as e:
        error_logger(
            "create_lambda_integration",
            str(e),
            logger=logger,
            mode="error"
        )
        return False

@log_method(level="info")
def add_lambda_permission(api_id):
    """Add permission for API Gateway to invoke the Lambda function."""
    try:
        # Create a session with the profile if specified
        session = Session(**get_boto3_session_args())
        lambda_client = session.client('lambda')
        
        # Create a unique statement ID
        statement_id = f"apigateway-{api_id}-{API_STAGE_NAME}"
        
        # Add the permission
        try:
            lambda_client.add_permission(
                FunctionName=LAMBDA_FUNCTION_NAME,
                StatementId=statement_id,
                Action='lambda:InvokeFunction',
                Principal='apigateway.amazonaws.com',
                SourceArn=f"arn:aws:execute-api:{AWS_REGION}:*:{api_id}/*/*"
            )
            logger.info(f"Added permission for API Gateway to invoke Lambda function: {LAMBDA_FUNCTION_NAME}")
        except lambda_client.exceptions.ResourceConflictException:
            logger.info(f"Permission already exists for API Gateway to invoke Lambda function: {LAMBDA_FUNCTION_NAME}")
        
        return True
    except Exception as e:
        error_logger(
            "add_lambda_permission",
            str(e),
            logger=logger,
            mode="error"
        )
        return False

@log_method(level="info")
def deploy_api(api_id):
    """Deploy the API to a stage."""
    try:
        # Create a session with the profile if specified
        session = Session(**get_boto3_session_args())
        apigw_client = session.client('apigateway')
        
        # Create the deployment
        response = apigw_client.create_deployment(
            restApiId=api_id,
            stageName=API_STAGE_NAME,
            description=f"Deployment to {API_STAGE_NAME} stage"
        )
        
        # Get the API URL
        api_url = f"https://{api_id}.execute-api.{AWS_REGION}.amazonaws.com/{API_STAGE_NAME}"
        logger.info(f"Deployed API to stage '{API_STAGE_NAME}' with URL: {api_url}")
        return api_url
    except Exception as e:
        error_logger(
            "deploy_api",
            str(e),
            logger=logger,
            mode="error"
        )
        return None

@log_method(level="info")
def create_api_gateway():
    """Create the API Gateway REST API with Lambda integration."""
    # Create the REST API
    api_id = create_rest_api()
    if not api_id:
        logger.error("Failed to create API Gateway REST API")
        return False
    
    # Get the root resource ID
    root_id = get_root_resource_id(api_id)
    if not root_id:
        logger.error("Failed to get root resource ID")
        return False
    
    # Create a resource for the API
    resource_id = create_resource(api_id, root_id, "api")
    if not resource_id:
        logger.error("Failed to create resource")
        return False
    
    # Create methods for the resource
    for method in ["GET", "POST", "PUT", "DELETE"]:
        if not create_method(api_id, resource_id, method):
            logger.error(f"Failed to create {method} method")
            return False
        
        if not create_lambda_integration(api_id, resource_id, method):
            logger.error(f"Failed to create Lambda integration for {method} method")
            return False
    
    # Add permission for API Gateway to invoke the Lambda function
    if not add_lambda_permission(api_id):
        logger.error("Failed to add Lambda permission")
        return False
    
    # Deploy the API
    api_url = deploy_api(api_id)
    if not api_url:
        logger.error("Failed to deploy API")
        return False
    
    logger.info(f"API Gateway REST API created successfully with URL: {api_url}")
    return api_url

if __name__ == "__main__":
    create_api_gateway()
