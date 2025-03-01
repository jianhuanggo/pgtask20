# AWS Lambda Docker Deployment with PGLogger Integration

This project provides a production-grade solution for deploying Docker containers to AWS Lambda with comprehensive logging using the PGLogger module.

## Features

- **Production-grade Dockerfile** for AWS Lambda Python 3.11 runtime
- **Comprehensive logging** using the PGLogger module
- **Structured JSON logging** for better log analysis
- **Deployment scripts** for AWS ECR and Lambda
- **Local testing capabilities** for Lambda functions
- **Error handling and monitoring** with detailed logging
- **Environment-based configuration** for different deployment stages

## Directory Structure

```
lambda_docker/
├── app/                        # Lambda function code
│   ├── lambda_function/        # Lambda handler code
│   │   ├── __init__.py
│   │   └── app.py              # Main Lambda handler with PGLogger integration
│   └── requirements.txt        # Python dependencies for Lambda function
├── deployment/                 # Deployment scripts and configuration
│   ├── scripts/                # Deployment script modules
│   │   ├── __init__.py
│   │   ├── deploy_to_ecr.py    # Script to build and push Docker image to ECR
│   │   └── update_lambda.py    # Script to update Lambda function with ECR image
│   ├── config.py               # Configuration module for deployment
│   ├── deploy.py               # Main deployment script
│   └── .env.example            # Example environment variables file
├── tests/                      # Test scripts
│   ├── unit/                   # Unit tests
│   │   └── test_lambda.py      # Unit tests for Lambda function
│   └── integration/            # Integration tests
├── Dockerfile                  # Dockerfile for Lambda function
├── local_test.py               # Script for local testing
└── README.md                   # This file
```

## PGLogger Integration

This project integrates with the PGLogger module to provide comprehensive logging capabilities:

- **Structured JSON logging** for better log analysis in production
- **Method-level logging** using decorators to track function calls and performance
- **Exception tracking** with detailed error information
- **Context-aware logging** with request IDs and timestamps
- **Configurable log levels** based on environment

### Logging Usage in Lambda Function

The Lambda function uses PGLogger as follows:

```python
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
    # Function implementation with logging
    logger.info(f"Lambda function invoked with request ID: {context.aws_request_id}")
    
    # Error handling with error_logger
    try:
        # Function logic
    except Exception as e:
        error_logger(
            "handler",
            str(e),
            logger=logger,
            mode="error",
            set_trace=True
        )
```

## Setup and Installation

### Prerequisites

- AWS CLI configured with appropriate permissions
- Docker installed and running
- Python 3.11 or later

### Configuration

1. Copy the example environment file:

```bash
cp deployment/.env.example deployment/.env
```

2. Edit the `.env` file with your AWS account details and configuration:

```
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=123456789012

# ECR Configuration
ECR_REPOSITORY_NAME=lambda-docker
ECR_IMAGE_TAG=latest

# Lambda Configuration
LAMBDA_FUNCTION_NAME=lambda-docker-function
LAMBDA_EXECUTION_ROLE=arn:aws:iam::123456789012:role/lambda-execution-role
LAMBDA_MEMORY_SIZE=128
LAMBDA_TIMEOUT=30

# Environment Configuration
ENVIRONMENT=development
LOG_LEVEL=INFO
LOG_FILE_PATH=/tmp/lambda_deployment.log
```

## Deployment

### Deploy to ECR and Lambda

To deploy the Docker image to ECR and update the Lambda function:

```bash
cd lambda_docker
python deployment/deploy.py --env-file deployment/.env
```

### Deploy to ECR Only

To build and push the Docker image to ECR without updating the Lambda function:

```bash
python deployment/deploy.py --env-file deployment/.env --ecr-only
```

### Update Lambda Only

To update the Lambda function with an existing ECR image:

```bash
python deployment/deploy.py --env-file deployment/.env --lambda-only
```

## Local Testing

To test the Lambda function locally:

```bash
cd lambda_docker
python local_test.py
```

This will:
1. Create a mock API Gateway event
2. Create a mock Lambda context
3. Invoke the Lambda handler function
4. Log the response using PGLogger

## Unit Testing

To run unit tests:

```bash
cd lambda_docker
pytest tests/unit/
```

## Logging Configuration

The Lambda function and deployment scripts use different logging configurations:

### Lambda Function Logging

- Uses JSON format for structured logging
- Logs to console only (CloudWatch in AWS)
- Configurable log level via environment variable

### Deployment Script Logging

- Uses standard text format
- Logs to both console and file
- File logging with configurable path
- Detailed context information

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| AWS_REGION | AWS region for deployment | us-east-1 |
| AWS_ACCOUNT_ID | AWS account ID | (required) |
| ECR_REPOSITORY_NAME | ECR repository name | lambda-docker |
| ECR_IMAGE_TAG | Docker image tag | latest |
| LAMBDA_FUNCTION_NAME | Lambda function name | lambda-docker-function |
| LAMBDA_EXECUTION_ROLE | IAM role ARN for Lambda | (required) |
| LAMBDA_MEMORY_SIZE | Lambda memory size in MB | 128 |
| LAMBDA_TIMEOUT | Lambda timeout in seconds | 30 |
| ENVIRONMENT | Deployment environment | development |
| LOG_LEVEL | Logging level | INFO |
| LOG_FILE_PATH | Path for log files | /tmp/lambda_deployment.log |

## Best Practices

This project follows these best practices:

1. **Structured logging** for better log analysis
2. **Environment-based configuration** for different deployment stages
3. **Comprehensive error handling** with detailed logging
4. **Modular code structure** for better maintainability
5. **Local testing capabilities** for faster development
6. **Production-ready Dockerfile** optimized for Lambda
7. **Automated deployment scripts** for consistent deployments
