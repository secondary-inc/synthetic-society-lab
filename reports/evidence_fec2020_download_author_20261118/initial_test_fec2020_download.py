"""Authored bytes and inert HTTP only; never contact the FEC in unit tests."""
import hashlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from civiclab.e01 import fec2020_download as source


class Response(io.BytesIO):
    status = 200

    def geturl(self):
        return source.URL


class FEC2020DownloadTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.data = b"AUTHORED_SOURCE_FIXTURE"
        self.patch_size = patch.object(source, "EXPECTED_BYTES", len(self.data))
        self.patch_hash = patch.object(source, "EXPECTED_SHA256", hashlib.sha256(self.data).hexdigest())
        self.patch_size.start(); self.addCleanup(self.patch_size.stop)
        self.patch_hash.start(); self.addCleanup(self.patch_hash.stop)

    def save(self, data):
        path = self.root / source.RELATIVE_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def test_local_match_uses_no_network_and_never_adopts(self):
        self.save(self.data)
        with patch.object(source.urllib.request, "build_opener") as opener:
            result = source.obtain(self.root, fetch=True)
        opener.assert_not_called()
        self.assertEqual(result["physical_http_GETs"], 0)
        self.assertFalse(result["source_adoption"])
        self.assertFalse(result["forecast_consumption"])

    def test_missing_default_refuses_without_network(self):
        with patch.object(source.urllib.request, "build_opener") as opener:
            with self.assertRaisesRegex(source.SourceRefused, "MISSING_USE_FETCH"):
                source.obtain(self.root)
        opener.assert_not_called()

    def test_existing_changed_bytes_are_never_replaced(self):
        path = self.save(b"X" * len(self.data))
        with patch.object(source.urllib.request, "build_opener") as opener:
            with self.assertRaisesRegex(source.SourceRefused, "HASH_MISMATCH"):
                source.obtain(self.root, fetch=True)
        opener.assert_not_called()
        self.assertEqual(path.read_bytes(), b"X" * len(self.data))

    def test_download_once_verifies_then_publishes(self):
        with patch.object(source.urllib.request, "build_opener") as factory:
            factory.return_value.open.return_value = Response(self.data)
            result = source.obtain(self.root, fetch=True)
        factory.return_value.open.assert_called_once()
        args, kwargs = factory.return_value.open.call_args
        self.assertEqual(args[0].full_url, source.URL)
        self.assertEqual(args[0].get_method(), "GET")
        self.assertEqual(kwargs, {"timeout": 30})
        self.assertEqual((self.root / source.RELATIVE_PATH).read_bytes(), self.data)
        self.assertEqual(result["physical_http_GETs"], 1)
        self.assertFalse(result["source_adoption"])

    def test_corrupt_oversized_and_http_identity_are_not_saved(self):
        for payload, status, url in ((b"X" * len(self.data), 200, source.URL),
                                     (self.data + b"X", 200, source.URL),
                                     (self.data, 404, source.URL),
                                     (self.data, 200, "https://example.invalid/file")):
            with self.subTest(status=status, url=url, length=len(payload)):
                response = Response(payload)
                response.status = status
                response.geturl = lambda: url
                with patch.object(source.urllib.request, "build_opener") as factory:
                    factory.return_value.open.return_value = response
                    with self.assertRaises(source.SourceRefused):
                        source.obtain(self.root, fetch=True)
                factory.return_value.open.assert_called_once()
                self.assertFalse((self.root / source.RELATIVE_PATH).exists())

    def test_redirect_and_symlink_are_refused(self):
        with self.assertRaisesRegex(source.SourceRefused, "REDIRECT_REFUSED"):
            source._NoRedirect().redirect_request(None, None, 302, None, {}, source.URL)
        target = self.save(self.data)
        target.unlink()
        other = self.root / "other"
        other.write_bytes(self.data)
        target.symlink_to(other)
        with self.assertRaisesRegex(source.SourceRefused, "UNSAFE_DESTINATION"):
            source.obtain(self.root, fetch=True)


if __name__ == "__main__":
    unittest.main()
