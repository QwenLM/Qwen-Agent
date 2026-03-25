"""
Test for CWE-918: SSRF via user-controlled URL in save_url_to_local_work_dir.

The function save_url_to_local_work_dir() in qwen_agent/utils/utils.py accepts
arbitrary URLs and makes HTTP requests to them. Without validation, this allows
SSRF attacks when the agent framework is deployed as a web service.

This test validates that:
1. URLs pointing to private/internal IP ranges are rejected
2. URLs pointing to localhost are rejected
3. URLs pointing to cloud metadata endpoints are rejected
4. URLs pointing to link-local addresses are rejected
5. Public URLs are allowed through validation
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from qwen_agent.utils.utils import validate_request_url


class TestSSRFProtection(unittest.TestCase):
    """Test that internal/private URLs are blocked by the SSRF validation."""

    def test_localhost_url_blocked(self):
        """URLs targeting localhost should be rejected."""
        with self.assertRaises(ValueError):
            validate_request_url('http://localhost/admin')

    def test_localhost_ip_blocked(self):
        """URLs targeting 127.0.0.1 should be rejected."""
        with self.assertRaises(ValueError):
            validate_request_url('http://127.0.0.1:8080/secret')

    def test_ipv6_localhost_blocked(self):
        """URLs targeting IPv6 localhost should be rejected."""
        with self.assertRaises(ValueError):
            validate_request_url('http://[::1]/admin')

    def test_private_10_range_blocked(self):
        """URLs targeting 10.x.x.x private range should be rejected."""
        with self.assertRaises(ValueError):
            validate_request_url('http://10.0.0.1/internal')

    def test_private_172_range_blocked(self):
        """URLs targeting 172.16-31.x.x private range should be rejected."""
        with self.assertRaises(ValueError):
            validate_request_url('http://172.16.0.1/internal')

    def test_private_192_168_range_blocked(self):
        """URLs targeting 192.168.x.x private range should be rejected."""
        with self.assertRaises(ValueError):
            validate_request_url('http://192.168.1.1/router')

    def test_cloud_metadata_blocked(self):
        """URLs targeting cloud metadata endpoint (169.254.169.254) should be rejected."""
        with self.assertRaises(ValueError):
            validate_request_url('http://169.254.169.254/latest/meta-data/')

    def test_link_local_blocked(self):
        """URLs targeting link-local addresses should be rejected."""
        with self.assertRaises(ValueError):
            validate_request_url('http://169.254.1.1/some-path')

    def test_public_url_allowed(self):
        """Public URLs should be allowed."""
        # These should NOT raise
        validate_request_url('https://example.com/file.pdf')
        validate_request_url('https://github.com/repo/file.txt')

    def test_zero_ip_blocked(self):
        """URLs targeting 0.0.0.0 should be rejected."""
        with self.assertRaises(ValueError):
            validate_request_url('http://0.0.0.0/')

    def test_save_url_integration_metadata(self):
        """Verify that save_url_to_local_work_dir itself rejects cloud metadata URLs."""
        from qwen_agent.utils.utils import save_url_to_local_work_dir
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaises(ValueError):
                save_url_to_local_work_dir('http://169.254.169.254/latest/meta-data/', tmpdir)

    def test_save_url_integration_localhost(self):
        """Verify that save_url_to_local_work_dir itself rejects localhost URLs."""
        from qwen_agent.utils.utils import save_url_to_local_work_dir
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaises(ValueError):
                save_url_to_local_work_dir('http://127.0.0.1:8080/secret', tmpdir)


if __name__ == '__main__':
    unittest.main()
