"""
Configuration module for Lambda Docker deployment.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add the project root to the Python path to import the logging module
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Import the PGLogger
from _logging.pg_logger import get_logger

# Load environment variables from .env file
env_file = os.environ.get("ENV_FILE", ".env")
load_dotenv(env_file)

# Configure the logger
logger = get_logger(
    name="deployment_config",
    log_level=os.environ.get("LOG_LEVEL", "INFO"),
    log_to_console=True,
    log_to_file=True,
    log_file_path=os.environ.get("LOG_FILE_PATH", "/tmp/lambda_deployment.log")
)

# AWS Configuration
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
AWS_ACCOUNT_ID = os.environ.get("AWS_ACCOUNT_ID", "")
AWS_PROFILE = os.environ.get("AWS_PROFILE", None)

# ECR Configuration
ECR_REPOSITORY_NAME = os.environ.get("ECR_REPOSITORY_NAME", "lambda-docker")
ECR_IMAGE_TAG = os.environ.get("ECR_IMAGE_TAG", "latest")

# Application Location Configuration
APP_LOCATION = os.environ.get("APP_LOCATION", None)

# Lambda Configuration
LAMBDA_FUNCTION_NAME = os.environ.get("LAMBDA_FUNCTION_NAME", "lambda-docker-function")
LAMBDA_MEMORY_SIZE = int(os.environ.get("LAMBDA_MEMORY_SIZE", "128"))
LAMBDA_TIMEOUT = int(os.environ.get("LAMBDA_TIMEOUT", "30"))
LAMBDA_EXECUTION_ROLE = os.environ.get("LAMBDA_EXECUTION_ROLE", "")

# VPC Configuration
VPC_ENABLED = os.environ.get("VPC_ENABLED", "false").lower() == "true"
VPC_ID = os.environ.get("VPC_ID", "")
VPC_SUBNETS = [subnet for subnet in os.environ.get("VPC_SUBNETS", "").split(",") if subnet]
VPC_SECURITY_GROUPS = [sg for sg in os.environ.get("VPC_SECURITY_GROUPS", "").split(",") if sg]

# IAM Configuration
IAM_ROLE_NAME = os.environ.get("IAM_ROLE_NAME", f"{LAMBDA_FUNCTION_NAME}-role")
IAM_ROLE_DESCRIPTION = os.environ.get("IAM_ROLE_DESCRIPTION", f"Role for {LAMBDA_FUNCTION_NAME}")
IAM_ROLE_RECREATE = os.environ.get("IAM_ROLE_RECREATE", "false").lower() == "true"

LAMBDA_ENVIRONMENT = {
    "Variables": {
        "ENVIRONMENT": os.environ.get("ENVIRONMENT", "development"),
        "LOG_LEVEL": os.environ.get("LOG_LEVEL", "INFO")
    }
}

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent

# Use custom application location if provided
if APP_LOCATION:
    APP_ROOT = Path(APP_LOCATION)
    DOCKERFILE_PATH = APP_ROOT / "Dockerfile"
    APP_DIR = APP_ROOT / "app"
else:
    APP_ROOT = PROJECT_ROOT
    DOCKERFILE_PATH = PROJECT_ROOT / "Dockerfile"
    APP_DIR = PROJECT_ROOT / "app"

def get_ecr_repository_uri():
    """Get the ECR repository URI."""
    if not AWS_ACCOUNT_ID:
        logger.error("AWS_ACCOUNT_ID is not set")
        return None
    return f"{AWS_ACCOUNT_ID}.dkr.ecr.{AWS_REGION}.amazonaws.com/{ECR_REPOSITORY_NAME}"

def get_image_uri():
    """Get the full image URI including tag."""
    repo_uri = get_ecr_repository_uri()
    if not repo_uri:
        return None
    return f"{repo_uri}:{ECR_IMAGE_TAG}"

def get_boto3_session_args():
    """Get the arguments for creating a boto3 session."""
    session_args = {
        'region_name': AWS_REGION
    }
    
    if AWS_PROFILE:
        session_args['profile_name'] = AWS_PROFILE
        logger.info(f"Using AWS profile: {AWS_PROFILE}")
    else:
        logger.info("Using default AWS credentials")
    
    return session_args

def get_lambda_role_arn():
    """Get the ARN of the Lambda execution role."""
    if LAMBDA_EXECUTION_ROLE:
        logger.info(f"Using provided Lambda execution role: {LAMBDA_EXECUTION_ROLE}")
        return LAMBDA_EXECUTION_ROLE
    
    # Import here to avoid circular imports
    from lambda_docker.deployment.scripts.manage_iam_role import get_role_arn
    
    role_arn = get_role_arn(IAM_ROLE_NAME)
    if role_arn:
        logger.info(f"Using existing IAM role: {IAM_ROLE_NAME} with ARN: {role_arn}")
        return role_arn
    
    logger.warning(f"IAM role '{IAM_ROLE_NAME}' not found and LAMBDA_EXECUTION_ROLE not provided")
    return None

def validate_app_location():
    """Validate the application location."""
    if APP_LOCATION:
        app_path = Path(APP_LOCATION)
        if not app_path.exists():
            logger.error(f"Application location does not exist: {APP_LOCATION}")
            return False
        
        dockerfile_path = app_path / "Dockerfile"
        if not dockerfile_path.exists():
            logger.error(f"Dockerfile not found at: {dockerfile_path}")
            return False
        
        logger.info(f"Using custom application location: {APP_LOCATION}")
    else:
        logger.info(f"Using default application location: {PROJECT_ROOT}")
    
    return True

def validate_vpc_config():
    """Validate the VPC configuration."""
    if VPC_ENABLED:
        if not VPC_ID:
            logger.error("VPC_ID is not set but VPC_ENABLED is true")
            return False
        
        if not VPC_SUBNETS:
            logger.error("VPC_SUBNETS is not set but VPC_ENABLED is true")
            return False
        
        if not VPC_SECURITY_GROUPS:
            logger.error("VPC_SECURITY_GROUPS is not set but VPC_ENABLED is true")
            return False
        
        logger.info(f"VPC configuration validated: VPC_ID={VPC_ID}, Subnets={VPC_SUBNETS}, Security Groups={VPC_SECURITY_GROUPS}")
    else:
        logger.info("VPC configuration is disabled")
    
    return True

def validate_config():
    """Validate the configuration."""
    if not AWS_ACCOUNT_ID:
        logger.error("AWS_ACCOUNT_ID is not set")
        return False
    
    if not ECR_REPOSITORY_NAME:
        logger.error("ECR_REPOSITORY_NAME is not set")
        return False
    
    if not LAMBDA_FUNCTION_NAME:
        logger.error("LAMBDA_FUNCTION_NAME is not set")
        return False
    
    if not validate_app_location():
        return False
    
    if not validate_vpc_config():
        return False
    
    logger.info(f"Configuration validated: Region={AWS_REGION}, ECR={ECR_REPOSITORY_NAME}, Lambda={LAMBDA_FUNCTION_NAME}")
    return True
