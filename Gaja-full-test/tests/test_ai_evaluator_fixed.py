#!/usr/bin/env python3
"""
Testy jednostkowe dla AI Evaluatora
"""

import pytest
import asyncio
import aiohttp
from unittest.mock import AsyncMock, patch, MagicMock
from src.evaluation.ai_evaluator import AIEvaluator, EvaluationCriteria, EvaluationResult


class TestAIEvaluator:
    """Testy dla klasy AIEvaluator"""
    
    def setup_method(self):
        """Setup przed każdym testem"""
        self.evaluator = AIEvaluator()
    
    @pytest.mark.asyncio
    async def test_test_connection_success(self):
        """Test pomyślnego połączenia z LM Studio"""
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            # Setup mock - success
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"status": "ok"})
            mock_get.return_value.__aenter__.return_value = mock_response
            
            # Test
            result = await self.evaluator.test_connection()
            
            # Asserts
            assert result is True
    
    @pytest.mark.asyncio
    async def test_test_connection_failure(self):
        """Test niepowodzenia połączenia z LM Studio"""
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            # Setup mock - błąd
            mock_get.side_effect = aiohttp.ClientError("Connection failed")
            
            # Test
            result = await self.evaluator.test_connection()
            
            # Asserts
            assert result is False
    
    @pytest.mark.asyncio
    async def test_evaluate_conversation_empty(self):
        """Test oceny pustej konwersacji"""
        
        # Test z pustą konwersacją
        result = await self.evaluator.evaluate_conversation([], "Test scenario", [])
        
        # Asserts - pusta konwersacja powinna otrzymać niską ocenę (nie 0)
        assert result.total_score < 20  # Model powinien ocenić pustą konwersację jako słabą
        assert result.success_percentage < 20
        assert not result.passes_quality_gate  # Pusta konwersacja nie powinna przejść
    
    def test_parse_evaluation_result_valid_json(self):
        """Test parsowania poprawnego JSON"""
        
        result_text = '''
        {
            "overall_score": 8.5,
            "max_score": 10.0,
            "criteria_scores": {
                "accuracy": 9.0,
                "context": 8.0,
                "proactivity": 8.5
            }
        }
        '''
        
        # Test
        result = self.evaluator._parse_evaluation_result(result_text)
        
        # Asserts
        assert result is not None
        assert result.get("overall_score") == 8.5
        assert result.get("max_score") == 10.0
    
    def test_parse_evaluation_result_invalid_json(self):
        """Test parsowania niepoprawnego JSON"""
        
        result_text = "To nie jest JSON"
        
        # Test
        result = self.evaluator._parse_evaluation_result(result_text)
        
        # Asserts
        assert result is None
    
    def test_parse_evaluation_result_json_with_text(self):
        """Test parsowania JSON z dodatkowym tekstem"""
        
        result_text = '''
        Tu jest jakiś tekst przed JSON.
        ```json
        {
            "overall_score": 7.5,
            "criteria_scores": {"accuracy": 8.0}
        }
        ```
        I jeszcze jakiś tekst po JSON.
        '''
        
        # Test
        result = self.evaluator._parse_evaluation_result(result_text)
        
        # Asserts
        assert result is not None
        assert result.get("overall_score") == 7.5
    
    def test_init_default_values(self):
        """Test domyślnych wartości przy inicjalizacji"""
        
        evaluator = AIEvaluator()
        
        assert evaluator.base_url == "http://localhost:1234"
        assert evaluator.model_name == "openai/gpt-oss-20b"
        assert evaluator.timeout == 600
    
    def test_init_custom_values(self):
        """Test niestandardowych wartości przy inicjalizacji"""
        
        evaluator = AIEvaluator(
            base_url="http://custom:5678",
            model_name="custom/model",
            timeout=300
        )
        
        assert evaluator.base_url == "http://custom:5678"
        assert evaluator.model_name == "custom/model"
        assert evaluator.timeout == 300
    
    @pytest.mark.asyncio
    async def test_evaluate_single_criteria_success(self):
        """Test oceny pojedynczego kryterium"""
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            # Setup mock response
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={
                "choices": [{
                    "message": {
                        "content": '{"score": 8.5, "max_score": 10.0, "reasoning": "Good response"}'
                    }
                }]
            })
            mock_post.return_value.__aenter__.return_value = mock_response
            
            # Test
            result = await self.evaluator._evaluate_single_criteria(
                EvaluationCriteria.ACCURACY,
                [{"query": "test", "response": {"data": {"response": "test answer"}}}],
                "Test scenario"
            )
            
            # Asserts
            assert isinstance(result, EvaluationResult)
            assert result.score == 8.5
            assert result.max_score == 10.0
            assert result.reasoning == "Good response"
