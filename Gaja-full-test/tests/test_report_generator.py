#!/usr/bin/env python3
"""
Testy jednostkowe dla report_generator
"""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.report_generator import ReportGenerator


class TestReportGenerator:
    """Testy dla klasy ReportGenerator"""
    
    def setup_method(self):
        """Setup przed każdym testem"""
        config = {
            "report": {
                "output_path": "test_report.html"
            }
        }
        self.generator = ReportGenerator(config)
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Cleanup po każdym teście"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_init_default_values(self):
        """Test domyślnych wartości przy inicjalizacji"""
        
        config = {}
        generator = ReportGenerator(config)
        
        assert generator.template_dir == Path("templates")
        assert generator.output_path == "results/report.html"
    
    def test_init_custom_values(self):
        """Test niestandardowych wartości przy inicjalizacji"""
        
        config = {
            "report": {
                "output_path": "custom/report.html"
            }
        }
        
        generator = ReportGenerator(config)
        assert generator.output_path == "custom/report.html"
    
    @patch('matplotlib.pyplot.subplots')
    @patch('matplotlib.pyplot.savefig')
    def test_create_charts(self, mock_savefig, mock_subplots):
        """Test tworzenia wykresów"""
        
        # Mock matplotlib
        mock_fig = MagicMock()
        mock_ax1 = MagicMock()
        mock_ax2 = MagicMock()
        mock_subplots.return_value = (mock_fig, (mock_ax1, mock_ax2))
        
        # Test data
        results = [
            {
                "name": "Test 1",
                "passed_steps": 3,
                "failed_steps": 0
            },
            {
                "name": "Test 2", 
                "passed_steps": 2,
                "failed_steps": 1
            }
        ]
        
        # Test
        chart_data = self.generator._create_charts(results)
        
        # Asserts
        assert isinstance(chart_data, str)
        mock_subplots.assert_called_once()
        mock_ax1.bar.assert_called()
        mock_ax2.pie.assert_called()
    
    @pytest.mark.asyncio
    @patch('src.report_generator.ReportGenerator._create_charts')
    @patch('jinja2.Environment.get_template')
    async def test_generate_report(self, mock_get_template, mock_create_charts):
        """Test generowania raportu"""
        
        # Mock Jinja2 template
        mock_template = MagicMock()
        mock_template.render.return_value = "<html>Test Report</html>"
        mock_get_template.return_value = mock_template
        
        # Mock charts
        mock_create_charts.return_value = "base64_chart_data"
        
        # Test data
        results = [
            {
                "name": "Test Scenario",
                "success": True,
                "passed_steps": 2,
                "failed_steps": 0,
                "total_steps": 2,
                "duration": 10.0,
                "start_time": "2025-01-09T10:00:00",
                "end_time": "2025-01-09T10:00:10",
                "steps": [
                    {"action": "send_text", "success": True},
                    {"action": "wait", "success": True}
                ]
            }
        ]
        
        summary = {
            "total_scenarios": 1,
            "passed_scenarios": 1,
            "failed_scenarios": 0
        }
        
        # Override output path to temp directory
        test_output = os.path.join(self.temp_dir, "test_report.html")
        self.generator.output_path = test_output
        
        # Test
        result_path = await self.generator.generate_report(results, summary)
        
        # Asserts
        assert result_path == test_output
        mock_create_charts.assert_called_once_with(results)
        mock_template.render.assert_called_once()
        
        # Check file was created
        assert os.path.exists(test_output)
    
    @pytest.mark.asyncio
    async def test_empty_results(self):
        """Test obsługi pustych wyników"""
        
        # Override output path to temp directory  
        test_output = os.path.join(self.temp_dir, "empty_report.html")
        self.generator.output_path = test_output
        
        summary = {
            "total_scenarios": 0,
            "passed_scenarios": 0,
            "failed_scenarios": 0
        }
        
        # Mock to avoid matplotlib errors with empty data
        with patch('src.report_generator.ReportGenerator._create_charts') as mock_charts:
            with patch('jinja2.Environment.get_template') as mock_get_template:
                # Mock template
                mock_template = MagicMock()
                mock_template.render.return_value = "<html>Empty Report</html>"
                mock_get_template.return_value = mock_template
                
                mock_charts.return_value = ""
                
                # Test
                result_path = await self.generator.generate_report([], summary)
                
                # Asserts
                assert result_path == test_output
