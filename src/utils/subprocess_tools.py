"""Subprocess utilities for running external commands."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass


@dataclass
class CommandResult:
    """Result from running a subprocess command."""

    returncode: int
    stdout: str
    stderr: str


def run_command(
    cmd: list[str],
    *,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
    timeout_s: int = 900,
) -> CommandResult:
    """Run a command with optional timeout and environment variables.

    Args:
        cmd: Command and arguments as a list
        cwd: Working directory for the command
        env: Environment variables to merge with current environment
        timeout_s: Timeout in seconds (default: 900)

    Returns:
        CommandResult with returncode, stdout, and stderr

    Raises:
        subprocess.TimeoutExpired: If command exceeds timeout
        subprocess.SubprocessError: If command fails to execute
    """
    # Merge environment variables with current environment
    full_env = os.environ.copy()
    if env:
        full_env.update(env)

    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            env=full_env,
            timeout=timeout_s,
            capture_output=True,
            text=True,
            check=False,
        )

        return CommandResult(
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )

    except subprocess.TimeoutExpired as e:
        raise subprocess.TimeoutExpired(
            cmd=e.cmd,
            timeout=e.timeout,
            output=e.stdout.decode() if e.stdout else None,
            stderr=e.stderr.decode() if e.stderr else None,
        ) from e
