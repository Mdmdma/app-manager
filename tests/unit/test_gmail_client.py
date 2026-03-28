"""Tests for jam.gmail_client module."""

import pytest
from unittest.mock import MagicMock, patch
from jam.gmail_client import (
    get_auth_url, get_credentials, list_emails, get_email,
    create_draft, send_email
)


@pytest.fixture
def mock_settings():
    """Fixture providing a mock Settings object with Gmail credentials."""
    settings = MagicMock()
    settings.gmail_client_id = "123456.apps.googleusercontent.com"
    settings.gmail_client_secret = "secret-key"
    settings.gmail_refresh_token = "refresh-token"
    settings.gmail_user_email = "user@example.com"
    return settings


class TestGetAuthUrl:
    """Tests for get_auth_url function."""
    
    def test_get_auth_url_missing_client_id(self):
        """get_auth_url should raise ValueError when client_id is missing."""
        settings = MagicMock()
        settings.gmail_client_id = ""
        settings.gmail_client_secret = "secret"
        
        with pytest.raises(ValueError, match="gmail_client_id not configured"):
            get_auth_url(settings=settings)
    
    def test_get_auth_url_missing_client_secret(self):
        """get_auth_url should raise ValueError when client_secret is missing."""
        settings = MagicMock()
        settings.gmail_client_id = "123456.apps.googleusercontent.com"
        settings.gmail_client_secret = ""
        
        with pytest.raises(ValueError, match="gmail_client_secret not configured"):
            get_auth_url(settings=settings)


class TestGetCredentials:
    """Tests for get_credentials function."""
    
    def test_get_credentials_missing_refresh_token(self):
        """get_credentials should raise ValueError when refresh_token is missing."""
        settings = MagicMock()
        settings.gmail_refresh_token = ""
        
        with pytest.raises(ValueError, match="gmail_refresh_token not configured"):
            get_credentials(settings=settings)


class TestListEmails:
    """Tests for list_emails function."""
    
    def test_list_emails_returns_empty_list(self, mock_settings):
        """list_emails should return empty list when no messages found."""
        with patch("jam.gmail_client.get_credentials") as mock_get_creds, \
             patch("jam.gmail_client.build") as mock_build:
            
            mock_creds = MagicMock()
            mock_get_creds.return_value = mock_creds
            
            mock_service = MagicMock()
            mock_build.return_value = mock_service
            
            # Mock the service chain: users().messages().list()
            mock_list_result = {"messages": []}
            mock_service.users().messages().list().execute.return_value = mock_list_result
            
            result = list_emails(settings=mock_settings)
            
            assert isinstance(result, list)
            assert len(result) == 0


class TestGetEmail:
    """Tests for get_email function."""
    
    def test_get_email_returns_full_message(self, mock_settings):
        """get_email should return full email details."""
        with patch("jam.gmail_client.get_credentials") as mock_get_creds, \
             patch("jam.gmail_client.build") as mock_build:
            
            mock_creds = MagicMock()
            mock_get_creds.return_value = mock_creds
            
            mock_service = MagicMock()
            mock_build.return_value = mock_service
            
            mock_msg = {
                "id": "msg-123",
                "payload": {
                    "headers": [
                        {"name": "Subject", "value": "Test Subject"},
                        {"name": "From", "value": "sender@example.com"},
                        {"name": "To", "value": "recipient@example.com"},
                        {"name": "Date", "value": "2026-03-28"},
                    ],
                    "parts": []
                }
            }
            
            mock_service.users().messages().get().execute.return_value = mock_msg
            
            result = get_email("msg-123", settings=mock_settings)
            
            assert result["id"] == "msg-123"
            assert result["subject"] == "Test Subject"
            assert result["from"] == "sender@example.com"
            assert result["to"] == "recipient@example.com"
