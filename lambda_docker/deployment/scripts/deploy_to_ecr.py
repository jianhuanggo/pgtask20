"""
Script to build and deploy Docker image to ECR.
"""
import os
import sys
import subprocess
import boto3
import time
from boto3.session import Session

# Add the project root to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

# Import the deployment config and logging
from lambda_docker.deployment.config import (
    AWS_REGION, ECR_REPOSITORY_NAME, ECR_IMAGE_TAG,
    DOCKERFILE_PATH, PROJECT_ROOT, get_ecr_repository_uri, get_image_uri,
    get_boto3_session_args
)
from _logging.pg_logger import get_logger, log_method, error_logger

# Configure the logger
logger = get_logger(
    name="deploy_to_ecr",
    log_level=os.environ.get("LOG_LEVEL", "INFO"),
    log_to_console=True,
    log_to_file=True,
    log_file_path=os.environ.get("LOG_FILE_PATH", "/tmp/ecr_deployment.log")
)

@log_method(level="info")
def run_command(command, cwd=None):
    """Run a shell command and return the output."""
    try:
        logger.info(f"Running command: {command}")
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            text=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        error_logger(
            "run_command",
            f"Command failed with exit code {e.returncode}: {e.stderr}",
            logger=logger,
            mode="error"
        )
        raise

@log_method(level="info")
def create_ecr_repository_if_not_exists():
    """Create the ECR repository if it doesn't exist."""
    try:
        # Create a session with the profile if specified
        session = Session(**get_boto3_session_args())
        ecr_client = session.client('ecr')
        
        # Check if repository exists
        try:
            ecr_client.describe_repositories(repositoryNames=[ECR_REPOSITORY_NAME])
            logger.info(f"ECR repository {ECR_REPOSITORY_NAME} already exists")
            return True
        except ecr_client.exceptions.RepositoryNotFoundException:
            # Create repository
            response = ecr_client.create_repository(
                repositoryName=ECR_REPOSITORY_NAME,
                imageScanningConfiguration={'scanOnPush': True},
                encryptionConfiguration={'encryptionType': 'AES256'}
            )
            logger.info(f"Created ECR repository: {ECR_REPOSITORY_NAME}")
            return True
    except Exception as e:
        error_logger(
            "create_ecr_repository_if_not_exists",
            str(e),
            logger=logger,
            mode="error"
        )
        return False

@log_method(level="info")
def get_ecr_login_command():
    """Get the ECR login command."""
    try:
        # Create a session with the profile if specified
        session = Session(**get_boto3_session_args())
        ecr_client = session.client('ecr')
        token = ecr_client.get_authorization_token()
        
        username, password = token['authorizationData'][0]['authorizationToken'].split(':')
        endpoint = token['authorizationData'][0]['proxyEndpoint']
        
        # Use Docker login command
        login_command = f"docker login --username AWS --password-stdin {endpoint}"
        logger.info(f"Generated ECR login command for endpoint: {endpoint}")
        return login_command, password
    except Exception as e:
        error_logger(
            "get_ecr_login_command",
            str(e),
            logger=logger,
            mode="error"
        )
        return None, None

@log_method(level="info")
def login_to_ecr():
    """Login to ECR."""
    try:
        login_command, password = get_ecr_login_command()
        if not login_command:
            return False
        
        # Execute login command
        process = subprocess.Popen(
            login_command,
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate(input=password)
        
        if process.returncode != 0:
            error_logger(
                "login_to_ecr",
                f"ECR login failed: {stderr}",
                logger=logger,
                mode="error"
            )
            return False
        
        logger.info("Successfully logged in to ECR")
        return True
    except Exception as e:
        error_logger(
            "login_to_ecr",
            str(e),
            logger=logger,
            mode="error"
        )
        return False

@log_method(level="info")
def build_docker_image():
    """Build the Docker image."""
    try:
        image_name = f"{ECR_REPOSITORY_NAME}:{ECR_IMAGE_TAG}"
        build_command = f"docker build -t {image_name} -f {DOCKERFILE_PATH} {PROJECT_ROOT}"
        
        output = run_command(build_command, cwd=str(PROJECT_ROOT))
        logger.info(f"Docker image built successfully: {image_name}")
        return True
    except Exception as e:
        error_logger(
            "build_docker_image",
            str(e),
            logger=logger,
            mode="error"
        )
        return False

@log_method(level="info")
def tag_and_push_image():
    """Tag and push the Docker image to ECR."""
    try:
        local_image = f"{ECR_REPOSITORY_NAME}:{ECR_IMAGE_TAG}"
        ecr_image_uri = get_image_uri()
        
        if not ecr_image_uri:
            logger.error("Failed to get ECR image URI")
            return False
        
        # Tag the image
        tag_command = f"docker tag {local_image} {ecr_image_uri}"
        run_command(tag_command)
        logger.info(f"Tagged image: {local_image} -> {ecr_image_uri}")
        
        # Push the image
        push_command = f"docker push {ecr_image_uri}"
        run_command(push_command)
        logger.info(f"Pushed image to ECR: {ecr_image_uri}")
        
        return True
    except Exception as e:
        error_logger(
            "tag_and_push_image",
            str(e),
            logger=logger,
            mode="error"
        )
        return False

@log_method(level="info")
def deploy_to_ecr():
    """Main function to deploy the Docker image to ECR."""
    start_time = time.time()
    logger.info(f"Starting deployment to ECR: {ECR_REPOSITORY_NAME}")
    
    # Create repository if it doesn't exist
    if not create_ecr_repository_if_not_exists():
        logger.error("Failed to create ECR repository")
        return False
    
    # Login to ECR
    if not login_to_ecr():
        logger.error("Failed to login to ECR")
        return False
    
    # Build Docker image
    if not build_docker_image():
        logger.error("Failed to build Docker image")
        return False
    
    # Tag and push image
    if not tag_and_push_image():
        logger.error("Failed to tag and push image")
        return False
    
    elapsed_time = time.time() - start_time
    logger.info(f"Deployment to ECR completed successfully in {elapsed_time:.2f} seconds")
    return True

if __name__ == "__main__":
    deploy_to_ecr()
