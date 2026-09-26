"""Exercise the production launcher control flow with portable Win32 doubles."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class LauncherTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("cc"), "portable C compiler unavailable")
    def test_branded_python_host(self):
        root=Path(__file__).resolve().parent.parent
        with tempfile.TemporaryDirectory() as work:
            binary=Path(work)/'host-test'
            subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Wno-unused-parameter','-Werror',
                '-I',str(root/'tests/native'),str(root/'tests/native/test_python_host.c'),'-o',str(binary)],check=True)
            subprocess.run([str(binary)],check=True)
    @unittest.skipUnless(shutil.which("cc"), "portable C compiler unavailable")
    def test_dispatch_and_failed_install_pointer(self):
        root = Path(__file__).resolve().parent.parent
        with tempfile.TemporaryDirectory() as work:
            binary = Path(work) / "launcher-test"
            subprocess.run([
                "cc", "-std=c11", "-Wall", "-Wextra", "-Wno-unused-parameter", "-Werror",
                "-I", str(root / "tests/native"),
                str(root / "tests/native/test_launcher.c"), "-o", str(binary),
            ], check=True)
            subprocess.run([str(binary)], check=True)
