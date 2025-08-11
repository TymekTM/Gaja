"""Generator raportu HTML dla systemu testowego GAJA."""

import json
import base64
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from io import BytesIO

import matplotlib.pyplot as plt
from jinja2 import Environment, FileSystemLoader
from loguru import logger


class ReportGenerator:
    """Generator raportu HTML."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.template_dir = Path("templates")
        self.output_path = config.get("report", {}).get("output_path", "results/report.html")
        
        # Jinja2 environment
        self.jinja_env = Environment(loader=FileSystemLoader(str(self.template_dir)))
    
    def _create_charts(self, results: List[Dict[str, Any]]) -> str:
        """Tworzy wykresy i zwraca jako base64."""
        
        # Przygotuj dane
        scenario_names = [r["name"] for r in results]
        passed_steps = [r["passed_steps"] for r in results]
        failed_steps = [r["failed_steps"] for r in results]
        
        # Utwórz wykres
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Wykres 1: Słupkowy - passed vs failed
        x_pos = range(len(scenario_names))
        
        ax1.bar([x - 0.2 for x in x_pos], passed_steps, 0.4, label='Passed', color='#28a745')
        ax1.bar([x + 0.2 for x in x_pos], failed_steps, 0.4, label='Failed', color='#dc3545')
        
        ax1.set_xlabel('Scenarios')
        ax1.set_ylabel('Steps Count')
        ax1.set_title('Test Results by Scenario')
        ax1.set_xticks(x_pos)
        ax1.set_xticklabels([name[:15] + '...' if len(name) > 15 else name for name in scenario_names], rotation=45)
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Wykres 2: Kołowy - ogólne statystyki
        total_passed = sum(passed_steps)
        total_failed = sum(failed_steps)
        
        if total_passed + total_failed > 0:
            ax2.pie([total_passed, total_failed], 
                   labels=['Passed', 'Failed'],
                   colors=['#28a745', '#dc3545'],
                   autopct='%1.1f%%',
                   startangle=90)
            ax2.set_title('Overall Test Results')
        
        plt.tight_layout()
        
        # Konwertuj do base64
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        chart_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close()
        
        return chart_base64
    
    def _calculate_statistics(self, results: List[Dict[str, Any]], summary: Dict[str, Any]) -> Dict[str, Any]:
        """Oblicza statystyki testów."""
        
        total_scenarios = len(results)
        passed_scenarios = sum(1 for r in results if r["failed_steps"] == 0)
        failed_scenarios = total_scenarios - passed_scenarios
        
        total_steps = sum(r["total_steps"] for r in results)
        total_passed_steps = sum(r["passed_steps"] for r in results)
        total_failed_steps = sum(r["failed_steps"] for r in results)
        
        success_rate = (total_passed_steps / max(total_steps, 1)) * 100
        
        # Znajdź najlepszy i najgorszy scenariusz
        best_scenario = None
        worst_scenario = None
        
        if results:
            best_scenario = max(results, key=lambda x: x["passed_steps"] / max(x["total_steps"], 1))
            worst_scenario = min(results, key=lambda x: x["passed_steps"] / max(x["total_steps"], 1))
        
        return {
            "total_scenarios": total_scenarios,
            "passed_scenarios": passed_scenarios,
            "failed_scenarios": failed_scenarios,
            "total_steps": total_steps,
            "total_passed_steps": total_passed_steps,
            "total_failed_steps": total_failed_steps,
            "success_rate": success_rate,
            "execution_time": summary.get("execution_time", 0),
            "best_scenario": best_scenario,
            "worst_scenario": worst_scenario
        }
    
    def _get_failed_tests(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Pobiera listę nieudanych testów z detalami."""
        failed_tests = []
        
        for result in results:
            for step_idx, step in enumerate(result["steps"]):
                if not step["success"]:
                    failed_test = {
                        "scenario": result["name"],
                        "step_index": step_idx,
                        "step_type": step.get("input", {}).get("type", "unknown"),
                        "input_text": step.get("input", {}).get("text", "")[:100],
                        "error": step.get("error", "Unknown error"),
                        "assertions": step.get("assertions", [])
                    }
                    failed_tests.append(failed_test)
        
        return failed_tests
    
    def _format_timestamp(self, timestamp: float) -> str:
        """Formatuje timestamp."""
        if timestamp:
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        return "Unknown"
    
    def _format_duration(self, seconds: float) -> str:
        """Formatuje czas trwania."""
        if seconds < 60:
            return f"{seconds:.1f} seconds"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f} minutes"
        else:
            hours = seconds / 3600
            return f"{hours:.1f} hours"
    
    async def generate_report(self, results: List[Dict[str, Any]], summary: Dict[str, Any]) -> str:
        """Generuje raport HTML."""
        
        try:
            logger.info("📊 Generating test report...")
            
            # Oblicz statystyki
            stats = self._calculate_statistics(results, summary)
            
            # Utwórz wykresy
            chart_base64 = self._create_charts(results)
            
            # Pobierz nieudane testy
            failed_tests = self._get_failed_tests(results)
            
            # Threshold dla oceny
            fail_threshold = self.config.get("report", {}).get("fail_threshold", 8.0)
            
            # Przygotuj dane dla template
            report_data = {
                "timestamp": self._format_timestamp(datetime.now().timestamp()),
                "stats": stats,
                "results": results,
                "failed_tests": failed_tests,
                "chart_base64": chart_base64,
                "fail_threshold": fail_threshold,
                "config": self.config,
                "format_duration": self._format_duration,
                "format_timestamp": self._format_timestamp
            }
            
            # Renderuj template
            template = self.jinja_env.get_template("report.html.j2")
            html_content = template.render(**report_data)
            
            # Zapisz raport
            output_path = Path(self.output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"✅ Report generated: {output_path}")
            
            return str(output_path.absolute())
            
        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            raise
