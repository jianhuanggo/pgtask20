#!/usr/bin/env python3
"""
Script to manage IAM roles for Lambda functions.

This script provides functionality to:
- Check if a role exists
- Create a role with the necessary trust relationship and policies
- Delete a role
- Recreate a role (delete if exists, then create)

Usage:
    python manage_iam_role.py --role-name my-role --check
    python manage_iam_role.py --role-name my-role --delete
    python manage_iam_role.py --role-name my-role --create
    python manage_iam_role.py --role-name my-role --recreate
"""

import os
import sys
import json
import argparse
import time
from pathlib import Path
from boto3.session import Session

# Add the project root to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

# Import the deployment config and logging
from lambda_docker.deployment.config import (
    AWS_REGION, get_boto3_session_args
)
from _logging.pg_logger import get_logger, log_method, error_logger

# Configure logger
logger = get_logger(
    name="iam_role_manager",
    log_level="INFO"
)

# IAM policy documents
LAMBDA_TRUST_POLICY = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "lambda.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}

LAMBDA_BASIC_EXECUTION_POLICY = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "arn:aws:logs:*:*:*"
        }
    ]
}

LAMBDA_VPC_ACCESS_POLICY = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ec2:CreateNetworkInterface",
                "ec2:DescribeNetworkInterfaces",
                "ec2:DeleteNetworkInterface"
            ],
            "Resource": "*"
        }
    ]
}

@log_method(level="info")
def check_role_exists(role_name):
    """
    Check if an IAM role exists.
    
    Args:
        role_name (str): The name of the IAM role to check.
        
    Returns:
        bool: True if the role exists, False otherwise.
    """
    try:
        # Create a session with the profile if specified
        session = Session(**get_boto3_session_args())
        iam_client = session.client('iam')
        
        # Try to get the role
        iam_client.get_role(RoleName=role_name)
        logger.info(f"IAM role '{role_name}' exists")
        return True
    except iam_client.exceptions.NoSuchEntityException:
        logger.info(f"IAM role '{role_name}' does not exist")
        return False
    except Exception as e:
        error_logger(
            "check_role_exists",
            str(e),
            logger=logger,
            mode="error"
        )
        return False

@log_method(level="info")
def delete_role(role_name):
    """
    Delete an IAM role if it exists.
    
    Args:
        role_name (str): The name of the IAM role to delete.
        
    Returns:
        bool: True if the role was deleted or doesn't exist, False if an error occurred.
    """
    try:
        # Check if the role exists
        if not check_role_exists(role_name):
            logger.info(f"IAM role '{role_name}' doesn't exist, nothing to delete")
            return True
        
        # Create a session with the profile if specified
        session = Session(**get_boto3_session_args())
        iam_client = session.client('iam')
        
        # First, detach all policies from the role
        try:
            # List attached policies
            attached_policies = iam_client.list_attached_role_policies(RoleName=role_name)
            
            # Detach each policy
            for policy in attached_policies.get('AttachedPolicies', []):
                policy_arn = policy['PolicyArn']
                logger.info(f"Detaching policy '{policy_arn}' from role '{role_name}'")
                iam_client.detach_role_policy(
                    RoleName=role_name,
                    PolicyArn=policy_arn
                )
            
            # List inline policies
            inline_policies = iam_client.list_role_policies(RoleName=role_name)
            
            # Delete each inline policy
            for policy_name in inline_policies.get('PolicyNames', []):
                logger.info(f"Deleting inline policy '{policy_name}' from role '{role_name}'")
                iam_client.delete_role_policy(
                    RoleName=role_name,
                    PolicyName=policy_name
                )
        except Exception as e:
            logger.warning(f"Error detaching policies from role '{role_name}': {str(e)}")
        
        # Delete the role
        iam_client.delete_role(RoleName=role_name)
        logger.info(f"IAM role '{role_name}' deleted")
        return True
    except Exception as e:
        error_logger(
            "delete_role",
            str(e),
            logger=logger,
            mode="error"
        )
        return False

@log_method(level="info")
def create_role(role_name, description="Lambda execution role", vpc_access=False):
    """
    Create an IAM role for Lambda execution.
    
    Args:
        role_name (str): The name of the IAM role to create.
        description (str): The description of the IAM role.
        vpc_access (bool): Whether to add VPC access permissions to the role.
        
    Returns:
        str: The ARN of the created role, or None if an error occurred.
    """
    try:
        # Create a session with the profile if specified
        session = Session(**get_boto3_session_args())
        iam_client = session.client('iam')
        
        # Create the role with the Lambda trust policy
        response = iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(LAMBDA_TRUST_POLICY),
            Description=description,
            MaxSessionDuration=3600
        )
        
        role_arn = response['Role']['Arn']
        logger.info(f"IAM role '{role_name}' created with ARN: {role_arn}")
        
        # Attach the basic execution policy
        basic_policy_name = f"{role_name}-basic-execution"
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName=basic_policy_name,
            PolicyDocument=json.dumps(LAMBDA_BASIC_EXECUTION_POLICY)
        )
        logger.info(f"Attached basic execution policy to role '{role_name}'")
        
        # Attach the VPC access policy if requested
        if vpc_access:
            vpc_policy_name = f"{role_name}-vpc-access"
            iam_client.put_role_policy(
                RoleName=role_name,
                PolicyName=vpc_policy_name,
                PolicyDocument=json.dumps(LAMBDA_VPC_ACCESS_POLICY)
            )
            logger.info(f"Attached VPC access policy to role '{role_name}'")
        
        # Wait for the role to be available
        logger.info(f"Waiting for role '{role_name}' to be available...")
        time.sleep(10)  # IAM changes can take time to propagate
        
        return role_arn
    except Exception as e:
        error_logger(
            "create_role",
            str(e),
            logger=logger,
            mode="error"
        )
        return None

