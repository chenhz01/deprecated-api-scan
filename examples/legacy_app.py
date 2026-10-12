"""Legacy app used in the deprecated-api-scan quickstart.

Run:
    python deprecated_scan.py scan --manifest manifests/python_stdlib_sample.json \
        --path examples/legacy_app.py --target 3.12
"""

import imp                    # removed in 3.12
import distutils.util         # removed in 3.12
import asyncio
import unittest


def load_plugin(path):
    return imp.load_source("plugin", path)


def slugify(s):
    return distutils.util.strtobool("True") if s else 0


def get_loop():
    return asyncio.get_event_loop()


class T(unittest.TestCase):
    def test_a(self):
        self.assertEquals(1 + 1, 2)   # alias removed in 3.12
