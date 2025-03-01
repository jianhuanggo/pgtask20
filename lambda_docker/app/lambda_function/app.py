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

@log_method(level="info", include_args=True, include_return=True)
def handler(event, context):
    """
    Lambda function handler with comprehensive logging.
    
    Args:
        event: The event dict from the Lambda trigger
        context: The Lambda context object
        
    Returns:
        dict: API Gateway compatible response
    """
    try:
        logger.info(f"Lambda function invoked with request ID: {context.aws_request_id}")
        
        # Extract request details for logging
        http_method = event.get('httpMethod', 'GET')
        path = event.get('path', '/')
        headers = event.get('headers', {})
        query_params = event.get('queryStringParameters', {})
        body = event.get('body')
        
        logger.info(f"Request details: method={http_method}, path={path}")
        
        # Process the request
        response_body = {
            "message": "Lambda function executed successfully",
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": context.aws_request_id,
            "environment": os.environ.get("ENVIRONMENT", "development")
        }
        
        # Create API Gateway response
        response = {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json"
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
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "error": "Internal server error",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": context.aws_request_id if hasattr(context, 'aws_request_id') else str(uuid.uuid4())
            })
        }
        
        return error_response