@log_method(level="info")
def recreate_role(role_name, description="Lambda execution role", vpc_access=False):
    """
    Recreate an IAM role for Lambda execution.
    
    Args:
        role_name (str): The name of the IAM role to recreate.
        description (str): The description of the IAM role.
        vpc_access (bool): Whether to add VPC access permissions to the role.
        
    Returns:
        str: The ARN of the recreated role, or None if an error occurred.
    """
    try:
        # Delete the role if it exists
        if not delete_role(role_name):
            logger.error(f"Failed to delete IAM role '{role_name}'")
            return None
        
        # Create the role
        role_arn = create_role(role_name, description, vpc_access)
        if not role_arn:
            logger.error(f"Failed to create IAM role '{role_name}'")
            return None
        
        logger.info(f"IAM role '{role_name}' recreated with ARN: {role_arn}")
        return role_arn
    except Exception as e:
        error_logger(
            "recreate_role",
            str(e),
            logger=logger,
            mode="error"
        )
        return None

@log_method(level="info")
def get_role_arn(role_name):
    """
    Get the ARN of an IAM role.
    
    Args:
        role_name (str): The name of the IAM role.
        
    Returns:
        str: The ARN of the role, or None if the role doesn't exist or an error occurred.
    """
    try:
        # Create a session with the profile if specified
        session = Session(**get_boto3_session_args())
        iam_client = session.client('iam')
        
        # Try to get the role
        response = iam_client.get_role(RoleName=role_name)
        role_arn = response['Role']['Arn']
        logger.info(f"IAM role '{role_name}' has ARN: {role_arn}")
        return role_arn
    except iam_client.exceptions.NoSuchEntityException:
        logger.info(f"IAM role '{role_name}' does not exist")
        return None
    except Exception as e:
        error_logger(
            "get_role_arn",
            str(e),
            logger=logger,
            mode="error"
        )
        return None

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Manage IAM roles for Lambda functions")
    parser.add_argument("--role-name", type=str, required=True, help="Name of the IAM role")
    parser.add_argument("--description", type=str, default="Lambda execution role", help="Description of the IAM role")
    parser.add_argument("--vpc-access", action="store_true", help="Add VPC access permissions to the role")
    parser.add_argument("--check", action="store_true", help="Check if the role exists")
    parser.add_argument("--delete", action="store_true", help="Delete the role if it exists")
    parser.add_argument("--create", action="store_true", help="Create the role if it doesn't exist")
    parser.add_argument("--recreate", action="store_true", help="Delete the role if it exists and create a new one")
    parser.add_argument("--get-arn", action="store_true", help="Get the ARN of the role")
    parser.add_argument("--env-file", type=str, help="Path to .env file")
    return parser.parse_args()

if __name__ == "__main__":
    # Parse command-line arguments
    args = parse_args()
    
    # Load environment variables from .env file if specified
    if args.env_file:
        from dotenv import load_dotenv
        load_dotenv(args.env_file)
    
    # Execute the requested action
    if args.check:
        exists = check_role_exists(args.role_name)
        print(f"Role '{args.role_name}' exists: {exists}")
    elif args.delete:
        success = delete_role(args.role_name)
        print(f"Role '{args.role_name}' deletion {'succeeded' if success else 'failed'}")
    elif args.create:
        role_arn = create_role(args.role_name, args.description, args.vpc_access)
        if role_arn:
            print(f"Role '{args.role_name}' created with ARN: {role_arn}")
        else:
            print(f"Failed to create role '{args.role_name}'")
    elif args.recreate:
        role_arn = recreate_role(args.role_name, args.description, args.vpc_access)
        if role_arn:
            print(f"Role '{args.role_name}' recreated with ARN: {role_arn}")
        else:
            print(f"Failed to recreate role '{args.role_name}'")
    elif args.get_arn:
        role_arn = get_role_arn(args.role_name)
        if role_arn:
            print(f"Role '{args.role_name}' ARN: {role_arn}")
        else:
            print(f"Failed to get ARN for role '{args.role_name}'")
    else:
        print("No action specified. Use --check, --delete, --create, --recreate, or --get-arn")
