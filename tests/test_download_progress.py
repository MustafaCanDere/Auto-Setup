"""İndirme ilerlemesi ayrıştırıcısı ve hız ölçer testleri (internet/ekran gerektirmez)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import atolye
except ImportError as e:  # tkinter olmayan ortamlar
    atolye = None
    _ERR = str(e)

MB = 1024 ** 2


@unittest.skipIf(atolye is None, "atolye içe aktarılamadı (tkinter yok?)")
class TestParse(unittest.TestCase):
    def p(self, line):
        return atolye.parse_download_progress(line)

    def test_winget_size_pair(self):
        r = self.p("  ██████████████▒▒▒▒▒▒▒▒▒▒▒▒  120 MB /  286 MB")
        self.assertEqual(r["done"], 120 * MB)
        self.assertEqual(r["total"], 286 * MB)
        self.assertAlmostEqual(r["pct"], 120 * 100 / 286, places=3)

    def test_winget_decimal_comma(self):
        r = self.p("  ███▒▒▒  1,50 GB / 3,00 GB")
        self.assertAlmostEqual(r["pct"], 50.0)

    def test_winget_bare_percent(self):
        self.assertEqual(self.p("  ██████▒▒▒▒▒▒  45%")["pct"], 45.0)

    def test_pip_raw(self):
        r = self.p("Progress 524288 of 1048576")
        self.assertEqual(r["done"], 524288)
        self.assertEqual(r["pct"], 50.0)

    def test_pip_downloading_start(self):
        r = self.p("Downloading torch-2.5.1-cp312-cp312-win_amd64.whl (203.1 MB)")
        self.assertTrue(r["start"])
        self.assertEqual(r["name"], "torch-2.5.1-cp312-cp312-win_amd64.whl")
        self.assertEqual(r["total"], int(203.1 * MB))

    def test_git_receiving(self):
        r = self.p("Receiving objects:  45% (123/456), 12.34 MiB | 2.10 MiB/s")
        self.assertEqual(r["pct"], 45.0)
        self.assertEqual(r["done"], int(12.34 * MB))

    def test_git_receiving_no_size(self):
        self.assertEqual(self.p("Receiving objects:   3% (4/120)")["pct"], 3.0)

    def test_normal_lines_ignored(self):
        for line in ("Found Visual Studio Code [Microsoft.VisualStudioCode] Version 1.95",
                     "Successfully installed numpy-2.1.0",
                     "Resolving deltas: 100% (10/10), done.",
                     "Requirement already satisfied: pip in c:\\python (24.2)",
                     "CPU kullanımı %45 seviyesinde kaldı",
                     "-", ""):
            self.assertIsNone(self.p(line), line)


@unittest.skipIf(atolye is None, "atolye içe aktarılamadı (tkinter yok?)")
class TestMeter(unittest.TestCase):
    def setUp(self):
        self.t = 0.0
        self.m = atolye.DownloadMeter(clock=lambda: self.t)

    def feed(self, done, total, dt=1.0):
        self.t += dt
        return self.m.feed({"done": done, "total": total, "pct": None, "name": None, "start": False})

    def test_speed_and_eta(self):
        self.feed(0, 100 * MB)
        frac, text = self.feed(10 * MB, 100 * MB)
        self.assertAlmostEqual(frac, 0.1)
        self.assertIn("%10", text)
        self.assertIn("10.0 MB / 100.0 MB", text)
        self.assertIn("10.0 MB/s", text)
        self.assertIn("kaldı", text)

    def test_throttle(self):
        self.feed(0, 100 * MB)
        self.assertIsNone(self.feed(1 * MB, 100 * MB, dt=0.01))

    def test_new_file_resets(self):
        self.feed(50 * MB, 100 * MB)
        self.feed(5 * MB, 20 * MB)
        self.assertEqual(self.m.total, 20 * MB)
        self.assertIsNone(self.m.speed)

    def test_milestones(self):
        self.feed(0, 100)
        self.assertEqual(self.m.milestone(), 0)
        self.feed(30, 100)
        self.assertEqual(self.m.milestone(), 25)
        self.assertIsNone(self.m.milestone())

    def test_eta_format(self):
        self.assertEqual(atolye.format_eta(42), "42 sn")
        self.assertEqual(atolye.format_eta(125), "2 dk 05 sn")


if __name__ == "__main__":
    unittest.main()
