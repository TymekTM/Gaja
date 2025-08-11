"""Główny moduł uruchamiający testy E2E dla GAJA."""

import argparse
import asyncio
import json
import sys
import time
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

import yaml
from loguru import logger

# Dodajmy ścieżkę do sys.path
sys.path.append(str(Path(__file__).parent))

from utils.api_client import GajaApiClient
from utils.audio_simple import AudioProcessor
from utils.data_gen import DataGenerator
from utils.hooks import SystemHooks
from utils.io import TestLogger
from utils.timeouts import TimeoutManager
from evaluator import GraderEvaluator
from report_generator import ReportGenerator
from schema import ScenarioSchema, StepSchema, TestResult

import argparse
import asyncio
import json
import sys
import time
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

import yaml
from loguru import logger
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

# Dodajmy ścieżkę do sys.path
sys.path.append(str(Path(__file__).parent))

from utils.api_client import GajaApiClient
from utils.audio_simple import AudioProcessor
from utils.data_gen import DataGenerator
from utils.hooks import SystemHooks
from utils.io import TestLogger
from utils.timeouts import TimeoutManager
from evaluator import GraderEvaluator
from report_generator import ReportGenerator
from schema import ScenarioSchema, StepSchema, TestResult

import argparse
import asyncio
import os
import sys
import time
import webbrowser
from pathlib import Path
from typing import Any, Dict, List

import yaml
from loguru import logger
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from evaluator import GraderEvaluator
from report_generator import ReportGenerator
from schema import validate_config, validate_scenario
from utils.api_client import GajaApiClient
from utils.audio_simple import AudioProcessor
from .utils.data_gen import DataGenerator
from utils.hooks import SystemHooks
from utils.io import TestLogger


