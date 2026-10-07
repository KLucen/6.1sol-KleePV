"""Exercise deduplication, complete restoration and overwrite protection."""

import importlib.util
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location("engineering_archive", Path(__file__).with_name("engineering_archive.py"))
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class SnapshotTest(unittest.TestCase):
    def test_roundtrip_and_guards(self):
        original = MODULE.ROOT, MODULE.META, MODULE.LOCAL
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "source"
            root.mkdir()
            (root / "empty").mkdir()
            (root / "a.bin").write_bytes(b"a" * 60)
            (root / "b.bin").write_bytes(b"a" * 60)
            (root / "record.json").write_bytes(b'{"n":1}\r\n')
            (root / "c.bin").write_bytes(b"c" * 60)
            MODULE.ROOT, MODULE.META, MODULE.LOCAL = root, root / "archive", root / "_upload"
            try:
                MODULE.build(90)
                manifest = MODULE.read(MODULE.META / "project-files.json")
                self.assertEqual(manifest["statistics"]["files"], 4)
                self.assertEqual(manifest["statistics"]["unique_objects"], 3)
                self.assertEqual(manifest["statistics"]["volumes"], 2)
                destination = Path(temporary) / "restored"
                MODULE.restore(MODULE.LOCAL, destination)
                MODULE.restore(MODULE.LOCAL, destination)
                self.assertTrue((destination / "empty").is_dir())
                for item in manifest["files"]:
                    self.assertEqual((destination / item["path"]).read_bytes(), (root / item["path"]).read_bytes())
                (destination / "a.bin").write_bytes(b"do not overwrite")
                with self.assertRaises(FileExistsError):
                    MODULE.restore(MODULE.LOCAL, destination)
                self.assertEqual((destination / "a.bin").read_bytes(), b"do not overwrite")
                with self.assertRaises(FileExistsError):
                    MODULE.build(90)
                for path in ("../escape", "C:/escape", "a\\b", "/escape"):
                    with self.assertRaises(ValueError):
                        MODULE.safe_path(destination, path)
            finally:
                MODULE.ROOT, MODULE.META, MODULE.LOCAL = original


if __name__ == "__main__":
    unittest.main()
