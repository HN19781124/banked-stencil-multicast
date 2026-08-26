"""Offline tests for the pinned CAD toolchain bootstrap."""

from __future__ import annotations

import hashlib
import io
import tarfile
import tempfile
import unittest
from pathlib import Path

from tools.bootstrap_cad import ASSETS, _safe_extract, platform_key, sha256_file


class BootstrapCadTests(unittest.TestCase):
    def test_supported_platform_aliases(self) -> None:
        self.assertEqual("windows-x64", platform_key("Windows", "AMD64"))
        self.assertEqual("linux-x64", platform_key("Linux", "x86_64"))
        self.assertEqual("linux-arm64", platform_key("Linux", "aarch64"))
        self.assertEqual("darwin-arm64", platform_key("Darwin", "arm64"))

    def test_assets_are_pinned(self) -> None:
        for key, asset in ASSETS.items():
            self.assertEqual(key, asset.platform_key)
            self.assertGreater(asset.size, 0)
            self.assertEqual(64, len(asset.sha256))
            int(asset.sha256, 16)
            self.assertIn("20260826", asset.filename)

    def test_sha256_file(self) -> None:
        payload = b"neumann-bottleneck\n"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "payload.bin"
            path.write_bytes(payload)
            self.assertEqual(hashlib.sha256(payload).hexdigest(), sha256_file(path))

    def test_archive_path_traversal_is_rejected(self) -> None:
        archive_bytes = io.BytesIO()
        with tarfile.open(fileobj=archive_bytes, mode="w:gz") as archive:
            member = tarfile.TarInfo("../escape.txt")
            payload = b"blocked"
            member.size = len(payload)
            archive.addfile(member, io.BytesIO(payload))
        archive_bytes.seek(0)
        with tempfile.TemporaryDirectory() as temporary:
            with tarfile.open(fileobj=archive_bytes, mode="r:gz") as archive:
                with self.assertRaises(RuntimeError):
                    _safe_extract(archive, Path(temporary))


if __name__ == "__main__":
    unittest.main()
