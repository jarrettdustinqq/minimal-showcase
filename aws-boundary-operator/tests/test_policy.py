import tempfile
import unittest
from pathlib import Path

from boundary_operator.policy import PolicyViolation, WorkspacePolicy, check_command


class WorkspacePolicyTests(unittest.TestCase):
    def test_resolve_allows_workspace_child(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            policy = WorkspacePolicy(root)
            self.assertEqual(policy.resolve("a/b.txt"), (root / "a/b.txt").resolve())

    def test_resolve_blocks_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            policy = WorkspacePolicy(Path(tmp))
            with self.assertRaises(PolicyViolation):
                policy.resolve("../outside.txt")

    def test_only_named_checks_are_available(self):
        self.assertEqual(check_command("git_diff_check"), ("git", "diff", "--check"))
        with self.assertRaises(PolicyViolation):
            check_command("rm_everything")


if __name__ == "__main__":
    unittest.main()
