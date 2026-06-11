import importlib.util
import json
import os
import urllib.error
import urllib.request
from typing import Any

import click

from .contracts import validate_provider_doctor_v2

PROVIDER_NAMES = ["codex", "claude", "gemini", "kimi", "glm", "mimo"]


@click.group("providers")
def providers_cmd() -> None:
    pass


@providers_cmd.command("doctor")
@click.argument("provider", required=False)
@click.option("--endpoint", default=None, help="Override provider endpoint for smoke checks.")
@click.option("--api-key-env", default=None, help="Override provider API key env var.")
@click.option("--live/--no-live", default=False, help="Run a live endpoint smoke request.")
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
@click.pass_context
def provider_doctor_cmd(
    ctx,
    provider: str | None,
    endpoint: str | None,
    api_key_env: str | None,
    live: bool,
    as_json: bool,
) -> None:
    config = ctx.obj["config"]
    payload = build_provider_doctor(
        config,
        provider=provider,
        endpoint=endpoint,
        api_key_env=api_key_env,
        live=live,
    )

    if as_json:
        click.echo(json.dumps(payload, indent=2))
    else:
        for name, provider_status in payload["providers"].items():
            click.echo(f"{name}: {provider_status['status']} ({provider_status['env_var']})")

    if provider is not None and _single_provider_has_blocker(payload):
        ctx.exit(2)


def build_provider_doctor(
    config: dict[str, Any],
    *,
    provider: str | None = None,
    endpoint: str | None = None,
    api_key_env: str | None = None,
    live: bool = False,
) -> dict[str, Any]:
    backends = config.get("agents", {}).get("backends", {})
    provider_names = [provider] if provider else PROVIDER_NAMES
    providers: dict[str, Any] = {}

    for name in provider_names:
        if name not in PROVIDER_NAMES:
            raise click.ClickException(f"Unknown provider: {name}")
        backend = backends.get(name, {})
        env_var = api_key_env or backend.get("api_key_env", _default_env_var(name))
        sdk_name = _sdk_name(name)
        sdk_available = _is_sdk_available(sdk_name)
        enabled = bool(backend.get("enabled", True))
        has_key = bool(os.environ.get(env_var, ""))
        provider_endpoint = endpoint or backend.get("endpoint", _default_endpoint(name))
        model = backend.get("model", _default_model(name))
        live_status = _live_status(
            enabled=enabled,
            has_key=has_key,
            live=live,
            endpoint=provider_endpoint,
            env_var=env_var,
        )
        problems = _provider_problems(
            has_key=has_key,
            sdk_available=sdk_available,
            live_status=live_status,
        )
        status = _provider_status(
            enabled=enabled,
            has_key=has_key,
            sdk_available=sdk_available,
            live_status=live_status,
        )
        providers[name] = {
            "enabled": enabled,
            "env_var": env_var,
            "has_key": has_key,
            "sdk": sdk_name or "stdlib",
            "sdk_available": sdk_available,
            "endpoint": provider_endpoint,
            "model": model,
            "live_checked": live,
            "live_status": live_status,
            "problems": problems,
            "status": status,
            "usage": f'kunity-yamae run --agent {name} "$TASK"',
        }

    payload = {
        "schema": "unity-harness.provider-doctor.v2",
        "providers": providers,
        "offline_handoffs": _offline_handoffs(),
    }
    return validate_provider_doctor_v2(payload)


def _default_env_var(name: str) -> str:
    defaults = {
        "codex": "OPENAI_API_KEY",
        "claude": "ANTHROPIC_API_KEY",
        "gemini": "GOOGLE_API_KEY",
        "kimi": "KIMI_API_KEY",
        "glm": "ZHIPU_API_KEY",
        "mimo": "MIMO_API_KEY",
    }
    return defaults[name]


def _sdk_name(name: str) -> str | None:
    sdks = {
        "codex": "openai",
        "claude": "anthropic",
        "gemini": "google.genai",
        "kimi": None,
        "glm": None,
        "mimo": None,
    }
    return sdks[name]


def _default_endpoint(name: str) -> str:
    endpoints = {
        "codex": "https://api.openai.com/v1/responses",
        "claude": "https://api.anthropic.com/v1/messages",
        "gemini": "https://generativelanguage.googleapis.com/v1beta/models",
        "kimi": "https://api.moonshot.cn/v1/chat/completions",
        "glm": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        "mimo": "https://api.mimo.ai/v1/chat/completions",
    }
    return endpoints[name]


def _default_model(name: str) -> str:
    models = {
        "codex": "gpt-4o",
        "claude": "claude-sonnet-4-20250514",
        "gemini": "gemini-2.5-flash",
        "kimi": "moonshot-v1-128k",
        "glm": "glm-4-plus",
        "mimo": "mimo-auto",
    }
    return models[name]


def _is_sdk_available(sdk_name: str | None) -> bool:
    if not sdk_name:
        return True
    try:
        return importlib.util.find_spec(sdk_name) is not None
    except ModuleNotFoundError:
        return False


def _live_status(
    *,
    enabled: bool,
    has_key: bool,
    live: bool,
    endpoint: str,
    env_var: str,
) -> str:
    if not live:
        return "not_requested"
    if not enabled or not has_key:
        return "skipped"

    request = urllib.request.Request(
        endpoint,
        data=b"{}",
        headers={
            "Authorization": f"Bearer {os.environ[env_var]}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            if 200 <= response.status < 300:
                return "ok"
            return "failed"
    except (urllib.error.URLError, TimeoutError):
        return "failed"


def _provider_problems(
    *,
    has_key: bool,
    sdk_available: bool,
    live_status: str,
) -> list[str]:
    problems = []
    if not has_key:
        problems.append("missing_credentials")
    if not sdk_available:
        problems.append("missing_sdk")
    if live_status == "failed":
        problems.append("live_check_failed")
    return problems


def _provider_status(
    *,
    enabled: bool,
    has_key: bool,
    sdk_available: bool,
    live_status: str,
) -> str:
    if not enabled:
        return "disabled"
    if not has_key:
        return "missing_credentials"
    if not sdk_available:
        return "missing_sdk"
    if live_status == "failed":
        return "live_check_failed"
    return "ready"


def _single_provider_has_blocker(payload: dict[str, Any]) -> bool:
    provider = next(iter(payload["providers"].values()))
    return provider["status"] not in {"ready", "disabled"}


def _offline_handoffs() -> dict[str, Any]:
    return {
        "local-patch": {
            "status": "ready",
            "requires_api_key": False,
            "usage": (
                'kunity-yamae run --agent local-patch "$TASK" '
                "--guarded-agent-patch --json"
            ),
        }
    }
