#!/usr/bin/env python3
"""
Testy jednostkowe dla SimpleTestRunner
"""

import pytest
import asyncio
import tempfile
import os
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path
from simple_runner import SimpleTestRunner


class TestSimpleTestRunner:
    """Testy dla klasy SimpleTestRunner"""
    
    def setup_method(self):
        """Setup przed każdym testem"""
        # Utwórz tymczasowy config
        self.temp_config = {
            "gaja": {
                "base_url": "http://localhost:8001",
                "auth_token": "test_token"
            },
            "voice": {
                "model": "tts-1",
                "voice": "alloy"
            }
        }
        
        with patch.object(SimpleTestRunner, 'load_config', return_value=self.temp_config):
            self.runner = SimpleTestRunner("test_config.yaml")
    
    def test_init(self):
        """Test inicjalizacji runnera"""
        assert self.runner.config == self.temp_config
        assert self.runner.results == []
        assert self.runner.jwt_token is None
        assert self.runner.conversation_history == {}
    
    @pytest.mark.asyncio
    async def test_health_checks_success(self):
        """Test pomyślnego health check"""
        
        with patch.object(self.runner, 'api_client') as mock_client:
            mock_client.health_check.return_value = True
            
            # Test
            result = await self.runner.health_checks()
            
            # Asserts
            assert result is True
    
    @pytest.mark.asyncio
    async def test_health_checks_failure(self):
        """Test niepowodzenia health check"""
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            # Mock failed health check
            mock_response = MagicMock()
            mock_response.status = 500
            mock_get.return_value.__aenter__.return_value = mock_response
            
            # Test
            result = await self.runner.health_checks()
            
            # Health checks return True if success_rate >= 0.5
            # With 0/1 checks passed, success_rate = 0.0 < 0.5, so should return False
            assert result is False
    
    @pytest.mark.asyncio
    async def test_login_success(self):
        """Test pomyślnego logowania"""
        
        # Mock aiohttp session
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"success": True, "token": "test_jwt_token"})
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response
            
            # Test
            result = await self.runner.login("admin")
            
            # Asserts
            assert result is True
            assert self.runner.jwt_token == "test_jwt_token"
    
    @pytest.mark.asyncio
    async def test_login_failure(self):
        """Test niepowodzenia logowania"""
        
        # Mock aiohttp session
        mock_response = MagicMock()
        mock_response.status = 401
        mock_response.text = AsyncMock(return_value="Unauthorized")
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response
            
            # Test
            result = await self.runner.login("admin")
            
            # Asserts
            assert result is False
            assert self.runner.jwt_token is None
    
    @pytest.mark.asyncio
    async def test_send_text_with_auth_success(self):
        """Test pomyślnego wysłania wiadomości z autoryzacją"""
        
        self.runner.jwt_token = "test_token"
        
        # Mock aiohttp session
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"response": "AI response"})
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response
            
            # Test
            result = await self.runner.send_text_with_auth("Test message")
            
            # Asserts
            assert result["success"] is True
            assert result["data"]["response"] == "AI response"
    
    @pytest.mark.asyncio
    async def test_send_text_with_auth_no_token(self):
        """Test wysłania wiadomości bez tokena"""
        
        self.runner.jwt_token = None
        
        # Test
        result = await self.runner.send_text_with_auth("Test message")
        
        # Asserts
        assert result["success"] is False
        assert "Brak tokena JWT" in result["error"]
    
    @pytest.mark.asyncio
    async def test_load_scenario_success(self):
        """Test pomyślnego ładowania scenariusza"""
        
        # Utwórz tymczasowy plik scenariusza
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
meta:
  name: "Test Scenario"
  tags: ["test"]

steps:
  - type: "text"
    message: "Test message"
""")
            temp_file = f.name
        
        try:
            # Test
            scenario = await self.runner.load_scenario(temp_file)
            
            # Asserts
            assert scenario is not None
            assert scenario["meta"]["name"] == "Test Scenario"
            assert len(scenario["steps"]) == 1
            
        finally:
            # Cleanup
            os.unlink(temp_file)
    
    @pytest.mark.asyncio
    async def test_load_scenario_file_not_found(self):
        """Test ładowania nieistniejącego scenariusza"""
        
        # Test
        scenario = await self.runner.load_scenario("nonexistent.yaml")
        
        # Asserts
        assert scenario is None
    
    @pytest.mark.asyncio
    async def test_execute_step_text(self):
        """Test wykonania kroku tekstowego"""
        
        self.runner.jwt_token = "test_token"
        self.runner._current_scenario_name = "test_scenario"
        
        # Mock send_text_with_auth
        mock_response = {"success": True, "data": {"response": "AI response"}}
        
        with patch.object(self.runner, 'send_text_with_auth', return_value=mock_response):
            step = {
                "type": "text",
                "message": "Test message"
            }
            
            # Test
            result = await self.runner.execute_step(step, 0)
            
            # Asserts
            assert result["success"] is True
            assert result["response"] == mock_response
            assert "test_scenario" in self.runner.conversation_history
            assert len(self.runner.conversation_history["test_scenario"]) == 1
    
    @pytest.mark.asyncio
    async def test_execute_step_audio(self):
        """Test wykonania kroku audio"""
        
        self.runner.jwt_token = "test_token"
        self.runner._current_scenario_name = "test_scenario"
        
        # Mock send_text_with_auth
        mock_response = {"success": True, "data": {"response": "AI audio response"}}
        
        with patch.object(self.runner, 'send_text_with_auth', return_value=mock_response):
            step = {
                "type": "audio",
                "tts_text": "Test audio message"
            }
            
            # Test
            result = await self.runner.execute_step(step, 0)
            
            # Asserts
            assert result["success"] is True
            assert result["response"] == mock_response
            assert "test_scenario" in self.runner.conversation_history
    
    @pytest.mark.asyncio
    async def test_execute_step_restart_gaja(self):
        """Test wykonania kroku restart_gaja"""
        
        step = {
            "type": "restart_gaja"
        }
        
        # Test
        result = await self.runner.execute_step(step, 0)
        
        # Asserts
        assert result["success"] is True
        assert result["response"]["message"] == "Restart symulowany"
    
    @pytest.mark.asyncio
    async def test_execute_step_unknown_type(self):
        """Test wykonania nieznanego typu kroku"""
        
        step = {
            "type": "unknown_step_type"
        }
        
        # Test
        result = await self.runner.execute_step(step, 0)
        
        # Asserts - zgodnie z implementacją, nieznane kroki są oznaczane jako sukces
        assert result["success"] is True
        assert result["action"] == "unknown_step_type"
    
    def test_generate_simple_report(self):
        """Test generowania raportu"""
        
        # Dodaj przykładowe wyniki
        self.runner.results = [
            {
                "name": "Test Scenario",
                "success": True,
                "steps": [{"success": True}],
                "start_time": "2025-01-09T10:00:00",
                "end_time": "2025-01-09T10:01:00"
            }
        ]
        
        # Test
        report_path = self.runner.generate_simple_report()
        
        # Asserts
        assert isinstance(report_path, str)
        assert report_path.endswith('.html')
        assert os.path.exists(report_path)
        
        # Cleanup
        if os.path.exists(report_path):
            os.unlink(report_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
