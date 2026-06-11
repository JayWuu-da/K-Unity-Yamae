import pytest


def test_provider_doctor_v2_contract_rejects_missing_status() -> None:
    from kunity_yamae.contracts import ContractError, validate_provider_doctor_v2

    with pytest.raises(ContractError, match="providers.codex.status"):
        validate_provider_doctor_v2(
            {
                "schema": "unity-harness.provider-doctor.v2",
                "providers": {
                    "codex": {
                        "enabled": True,
                        "env_var": "OPENAI_API_KEY",
                        "has_key": False,
                        "sdk": "openai",
                        "sdk_available": True,
                        "problems": ["missing_key"],
                    }
                },
            }
        )


def test_run_result_v1_contract_accepts_plan_only_result() -> None:
    from kunity_yamae.contracts import validate_run_result_v1

    payload = {
        "schema": "unity-harness.run-result.v1",
        "status": "planned",
        "plan_only": True,
        "provider_requests": 0,
        "stages": [
            {"stage": "scan", "status": "ok"},
            {"stage": "risk", "status": "ok"},
        ],
    }

    assert validate_run_result_v1(payload)["status"] == "planned"