class TestRunner:
    """Główny runner testów end-to-end."""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config = None
        self.console = Console()
        self.test_logger = None
        
        # Komponenty
        self.api_client = None
        self.audio_processor = None
        self.data_generator = None
        self.evaluator = None
        self.hooks = None
        self.report_generator = None
    
    def load_config(self) -> None:
        """Ładuje i waliduje konfigurację."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                raw_config = yaml.safe_load(f)
            
            # Podstawienia zmiennych środowiskowych
            config_str = yaml.dump(raw_config)
            for key, value in os.environ.items():
                config_str = config_str.replace(f"${{{key}}}", value)
            
            self.config = yaml.safe_load(config_str)
            
            # Walidacja
            validate_config(self.config)
            
            logger.info("✅ Configuration loaded and validated")
            
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            raise
    
    def check_dependencies(self) -> None:
        """Sprawdza dostępność zależności."""
        # Sprawdź FFmpeg
        try:
            import subprocess
            result = subprocess.run(["ffmpeg", "-version"], 
                                    capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                raise RuntimeError("FFmpeg not working properly")
            logger.info("✅ FFmpeg available")
        except Exception:
            logger.error("❌ FFmpeg not found or not working. Please install FFmpeg.")
            raise
        
        # Sprawdź klucze API
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            logger.error("❌ OPENAI_API_KEY not set in environment")
            raise ValueError("OPENAI_API_KEY required for TTS")
        
        logger.info("✅ Dependencies check passed")
    
    async def initialize_components(self) -> None:
        """Inicjalizuje wszystkie komponenty."""
        self.test_logger = TestLogger()
        
        # API Client
        gaja_config = self.config["gaja"]
        self.api_client = GajaApiClient(
            base_url=gaja_config["base_url"],
            api_key=gaja_config.get("api_key")
        )
        
        # Audio Processor
        voice_config = self.config["voice"]
        self.audio_processor = AudioProcessor(
            sample_rate=voice_config["sample_rate"],
            output_format=voice_config["output_format"]
        )
        
        # Data Generator
        runtime_config = self.config["runtime"]
        self.data_generator = DataGenerator(seed=runtime_config["seed"])
        
        # Evaluator
        self.evaluator = GraderEvaluator(self.config)
        
        # Hooks
        self.hooks = SystemHooks(self.config)
        
        # Report Generator
        self.report_generator = ReportGenerator(self.config)
        
        logger.info("✅ All components initialized")
    
    async def check_services_health(self) -> None:
        """Sprawdza dostępność serwisów."""
        # Sprawdź GAJA Server
        gaja_healthy = await self.api_client.health_check()
        if not gaja_healthy:
            raise RuntimeError("GAJA Server is not healthy")
        logger.info("✅ GAJA Server is healthy")
        
        # Sprawdź LM Studio
        lm_studio_healthy = await self.evaluator.check_lm_studio_health()
        if not lm_studio_healthy:
            logger.warning("⚠️ LM Studio not available - semantic evaluation will be skipped")
        else:
            logger.info("✅ LM Studio is available")
    
    def load_scenarios(self, scenario_paths: List[str]) -> List[Dict[str, Any]]:
        """Ładuje i waliduje scenariusze."""
        scenarios = []
        
        for path in scenario_paths:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    scenario_data = yaml.safe_load(f)
                
                # Walidacja
                scenario = validate_scenario(scenario_data)
                scenarios.append({
                    "path": path,
                    "data": scenario.model_dump()
                })
                
                logger.info(f"✅ Loaded scenario: {scenario.meta.name}")
                
            except Exception as e:
                logger.error(f"Failed to load scenario {path}: {e}")
                raise
        
        return scenarios
    
    async def authenticate_api(self) -> None:
        """Uwierzytelnia z API GAJA."""
        creds = self.data_generator.generate_test_credentials()
        
        success = await self.api_client.authenticate(
            email=creds["email"],
            password=creds["password"]
        )
        
        if not success:
            logger.warning("Authentication failed - some features may not work")
    
    async def execute_step(
        self,
        scenario_name: str,
        step_idx: int,
        step: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Wykonuje pojedynczy krok scenariusza."""
        step_type = step["type"]
        expect = step["expect"]
        
        input_data = {}
        output_data = {}
        plugin_data = None
        
        try:
            if step_type == "text":
                # Krok tekstowy
                message = step["message"]
                input_data = {"text": message, "type": "text"}
                
                response = await self.api_client.send_text(message)
                output_data = {
                    "text": response.text,
                    "raw_response": response.raw_response
                }
                
            elif step_type == "audio":
                # Krok audio
                tts_text = step["tts_text"]
                input_data = {"text": tts_text, "type": "audio"}
                
                # Generuj audio z TTS
                voice_config = self.config["voice"]
                audio_path = await self.audio_processor.tts_to_wav(
                    text=tts_text,
                    voice=voice_config["tts_voice"]
                )
                
                input_data["audio_path"] = audio_path
                
                # Wyślij audio do GAJA (na razie placeholder)
                response = await self.api_client.send_audio(audio_path)
                output_data = {
                    "text": response.text,
                    "audio_path": response.audio_path,
                    "raw_response": response.raw_response
                }
                
            elif step_type == "action":
                # Krok akcji systemowej
                action = step["action"]
                input_data = {"action": action, "type": "action"}
                
                result = await self.hooks.execute_action(action)
                output_data = {
                    "text": f"Action {action} executed",
                    "action_result": result
                }
                plugin_data = result
                
            else:
                raise ValueError(f"Unknown step type: {step_type}")
            
            # Wykonaj asercje
            assertions_results = await self.verify_assertions(
                step["expect"]["assertions"],
                input_data,
                output_data,
                plugin_data
            )
            
            # Zapisz log
            self.test_logger.log_step_execution(
                scenario=scenario_name,
                step_idx=step_idx,
                step_type=step_type,
                input_data=input_data,
                output_data=output_data,
                plugin_data=plugin_data,
                assertions=assertions_results
            )
            
            # Pauza między krokami
            sleep_ms = self.config["runtime"]["between_steps_sleep_ms"]
            if sleep_ms > 0:
                await asyncio.sleep(sleep_ms / 1000.0)
            
            return {
                "success": all(a["passed"] for a in assertions_results),
                "input": input_data,
                "output": output_data,
                "assertions": assertions_results
            }
            
        except Exception as e:
            logger.error(f"Step execution failed: {e}")
            self.test_logger.log_error(
                scenario=scenario_name,
                step_idx=step_idx,
                error_type=type(e).__name__,
                error_message=str(e)
            )
            
            return {
                "success": False,
                "error": str(e),
                "input": input_data,
                "output": output_data
            }
    
    async def verify_assertions(
        self,
        assertions: List[Dict[str, Any]],
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        plugin_data: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """Weryfikuje asercje dla kroku."""
        results = []
        
        for assertion in assertions:
            kind = assertion["kind"]
            target = assertion.get("target", "assistant_text")
            value = assertion.get("value")
            
            try:
                if kind == "contains":
                    # Sprawdź czy target zawiera wartość
                    target_text = self._get_assertion_target(target, output_data, plugin_data)
                    passed = value.lower() in target_text.lower() if value else False
                    
                    results.append({
                        "kind": kind,
                        "passed": passed,
                        "detail": f"Looking for '{value}' in {target}",
                        "target_value": target_text[:100]
                    })
                
                elif kind == "semantic_ok":
                    # Ocena semantyczna przez LM Studio
                    try:
                        grade, comments = await self.evaluator.grade_semantic_response(
                            user_input=input_data.get("text", ""),
                            assistant_text=output_data.get("text", ""),
                            meta_json={"input": input_data, "output": output_data}
                        )
                        
                        threshold = self.config["report"]["fail_threshold"]
                        passed = grade >= threshold
                        
                        results.append({
                            "kind": kind,
                            "passed": passed,
                            "grade": grade,
                            "detail": comments,
                            "threshold": threshold
                        })
                        
                    except Exception as e:
                        logger.warning(f"Semantic evaluation failed: {e}")
                        results.append({
                            "kind": kind,
                            "passed": False,
                            "detail": f"Evaluation error: {str(e)}"
                        })
                
                elif kind == "effect_ok":
                    # Sprawdzenie efektu akcji
                    if plugin_data:
                        grade, comments = await self.evaluator.grade_effect_verification(
                            expected_effect=assertion.get("expected_effect", "unknown"),
                            actual_result=plugin_data
                        )
                        passed = grade >= 8.0
                    else:
                        passed = False
                        comments = "No plugin data to verify effect"
                    
                    results.append({
                        "kind": kind,
                        "passed": passed,
                        "detail": comments
                    })
                
                elif kind == "jsonpath_eq":
                    # JSON path equality (placeholder)
                    results.append({
                        "kind": kind,
                        "passed": False,
                        "detail": "JSONPath assertions not implemented yet"
                    })
                
                else:
                    results.append({
                        "kind": kind,
                        "passed": False,
                        "detail": f"Unknown assertion kind: {kind}"
                    })
                    
            except Exception as e:
                logger.error(f"Assertion verification failed: {e}")
                results.append({
                    "kind": kind,
                    "passed": False,
                    "detail": f"Assertion error: {str(e)}"
                })
        
        return results
    
    def _get_assertion_target(
        self,
        target: str,
        output_data: Dict[str, Any],
        plugin_data: Dict[str, Any] = None
    ) -> str:
        """Pobiera wartość docelową dla asercji."""
        if target == "assistant_text":
            return output_data.get("text", "")
        elif target == "assistant_audio_path":
            return output_data.get("audio_path", "")
        elif target == "plugin_result":
            return str(plugin_data) if plugin_data else ""
        elif target == "side_effect":
            return str(output_data.get("action_result", ""))
        else:
            return ""
    
    async def run_scenario(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Wykonuje pojedynczy scenariusz."""
        scenario_name = scenario["data"]["meta"]["name"]
        steps = scenario["data"]["steps"]
        
        logger.info(f"🎬 Starting scenario: {scenario_name}")
        
        scenario_results = {
            "name": scenario_name,
            "total_steps": len(steps),
            "passed_steps": 0,
            "failed_steps": 0,
            "steps": []
        }
        
        for step_idx, step in enumerate(steps):
            logger.info(f"📋 Executing step {step_idx + 1}/{len(steps)}: {step['type']}")
            
            step_result = await self.execute_step(scenario_name, step_idx, step)
            scenario_results["steps"].append(step_result)
            
            if step_result["success"]:
                scenario_results["passed_steps"] += 1
            else:
                scenario_results["failed_steps"] += 1
        
        logger.info(f"✅ Scenario completed: {scenario_name} ({scenario_results['passed_steps']}/{scenario_results['total_steps']} passed)")
        
        return scenario_results
    
    async def run_all_scenarios(self, scenarios: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Wykonuje wszystkie scenariusze."""
        results = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            
            task = progress.add_task("Running scenarios...", total=len(scenarios))
            
            for scenario in scenarios:
                progress.update(task, description=f"Running: {scenario['data']['meta']['name']}")
                
                result = await self.run_scenario(scenario)
                results.append(result)
                
                progress.advance(task)
        
        return results
    
    async def generate_and_open_report(self, results: List[Dict[str, Any]]) -> None:
        """Generuje raport i otwiera w przeglądarce."""
        logger.info("📊 Generating test report...")
        
        # Pobierz podsumowanie logów
        summary = self.test_logger.get_execution_summary()
        
        # Generuj raport
        report_path = await self.report_generator.generate_report(results, summary)
        
        # Otwórz w przeglądarce
        report_url = f"file://{Path(report_path).absolute()}"
        webbrowser.open(report_url)
        
        logger.info(f"📖 Report generated and opened: {report_path}")
    
    async def run(self, scenario_paths: List[str]) -> None:
        """Główna funkcja uruchamiania testów."""
        try:
            # Inicjalizacja
            self.load_config()
            self.check_dependencies()
            await self.initialize_components()
            await self.check_services_health()
            
            # Uwierzytelnienie
            await self.authenticate_api()
            
            # Załaduj scenariusze
            scenarios = self.load_scenarios(scenario_paths)
            
            # Wykonaj testy
            results = await self.run_all_scenarios(scenarios)
            
            # Generuj raport
            await self.generate_and_open_report(results)
            
            # Podsumowanie
            total_scenarios = len(results)
            passed_scenarios = sum(1 for r in results if r["passed_steps"] == r["total_steps"])
            
            logger.info(f"🎉 Testing completed: {passed_scenarios}/{total_scenarios} scenarios passed")
            
        except Exception as e:
            logger.error(f"Test run failed: {e}")
            raise
        finally:
            # Cleanup
            if self.api_client:
                await self.api_client.__aexit__(None, None, None)


def main():
    """Punkt wejścia aplikacji."""
    parser = argparse.ArgumentParser(description="GAJA End-to-End Test Runner")
    parser.add_argument(
        "--scenario",
        type=str,
        help="Path to specific scenario file"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all scenarios in scenarios/ directory"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.yaml",
        help="Path to config file"
    )
    
    args = parser.parse_args()
    
    # Determine scenario paths
    scenario_paths = []
    
    if args.all:
        scenarios_dir = Path("scenarios")
        if scenarios_dir.exists():
            scenario_paths = list(scenarios_dir.glob("*.yaml"))
        else:
            logger.error("scenarios/ directory not found")
            sys.exit(1)
    elif args.scenario:
        scenario_paths = [args.scenario]
    else:
        parser.print_help()
        sys.exit(1)
    
    if not scenario_paths:
        logger.error("No scenarios found to run")
        sys.exit(1)
    
    # Configure logging
    logger.remove()
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    # Run tests
    runner = TestRunner(config_path=args.config)
    
    try:
        asyncio.run(runner.run([str(p) for p in scenario_paths]))
    except KeyboardInterrupt:
        logger.info("Test run interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Test run failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
