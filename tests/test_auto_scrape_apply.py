"""Tests for auto_scrape_and_apply.py loop daemon and subsystems."""

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from auto_scrape_and_apply import (
    ApplyEngine,
    AutoScrapeApplyDaemon,
    FitEvaluator,
    StateManager,
    TRACKER_HEADER,
    derive_archive_name,
    escape_latex,
    parse_args,
    sanitize_filename,
)


class AutoScrapeApplyTests(unittest.TestCase):
    """Test suite for the automated 5-minute scrape and apply engine."""

    def test_derive_archive_name_matches_canonical_rule(self):
        """Archive name should be lowercase, single path component, no slashes."""
        self.assertEqual(
            derive_archive_name("Deloitte Canada", "Cyber & Digital Trust Co-op"),
            "deloitte_canada_cyber_digital_trust_coop",
        )
        self.assertEqual(
            derive_archive_name("Novo Nordisk A/S", "Systems Admin / DevOps"),
            "novo_nordisk_as_systems_admin_devops",
        )
        self.assertEqual(derive_archive_name("///", "---"), "unnamed_application")

    def test_sanitize_filename(self):
        """File name sanitizer should remove invalid characters and format underscores."""
        self.assertEqual(sanitize_filename("Deloitte (Canada) Inc."), "Deloitte_Canada_Inc")
        self.assertEqual(sanitize_filename("IT / SysAdmin Co-op"), "IT_SysAdmin_Co-op")

    def test_escape_latex(self):
        """Special LaTeX characters should be safely escaped."""
        raw = "C&A 100% $50 #1 _under {brace} \\path"
        escaped = escape_latex(raw)
        self.assertIn(r"\&", escaped)
        self.assertIn(r"\%", escaped)
        self.assertIn(r"\$", escaped)
        self.assertIn(r"\#", escaped)
        self.assertIn(r"\_", escaped)
        self.assertIn(r"\{", escaped)
        self.assertIn(r"\}", escaped)

    def test_fit_evaluator_scoring(self):
        """Test fit evaluation scoring and gates."""
        # High match test
        title = "Junior Systems Administrator Co-op (Winter 2027)"
        desc = "Seeking student for Linux administration, Active Directory, Cisco VLANs, and Docker troubleshooting."
        loc = "Toronto, ON"
        comp = "TechCorp"
        band, score, notes = FitEvaluator.evaluate_posting(title, desc, loc, comp)
        self.assertIn(band, ("high", "medium"))
        self.assertGreaterEqual(score, 70)
        self.assertIn("linux", notes.lower())

        # Excluded / Out of range test
        title_excl = "Principal Architect - 10+ years experience"
        desc_excl = "French essential, bilingual imperative"
        loc_excl = "Calgary, AB"
        band_excl, score_excl, _ = FitEvaluator.evaluate_posting(title_excl, desc_excl, loc_excl, "Firm")
        self.assertEqual(band_excl, "low")
        self.assertLess(score_excl, 50)

    def test_state_manager_dedup(self):
        """StateManager should detect previously seen or applied jobs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_seen = Path(tmpdir) / "seen_jobs.json"
            tmp_tracker = Path(tmpdir) / "tracker.csv"

            # Populate mock seen_jobs.json
            seen_content = {
                "seen": {
                    "job-123": {
                        "id": "job-123",
                        "title": "Systems Analyst",
                        "company": "RBC",
                        "url": "https://example.com/job-123",
                    }
                }
            }
            tmp_seen.write_text(json.dumps(seen_content), encoding="utf-8")

            # Populate mock tracker
            with open(tmp_tracker, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(TRACKER_HEADER.split(","))
                writer.writerow([
                    "2026-08-29", "TD Bank", "Banking", "IT Support", "Co-op", "portal",
                    "Drafted", "", "85", "Notes", "cv/main.pdf", "cover_letters/cover.pdf",
                    "https://example.com/td-job", "2026-09-30"
                ])

            with patch("auto_scrape_and_apply.SEEN_JOBS_FILE", tmp_seen), \
                 patch("auto_scrape_and_apply.TRACKER_FILE", tmp_tracker):
                state_mgr = StateManager()

                # Should detect already seen
                self.assertTrue(state_mgr.is_already_seen_or_applied("https://example.com/job-123", "RBC", "Systems Analyst", "job-123"))
                # Should detect already tracked
                self.assertTrue(state_mgr.is_already_seen_or_applied("https://example.com/td-job", "TD Bank", "IT Support"))
                # Should not flag a brand new job
                self.assertFalse(state_mgr.is_already_seen_or_applied("https://example.com/bmo-job", "BMO", "Network Specialist"))

    def test_apply_engine_latex_generation(self):
        """ApplyEngine should generate valid LaTeX mentioning Claude Code and candidate details."""
        state_mgr = MagicMock()
        apply_engine = ApplyEngine(state_mgr=state_mgr, dry_run=True)

        cv_tex = apply_engine.generate_cv_latex("Deloitte", "Cloud Systems Co-op", "Linux, Docker, AWS")
        cover_tex = apply_engine.generate_cover_letter_latex("Deloitte", "Cloud Systems Co-op", "Linux, Docker, AWS")

        # Grounding check
        self.assertIn("Deloitte", cv_tex)
        self.assertIn("Cloud Systems Co-op", cv_tex)

        # AI Tooling rule: cover letter must mention Claude Code
        self.assertIn("Claude Code", cover_tex)
        self.assertIn("Deloitte", cover_tex)
        self.assertIn("Cloud Systems Co-op", cover_tex)

    def test_daemon_filter_and_cycle(self):
        """Daemon should filter qualifying jobs and invoke apply workflow."""
        daemon = AutoScrapeApplyDaemon(
            interval=300,
            min_fit="medium",
            max_applies_per_cycle=2,
            once=True,
            dry_run=True,
        )

        mock_new_jobs = [
            {"id": "1", "company": "Co A", "title": "IT Co-op", "fit": "high", "fit_score": 90},
            {"id": "2", "company": "Co B", "title": "Linux Admin Co-op", "fit": "medium", "fit_score": 75},
            {"id": "3", "company": "Co C", "title": "Senior Arch", "fit": "low", "fit_score": 30},
        ]

        with patch.object(daemon.scraper, "run_scrape_cycle", return_value=mock_new_jobs), \
             patch.object(daemon.apply_engine, "apply_to_job", return_value=True) as mock_apply:

            scraped_count, applied_count = daemon.run_one_cycle()
            self.assertEqual(scraped_count, 3)
            # Only top 2 medium/high jobs should be applied to
            self.assertEqual(applied_count, 2)
            self.assertEqual(mock_apply.call_count, 2)


    def test_cli_parse_args(self):
        """CLI arguments should parse correctly."""
        with patch("sys.argv", ["auto_scrape_and_apply.py", "--interval", "180", "--once", "--dry-run", "--min-fit", "high", "--max-applies-per-cycle", "3", "--verbose"]):
            args = parse_args()
            self.assertEqual(args.interval, 180)
            self.assertTrue(args.once)
            self.assertTrue(args.dry_run)
            self.assertEqual(args.min_fit, "high")
            self.assertEqual(args.max_applies_per_cycle, 3)
            self.assertTrue(args.verbose)

    def test_state_manager_record_application_to_tracker(self):
        """StateManager should record a drafted application to tracker CSV."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_tracker = Path(tmpdir) / "tracker.csv"
            with patch("auto_scrape_and_apply.TRACKER_FILE", tmp_tracker):
                state_mgr = StateManager(dry_run=False)
                state_mgr.record_application_to_tracker(
                    company="IBM Canada",
                    role="Systems Specialist",
                    fit_score=90,
                    cv_pdf_path="cv/main_IBM_Systems.pdf",
                    cover_pdf_path="cover_letters/cover_IBM_Systems.pdf",
                    source_url="https://ibm.com/jobs/123",
                    deadline="2026-10-15",
                )

                self.assertTrue(tmp_tracker.exists())
                content = tmp_tracker.read_text(encoding="utf-8")
                self.assertIn("IBM Canada", content)
                self.assertIn("Systems Specialist", content)
    def test_live_latex_compilation_and_ats(self):
        """Test actual LaTeX compilation and ATS text extraction check."""
        state_mgr = MagicMock()
        apply_engine = ApplyEngine(state_mgr=state_mgr, dry_run=False)

        with tempfile.TemporaryDirectory() as tmpdir:
            test_cv_tex = Path(tmpdir) / "main_TestComp_TestRole.tex"
            test_cover_tex = Path(tmpdir) / "cover_TestComp_TestRole.tex"

            cv_content = apply_engine.generate_cv_latex("TestComp", "TestRole", "Linux administration, Active Directory")
            test_cv_tex.write_text(cv_content, encoding="utf-8")

            # Test compile CV
            ok = apply_engine.compile_cv(test_cv_tex)
            self.assertTrue(ok)
            pdf_path = test_cv_tex.with_suffix(".pdf")
            self.assertTrue(pdf_path.exists())
            self.assertGreater(pdf_path.stat().st_size, 1000)

            # Test ATS verification
            ats_ok = apply_engine.verify_pdf_ats(pdf_path)
            self.assertTrue(ats_ok)

            # Test aux cleanup
            apply_engine.cleanup_latex_aux(test_cv_tex)
            self.assertFalse(test_cv_tex.with_suffix(".aux").exists())
            self.assertFalse(test_cv_tex.with_suffix(".log").exists())


if __name__ == "__main__":
    unittest.main()


