"""
Unit tests for ECR repository management.
"""
import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Add the project root to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

# Import the module to test
from lambda_docker.deployment.scripts.manage_ecr_repository import (
    check_repository_exists,
    delete_repository,
    create_repository,
    recreate_repository
)

class TestECRManagement:
    """Test ECR repository management functions."""
    
    @patch('lambda_docker.deployment.scripts.manage_ecr_repository.Session')
    def test_check_repository_exists_true(self, mock_session):
        """Test check_repository_exists when repository exists."""
        # Mock the ECR client
        mock_ecr_client = MagicMock()
        mock_session.return_value.client.return_value = mock_ecr_client
        
        # Set up the mock to indicate that the repository exists
        mock_ecr_client.describe_repositories.return_value = {
            'repositories': [{'repositoryName': 'test-repo'}]
        }
        
        # Call the function
        result = check_repository_exists('test-repo')
        
        # Verify the result
        assert result is True
        mock_ecr_client.describe_repositories.assert_called_once_with(repositoryNames=['test-repo'])
    
    @patch('lambda_docker.deployment.scripts.manage_ecr_repository.Session')
    def test_check_repository_exists_false(self, mock_session):
        """Test check_repository_exists when repository doesn't exist."""
        # Mock the ECR client
        mock_ecr_client = MagicMock()
        mock_session.return_value.client.return_value = mock_ecr_client
        
        # Set up the mock to indicate that the repository doesn't exist
        mock_ecr_client.exceptions.RepositoryNotFoundException = Exception
        mock_ecr_client.describe_repositories.side_effect = mock_ecr_client.exceptions.RepositoryNotFoundException
        
        # Call the function
        result = check_repository_exists('test-repo')
        
        # Verify the result
        assert result is False
        mock_ecr_client.describe_repositories.assert_called_once_with(repositoryNames=['test-repo'])
    
    @patch('lambda_docker.deployment.scripts.manage_ecr_repository.check_repository_exists')
    @patch('lambda_docker.deployment.scripts.manage_ecr_repository.Session')
    def test_delete_repository_exists(self, mock_session, mock_check):
        """Test delete_repository when repository exists."""
        # Mock the ECR client
        mock_ecr_client = MagicMock()
        mock_session.return_value.client.return_value = mock_ecr_client
        
        # Set up the mock to indicate that the repository exists
        mock_check.return_value = True
        
        # Call the function
        result = delete_repository('test-repo', force=True)
        
        # Verify the result
        assert result is True
        mock_check.assert_called_once_with('test-repo')
        mock_ecr_client.delete_repository.assert_called_once_with(
            repositoryName='test-repo',
            force=True
        )
    
    @patch('lambda_docker.deployment.scripts.manage_ecr_repository.check_repository_exists')
    @patch('lambda_docker.deployment.scripts.manage_ecr_repository.Session')
    def test_delete_repository_not_exists(self, mock_session, mock_check):
        """Test delete_repository when repository doesn't exist."""
        # Mock the ECR client
        mock_ecr_client = MagicMock()
        mock_session.return_value.client.return_value = mock_ecr_client
        
        # Set up the mock to indicate that the repository doesn't exist
        mock_check.return_value = False
        
        # Call the function
        result = delete_repository('test-repo')
        
        # Verify the result
        assert result is True
        mock_check.assert_called_once_with('test-repo')
        mock_ecr_client.delete_repository.assert_not_called()
    
    @patch('lambda_docker.deployment.scripts.manage_ecr_repository.Session')
    def test_create_repository(self, mock_session):
        """Test create_repository."""
        # Mock the ECR client
        mock_ecr_client = MagicMock()
        mock_session.return_value.client.return_value = mock_ecr_client
        
        # Call the function
        result = create_repository('test-repo')
        
        # Verify the result
        assert result is True
        mock_ecr_client.create_repository.assert_called_once_with(
            repositoryName='test-repo',
            imageScanningConfiguration={'scanOnPush': True},
            encryptionConfiguration={'encryptionType': 'AES256'}
        )
    
    @patch('lambda_docker.deployment.scripts.manage_ecr_repository.delete_repository')
    @patch('lambda_docker.deployment.scripts.manage_ecr_repository.create_repository')
    def test_recreate_repository(self, mock_create, mock_delete):
        """Test recreate_repository."""
        # Set up the mocks
        mock_delete.return_value = True
        mock_create.return_value = True
        
        # Call the function
        result = recreate_repository('test-repo', force=True)
        
        # Verify the result
        assert result is True
        mock_delete.assert_called_once_with('test-repo', True)
        mock_create.assert_called_once_with('test-repo')
