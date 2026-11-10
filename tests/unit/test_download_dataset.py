import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.download_dataset import NAMES, extract


class DownloadTests(unittest.TestCase):
    def test_extract_replay_and_preserve_changed_local_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / "source.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                for name in NAMES:
                    bundle.writestr(name, "id\nexample\n")
                bundle.writestr("../outside.csv", "must not extract")
            output = root / "raw"
            first = extract(archive, output)
            self.assertEqual(first, extract(archive, output))
            self.assertFalse((root / "outside.csv").exists())
            changed = output / NAMES[0]
            changed.write_text("local data\n")
            missing = output / NAMES[-1]
            missing.unlink()
            with self.assertRaisesRegex(ValueError, "Existing file differs"):
                extract(archive, output)
            self.assertEqual(changed.read_text(), "local data\n")
            self.assertFalse(missing.exists())

    def test_missing_archive_member_fails_before_writing(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / "incomplete.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr(NAMES[0], "id\n1\n")
            with self.assertRaises(KeyError):
                extract(archive, root / "raw")
            self.assertFalse((root / "raw").exists())
