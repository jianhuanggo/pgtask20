"""
Main script to deploy the API Gateway REST API for the Lambda function.
"""
import os
import sys
import argparse
from pathlib import Path

# Add the project root to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Import the deployment config and logging
from lambda_docker.deployment.config import validate_config
from lambda_docker.deployment.scripts.api_gateway.create_api import create_api_gateway
from lambda_docker.deployment.scripts.api_gateway.delete_api import delete_api_gateway
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

@log_method(level="info")
def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Deploy API Gateway REST API for Lambda function")
    parser.add_argument("--env-file", type=str, help="Path to .env file")
    parser.add_argument("--delete", action="store_true", help="Delete the API Gateway REST API")
    return parser.parse_args()

@log_method(level="info")
def load_env_file(env_file):
    """Load environment variables from .env file."""
    if env_file:
        env_path = Path(env_file)
        if env_path.exists():
            logger.info(f"Loading environment variables from {env_file}")
            with open(env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        key, value = line.split("=", 1)
                        os.environ[key] = value
            logger.info(f"Using environment file: {env_file}")
        else:
            logger.error(f"Environment file not found: {env_file}")
            return False
    return True

@log_method(level="info")
def main():
    """Main function to deploy or delete the API Gateway REST API."""
    # Parse command-line arguments
    args = parse_args()
    
    # Load environment variables from .env file
    if args.env_file and not load_env_file(args.env_file):
        return 1
    
    # Validate configuration
    if not validate_config():
        logger.error("Invalid configuration")
        return 1
    
    # Deploy or delete the API Gateway REST API
    if args.delete:
        logger.info("Deleting API Gateway REST API")
        if delete_api_gateway():
            logger.info("API Gateway REST API deleted successfully")
            return 0
        else:
            logger.error("Failed to delete API Gateway REST API")
            return 1
    else:
        logger.info("Deploying API Gateway REST API")
        api_url = create_api_gateway()
        if api_url:
            logger.info(f"API Gateway REST API deployed successfully with URL: {api_url}")
            return 0
        else:
            logger.error("Failed to deploy API Gateway REST API")
            return 1

if __name__ == "__main__":
    sys.exit(main())
