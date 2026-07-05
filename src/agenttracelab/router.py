"""Run the same job through several terminal agents and rank the results."""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TerminalAgent:
    name: str
    model: str | None
    command: list[str]
    provider: str | None = None
    cwd: str | None = None
    timeout_sec: int = 900
    env: dict[str, str] | None = None


def example_config() -> dict[str, Any]:
    """Return a starter config users edit for their installed terminal agents."""

    return {
        "agents": [
            {
                "name": "Claude Code",
                "provider": "anthropic",
                "model": "claude-sonnet-5",
                "command": ["claude", "-p", "{prompt}"],
            },
            {
                "name": "Codex",
                "provider": "openai",
                "model": "gpt-5.4",
                "command": ["codex", "exec", "{prompt}"],
            },
            {
                "name": "Gemini CLI",
                "provider": "google",
                "model": "gemini-3.1-pro",
                "command": ["gemini", "-p", "{prompt}"],
            },
            {
                "name": "Cursor Agent",
                "provider": "cursor",
                "model": "cursor-agent",
                "command": ["cursor-agent", "--print", "{prompt}"],
            },
        ]
    }


def write_example_config(path: str | Path) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(example_config(), indent=2) + "\n", encoding="utf-8")
    return out


def load_agents(path: str | Path) -> list[TerminalAgent]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    agents = []
    for item in data.get("agents", []):
        command = item.get("command")
        if not isinstance(command, list) or not all(isinstance(part, str) for part in command):
            raise ValueError(f"Agent {item.get('name', '<unnamed>')} needs command as a list of strings.")
        agents.append(
            TerminalAgent(
                name=str(item["name"]),
                provider=item.get("provider"),
                model=item.get("model"),
                command=command,
                cwd=item.get("cwd"),
                timeout_sec=int(item.get("timeout_sec", 900)),
                env=item.get("env"),
            )
        )
    if not agents:
        raise ValueError(f"No agents found in {path}. Expected an 'agents' array.")
    return agents


def _format_command(command: list[str], prompt: str, job_path: str | None) -> list[str]:
    return [
        part.replace("{prompt}", prompt).replace("{job_path}", job_path or "")
        for part in command
    ]


def _score_from_regex(output: str, score_regex: str | None) -> float:
    if not score_regex:
        return 1.0
    match = re.search(score_regex, output, flags=re.MULTILINE)
    if not match:
        return 0.0
    if match.groups():
        try:
            return max(0.0, min(1.0, float(match.group(1))))
        except ValueError:
            return 1.0
    return 1.0


def _run_success_command(command: list[str] | None, cwd: str | Path | None) -> tuple[bool, str]:
    if not command:
        return False, "No success command configured."
    proc = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=300)
    output = (proc.stdout + "\n" + proc.stderr).strip()
    return proc.returncode == 0, output


def run_terminal_agent(
    agent: TerminalAgent,
    prompt: str,
    *,
    task_id: str,
    out_dir: str | Path,
    job_path: str | None = None,
    success_regex: str | None = None,
    score_regex: str | None = None,
    success_command: list[str] | None = None,
) -> Path:
    """Run one configured terminal agent and write a native-format log."""

    command = _format_command(agent.command, prompt, job_path)
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            command,
            cwd=agent.cwd,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=agent.timeout_sec,
            env={**os.environ, **(agent.env or {})},
        )
        latency_ms = round((time.perf_counter() - t0) * 1000, 1)
        stdout = proc.stdout.strip()
        stderr = proc.stderr.strip()
        output = stdout if not stderr else stdout + "\n\n[stderr]\n" + stderr
        command_ok = proc.returncode == 0
    except subprocess.TimeoutExpired as exc:
        latency_ms = round((time.perf_counter() - t0) * 1000, 1)
        output = f"Timed out after {agent.timeout_sec}s.\n{exc.stdout or ''}\n{exc.stderr or ''}".strip()
        command_ok = False

    checks: list[dict[str, Any]] = [
        {
            "name": "run_agent_command",
            "arguments": {"command": command},
            "ok": command_ok,
        }
    ]

    if success_command:
        passed, check_output = _run_success_command(success_command, agent.cwd)
        checks.append(
            {
                "name": "run_success_command",
                "arguments": {"command": success_command},
                "ok": passed,
                "result": check_output[-2000:],
            }
        )
        final_correct = passed
        final_score = 1.0 if passed else 0.0
    elif success_regex:
        final_correct = re.search(success_regex, output, flags=re.MULTILINE) is not None
        final_score = 1.0 if final_correct else 0.0
    else:
        final_correct = command_ok
        final_score = _score_from_regex(output, score_regex) if command_ok else 0.0

    success_turn = 1 if final_correct else None
    log = {
        "agent": agent.name,
        "model": agent.model,
        "provider": agent.provider,
        "task_id": task_id,
        "success_turn": success_turn,
        "final_correct": final_correct,
        "final_score": final_score,
        "turns": [
            {"role": "user", "content": prompt},
            {
                "role": "assistant",
                "content": output,
                "latency_ms": latency_ms,
                "tool_calls": checks,
            },
        ],
    }

    safe_name = re.sub(r"[^a-zA-Z0-9_.-]+", "_", agent.name).strip("_") or "agent"
    out_path = Path(out_dir) / f"{safe_name}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(log, indent=2), encoding="utf-8")
    return out_path
