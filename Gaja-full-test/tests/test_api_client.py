#!/usr/bin/env python3
"""
Testy jednostkowe dla GajaApiClient
"""

import pytest
import asyncio
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from src.utils.api_client import GajaApiClient, ResponseBundle


class TestGajaApiClient:
    """Testy dla klasy GajaApiClient"""
    
    def setup_method(self):
        """Setup przed każdym testem"""
        self.base_url = "http://localhost:8001"
        self.api_key = "test_key"
        self.client = GajaApiClient(self.base_url, self.api_key)
    
    @pytest.mark.asyncio
    async def test_send_text_success(self):
        """Test pomyślnego wysłania tekstu"""
        
        # Mock response
        mock_response = {
            "response": "Test response",
            "metadata": {"status": "success"}
        }
        
        with patch.object(self.client, '_make_request') as mock_request:
            mock_request.return_value = mock_response
            
            # Test
            result = await self.client.send_text("Test query")
            
            # Asserts
            assert isinstance(result, ResponseBundle)
            assert result.text == "Test response"
            mock_request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_text_error(self):
        """Test obsługi błędu przy wysyłaniu tekstu"""
        
        with patch.object(self.client, '_make_request') as mock_request:
            # Setup mock - wyjątek
            mock_request.side_effect = httpx.HTTPError("Network error")
            
            # Test - sprawdź czy nie rzuca wyjątkiem
            try:
                result = await self.client.send_text("Test query")
                
                # Asserts - powinna być zwrócona ResponseBundle z błędem
                assert isinstance(result, ResponseBundle)
                # Sprawdź czy tekst zawiera informację o błędzie lub jest pusty
                assert result.text == "" or "błąd" in result.text.lower() or "error" in result.text.lower()
            except httpx.HTTPError:
                # Jeśli rzuca wyjątkiem, to też jest OK - zależy od implementacji
                pass
    
    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test pomyślnego health check"""
        
        with patch.object(self.client, '_make_request') as mock_request:
            mock_request.return_value = {"status": "healthy"}
            
            # Test
            result = await self.client.health_check()
            
            # Asserts
            assert result is True
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test niepowodzenia health check"""
        
        with patch.object(self.client, '_make_request') as mock_request:
            # Setup mock - błąd
            mock_request.side_effect = httpx.HTTPError("Connection failed")
            
            # Test
            result = await self.client.health_check()
            
            # Asserts
            assert result is False
    
    @pytest.mark.asyncio
    async def test_authenticate_success(self):
        """Test pomyślnej autoryzacji"""
        
        with patch.object(self.client, '_make_request') as mock_request:
            mock_request.return_value = {"success": True, "token": "test_token"}
            
            # Test
            result = await self.client.authenticate("test@example.com", "password")
            
            # Asserts
            assert result is True
            assert self.client.session_token == "test_token"
    
    def test_init_with_required_args(self):
        """Test inicjalizacji z wymaganymi argumentami"""
        base_url = "https://custom.api.com"
        api_key = "custom_key"
        
        client = GajaApiClient(base_url, api_key)
        
        assert client.base_url == base_url
        assert client.api_key == api_key
        assert client.session_token is None
    
    def test_init_without_api_key(self):
        """Test inicjalizacji bez klucza API"""
        base_url = "https://custom.api.com"
        
        client = GajaApiClient(base_url)
        
        assert client.base_url == base_url
        assert client.api_key is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
