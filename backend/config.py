"""Load SONIQ configuration from YAML without embedding credentials."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field


class NodeConfig(BaseModel):
    transport: Literal["docker", "ssh", "gnmi", "mock"] = "docker"
    container: str | None = None
    host: str | None = None
    port: int | None = None
    username: str | None = None
    management_ip: str | None = None


class SonicConfig(BaseModel):
    nodes: dict[str, NodeConfig] = Field(default_factory=dict)
    commands: dict[str, str] = Field(default_factory=dict)


class AgentConfig(BaseModel):
    max_steps: int = 10
    require_approval: bool = True
    llm_enabled: bool = False
    planner: Literal["deterministic", "llm"] = "deterministic"


class ToolsConfig(BaseModel):
    allow_write: bool = False
    mode: Literal["mock", "live"] = "mock"
    timeout_seconds: float = 15.0


class MockConfig(BaseModel):
    scenario: str = "high_latency_leaf1_leaf2"


class LlmConfig(BaseModel):
    provider: str = "none"
    model: str = "none"
    api_key_env: str = "SONIQ_LLM_API_KEY"


class LoggingConfig(BaseModel):
    level: str = "INFO"
    json_logs: bool = True


class StorageConfig(BaseModel):
    kind: Literal["memory", "json"] = "memory"
    json_path: str = "data/investigations"


class AppConfig(BaseModel):
    sonic: SonicConfig = Field(default_factory=SonicConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    tools: ToolsConfig = Field(default_factory=ToolsConfig)
    mock: MockConfig = Field(default_factory=MockConfig)
    llm: LlmConfig = Field(default_factory=LlmConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)


def default_config_path() -> Path:
    return Path(__file__).resolve().parents[1] / "config" / "config.yaml"


def load_config(path: Path | None = None) -> AppConfig:
    config_path = path or default_config_path()
    if not config_path.exists():
        return AppConfig()
    raw: dict[str, Any] = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    return AppConfig.model_validate(raw)
