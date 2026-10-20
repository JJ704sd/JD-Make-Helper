"""Exercise the public local hub workflow against real files and SQLite."""
import importlib.util
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/distill-internship-projects/scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("project_hub", SCRIPTS / "project_hub.py")
hub = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(hub)


class ProjectHubTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / "project"
        self.project.mkdir()
        (self.project / "progress.md").write_text("# Progress\nLocal tests passed.\nProduction not verified.\n", encoding="utf-8")
        self.db = self.root / "private/hub.sqlite3"
        self.config = self.root / "sources.json"
        self.bundle = self.root / "reading"
        self.settings = {"projects": [{"id": "p", "name": "Project P", "root": str(self.project),
                                       "documents": ["progress.md"], "git": False}]}
        self.write_config()

    def write_config(self):
        self.config.write_text(json.dumps(self.settings), encoding="utf-8")

    def collect(self):
        self.write_config()
        return hub.collect(self.config, self.db, self.bundle)

    def node(self, mid="p-local-check"):
        sid = self.collect()["projects"][0]["snapshots"][0]
        return {"id": mid, "project_id": "p", "title": "Local validation", "summary": "Local tests recorded; production is unknown.",
                "kind": "验证", "evidence": [{"snapshot_id": sid, "start_line": 2, "end_line": 3}]}

    def ingest(self, nodes):
        file = self.root / "nodes.json"
        file.write_text(json.dumps({"schema_version": "project-milestones-v1", "milestones": nodes}, ensure_ascii=False), encoding="utf-8")
        return hub.import_milestones(self.db, file)

    def test_repeated_capture_is_idempotent_and_unknown_date_is_not_mtime(self):
        self.assertEqual(self.collect()["new_snapshots"], 1)
        self.assertEqual(self.collect()["new_snapshots"], 0)
        index = json.loads((self.bundle / "index.json").read_text(encoding="utf-8"))
        self.assertIsNone(json.loads(index["sources"][0]["metadata"])["date"])

    def test_document_revision_preserves_evidence_and_flags_review(self):
        node = self.node()
        node.update(status="已确认", ownership="User confirmed only local test execution", verification="Historical synthetic local run")
        self.ingest([node])
        (self.project / "progress.md").write_text("# Correction\nEarlier result withdrawn.\n", encoding="utf-8")
        self.assertEqual(self.collect()["new_snapshots"], 1)
        item = hub.hub_data(self.db)["milestones"][0]
        self.assertTrue(item["needs_review"])
        self.assertIn("Local tests passed", item["evidence"][0]["excerpt"])
        out = self.root / "export"
        hub.export_hub(self.db, out)
        self.assertIn("待确认", (out / "claim-ledger.md").read_text(encoding="utf-8"))

    def test_missing_document_is_explicit_and_old_snapshot_remains(self):
        self.ingest([self.node()])
        (self.project / "progress.md").unlink()
        report = self.collect()
        self.assertTrue(report["projects"][0]["warnings"])
        self.assertTrue(hub.hub_data(self.db)["milestones"][0]["needs_review"])

    def test_partial_capture_keeps_other_project_and_reports_missing_root(self):
        self.settings["projects"].append({"id": "missing", "root": str(self.root / "absent"), "documents": ["a.md"]})
        report = self.collect()
        self.assertEqual(report["new_snapshots"], 1)
        self.assertIn("unavailable", report["projects"][1]["warnings"][0])

    def test_unavailable_project_root_invalidates_freshness_without_deleting_evidence(self):
        self.ingest([self.node()])
        self.project.rename(self.root / "moved-project")
        self.collect()
        node = hub.hub_data(self.db)["milestones"][0]
        self.assertTrue(node["needs_review"])
        self.assertIn("Local tests passed", node["evidence"][0]["excerpt"])

    def test_invalid_reference_rolls_back_entire_import(self):
        good = self.node()
        bad = json.loads(json.dumps(good)); bad["id"] = "bad"; bad["evidence"][0]["end_line"] = 999
        with self.assertRaises(ValueError):
            self.ingest([good, bad])
        self.assertEqual(hub.hub_data(self.db)["milestones"], [])

    def test_cross_project_reference_and_duplicate_ids_are_rejected(self):
        node = self.node()
        self.settings["projects"].append({"id": "other", "root": str(self.project), "documents": []})
        self.collect()
        bad = dict(node, project_id="other")
        with self.assertRaises(ValueError):
            self.ingest([bad])
        with self.assertRaises(ValueError):
            self.ingest([node, node])

    def test_no_evidence_or_implicit_confirmation_cannot_be_imported(self):
        node = self.node()
        for bad in (dict(node, evidence=[]), dict(node, status="已确认"), dict(node, date="2026-02-30")):
            with self.assertRaises(ValueError):
                self.ingest([bad])

    def test_stable_node_updates_keep_revision_history_and_reimport_is_noop(self):
        node = self.node()
        self.assertEqual(self.ingest([node])["imported_or_updated"], 1)
        self.assertEqual(self.ingest([node])["unchanged"], 1)
        node["summary"] = "Correction: only one local sample was checked."
        self.ingest([node])
        with closing(sqlite3.connect(self.db)) as con:
            self.assertEqual(con.execute("SELECT count(*) FROM milestone_history").fetchone()[0], 2)
        self.assertEqual(hub.hub_data(self.db)["milestones"][0]["revision"], 2)

    def test_confirming_a_plan_does_not_export_a_completed_resume_claim(self):
        node = self.node()
        node.update(kind="计划", status="已确认", ownership="User confirmed the plan only", verification="A proposal, not completed work")
        self.ingest([node])
        hub.export_hub(self.db, self.root / "export")
        ledger = (self.root / "export/claim-ledger.md").read_text(encoding="utf-8")
        self.assertIn("| 计划 |", ledger)
        self.assertIn("表述状态：计划", (self.root / "export/resume-context.md").read_text(encoding="utf-8"))

    def test_supersession_preserves_old_node_and_excludes_it_from_resume_context(self):
        old = self.node("old"); old["summary"] = "OLD-SENTINEL"
        self.ingest([old])
        new = self.node("new"); new.update(supersedes=["old"], kind="修正")
        self.ingest([new])
        items = {n["id"]: n for n in hub.hub_data(self.db)["milestones"]}
        self.assertEqual(items["old"]["superseded_by"], "new")
        hub.export_hub(self.db, self.root / "export")
        self.assertNotIn("OLD-SENTINEL", (self.root / "export/resume-context.md").read_text(encoding="utf-8"))

    def test_supersession_cycle_is_rejected_without_changing_prior_links(self):
        self.ingest([self.node("a"), self.node("b")])
        a = self.node("a"); a["supersedes"] = ["b"]
        b = self.node("b"); b["supersedes"] = ["a"]
        with self.assertRaises(ValueError):
            self.ingest([a, b])
        self.assertTrue(all(n["superseded_by"] is None for n in hub.hub_data(self.db)["milestones"]))

    def test_limits_and_unsupported_types_are_reported(self):
        self.settings.update(max_file_bytes=12, max_files_per_project=1)
        self.settings["projects"][0]["documents"] = ["progress.md", "another.md", "binary.pdf"]
        (self.project / "another.md").write_text("More", encoding="utf-8")
        (self.project / "binary.pdf").write_bytes(b"%PDF")
        report = self.collect()
        warnings = " ".join(report["projects"][0]["warnings"])
        self.assertIn("Truncated", warnings)
        self.assertIn("limit", warnings)

    def test_path_escape_and_secret_files_are_not_read(self):
        self.settings["projects"][0]["documents"] = ["../secret.md"]
        with self.assertRaises(ValueError):
            self.collect()
        self.assertFalse(self.db.exists())
        self.settings["projects"][0]["documents"] = [".env.md", "progress.md"]
        (self.project / ".env.md").write_text("SENSITIVE", encoding="utf-8")
        self.assertEqual(self.collect()["new_snapshots"], 1)

    def test_external_symlink_is_skipped(self):
        outside = self.root / "outside.md"; outside.write_text("SECRET", encoding="utf-8")
        try:
            (self.project / "link.md").symlink_to(outside)
        except OSError:
            self.skipTest("Symlinks unavailable for this account")
        self.settings["projects"][0]["documents"] = ["link.md"]
        self.assertEqual(self.collect()["new_snapshots"], 0)

    def test_tokens_are_minimized_and_script_injection_stays_data(self):
        (self.project / "progress.md").write_text('# Check\napi_key = not-for-export\n</script><script>window.INJECTED=1</script>\n', encoding="utf-8")
        node = self.node(); node["title"] = '</script><script>window.TITLE_INJECTION=1</script>'
        self.ingest([node])
        hub.export_hub(self.db, self.root / "export")
        text = (self.root / "export/index.html").read_text(encoding="utf-8")
        self.assertNotIn("not-for-export", text)
        self.assertNotIn('</script><script>window.', text)
        self.assertIn("\\u003c/script\\u003e", text)
        self.assertIn("[REDACTED]", text)

    def test_chat_roles_corrections_and_coverage_are_preserved(self):
        (self.project / "chat.json").write_text(json.dumps({"page": {"hasMore": True}, "turns": [{"items": [
            {"type": "agentMessage", "text": "Production success"},
            {"type": "userMessage", "text": "Correction: not deployed"}]}]}), encoding="utf-8")
        self.settings["projects"][0].update(documents=[], chats=["chat.json"])
        report = self.collect()
        with closing(sqlite3.connect(self.db)) as con:
            content, metadata = con.execute("SELECT content,metadata FROM snapshots").fetchone()
        self.assertIn("role=assistant", content)
        self.assertIn("role=user", content)
        self.assertIn("not deployed", content)
        self.assertTrue(json.loads(metadata)["has_more"])
        self.assertEqual(len(report["projects"][0]["snapshots"]), 1)

    def test_git_history_is_captured_without_modifying_repo_or_proving_ownership(self):
        def git(*args):
            return subprocess.run(["git", "-C", str(self.project), *args], check=True, capture_output=True)
        git("init", "-q")
        git("add", "progress.md")
        git("-c", "user.name=Synthetic", "-c", "user.email=synthetic@example.invalid", "commit", "-qm", "feat: local parser")
        before = git("status", "--porcelain").stdout
        self.settings["projects"][0].update(git=True, documents=[])
        report = self.collect()
        self.assertEqual(git("status", "--porcelain").stdout, before)
        self.assertEqual(report["new_snapshots"], 1)
        with closing(sqlite3.connect(self.db)) as con:
            content, metadata = con.execute("SELECT content,metadata FROM snapshots").fetchone()
        self.assertIn("feat: local parser", content)
        self.assertIn("commit", json.loads(metadata))
        self.assertNotIn("Synthetic", content)

    def test_unrelated_database_is_never_repurposed(self):
        self.db.parent.mkdir()
        with closing(sqlite3.connect(self.db)) as con:
            con.execute("CREATE TABLE business_records(value TEXT)")
        with self.assertRaises(ValueError):
            self.collect()
        with closing(sqlite3.connect(self.db)) as con:
            self.assertEqual(con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchone()[0], "business_records")

    def test_cli_workflow_and_search(self):
        node = self.node(); self.ingest([node])
        result = subprocess.run([sys.executable, "-X", "utf8", "-B", str(SCRIPTS / "project_hub.py"),
                                 "search", "--db", str(self.db), "--query", "production", "--project", "p"],
                                capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)[0]["id"], node["id"])


if __name__ == "__main__":
    unittest.main()
