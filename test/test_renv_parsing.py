#!/usr/bin/env python3
"""
Comprehensive tests for renv repository specification parsing.
"""

import unittest
from rockerc.renv import parse_repo_spec


class TestRenvRepositorySpecParsing(unittest.TestCase):
    """Test repository specification parsing functionality."""

    def test_basic_repo_parsing(self):
        """Test basic owner/repo parsing."""
        owner, repo, branch, subfolder = parse_repo_spec("blooop/bencher")
        self.assertEqual(owner, "blooop")
        self.assertEqual(repo, "bencher")
        self.assertEqual(branch, "main")  # defaults to main
        self.assertEqual(subfolder, "")

    def test_repo_with_branch(self):
        """Test parsing repo with explicit branch."""
        owner, repo, branch, subfolder = parse_repo_spec("osrf/rocker@develop")
        self.assertEqual(owner, "osrf")
        self.assertEqual(repo, "rocker")
        self.assertEqual(branch, "develop")
        self.assertEqual(subfolder, "")

    def test_repo_with_feature_branch(self):
        """Test parsing repo with feature branch containing slash."""
        owner, repo, branch, subfolder = parse_repo_spec("company/project@feature/new-ui")
        self.assertEqual(owner, "company")
        self.assertEqual(repo, "project")
        self.assertEqual(branch, "feature/new-ui")
        self.assertEqual(subfolder, "")

    def test_repo_with_subfolder(self):
        """Test parsing repo with subfolder."""
        owner, repo, branch, subfolder = parse_repo_spec("blooop/bencher#scripts")
        self.assertEqual(owner, "blooop")
        self.assertEqual(repo, "bencher")
        self.assertEqual(branch, "main")
        self.assertEqual(subfolder, "scripts")

    def test_repo_with_nested_subfolder(self):
        """Test parsing repo with nested subfolder."""
        owner, repo, branch, subfolder = parse_repo_spec("company/project#docs/examples/basic")
        self.assertEqual(owner, "company")
        self.assertEqual(repo, "project")
        self.assertEqual(branch, "main")
        self.assertEqual(subfolder, "docs/examples/basic")

    def test_repo_with_branch_and_subfolder(self):
        """Test parsing repo with both branch and subfolder."""
        owner, repo, branch, subfolder = parse_repo_spec("user/repo@feature/cool-stuff#src/main")
        self.assertEqual(owner, "user")
        self.assertEqual(repo, "repo")
        self.assertEqual(branch, "feature/cool-stuff")
        self.assertEqual(subfolder, "src/main")

    def test_complex_branch_names(self):
        """Test parsing with complex branch names."""
        test_cases = [
            ("owner/repo@bugfix/issue-123", "bugfix/issue-123"),
            ("owner/repo@release/v1.2.3", "release/v1.2.3"),
            ("owner/repo@hotfix/critical-bug", "hotfix/critical-bug"),
            ("owner/repo@dev", "dev"),
            ("owner/repo@master", "master"),
        ]

        for repo_spec, expected_branch in test_cases:
            with self.subTest(repo_spec=repo_spec):
                _, _, branch, _ = parse_repo_spec(repo_spec)
                self.assertEqual(branch, expected_branch)

    def test_complex_subfolder_paths(self):
        """Test parsing with complex subfolder paths."""
        test_cases = [
            ("owner/repo#src", "src"),
            ("owner/repo#docs/api", "docs/api"),
            ("owner/repo#examples/tutorial/step1", "examples/tutorial/step1"),
            ("owner/repo#packages/core/lib", "packages/core/lib"),
        ]

        for repo_spec, expected_subfolder in test_cases:
            with self.subTest(repo_spec=repo_spec):
                _, _, _, subfolder = parse_repo_spec(repo_spec)
                self.assertEqual(subfolder, expected_subfolder)

    def test_invalid_specifications(self):
        """Test that invalid specifications raise ValueError."""
        invalid_specs = [
            "invalid-repo",  # no slash
            "/repo",  # empty owner
            "owner/",  # empty repo
            "",  # empty string
            "   ",  # whitespace only
            "owner//repo",  # double slash
        ]

        for invalid_spec in invalid_specs:
            with self.subTest(repo_spec=invalid_spec):
                with self.assertRaises(ValueError):
                    parse_repo_spec(invalid_spec)

    def test_edge_cases(self):
        """Test edge cases in parsing."""
        # Multiple @ symbols (should use first split)
        _, _, branch, _ = parse_repo_spec("owner/repo@branch@extra")
        self.assertEqual(branch, "branch@extra")

        # Multiple # symbols (should use first split)
        _, _, _, subfolder = parse_repo_spec("owner/repo#folder#extra")
        self.assertEqual(subfolder, "folder#extra")

        # @ and # together
        _, _, branch, subfolder = parse_repo_spec("owner/repo@dev#src#more")
        self.assertEqual(branch, "dev")
        self.assertEqual(subfolder, "src#more")

    def test_real_world_examples(self):
        """Test real-world repository examples."""
        examples = [
            {"spec": "blooop/bencher@main", "expected": ("blooop", "bencher", "main", "")},
            {"spec": "osrf/rocker", "expected": ("osrf", "rocker", "main", "")},
            {
                "spec": "microsoft/vscode@feature/new-editor#extensions/python",
                "expected": ("microsoft", "vscode", "feature/new-editor", "extensions/python"),
            },
            {
                "spec": "tensorflow/tensorflow@release-2.9#tensorflow/python",
                "expected": ("tensorflow", "tensorflow", "release-2.9", "tensorflow/python"),
            },
        ]

        for example in examples:
            with self.subTest(spec=example["spec"]):
                result = parse_repo_spec(example["spec"])
                self.assertEqual(result, example["expected"])


if __name__ == "__main__":
    unittest.main()
