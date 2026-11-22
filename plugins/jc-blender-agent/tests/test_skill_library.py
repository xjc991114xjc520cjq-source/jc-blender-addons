import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bridge.skill_library import ROOT as DATA, catalog, skill_result
from bridge.common import VERSION
from bridge.agents import agent_instructions


class SkillLibraryTests(unittest.TestCase):
    def test_sources_integrity_licenses_and_paging(self):
        entries = catalog()["skills"]
        self.assertEqual(len(entries), 14)
        for entry in entries:
            self.assertTrue(entry["source"].startswith("https://github.com/"))
            self.assertIn("LICENSE.upstream.txt", entry["files"])
            self.assertIn("SKILL.md", entry["files"])
            self.assertEqual(set(skill_result(entry["name"], "")["resources"]), set(entry["files"]))
            for path, meta in entry["files"].items():
                data = (DATA / "vendor" / entry["name"] / path).read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(), meta["sha256"])
            pages = []
            offset = 0
            while True:
                value = skill_result(entry["name"], offset=offset)
                pages.append(value["text"])
                self.assertLessEqual(len(value["text"]), 16000)
                if value["next_offset"] is None:
                    break
                offset = value["next_offset"]
            self.assertEqual("".join(pages), (DATA / "vendor" / entry["name"] / "SKILL.md").read_text(encoding="utf-8-sig"))

    def test_reject_unknown_and_traversal(self):
        for name, resource in [("../secret", "SKILL.md"), ("blender-core", "../../common.py"), ("blender-core", "/etc/passwd")]:
            with self.assertRaises(ValueError):
                skill_result(name, resource)
        with self.assertRaises(ValueError):
            skill_result("blender-core", offset=-1)

    def test_switch_controls_instruction_injection(self):
        self.assertNotIn("按问题读取 Blender 技能", agent_instructions(False))
        self.assertIn("按问题读取 Blender 技能", agent_instructions(True))
        self.assertIn("二次变换", agent_instructions(True))

    def test_bundled_release_relocates_without_local_skills(self):
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp)
            with zipfile.ZipFile(ROOT / "dist" / f"JC-Blender-Agent-{VERSION}.zip") as archive:
                archive.extractall(dest)
            check = """import sys,json
from pathlib import Path
sys.path.insert(0,str(Path('jc_blender_agent/runtime').resolve()))
from bridge.skill_library import catalog,skill_result
for item in catalog()['skills']:
 for resource in item['files']:
  assert skill_result(item['name'],resource)['text']
print(json.dumps({'skills':len(catalog()['skills'])}))
"""
            proc = subprocess.run([sys.executable, "-I", "-c", check], cwd=dest, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(json.loads(proc.stdout)["skills"], 14)


if __name__ == "__main__":
    unittest.main()
