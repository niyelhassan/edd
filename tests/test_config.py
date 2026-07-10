import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


CONFIG_PATH = Path(__file__).resolve().parents[1] / "app" / "config.py"
SPEC = importlib.util.spec_from_file_location("edd_config", CONFIG_PATH)
CONFIG = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(CONFIG)


class LocalEnvTests(unittest.TestCase):
    def test_missing_env_file_is_a_noop(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {}, clear=True):
                CONFIG.load_local_env(Path(directory))
                self.assertNotIn("SECRET_KEY", os.environ)

    def test_reads_simple_and_multiline_values_without_overwriting_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            (base / ".env").write_text(
                "EXISTING=from-file\n"
                "SIMPLE='value'\n"
                "JSON={\n"
                '  "type": "service_account"\n'
                "}\n",
                encoding="utf-8",
            )
            with patch.dict(os.environ, {"EXISTING": "from-environment"}, clear=True):
                CONFIG.load_local_env(base)
                self.assertEqual(os.environ["EXISTING"], "from-environment")
                self.assertEqual(os.environ["SIMPLE"], "value")
                self.assertEqual(
                    os.environ["JSON"], '{\n  "type": "service_account"\n}'
                )


if __name__ == "__main__":
    unittest.main()
