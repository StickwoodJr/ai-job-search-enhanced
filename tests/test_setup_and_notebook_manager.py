"""Unit tests for tools/setup_wizard.py and rag/notebook_manager.py."""

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestSetupWizard(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.test_dir)
        self.swarm_file = REPO_ROOT / "config" / "swarm_sectors.json"
        self.orig_swarm = self.swarm_file.read_text(encoding="utf-8") if self.swarm_file.exists() else None
        if self.orig_swarm:
            self.addCleanup(self.swarm_file.write_text, self.orig_swarm, encoding="utf-8")

    def test_doctor_runs(self):
        import tools.setup_wizard as wizard
        res = wizard.run_doctor()
        self.assertIn("python", res)
        self.assertTrue(res["python"])
        self.assertIn("git", res)

    def test_configure_swarm_sectors_non_interactive(self):
        import tools.setup_wizard as wizard
        cfg = wizard.configure_swarm_sectors(interactive=False, location="Vancouver, BC", candidate_name="Jane Doe")
        self.assertEqual(cfg["home_location"], "Vancouver, BC")
        self.assertIn("sectors", cfg)
        self.assertIn("systems_hardware", cfg["sectors"])
        self.assertIn("networking_noc", cfg["sectors"])
        self.assertIn("cloud_cyber", cfg["sectors"])

    def test_configure_candidate_profile_non_interactive(self):
        import tools.setup_wizard as wizard
        data = {
            "name": "[YOUR_NAME]",
            "email": "[YOUR_EMAIL]",
            "phone": "[YOUR_PHONE]",
            "location": "[YOUR_ADDRESS]",
        }
        res = wizard.configure_candidate_profile(interactive=False, data=data)
        self.assertEqual(res["name"], "[YOUR_NAME]")


class TestNotebookManager(unittest.TestCase):
    def test_get_current_config(self):
        import rag.notebook_manager as nm
        cfg = nm.get_current_config()
        self.assertIn("enabled", cfg)
        self.assertIn("default_notebook_id", cfg)

    def test_select_notebook(self):
        import rag.notebook_manager as nm
        orig = nm.get_current_config()
        test_id = "test-notebook-uuid-12345"
        test_title = "Test Coursework Notebook"
        nm.cmd_select(test_id, test_title)
        
        updated = nm.get_current_config()
        self.assertEqual(updated["default_notebook_id"], test_id)
        self.assertEqual(updated["default_notebook_title"], test_title)
        
        # Restore original config
        nm.save_config(orig)


if __name__ == "__main__":
    unittest.main()
