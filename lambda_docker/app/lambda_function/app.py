"""
AWS Lambda function with PGLogger integration.
"""
import os
import json
import time
import uuid
from datetime import datetime
import sys
import traceback

# Add the project root to the Python path to import the logging module
sys.path.append('/var/task')
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

# Import the PGLogger
from _logging.pg_logger import get_logger, log_method, error_logger

# Configure the logger
logger = get_logger(
    name="lambda_function",
    log_level=os.environ.get("LOG_LEVEL", "INFO"),
    log_to_console=True,
    log_to_file=False,
    use_json_format=True
)

@log_method(level="info")
def handle_get_request(path_params, query_params, context):
    """Handle GET requests."""
    logger.info(f"Processing GET request: path_params={path_params}, query_params={query_params}")
    
    # Process the GET request
    response_body = {
        "message": "GET request processed successfully",
        "timestamp": datetime.utcnow().isoformat(),
        "request_id": context.aws_request_id,
        "environment": os.environ.get("ENVIRONMENT", "development"),
        "path_params": path_params,
        "query_params": query_params
    }
    
    return response_body

@log_method(level="info")
def handle_post_request(body, context):
    """Handle POST requests."""
    logger.info(f"Processing POST request: body={body}")
    
    # Process the POST request
    response_body = {
        "message": "POST request processed successfully",
        "timestamp": datetime.utcnow().isoformat(),
        "request_id": context.aws_request_id,
        "environment": os.environ.get("ENVIRONMENT", "development"),
        "received_data": body
    }
    
    return response_body

@log_method(level="info")
def handle_put_request(path_params, body, context):
    """Handle PUT requests."""
    logger.info(f"Processing PUT request: path_params={path_params}, body={body}")
    
    # Process the PUT request
    response_body = {
        "message": "PUT request processed successfully",
        "timestamp": datetime.utcnow().isoformat(),
        "request_id": context.aws_request_id,
        "environment": os.environ.get("ENVIRONMENT", "development"),
        "path_params": path_params,
        "updated_data": body
    }
    
    return response_body

@log_method(level="info")
def handle_delete_request(path_params, context):
    """Handle DELETE requests."""
    logger.info(f"Processing DELETE request: path_params={path_params}")
    
    # Process the DELETE request
    response_body = {
        "message": "DELETE request processed successfully",
        "timestamp": datetime.utcnow().isoformat(),
        "request_id": context.aws_request_id,
        "environment": os.environ.get("ENVIRONMENT", "development"),
        "path_params": path_params
    }
    
    return response_body

@log_method(level="info", include_args=True, include_return=True)
def handler(event, context):
    """
    Lambda function handler for API Gateway integration.
    
    Args:
        event: The event dict from the API Gateway trigger
        context: The Lambda context object
        
    Returns:
        dict: API Gateway compatible response
    """
    try:
        logger.info(f"Lambda function invoked with request ID: {context.aws_request_id}")
        
        # Extract request details for logging
        http_method = event.get('httpMethod', 'GET')
        path = event.get('path', '/')
        headers = event.get('headers', {}) or {}
        path_params = event.get('pathParameters', {}) or {}
        query_params = event.get('queryStringParameters', {}) or {}
        
        # Parse request body if present
        body = event.get('body')
        if body:
            try:
                body = json.loads(body)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse request body as JSON: {body}")
        
        logger.info(f"Request details: method={http_method}, path={path}")
        
        # Process the request based on HTTP method
        if http_method == 'GET':
            response_body = handle_get_request(path_params, query_params, context)
        elif http_method == 'POST':
            response_body = handle_post_request(body, context)
        elif http_method == 'PUT':
            response_body = handle_put_request(path_params, body, context)
        elif http_method == 'DELETE':
            response_body = handle_delete_request(path_params, context)
        else:
            # Method not allowed
            return {
                "statusCode": 405,
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": json.dumps({
                    "error": "Method not allowed",
                    "message": f"HTTP method {http_method} is not supported",
                    "timestamp": datetime.utcnow().isoformat(),
                    "request_id": context.aws_request_id
                })
            }
        
        # Create API Gateway response
        response = {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,Authorization",
                "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS"
            },
            "body": json.dumps(response_body)
        }
        
        logger.info(f"Lambda function completed successfully: {response_body['request_id']}")
        return response
        
    except Exception as e:
        # Log the exception with traceback
        error_logger(
            "handler",
            str(e),
            logger=logger,
            mode="error",
            set_trace=True
        )
        
        # Create error response
        error_response = {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,Authorization",
                "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS"
            },
            "body": json.dumps({
                "error": "Internal server error",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": context.aws_request_id if hasattr(context, 'aws_request_id') else str(uuid.uuid4())
            })
        }
        
        return error_response
