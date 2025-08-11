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
            mock_response.json = AsyncMock(return_value={
                "data": [{"id": "openai/gpt-oss-20b"}]
            })
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
            "score": 8.5,
            "max_score": 10.0,
            "reasoning": "Good response",
            "issues": ["Minor issue"],
            "suggestions": ["Improve X"],
            "severity": "low"
        }
        '''
        
        # Test
        result = self.evaluator._parse_evaluation_result(result_text, EvaluationCriteria.ACCURACY)
        
        # Asserts
        assert isinstance(result, EvaluationResult)
        assert result.score == 8.5
        assert result.max_score == 10.0
        assert result.reasoning == "Good response"
    
    def test_init_default_values(self):
        """Test domyślnych wartości przy inicjalizacji"""
        
        evaluator = AIEvaluator()
        
        assert evaluator.lm_studio_url == "http://127.0.0.1:1234"
        assert evaluator.model_name == "openai/gpt-oss-20b"
        assert evaluator.quality_gate_threshold == 75.0
