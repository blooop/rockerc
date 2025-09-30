"""Tests for YAML validation and error messages."""

import pytest
from rockerc.rockerc import _validate_args_format


def test_validate_args_format_valid():
    """Test that valid args pass validation."""
    valid_args = ["nvidia", "x11", "user", "git"]
    _validate_args_format(valid_args, "test.yaml")  # Should not raise


def test_validate_args_format_empty():
    """Test that empty args pass validation."""
    _validate_args_format([], "test.yaml")  # Should not raise
    _validate_args_format(None, "test.yaml")  # Should not raise


def test_validate_args_format_malformed():
    """Test that malformed aggregate strings are detected."""
    malformed_args = ["nvidia - x11 - user"]
    with pytest.raises(ValueError, match="Malformed args entry"):
        _validate_args_format(malformed_args, "test.yaml")


def test_validate_args_format_malformed_multiple():
    """Test detection of malformed strings with multiple parts."""
    malformed_args = ["git - ssh - cwd"]
    with pytest.raises(ValueError, match="YAML indentation issue"):
        _validate_args_format(malformed_args, "test.yaml")


def test_validate_args_format_error_message():
    """Test that error message contains helpful formatting examples."""
    malformed_args = ["nvidia - x11"]
    with pytest.raises(ValueError) as excinfo:
        _validate_args_format(malformed_args, "rockerc.yaml")

    error_msg = str(excinfo.value)
    assert "nvidia - x11" in error_msg
    assert "rockerc.yaml" in error_msg
    assert "❌ Incorrect" in error_msg
    assert "✅ Correct" in error_msg
    assert "args:" in error_msg


def test_validate_args_format_valid_with_dashes():
    """Test that valid extensions with dashes in their names pass validation."""
    valid_args = ["ssh-client", "dev-helpers", "user-preserve-home"]
    _validate_args_format(valid_args, "test.yaml")  # Should not raise


def test_validate_args_format_valid_single_dash():
    """Test that single dash (flag) passes validation."""
    valid_args = ["-v", "--verbose"]
    _validate_args_format(valid_args, "test.yaml")  # Should not raise
