"""Moduł I/O dla logowania i zapisywania artefaktów."""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


class TestLogger:
    """Logger dla systemu testowego."""
    
    def __init__(self, logs_dir: str = "results/logs"):
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Plik główny z logami
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.main_log_file = self.logs_dir / f"test_run_{timestamp}.jsonl"
        self.execution_start = time.time()
    
    def log_step_execution(
        self,
        scenario: str,
        step_idx: int,
        step_type: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        plugin_data: Optional[Dict[str, Any]] = None,
        assertions: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """Loguje wykonanie kroku."""
        
        log_entry = {
            "ts": datetime.now().isoformat(),
            "scenario": scenario,
            "step_idx": step_idx,
            "type": step_type,
            "input": input_data,
            "assistant": output_data,
            "plugin": plugin_data,
            "assertions": assertions or []
        }
        
        # Zapisz do pliku JSONL
        with open(self.main_log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        
        # Log do console
        status = "✅" if all(a.get("passed", False) for a in (assertions or [])) else "❌"
        logger.info(f"{status} {scenario}[{step_idx}] {step_type}: {input_data.get('text', input_data.get('message', ''))[:50]}...")
    
    def log_grade_result(
        self,
        scenario: str,
        step_idx: int,
        grade: float,
        comments: str,
        grader_input: Dict[str, Any]
    ) -> None:
        """Loguje wynik oceny z grader."""
        
        grade_entry = {
            "ts": datetime.now().isoformat(),
            "scenario": scenario,
            "step_idx": step_idx,
            "grade": grade,
            "comments": comments,
            "grader_input": grader_input
        }
        
        # Zapisz do osobnego pliku
        grade_file = self.logs_dir / f"grades_{scenario}_{step_idx}.json"
        with open(grade_file, "w", encoding="utf-8") as f:
            json.dump(grade_entry, f, ensure_ascii=False, indent=2)
        
        logger.info(f"📊 Grade {grade:.1f}/10 for {scenario}[{step_idx}]: {comments}")
    
    def log_error(
        self,
        scenario: str,
        step_idx: int,
        error_type: str,
        error_message: str,
        stack_trace: Optional[str] = None
    ) -> None:
        """Loguje błąd wykonania."""
        
        error_entry = {
            "ts": datetime.now().isoformat(),
            "scenario": scenario,
            "step_idx": step_idx,
            "error_type": error_type,
            "error_message": error_message,
            "stack_trace": stack_trace
        }
        
        with open(self.main_log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(error_entry, ensure_ascii=False) + "\n")
        
        logger.error(f"💥 {scenario}[{step_idx}] {error_type}: {error_message}")
    
    def save_artifact(self, content: bytes, filename: str, artifact_type: str = "audio") -> str:
        """Zapisuje artefakt (audio, obraz, etc.) do folderu."""
        
        artifacts_dir = self.logs_dir.parent / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        
        # Dodaj timestamp do nazwy pliku
        timestamp = int(time.time())
        name_parts = filename.split(".")
        if len(name_parts) > 1:
            name = ".".join(name_parts[:-1])
            ext = name_parts[-1]
            full_filename = f"{name}_{timestamp}.{ext}"
        else:
            full_filename = f"{filename}_{timestamp}"
        
        artifact_path = artifacts_dir / full_filename
        
        with open(artifact_path, "wb") as f:
            f.write(content)
        
        logger.debug(f"💾 Artifact saved: {artifact_path}")
        return str(artifact_path)
    
    def save_text_artifact(self, content: str, filename: str) -> str:
        """Zapisuje artefakt tekstowy."""
        return self.save_artifact(content.encode("utf-8"), filename, "text")
    
    def load_test_logs(self) -> List[Dict[str, Any]]:
        """Ładuje logi z bieżącego uruchomienia."""
        
        if not self.main_log_file.exists():
            return []
        
        logs = []
        with open(self.main_log_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    logs.append(json.loads(line.strip()))
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse log line: {e}")
        
        return logs
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Zwraca podsumowanie wykonania testów."""
        
        logs = self.load_test_logs()
        execution_time = time.time() - self.execution_start
        
        scenarios = set()
        total_steps = 0
        passed_steps = 0
        failed_steps = 0
        errors = 0
        
        for log in logs:
            if "scenario" in log:
                scenarios.add(log["scenario"])
                
            if "step_idx" in log:
                total_steps += 1
                
                # Sprawdź assertions
                assertions = log.get("assertions", [])
                if assertions:
                    if all(a.get("passed", False) for a in assertions):
                        passed_steps += 1
                    else:
                        failed_steps += 1
                
            if "error_type" in log:
                errors += 1
        
        return {
            "execution_time": execution_time,
            "scenarios_count": len(scenarios),
            "total_steps": total_steps,
            "passed_steps": passed_steps,
            "failed_steps": failed_steps,
            "errors": errors,
            "success_rate": passed_steps / max(total_steps, 1) * 100
        }
