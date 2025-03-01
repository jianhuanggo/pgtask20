"""
Script to manage ECR repositories.
"""
import os
import sys
import argparse
import boto3
from boto3.session import Session

# Add the project root to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

# Import the deployment config and logging
from lambda_docker.deployment.config import (
    AWS_REGION, ECR_REPOSITORY_NAME, get_boto3_session_args
)
from _logging.pg_logger import get_logger, log_method, error_logger

# Configure the logger
logger = get_logger(
    name="manage_ecr_repository",
    log_level=os.environ.get("LOG_LEVEL", "INFO"),
    log_to_console=True,
    log_to_file=True,
    log_file_path=os.environ.get("LOG_FILE_PATH", "/tmp/ecr_management.log")
)

@log_method(level="info")
def check_repository_exists(repository_name=None):
    """Check if an ECR repository exists."""
    try:
        repo_name = repository_name or ECR_REPOSITORY_NAME
        
        # Create a session with the profile if specified
        session = Session(**get_boto3_session_args())
        ecr_client = session.client('ecr')
        
        # Check if repository exists
        try:
            ecr_client.describe_repositories(repositoryNames=[repo_name])
            logger.info(f"ECR repository {repo_name} exists")
            return True
        except ecr_client.exceptions.RepositoryNotFoundException:
            logger.info(f"ECR repository {repo_name} doesn't exist")
            return False
    except Exception as e:
        error_logger(
            "check_repository_exists",
            str(e),
            logger=logger,
            mode="error"
        )
        return False

@log_method(level="info")
def delete_repository(repository_name=None, force=False):
    """Delete an ECR repository."""
    try:
        repo_name = repository_name or ECR_REPOSITORY_NAME
        
        # Create a session with the profile if specified
        session = Session(**get_boto3_session_args())
        ecr_client = session.client('ecr')
        
        # Check if repository exists
        if not check_repository_exists(repo_name):
            logger.info(f"ECR repository {repo_name} doesn't exist, nothing to delete")
            return True
        
        # Delete repository
        ecr_client.delete_repository(
            repositoryName=repo_name,
            force=force  # Force deletion even if it contains images
        )
        
        logger.info(f"Deleted ECR repository: {repo_name}")
        return True
    except Exception as e:
        error_logger(
            "delete_repository",
            str(e),
            logger=logger,
            mode="error"
        )
        return False

@log_method(level="info")
def create_repository(repository_name=None):
    """Create an ECR repository."""
    try:
        repo_name = repository_name or ECR_REPOSITORY_NAME
        
        # Create a session with the profile if specified
        session = Session(**get_boto3_session_args())
        ecr_client = session.client('ecr')
        
        # Create repository
        ecr_client.create_repository(
            repositoryName=repo_name,
            imageScanningConfiguration={'scanOnPush': True},
            encryptionConfiguration={'encryptionType': 'AES256'}
        )
        
        logger.info(f"Created ECR repository: {repo_name}")
        return True
    except Exception as e:
        error_logger(
            "create_repository",
            str(e),
            logger=logger,
            mode="error"
        )
        return False

@log_method(level="info")
def recreate_repository(repository_name=None, force=False):
    """Delete an ECR repository if it exists and create a new one."""
    try:
        repo_name = repository_name or ECR_REPOSITORY_NAME
        
        # Delete repository if it exists
        if not delete_repository(repo_name, force):
            logger.error(f"Failed to delete ECR repository: {repo_name}")
            return False
        
        # Create repository
        if not create_repository(repo_name):
            logger.error(f"Failed to create ECR repository: {repo_name}")
            return False
        
        logger.info(f"Successfully recreated ECR repository: {repo_name}")
        return True
    except Exception as e:
        error_logger(
            "recreate_repository",
            str(e),
            logger=logger,
            mode="error"
        )
        return False

if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Manage ECR repositories")
    parser.add_argument("--repository-name", type=str, help="ECR repository name")
    parser.add_argument("--check", action="store_true", help="Check if repository exists")
    parser.add_argument("--delete", action="store_true", help="Delete repository")
    parser.add_argument("--create", action="store_true", help="Create repository")
    parser.add_argument("--recreate", action="store_true", help="Delete and recreate repository")
    parser.add_argument("--force", action="store_true", help="Force deletion even if repository contains images")
    parser.add_argument("--env-file", type=str, help="Path to .env file")
    args = parser.parse_args()
    
    # Load environment variables from .env file if specified
    if args.env_file:
        from dotenv import load_dotenv
        load_dotenv(args.env_file)
    
    # Get repository name
    repository_name = args.repository_name or ECR_REPOSITORY_NAME
    
    # Execute requested action
    if args.check:
        check_repository_exists(repository_name)
    elif args.delete:
        delete_repository(repository_name, args.force)
    elif args.create:
        create_repository(repository_name)
    elif args.recreate:
        recreate_repository(repository_name, args.force)
    else:
        parser.print_help()
