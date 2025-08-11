"""Ewaluator używający lokalnej instancji LM Studio do oceny jakości odpowiedzi."""

import json
import os
from pathlib import Path
from typing import Any, Dict, Tuple

import httpx
from jinja2 import Environment, FileSystemLoader
from loguru import logger


class GraderEvaluator:
    """Ewaluator używający LM Studio do oceny odpowiedzi."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        grader_config = config.get("grader", {})
        
        self.base_url = grader_config.get("lmstudio_base_url", "http://localhost:1234/v1/chat/completions")
        self.model = grader_config.get("model", "gpt-oss-20b")
        self.max_tokens = grader_config.get("max_tokens", 512)
        self.temperature = grader_config.get("temperature", 0.1)
        
        # Załaduj prompty
        self.jinja_env = Environment(loader=FileSystemLoader('prompts'))
        
    def _load_prompt_template(self, template_name: str):
        """Ładuje template promptu."""
        try:
            template = self.jinja_env.get_template(template_name)
            return template
        except Exception as e:
            logger.error(f"Failed to load prompt template {template_name}: {e}")
            raise
    
    async def _call_lm_studio(self, messages: list) -> Dict[str, Any]:
        """Wywołuje LM Studio API."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.base_url,
                    json={
                        "model": self.model,
                        "messages": messages,
                        "max_tokens": self.max_tokens,
                        "temperature": self.temperature
                    }
                )
                
                response.raise_for_status()
                return response.json()
                
        except httpx.ConnectError:
            logger.error("Cannot connect to LM Studio. Make sure it's running on the configured URL.")
            raise
        except httpx.HTTPError as e:
            logger.error(f"LM Studio API error: {e}")
            raise
        except Exception as e:
            logger.error(f"LM Studio call failed: {e}")
            raise
    
    def _parse_grade_response(self, response_text: str) -> Tuple[float, str]:
        """Parsuje odpowiedź gradatora i wyciąga ocenę + komentarze."""
        try:
            # Spróbuj sparsować jako JSON
            if response_text.strip().startswith("{"):
                data = json.loads(response_text)
                grade = data.get("ocena", 0.0)
                comments = data.get("uwagi", "Brak komentarzy")
                return float(grade), comments
            
            # Fallback - szukaj wzorców w tekście
            lines = response_text.strip().split("\n")
            grade = 5.0  # domyślna ocena
            comments = response_text
            
            for line in lines:
                line = line.strip()
                if "ocena" in line.lower() or "grade" in line.lower():
                    # Szukaj cyfr
                    import re
                    numbers = re.findall(r'\d+\.?\d*', line)
                    if numbers:
                        grade = float(numbers[0])
                        break
            
            return grade, comments
            
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse grader response as JSON: {response_text[:100]}...")
            return 5.0, response_text
        except Exception as e:
            logger.error(f"Failed to parse grader response: {e}")
            return 0.0, f"Parse error: {str(e)}"
    
    async def grade_semantic_response(
        self,
        user_input: str,
        assistant_text: str,
        meta_json: Dict[str, Any]
    ) -> Tuple[float, str]:
        """Ocenia semantyczną poprawność odpowiedzi asystenta."""
        
        try:
            # Załaduj template promptu
            system_template = self._load_prompt_template("grader_system.txt")
            user_template = self._load_prompt_template("grader_user.txt")
            
            # Renderuj prompty
            system_prompt = system_template.render()
            user_prompt = user_template.render(
                user_input=user_input,
                assistant_text=assistant_text,
                meta_json=json.dumps(meta_json, ensure_ascii=False, indent=2)
            )
            
            # Przygotuj messages dla LM Studio
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            logger.debug(f"Sending grading request for: {user_input[:50]}...")
            
            # Wywołaj LM Studio
            response = await self._call_lm_studio(messages)
            
            # Wyciągnij text odpowiedzi
            response_text = ""
            if "choices" in response and len(response["choices"]) > 0:
                choice = response["choices"][0]
                if "message" in choice and "content" in choice["message"]:
                    response_text = choice["message"]["content"]
            
            if not response_text:
                logger.error("Empty response from LM Studio")
                return 0.0, "Empty response from grader"
            
            # Parsuj ocenę
            grade, comments = self._parse_grade_response(response_text)
            
            # Clamp grade to 0-10 range
            grade = max(0.0, min(10.0, grade))
            
            logger.info(f"📊 Graded response: {grade:.1f}/10 - {comments[:50]}...")
            
            return grade, comments
            
        except Exception as e:
            logger.error(f"Grading failed: {e}")
            return 0.0, f"Grading error: {str(e)}"
    
    async def grade_effect_verification(
        self,
        expected_effect: str,
        actual_result: Dict[str, Any]
    ) -> Tuple[float, str]:
        """Ocenia czy oczekiwany efekt został osiągnięty."""
        
        try:
            # Prosty ewaluator efektów bez LLM
            if not actual_result:
                return 0.0, "No result data to verify effect"
            
            # Sprawdź podstawowe pola
            success = actual_result.get("success", False)
            
            if success:
                if expected_effect == "habit_add" and "habit" in str(actual_result).lower():
                    return 10.0, "Habit successfully added"
                elif expected_effect == "calendar_add" and "calendar" in str(actual_result).lower():
                    return 10.0, "Calendar event successfully added"
                elif expected_effect == "service_restarted" and actual_result.get("action") == "service_restarted":
                    return 10.0, "Service successfully restarted"
                else:
                    return 7.0, f"Effect occurred but unclear if matches expected: {expected_effect}"
            else:
                error_msg = actual_result.get("error", "Unknown error")
                return 2.0, f"Effect failed: {error_msg}"
                
        except Exception as e:
            logger.error(f"Effect verification failed: {e}")
            return 0.0, f"Verification error: {str(e)}"
    
    async def check_lm_studio_health(self) -> bool:
        """Sprawdza czy LM Studio jest dostępne."""
        try:
            messages = [{"role": "user", "content": "Hello"}]
            response = await self._call_lm_studio(messages)
            
            return "choices" in response and len(response["choices"]) > 0
            
        except Exception as e:
            logger.warning(f"LM Studio health check failed: {e}")
            return False
