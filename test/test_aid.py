"""Tests for aid (AI Develop) command functionality."""

import pytest
from rockerc.aid import parse_aid_args, build_ai_command


def test_parse_aid_args_default_gemini():
    """Test that gemini is the default agent."""
    args = parse_aid_args(["owner/repo", "test", "prompt"])
    assert args.agent == "gemini"
    assert args.repo_spec == "owner/repo"
    assert args.prompt == ["test", "prompt"]


def test_parse_aid_args_claude():
    """Test claude agent selection."""
    args = parse_aid_args(["--claude", "owner/repo", "test", "prompt"])
    assert args.agent == "claude"
    assert args.repo_spec == "owner/repo"
    assert args.prompt == ["test", "prompt"]


def test_parse_aid_args_codex():
    """Test codex agent selection."""
    args = parse_aid_args(["--codex", "owner/repo@branch", "complex", "multi", "word", "prompt"])
    assert args.agent == "codex"
    assert args.repo_spec == "owner/repo@branch"
    assert args.prompt == ["complex", "multi", "word", "prompt"]


def test_build_ai_command_gemini():
    """Test gemini command construction."""
    command = build_ai_command("gemini", "test prompt")
    assert command == ["gemini", "--prompt-interactive", "test prompt"]


def test_build_ai_command_claude():
    """Test claude command construction."""
    command = build_ai_command("claude", "test prompt")
    assert command == ["claude", "test prompt"]


def test_build_ai_command_codex():
    """Test codex command construction."""
    command = build_ai_command("codex", "test prompt")
    assert command == [
        "openai",
        "api",
        "chat.completions.create",
        "-m",
        "gpt-4",
        "-g",
        "user",
        "test prompt",
    ]


def test_build_ai_command_quote_escaping():
    """Test that single quotes in prompts are properly escaped."""
    command = build_ai_command("gemini", "test 'quoted' prompt")
    # No escaping needed, prompt is passed as-is
    assert command == ["gemini", "--prompt-interactive", "test 'quoted' prompt"]


def test_build_ai_command_invalid_agent():
    """Test that invalid agent raises ValueError."""
    with pytest.raises(ValueError, match="Unsupported AI agent"):
        build_ai_command("invalid_agent", "test prompt")


def test_run_aid_invalid_repo_spec(monkeypatch):
    """Test that invalid repo spec returns 1."""
    from rockerc.aid import run_aid

    # Patch sys.argv to simulate CLI call
    monkeypatch.setattr("sys.argv", ["aid", "invalid/repo@", "prompt"])
    # Should return 1 for invalid repo spec
    assert run_aid() == 1


def test_run_aid_invalid_agent(monkeypatch):
    """Test that invalid agent returns 1."""
    from rockerc.aid import run_aid

    # Patch parse_aid_args to return invalid agent
    class Args:
        agent = "invalid_agent"
        repo_spec = "owner/repo"
        prompt = ["prompt"]

    monkeypatch.setattr("rockerc.aid.parse_aid_args", lambda args=None: Args())
    # Should return 1 for invalid agent
    assert run_aid() == 1


def test_parse_aid_args_missing_arguments():
    """Test that missing arguments raises SystemExit (argparse behavior)."""
    with pytest.raises(SystemExit):
        parse_aid_args(["owner/repo"])  # Missing prompt


def test_parse_aid_args_mutually_exclusive_agents():
    """Test that multiple agents can't be specified."""
    with pytest.raises(SystemExit):
        parse_aid_args(["--gemini", "--claude", "owner/repo", "prompt"])


def test_parse_aid_args_repo_with_subfolder():
    """Test parsing repo spec with subfolder."""
    args = parse_aid_args(["owner/repo#subfolder", "test", "prompt"])
    assert args.repo_spec == "owner/repo#subfolder"
    assert args.prompt == ["test", "prompt"]
