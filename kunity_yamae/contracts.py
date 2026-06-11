from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ContractError(Exception):
    field: str

    def __str__(self) -> str:
        return f"Missing or invalid contract field: {self.field}"


def validate_provider_doctor_v2(payload: dict[str, Any]) -> dict[str, Any]:
    _require(payload.get("schema") == "unity-harness.provider-doctor.v2", "schema")
    providers = _require_dict(payload, "providers")
    for name, provider_value in providers.items():
        provider = _require_mapping(provider_value, f"providers.{name}")
        for field in (
            "enabled",
            "env_var",
            "has_key",
            "sdk",
            "sdk_available",
            "problems",
            "status",
        ):
            _require(field in provider, f"providers.{name}.{field}")
    return payload


def validate_run_result_v1(payload: dict[str, Any]) -> dict[str, Any]:
    _require(payload.get("schema") == "unity-harness.run-result.v1", "schema")
    _require(payload.get("status") in {"planned", "completed", "failed"}, "status")
    _require(isinstance(payload.get("plan_only"), bool), "plan_only")
    _require(isinstance(payload.get("provider_requests"), int), "provider_requests")
    _require(isinstance(payload.get("stages"), list), "stages")
    return payload


def _require_dict(payload: dict[str, Any], field: str) -> dict[str, Any]:
    value = payload.get(field)
    return _require_mapping(value, field)


def _require_mapping(value: Any, field: str) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    raise ContractError(field)


def _require(condition: bool, field: str) -> None:
    if not condition:
        raise ContractError(field)
