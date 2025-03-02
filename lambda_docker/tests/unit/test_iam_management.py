"""
Unit tests for IAM role management.
"""
import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Add the project root to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

# Import the module to test
from lambda_docker.deployment.scripts.manage_iam_role import (
    check_role_exists,
    delete_role,
    create_role,
    recreate_role,
    get_role_arn
)

class TestIAMRoleManagement:
    """Test IAM role management functions."""
    
    @patch('lambda_docker.deployment.scripts.manage_iam_role.Session')
    def test_check_role_exists_true(self, mock_session):
        """Test check_role_exists when role exists."""
        # Mock the IAM client
        mock_iam_client = MagicMock()
        mock_session.return_value.client.return_value = mock_iam_client
        
        # Set up the mock to indicate that the role exists
        mock_iam_client.get_role.return_value = {
            'Role': {'RoleName': 'test-role', 'Arn': 'arn:aws:iam::123456789012:role/test-role'}
        }
        
        # Call the function
        result = check_role_exists('test-role')
        
        # Verify the result
        assert result is True
        mock_iam_client.get_role.assert_called_once_with(RoleName='test-role')
    
    @patch('lambda_docker.deployment.scripts.manage_iam_role.Session')
    def test_check_role_exists_false(self, mock_session):
        """Test check_role_exists when role doesn't exist."""
        # Mock the IAM client
        mock_iam_client = MagicMock()
        mock_session.return_value.client.return_value = mock_iam_client
        
        # Set up the mock to indicate that the role doesn't exist
        mock_iam_client.exceptions.NoSuchEntityException = Exception
        mock_iam_client.get_role.side_effect = mock_iam_client.exceptions.NoSuchEntityException
        
        # Call the function
        result = check_role_exists('test-role')
        
        # Verify the result
        assert result is False
        mock_iam_client.get_role.assert_called_once_with(RoleName='test-role')
    
    @patch('lambda_docker.deployment.scripts.manage_iam_role.check_role_exists')
    @patch('lambda_docker.deployment.scripts.manage_iam_role.Session')
    def test_delete_role_exists(self, mock_session, mock_check):
        """Test delete_role when role exists."""
        # Mock the IAM client
        mock_iam_client = MagicMock()
        mock_session.return_value.client.return_value = mock_iam_client
        
        # Set up the mock to indicate that the role exists
        mock_check.return_value = True
        
        # Mock the list_attached_role_policies response
        mock_iam_client.list_attached_role_policies.return_value = {
            'AttachedPolicies': [
                {'PolicyArn': 'arn:aws:iam::aws:policy/AWSLambdaExecute'}
            ]
        }
        
        # Mock the list_role_policies response
        mock_iam_client.list_role_policies.return_value = {
            'PolicyNames': ['inline-policy']
        }
        
        # Call the function
        result = delete_role('test-role')
        
        # Verify the result
        assert result is True
        mock_check.assert_called_once_with('test-role')
        mock_iam_client.detach_role_policy.assert_called_once_with(
            RoleName='test-role',
            PolicyArn='arn:aws:iam::aws:policy/AWSLambdaExecute'
        )
        mock_iam_client.delete_role_policy.assert_called_once_with(
            RoleName='test-role',
            PolicyName='inline-policy'
        )
        mock_iam_client.delete_role.assert_called_once_with(RoleName='test-role')
    
    @patch('lambda_docker.deployment.scripts.manage_iam_role.check_role_exists')
    @patch('lambda_docker.deployment.scripts.manage_iam_role.Session')
    def test_delete_role_not_exists(self, mock_session, mock_check):
        """Test delete_role when role doesn't exist."""
        # Mock the IAM client
        mock_iam_client = MagicMock()
        mock_session.return_value.client.return_value = mock_iam_client
        
        # Set up the mock to indicate that the role doesn't exist
        mock_check.return_value = False
        
        # Call the function
        result = delete_role('test-role')
        
        # Verify the result
        assert result is True
        mock_check.assert_called_once_with('test-role')
        mock_iam_client.delete_role.assert_not_called()
    
    @patch('lambda_docker.deployment.scripts.manage_iam_role.Session')
    def test_create_role(self, mock_session):
        """Test create_role."""
        # Mock the IAM client
        mock_iam_client = MagicMock()
        mock_session.return_value.client.return_value = mock_iam_client
        
        # Set up the mock to return a role ARN
        mock_iam_client.create_role.return_value = {
            'Role': {
                'RoleName': 'test-role',
                'Arn': 'arn:aws:iam::123456789012:role/test-role'
            }
        }
        
        # Call the function
        role_arn = create_role('test-role', 'Test role description')
        
        # Verify the result
        assert role_arn == 'arn:aws:iam::123456789012:role/test-role'
        mock_iam_client.create_role.assert_called_once()
        mock_iam_client.put_role_policy.assert_called()
    
    @patch('lambda_docker.deployment.scripts.manage_iam_role.Session')
    def test_create_role_with_vpc_access(self, mock_session):
        """Test create_role with VPC access."""
        # Mock the IAM client
        mock_iam_client = MagicMock()
        mock_session.return_value.client.return_value = mock_iam_client
        
        # Set up the mock to return a role ARN
        mock_iam_client.create_role.return_value = {
            'Role': {
                'RoleName': 'test-role',
                'Arn': 'arn:aws:iam::123456789012:role/test-role'
            }
        }
        
        # Call the function with vpc_access=True
        role_arn = create_role('test-role', 'Test role description', vpc_access=True)
        
        # Verify the result
        assert role_arn == 'arn:aws:iam::123456789012:role/test-role'
        mock_iam_client.create_role.assert_called_once()
        
        # Verify that put_role_policy was called twice (basic execution and VPC access)
        assert mock_iam_client.put_role_policy.call_count == 2
    
    @patch('lambda_docker.deployment.scripts.manage_iam_role.delete_role')
    @patch('lambda_docker.deployment.scripts.manage_iam_role.create_role')
    def test_recreate_role(self, mock_create, mock_delete):
        """Test recreate_role."""
        # Set up the mocks
        mock_delete.return_value = True
        mock_create.return_value = 'arn:aws:iam::123456789012:role/test-role'
        
        # Call the function
        role_arn = recreate_role('test-role', 'Test role description')
        
        # Verify the result
        assert role_arn == 'arn:aws:iam::123456789012:role/test-role'
        mock_delete.assert_called_once_with('test-role')
        mock_create.assert_called_once_with('test-role', 'Test role description', False)
    
    @patch('lambda_docker.deployment.scripts.manage_iam_role.delete_role')
    @patch('lambda_docker.deployment.scripts.manage_iam_role.create_role')
    def test_recreate_role_with_vpc_access(self, mock_create, mock_delete):
        """Test recreate_role with VPC access."""
        # Set up the mocks
        mock_delete.return_value = True
        mock_create.return_value = 'arn:aws:iam::123456789012:role/test-role'
        
        # Call the function with vpc_access=True
        role_arn = recreate_role('test-role', 'Test role description', vpc_access=True)
        
        # Verify the result
        assert role_arn == 'arn:aws:iam::123456789012:role/test-role'
        mock_delete.assert_called_once_with('test-role')
        mock_create.assert_called_once_with('test-role', 'Test role description', True)
    
    @patch('lambda_docker.deployment.scripts.manage_iam_role.Session')
    def test_get_role_arn(self, mock_session):
        """Test get_role_arn."""
        # Mock the IAM client
        mock_iam_client = MagicMock()
        mock_session.return_value.client.return_value = mock_iam_client
        
        # Set up the mock to return a role ARN
        mock_iam_client.get_role.return_value = {
            'Role': {
                'RoleName': 'test-role',
                'Arn': 'arn:aws:iam::123456789012:role/test-role'
            }
        }
        
        # Call the function
        role_arn = get_role_arn('test-role')
        
        # Verify the result
        assert role_arn == 'arn:aws:iam::123456789012:role/test-role'
        mock_iam_client.get_role.assert_called_once_with(RoleName='test-role')
    
    @patch('lambda_docker.deployment.scripts.manage_iam_role.Session')
    def test_get_role_arn_not_exists(self, mock_session):
        """Test get_role_arn when role doesn't exist."""
        # Mock the IAM client
        mock_iam_client = MagicMock()
        mock_session.return_value.client.return_value = mock_iam_client
        
        # Set up the mock to indicate that the role doesn't exist
        mock_iam_client.exceptions.NoSuchEntityException = Exception
        mock_iam_client.get_role.side_effect = mock_iam_client.exceptions.NoSuchEntityException
        
        # Call the function
        role_arn = get_role_arn('test-role')
        
        # Verify the result
        assert role_arn is None
        mock_iam_client.get_role.assert_called_once_with(RoleName='test-role')
