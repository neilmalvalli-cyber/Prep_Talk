"""Distribution boundary checks; no runner or candidate execution."""

import importlib.util
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch


SOURCE = Path(__file__).resolve().parents[1] / "package_source.py"
spec = importlib.util.spec_from_file_location("package_source", SOURCE)
packager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packager)


class SourceBundleTests(unittest.TestCase):
    def test_only_allowlisted_files_are_distributed_and_existing_output_is_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in packager.RUNNER_FILES:
                path = root / "apps/runner" / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("synthetic runner source")
            for name in ("coding", "coding-private"):
                path = root / "content" / name / "problem.json"
                path.parent.mkdir(parents=True)
                path.write_text("{}")
            for name in (".env", "data/owner.key", "data/interviews.json",
                         "apps/runner/.env", "apps/runner/__pycache__/main.pyc",
                         "content/scenario-private/answers.json"):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("DO_NOT_DISTRIBUTE")
            output = root / "bundle.tar.gz"
            with patch.object(packager, "ROOT", root):
                self.assertEqual(packager.package(output), len(packager.RUNNER_FILES) + 2)
                original = output.read_bytes()
                with self.assertRaises(FileExistsError):
                    packager.package(output)
                self.assertEqual(output.read_bytes(), original)
            with tarfile.open(output) as archive:
                expected = {"apps/runner/" + name for name in packager.RUNNER_FILES}
                expected.update({"content/coding/problem.json", "content/coding-private/problem.json"})
                self.assertEqual(set(archive.getnames()), expected)
                for member in archive.getmembers():
                    self.assertTrue(member.isfile())
                    self.assertNotIn(b"DO_NOT_DISTRIBUTE", archive.extractfile(member).read())
