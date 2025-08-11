"""Schemat walidacyjny dla scenariuszy testowych GAJA."""

from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field


class AssertionSchema(BaseModel):
    """Pojedyncza asercja w kroku testowym."""
    kind: Literal["contains", "jsonpath_eq", "semantic_ok", "effect_ok"]
    target: Literal["assistant_text", "assistant_audio_path", "plugin_result", "side_effect"] = "assistant_text"
    value: Optional[str] = None


class ExpectationSchema(BaseModel):
    """Oczekiwanie dla kroku testowego."""
    action: str
    assertions: List[AssertionSchema] = Field(default_factory=list)


class StepSchema(BaseModel):
    """Pojedynczy krok scenariusza testowego."""
    type: Literal["text", "audio", "action"]
    
    # Pola dla typu "text"
    message: Optional[str] = None
    
    # Pola dla typu "audio"
    tts_text: Optional[str] = None
    
    # Pola dla typu "action"
    action: Optional[str] = None
    
    # Wspólne pola
    expect: ExpectationSchema


class MetaSchema(BaseModel):
    """Metadane scenariusza."""
    name: str
    tags: List[str] = Field(default_factory=list)


class ScenarioSchema(BaseModel):
    """Kompletny scenariusz testowy."""
    meta: MetaSchema
    steps: List[StepSchema]


class ConfigSchema(BaseModel):
    """Konfiguracja systemu testowego."""
    gaja: Dict[str, Union[str, int]]
    voice: Dict[str, Union[str, int]]
    grader: Dict[str, Union[str, int, float]]
    report: Dict[str, Union[str, float]]
    runtime: Dict[str, Union[str, int, float, bool]]


class TestResult(BaseModel):
    """Wynik pojedynczego testu."""
    scenario_name: str
    step_index: int
    step_type: str
    success: bool
    grade: Optional[float] = None
    error_message: Optional[str] = None
    execution_time: float
    timestamp: str


class StepExecutionLog(BaseModel):
    """Log wykonania kroku."""
    ts: str
    scenario: str
    step_idx: int
    type: str
    input: Dict[str, Any]
    assistant: Dict[str, Any]
    plugin: Optional[Dict[str, Any]] = None
    assertions: List[Dict[str, Any]]


def validate_scenario(scenario_data: Dict[str, Any]) -> ScenarioSchema:
    """Waliduje scenariusz względem schematu."""
    return ScenarioSchema.model_validate(scenario_data)


def validate_config(config_data: Dict[str, Any]) -> ConfigSchema:
    """Waliduje konfigurację względem schematu."""
    return ConfigSchema.model_validate(config_data)
