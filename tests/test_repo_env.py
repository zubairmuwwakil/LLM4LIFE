import importlib.util
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    with mock.patch.dict(os.environ, {"PYTHONPATH": str(SCRIPTS)}, clear=False):
        spec.loader.exec_module(module)
    return module


import sys
sys.path.insert(0, str(SCRIPTS))
REPO_ENV = load("repo_env_test", "repo_env.py")
INIT_ENV = load("init_local_env_test", "init_local_env.py")


class RepoEnvTests(unittest.TestCase):
    def test_loads_quoted_values_without_executing_shell(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env"
            path.write_text(
                'OBSIDIAN_VAULT_PATH="/Users/example/My Vault"\n'
                'FRAGMENT=https://example.test/path#section\n'
                'COMMENTED=value # comment\n'
            )
            with mock.patch.dict(os.environ, {}, clear=True):
                values = REPO_ENV.load_repo_env(path=path)
                self.assertEqual(values["OBSIDIAN_VAULT_PATH"], "/Users/example/My Vault")
                self.assertEqual(os.environ["OBSIDIAN_VAULT_PATH"], "/Users/example/My Vault")
                self.assertEqual(values["FRAGMENT"], "https://example.test/path#section")
                self.assertEqual(values["COMMENTED"], "value")

    def test_existing_process_environment_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env"
            path.write_text("OBSIDIAN_VAULT_SCOPE=from-file\n")
            with mock.patch.dict(os.environ, {"OBSIDIAN_VAULT_SCOPE": "from-shell"}, clear=True):
                REPO_ENV.load_repo_env(path=path)
                self.assertEqual(os.environ["OBSIDIAN_VAULT_SCOPE"], "from-shell")

    def test_env_parser_rejects_shell_syntax(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env"
            path.write_text("echo unsafe\n")
            with self.assertRaises(ValueError):
                REPO_ENV.read_env_file(path)


class InitLocalEnvTests(unittest.TestCase):
    def test_captures_current_values_generates_token_and_chmods(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env"
            current = {
                "OBSIDIAN_VAULT_PATH": "/Users/example/My Vault",
                "OBSIDIAN_VAULT_SCOPE": "primary-vault",
                "DATABASE_URL": "postgresql://example.invalid/db",
            }
            with mock.patch.dict(os.environ, current, clear=True):
                status = INIT_ENV.initialize(
                    path=path,
                    capture_current=True,
                    rotate_bridge_token=False,
                )
            values = REPO_ENV.read_env_file(path)
            self.assertEqual(values["OBSIDIAN_VAULT_PATH"], current["OBSIDIAN_VAULT_PATH"])
            self.assertEqual(values["DATABASE_URL"], current["DATABASE_URL"])
            self.assertEqual(len(values["OBSIDIAN_BRIDGE_TOKEN"]), 64)
            self.assertTrue(status["bridge_token_generated_or_rotated"])
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_existing_bridge_token_is_preserved_without_rotation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env"
            token = "a" * 64
            path.write_text(f"OBSIDIAN_BRIDGE_TOKEN={token}\n")
            INIT_ENV.initialize(path=path, capture_current=False, rotate_bridge_token=False)
            values = REPO_ENV.read_env_file(path)
            self.assertEqual(values["OBSIDIAN_BRIDGE_TOKEN"], token)

    def test_explicit_rotation_changes_bridge_token(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env"
            token = "a" * 64
            path.write_text(f"OBSIDIAN_BRIDGE_TOKEN={token}\n")
            INIT_ENV.initialize(path=path, capture_current=False, rotate_bridge_token=True)
            values = REPO_ENV.read_env_file(path)
            self.assertNotEqual(values["OBSIDIAN_BRIDGE_TOKEN"], token)
            self.assertEqual(len(values["OBSIDIAN_BRIDGE_TOKEN"]), 64)


if __name__ == "__main__":
    unittest.main()
