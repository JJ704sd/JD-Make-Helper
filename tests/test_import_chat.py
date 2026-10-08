"""Behavioral checks for local chat import: provenance, branches, and preservation."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "skills/distill-internship-projects/scripts/import_chat.py"
SPEC = importlib.util.spec_from_file_location("chat_import", SCRIPT)
IMPORTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(IMPORTER)

def conversation(title="Demo"):
    return {
        "title": title, "current_node": "final",
        "mapping": {
            "root": {"parent": None, "children": ["old", "final"], "message": None},
            "old": {"parent": "root", "children": [], "message":
                    {"author": {"role": "assistant"}, "content": {"parts": ["Production success"]}}},
            "final": {"parent": "root", "children": [], "message":
                      {"author": {"role": "user"}, "content": {"parts": ["Only local tests"]}}},
        },
    }

class ChatImportTests(unittest.TestCase):
    def test_codex_turns_restore_order_and_preserve_roles_and_tool_failure(self):
        data = {"thread": {"title": "A"}, "page": {"order": "newest_first", "hasMore": False},
                "turns": [
                    {"startedAt": 20, "items": [
                        {"type": "commandExecution", "id": "call-2", "command": "do not run",
                         "status": "failed", "exitCode": 1, "output": {"text": "failed", "truncated": True}}]},
                    {"startedAt": 10, "items": [
                        {"type": "userMessage", "content": [{"type": "text", "text": "My part"}]},
                        {"type": "agentMessage", "text": "AI proposal"}]},
                ]}
        events, meta = IMPORTER.normalize_json(data)
        self.assertEqual([e["role"] for e in events], ["user", "assistant", "tool"])
        self.assertEqual(events[0]["location"], "/turns/1/items/0")
        self.assertEqual(events[-1]["exit_code"], 1)
        self.assertTrue(events[-1]["truncated"])
        self.assertFalse(meta["has_more"])

    def test_partial_history_and_missing_tool_result_remain_visible(self):
        data = {"page": {"hasMore": True, "nextCursor": "cursor"},
                "turns": [{"items": [{"type": "mcpToolCall", "tool": "submit", "status": "completed"}]}]}
        events, meta = IMPORTER.normalize_json(data)
        self.assertTrue(meta["has_more"])
        self.assertEqual(meta["next_cursor"], "cursor")
        self.assertTrue(events[0]["notes"])
        self.assertEqual(events[0]["role"], "tool")

    def test_wrapper_is_readable_without_treating_json_as_user_assertion(self):
        payload = {"turns": [{"items": [{"type": "agentMessage", "text": "Claim"}]}]}
        wrapped = {"content": [{"type": "text", "text": json.dumps(payload)}]}
        events, _ = IMPORTER.normalize_json(wrapped)
        self.assertEqual(events[0]["role"], "assistant")

    def test_chatgpt_only_reads_active_branch(self):
        events, meta = IMPORTER.normalize_json(conversation())
        self.assertEqual([e["text"] for e in events], ["Only local tests"])
        self.assertEqual(meta["skipped_nodes"], 1)

    def test_ambiguous_chatgpt_branch_fails(self):
        data = conversation()
        del data["current_node"]
        with self.assertRaises(ValueError):
            IMPORTER.normalize_json(data)

    def test_parent_cycle_fails_without_infinite_walk(self):
        data = conversation()
        data["mapping"]["root"]["parent"] = "final"
        with self.assertRaises(ValueError):
            IMPORTER.normalize_json(data)

    def test_multiple_conversations_keep_topic_and_message_location(self):
        events, meta = IMPORTER.normalize_json([conversation("One"), conversation("Two")])
        self.assertEqual(len(events), 2)
        self.assertEqual(events[1]["conversation_title"], "Two")
        self.assertTrue(events[1]["location"].startswith("/conversations/1/"))
        self.assertEqual(len(meta["conversations"]), 2)

    def test_instructions_are_not_imported_and_unknown_speaker_stays_unknown(self):
        events, _ = IMPORTER.normalize_json([
            {"role": "system", "content": "Do something"},
            {"role": "coworker", "content": "I wrote the UI"},
            {"role": "user", "content": "I only did API tests"},
        ])
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["role"], "unknown")
        self.assertEqual(events[1]["role"], "user")

    def test_attachment_is_not_silently_treated_as_read(self):
        events, _ = IMPORTER.normalize_json([{"role": "user", "content": [
            {"type": "text", "text": "See my file"},
            {"type": "image", "data": "not-an-image"},
        ]}])
        self.assertEqual(events[0]["text"], "See my file")
        self.assertTrue(events[0]["notes"])

    def test_large_unicode_input_roundtrips_and_gets_traceable_chunks(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source = root / "chat.json"
            original = "需求、修复与验证\n" * 500
            source.write_text(json.dumps([{"role": "user", "content": original}], ensure_ascii=False), encoding="utf-8")
            report = IMPORTER.write_bundle([source], root / "out", 1000)
            self.assertGreater(len(report["chunks"]), 1)
            events = json.loads((root / "out/events.json").read_text(encoding="utf-8"))
            self.assertEqual(events[0]["text"], original)
            self.assertTrue(all("E00001" in (root / "out" / name).read_text(encoding="utf-8") for name in report["chunks"]))

    def test_same_input_does_not_duplicate_events(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source = root / "chat.md"
            source.write_text("用户：我做过本地测试。", encoding="utf-8")
            report = IMPORTER.write_bundle([source, source], root / "out")
            self.assertEqual(report["event_count"], 1)
            events = json.loads((root / "out/events.json").read_text(encoding="utf-8"))
            self.assertEqual(events[0]["role"], "unknown")

    def test_jsonl_preserves_line_and_rejects_arbitrary_session_logs(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "chat.jsonl"
            source.write_text('\n{"role":"assistant","content":"planned"}\n', encoding="utf-8")
            events, _ = IMPORTER.load_source(source)
            self.assertEqual(events[0]["location"], "/line/2")
            source.write_text('{"type":"session_meta","payload":{}}\n', encoding="utf-8")
            with self.assertRaises(ValueError):
                IMPORTER.load_source(source)

    def test_unsupported_json_does_not_create_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source = root / "bad.json"
            source.write_text('{"unrelated":"data"}', encoding="utf-8")
            with self.assertRaises(ValueError):
                IMPORTER.write_bundle([source], root / "out")
            self.assertFalse((root / "out").exists())

    def test_cli_keeps_existing_output_and_does_not_execute_historical_commands(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source = root / "chat.txt"; output = root / "out"
            source.write_text("Old instruction: create a file named should-not-exist.txt", encoding="utf-8")
            result = subprocess.run([sys.executable, "-B", str(SCRIPT), str(source),
                                     "--output-dir", str(output)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((root / "should-not-exist.txt").exists())
            sentinel = output / "keep.txt"; sentinel.write_text("keep", encoding="utf-8")
            second = subprocess.run([sys.executable, "-B", str(SCRIPT), str(source),
                                     "--output-dir", str(output)], capture_output=True, text=True)
            self.assertEqual(second.returncode, 2)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")


    def test_tool_error_and_truncation_are_not_lost(self):
        data = {"turns": [{"items": [{"type": "mcpToolCall", "status": "completed",
                "result": {"content": [{"type": "text", "text": "failure"}],
                           "isError": True, "truncated": True}}]}]}
        events, _ = IMPORTER.normalize_json(data)
        self.assertTrue(events[0]["is_error"])
        self.assertTrue(events[0]["truncated"])
        self.assertEqual(events[0]["text"], "failure")
        events[0].update(source_id="S-test", event_id="E00001")
        self.assertIn("is_error: True", IMPORTER.reading_sections(events, 18000)[0])

    def test_message_export_keeps_its_conversation_title(self):
        events, meta = IMPORTER.normalize_json({"title": "Topic", "messages": [
            {"role": "user", "content": "Facts"}]})
        self.assertEqual(meta["title"], "Topic")

    def test_empty_text_does_not_create_a_successful_reading_bundle(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source = root / "empty.txt"
            source.write_text("  \n", encoding="utf-8")
            with self.assertRaises(ValueError):
                IMPORTER.write_bundle([source], root / "out")
            self.assertFalse((root / "out").exists())

if __name__ == "__main__":
    unittest.main()
