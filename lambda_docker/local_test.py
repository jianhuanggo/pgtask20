"""
Local test script for Lambda function.
"""
import os
import sys
import json
import uuid
from datetime import datetime

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Import the PGLogger
from _logging.pg_logger import get_logger

# Configure the logger
logger = get_logger(
    name="local_test",
    log_level="INFO",
    log_to_console=True,
    log_to_file=False
)

# Import the Lambda handler
try:
    from lambda_docker.app.lambda_function.app import handler
    logger.info("Successfully imported Lambda handler")
except ImportError as e:
    logger.error(f"Failed to import Lambda handler: {str(e)}")
    sys.exit(1)

def create_mock_event():
    """Create a mock API Gateway event."""
    return {
        "httpMethod": "GET",
        "path": "/test",
        "headers": {
            "Content-Type": "application/json",
            "User-Agent": "Local Test Script"
        },
        "queryStringParameters": {
            "param1": "value1",
            "param2": "value2"
        },
        "body": json.dumps({
            "test": "data"
        })
    }

class MockLambdaContext:
    """Mock Lambda context object."""
    def __init__(self):
        self.function_name = "local-test-function"
        self.function_version = "$LATEST"
        self.invoked_function_arn = "arn:aws:lambda:local:123456789012:function:local-test-function"
        self.memory_limit_in_mb = 128
        self.aws_request_id = str(uuid.uuid4())
        self.log_group_name = "/aws/lambda/local-test-function"
        self.log_stream_name = f"{datetime.now().strftime('%Y/%m/%d')}/[$LATEST]{uuid.uuid4()}"
        self.identity = None
        self.client_context = None
        self.remaining_time_in_millis = 30000

    def get_remaining_time_in_millis(self):
        """Return remaining execution time in milliseconds."""
        return self.remaining_time_in_millis

def run_local_test():
    """Run the Lambda function locally."""
    try:
        # Create mock event and context
        event = create_mock_event()
        context = MockLambdaContext()
        
        logger.info(f"Invoking Lambda function with request ID: {context.aws_request_id}")
        logger.info(f"Event: {json.dumps(event, indent=2)}")
        
        # Invoke the handler
        response = handler(event, context)
        
        # Print the response
        logger.info(f"Lambda function response: {json.dumps(response, indent=2)}")
        
        # Check response status code
        status_code = response.get("statusCode")
        if status_code == 200:
            logger.info("Lambda function executed successfully")
        else:
            logger.warning(f"Lambda function returned non-200 status code: {status_code}")
        
        return response
    except Exception as e:
        logger.error(f"Error running local test: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

if __name__ == "__main__":
    run_local_test()
