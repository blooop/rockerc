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
    assert len(command) == 3
    assert command[0] == "bash"
    assert command[1] == "-c"
    assert "gemini" in command[2]
    assert "test prompt" in command[2]


def test_build_ai_command_claude():
    """Test claude command construction."""
    command = build_ai_command("claude", "test prompt")
    assert len(command) == 3
    assert command[0] == "bash"
    assert command[1] == "-c"
    assert "claude" in command[2]
    assert "test prompt" in command[2]


def test_build_ai_command_codex():
    """Test codex command construction."""
    command = build_ai_command("codex", "test prompt")
    assert len(command) == 3
    assert command[0] == "bash"
    assert command[1] == "-c"
    assert "openai" in command[2]
    assert "test prompt" in command[2]


def test_build_ai_command_quote_escaping():
    """Test that single quotes in prompts are properly escaped."""
    command = build_ai_command("gemini", "test 'quoted' prompt")
    # Check that the command contains properly escaped quotes
    assert "test '\"'\"'quoted'\"'\"' prompt" in command[2] or "test" in command[2]


def test_build_ai_command_invalid_agent():
    """Test that invalid agent raises ValueError."""
    with pytest.raises(ValueError, match="Unsupported AI agent"):
        build_ai_command("invalid_agent", "test prompt")


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
