"""Kurulum motoru entegrasyon testi (gerçek pip, git ve winget akışı).

Varsayılan olarak ATLANIR. İnternet, ekran (Tkinter) ve Windows gerektirir.
Çalıştırmak için, mümkünse tek kullanımlık bir sanal ortamın Python'uyla:

    set ATOLYE_INTEGRATION=1
    python -m unittest tests.test_engine_integration -v

Kurulumlar güvenlidir: pip paketi çalıştırdığın Python'a, git deposu geçici bir klasöre kurulur,
winget için zaten kurulu bir paket kullanılır (yeni bir şey yüklenmez).
"""
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

RUN = os.environ.get("ATOLYE_INTEGRATION") == "1"


def _prog(pid, ptype, pkg):
    return {"id": pid, "name": pid, "category": "dev", "type": ptype,
            "package_id": pkg, "desc": "test", "tags": [], "default": False}


@unittest.skipUnless(RUN and os.name == "nt", "ATOLYE_INTEGRATION=1 ve Windows gerekir")
class TestInstallEngine(unittest.TestCase):
    def _run_engine(self, programs, timeout=240):
        import tkinter as tk
        import atolye

        tmp_home = tempfile.mkdtemp(prefix="atolye_home_")
        old = {k: os.environ.get(k) for k in ("USERPROFILE", "HOME")}
        os.environ["USERPROFILE"] = tmp_home
        os.environ["HOME"] = tmp_home
        root = tk.Tk()
        try:
            app = atolye.SuperInstallerApp(root)
            app.overlay = atolye.InstallOverlay(root, app.cancel_installation)
            app.overlay.begin(len(programs))
            app.is_installing = True
            app.cancel_requested = False
            threading.Thread(target=app._run_install_thread, args=(programs,), daemon=True).start()

            deadline = time.time() + timeout
            while time.time() < deadline:
                root.update()
                if not app.is_installing and not app.overlay._running:
                    break
                time.sleep(0.05)
            else:
                self.fail("Kurulum zaman aşımına uğradı")
            root.update()
            counts = {k: int(v.cget("text")) for k, v in app.overlay._count_labels.items()}
            title = app.overlay.title.cget("text")
            return tmp_home, counts, title
        finally:
            root.destroy()
            for k, v in old.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    def test_pip_and_git_install(self):
        progs = [
            _prog("it_pip", "pip", "pyfiglet"),
            _prog("it_git", "git_repo", "https://github.com/octocat/Hello-World.git"),
        ]
        home, counts, title = self._run_engine(progs)
        self.assertEqual(counts, {"ok": 2, "skip": 0, "fail": 0}, f"Sayaçlar beklenenden farklı: {counts}")
        self.assertEqual(title, "Hepsi hazır")
        repo = os.path.join(home, "Engineering_Tools", "it_git")
        self.assertTrue(os.path.isdir(os.path.join(repo, ".git")), "git deposu klonlanmadı")
        out = subprocess.run([sys.executable, "-c", "import pyfiglet; print(pyfiglet.__name__)"],
                             capture_output=True, text=True)
        self.assertEqual(out.stdout.strip(), "pyfiglet", out.stderr)

    def test_winget_already_installed_is_reported_as_skipped(self):
        # Python 3.12 bu makinede winget ile kurulu olmalı; yoksa test anlamsızdır
        probe = subprocess.run(["winget", "list", "--id", "Python.Python.3.12", "-e"],
                               capture_output=True, text=True)
        if "Python.Python.3.12" not in probe.stdout:
            self.skipTest("Python.Python.3.12 winget ile kurulu değil")
        home, counts, _ = self._run_engine([_prog("it_winget", "winget", "Python.Python.3.12")])
        self.assertEqual(counts["fail"], 0, f"Hata sayısı 0 olmalı: {counts}")
        self.assertEqual(counts["ok"] + counts["skip"], 1)

    def test_failed_install_is_counted(self):
        progs = [_prog("it_bad", "pip", "this-package-does-not-exist-atolye-xyz-123")]
        home, counts, title = self._run_engine(progs, timeout=120)
        self.assertEqual(counts["fail"], 1, counts)
        self.assertEqual(title, "Kurulum tamamlandı")


if __name__ == "__main__":
    unittest.main()
