"""
Main deployment script for Lambda Docker.
"""
import os
import sys
import argparse
import time
from pathlib import Path

# Add the project root to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Import the deployment config and logging
from lambda_docker.deployment.config import validate_config
from lambda_docker.deployment.scripts.deploy_to_ecr import deploy_to_ecr
from lambda_docker.deployment.scripts.update_lambda import update_lambda
from _logging.pg_logger import get_logger, log_method, error_logger

# Configure the logger
logger = get_logger(
    name="deployment",
    log_level=os.environ.get("LOG_LEVEL", "INFO"),
    log_to_console=True,
    log_to_file=True,
    log_file_path=os.environ.get("LOG_FILE_PATH", "/tmp/deployment.log")
)

@log_method(level="info")
def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Deploy Lambda Docker application")
    parser.add_argument("--env-file", type=str, help="Path to .env file")
    parser.add_argument("--ecr-only", action="store_true", help="Deploy to ECR only")
    parser.add_argument("--lambda-only", action="store_true", help="Update Lambda only")
    return parser.parse_args()

@log_method(level="info")
def main():
    """Main deployment function."""
    start_time = time.time()
    logger.info("Starting Lambda Docker deployment")
    
    # Parse arguments
    args = parse_arguments()
    
    # Load environment variables from .env file if provided
    if args.env_file:
        env_file = Path(args.env_file)
        if env_file.exists():
            os.environ["ENV_FILE"] = str(env_file)
            logger.info(f"Using environment file: {env_file}")
        else:
            logger.error(f"Environment file not found: {env_file}")
            return False
    
    # Validate configuration
    if not validate_config():
        logger.error("Configuration validation failed")
        return False
    
    # Deploy to ECR
    if not args.lambda_only:
        logger.info("Deploying to ECR...")
        if not deploy_to_ecr():
            logger.error("Deployment to ECR failed")
            return False
    
    # Update Lambda function
    if not args.ecr_only:
        logger.info("Updating Lambda function...")
        if not update_lambda():
            logger.error("Lambda function update failed")
            return False
    
    elapsed_time = time.time() - start_time
    logger.info(f"Deployment completed successfully in {elapsed_time:.2f} seconds")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
