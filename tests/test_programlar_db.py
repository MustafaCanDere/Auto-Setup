"""Program veritabanı tutarlılık testleri (harici bağımlılık yok)."""
import os
import sys
import unittest
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from programlar_db import CATEGORIES, PROGRAMS, PRESETS  # noqa: E402

ALLOWED_TYPES = {"winget", "pip", "git_repo", "direct_zip", "direct_exe"}
REQUIRED_KEYS = ("id", "name", "category", "type", "package_id", "desc")


class TestProgramDatabase(unittest.TestCase):
    def test_not_empty(self):
        self.assertGreater(len(PROGRAMS), 0)

    def test_required_keys(self):
        for p in PROGRAMS:
            for key in REQUIRED_KEYS:
                self.assertIn(key, p, f"{p.get('id')} kaydında '{key}' eksik")
                self.assertTrue(str(p[key]).strip(), f"{p['id']}: '{key}' boş")

    def test_unique_ids(self):
        dupes = [i for i, c in Counter(p["id"] for p in PROGRAMS).items() if c > 1]
        self.assertEqual(dupes, [], f"Tekrarlayan id'ler: {dupes}")

    def test_known_types(self):
        for p in PROGRAMS:
            self.assertIn(p["type"], ALLOWED_TYPES, f"{p['id']}: bilinmeyen tip {p['type']}")

    def test_categories_exist(self):
        cat_ids = {c["id"] for c in CATEGORIES}
        for p in PROGRAMS:
            self.assertIn(p["category"], cat_ids, f"{p['id']}: bilinmeyen kategori")

    def test_git_repos_use_https(self):
        for p in PROGRAMS:
            if p["type"] == "git_repo":
                self.assertTrue(p["package_id"].startswith("https://"),
                                f"{p['id']}: git adresi https olmalı")

    def test_direct_zip_uses_https(self):
        for p in PROGRAMS:
            if p["type"] in ("direct_zip", "direct_exe"):
                self.assertTrue(p["package_id"].startswith("https://"),
                                f"{p['id']}: indirme adresi https olmalı")

    def test_presets_reference_real_programs(self):
        ids = {p["id"] for p in PROGRAMS}
        for key, preset in PRESETS.items():
            unknown = [i for i in preset["ids"] if i not in ids]
            self.assertEqual(unknown, [], f"'{key}' profilinde bilinmeyen id'ler: {unknown}")


if __name__ == "__main__":
    unittest.main()
