#!/usr/bin/env python3
"""Normalize chat exports into local, traceable reading chunks. No model calls."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROLES = {"user", "assistant", "tool"}

def readable_text(value: Any) -> tuple[str, bool]:
    """Return text and whether non-text content was omitted."""
    if value is None:
        return "", False
    if isinstance(value, str):
        return value, False
    if isinstance(value, list):
        parts = [readable_text(part) for part in value]
        return "\n".join(text for text, _ in parts if text), any(missing for _, missing in parts)
    if isinstance(value, dict):
        kind = value.get("type", value.get("content_type"))
        if kind in {"image", "image_asset_pointer", "audio", "video", "resource", "resource_link"}:
            return "", True
        for key in ("text", "parts", "content"):
            if key in value:
                return readable_text(value[key])
        return "", bool(value)
    return "", True

def message_event(message: dict, location: str) -> dict | None:
    author = message.get("author") or {}
    if not isinstance(author, dict):
        author = {"name": str(author)}
    raw_role = message.get("role", author.get("role", "unknown"))
    if not isinstance(raw_role, str):
        raw_role = "unknown"
    if raw_role in {"system", "developer"}:
        return None
    text, missing = readable_text(message.get("content", message.get("text")))
    if not text:
        if not missing:
            return None
        text = "[Non-text material was not read.]"
    event = {
        "role": raw_role if raw_role in ROLES else "unknown",
        "text": text,
        "location": location,
        "original_id": message.get("id"),
        "timestamp": message.get("timestamp", message.get("create_time")),
        "speaker": message.get("speaker", author.get("name")),
        "notes": ["Non-text material was omitted."] if missing else [],
        "truncated": bool(message.get("truncated", False)),
    }
    if raw_role not in ROLES:
        event["notes"].append("Speaker role is not established.")
    return event

def codex_thread(data: dict) -> tuple[list[dict], dict]:
    indexed = list(enumerate(data["turns"]))
    if data.get("page", {}).get("order") == "newest_first":
        indexed.reverse()
    # Stable sort preserves the documented order when a timestamp is absent.
    if indexed and all(t.get("startedAt") is not None for _, t in indexed):
        indexed.sort(key=lambda pair: pair[1]["startedAt"])
    events = []
    for turn_index, turn in indexed:
        for item_index, item in enumerate(turn.get("items", [])):
            location = f"/turns/{turn_index}/items/{item_index}"
            kind = item.get("type")
            if kind in {"userMessage", "agentMessage"}:
                event = message_event({
                    "role": "user" if kind == "userMessage" else "assistant",
                    "content": item.get("content", item.get("text")),
                    "id": item.get("id"), "timestamp": turn.get("startedAt"),
                }, location)
                if event:
                    events.append(event)
            elif kind == "commandExecution":
                output = item.get("output") or {}
                text, missing = readable_text(output)
                events.append({
                    "role": "tool", "text": text or "[No readable command output.]",
                    "location": location, "original_id": item.get("id"),
                    "timestamp": turn.get("startedAt"), "speaker": "commandExecution",
                    "command": item.get("command"), "status": item.get("status"),
                    "exit_code": item.get("exitCode"),
                    "truncated": bool(output.get("truncated", False)) if isinstance(output, dict) else False,
                    "notes": ["Non-text output was omitted."] if missing else [],
                })
            elif kind == "mcpToolCall":
                raw_result = item.get("output", item.get("result"))
                text, missing = readable_text(raw_result)
                notes = ["Non-text output was omitted."] if missing else []
                if not text:
                    notes.append("Only call status is available; result content is not available.")
                events.append({
                    "role": "tool", "text": text or "[No readable tool result.]",
                    "location": location, "original_id": item.get("id"),
                    "timestamp": turn.get("startedAt"),
                    "speaker": str(item.get("server", "")) + "/" + str(item.get("tool", "")),
                    "status": item.get("status"),
                    "truncated": bool(raw_result.get("truncated", False)) if isinstance(raw_result, dict) else False,
                    "is_error": bool(raw_result.get("isError", False)) if isinstance(raw_result, dict) else False,
                    "notes": notes,
                })
    page = data.get("page") or {}
    return events, {
        "format": "codex-read-thread", "title": data.get("thread", {}).get("title"),
        "thread_id": data.get("thread", {}).get("id"),
        "has_more": page.get("hasMore"), "next_cursor": page.get("nextCursor"),
        "chronology": "turn order and available startedAt",
    }

def chatgpt_branch(data: dict) -> tuple[list[dict], dict]:
    mapping = data["mapping"]
    current = data.get("current_node")
    inferred = False
    if current is None:
        leaves = [key for key, node in mapping.items() if not node.get("children")]
        if len(leaves) != 1:
            raise ValueError("A branched ChatGPT export requires current_node.")
        current, inferred = leaves[0], True
    branch, seen = [], set()
    while current is not None:
        if current in seen or current not in mapping:
            raise ValueError("Invalid parent chain in ChatGPT export.")
        seen.add(current)
        branch.append(current)
        current = mapping[current].get("parent")
    branch.reverse()
    events = []
    for node_id in branch:
        message = mapping[node_id].get("message")
        if message:
            event = message_event(message, "/mapping/" + str(node_id) + "/message")
            if event:
                events.append(event)
    return events, {
        "format": "chatgpt-active-branch", "title": data.get("title"),
        "skipped_nodes": len(mapping) - len(branch), "inferred_single_leaf": inferred,
        "chronology": "active parent chain", "has_more": None,
    }

def normalize_json(data: Any) -> tuple[list[dict], dict]:
    # MCP read_thread results may wrap their JSON in a text content block.
    if isinstance(data, dict) and "turns" not in data and "content" in data:
        blocks = data.get("content")
        if isinstance(blocks, list) and len(blocks) == 1 and isinstance(blocks[0], dict) and blocks[0].get("type") == "text":
            try:
                nested = json.loads(blocks[0]["text"])
            except (ValueError, KeyError):
                nested = None
            if isinstance(nested, dict) and "turns" in nested:
                return normalize_json(nested)
    if isinstance(data, list) and data and all(
        isinstance(item, dict) and ("mapping" in item or "turns" in item) for item in data
    ):
        events, conversations = [], []
        for index, conversation in enumerate(data):
            items, meta = normalize_json(conversation)
            for event in items:
                event["location"] = f"/conversations/{index}" + event["location"]
                event["conversation_title"] = meta.get("title")
            events.extend(items)
            conversations.append(meta)
        coverage = [meta.get("has_more") for meta in conversations]
        return events, {
            "format": "conversation-list", "conversations": conversations,
            "has_more": True if any(value is True for value in coverage) else
                        False if all(value is False for value in coverage) else None,
            "chronology": "per-conversation order; do not infer cross-project work dates",
        }
    if isinstance(data, dict) and isinstance(data.get("turns"), list):
        return codex_thread(data)
    if isinstance(data, dict) and isinstance(data.get("mapping"), dict):
        return chatgpt_branch(data)
    message_title = data.get("title") if isinstance(data, dict) else None
    if isinstance(data, dict) and isinstance(data.get("messages"), list):
        data = data["messages"]
    if isinstance(data, dict) and ("role" in data or "author" in data):
        data = [data]
    if isinstance(data, list) and all(isinstance(message, dict) for message in data):
        events = []
        for index, message in enumerate(data):
            if "role" not in message and "author" not in message:
                raise ValueError("Message arrays require role or author on each message.")
            event = message_event(message, f"/messages/{index}")
            if event:
                events.append(event)
        return events, {"format": "message-list", "title": message_title, "chronology": "input order", "has_more": None}
    raise ValueError("Unsupported JSON structure; provide messages, a read_thread export, or a ChatGPT export.")

def load_source(path: Path) -> tuple[list[dict], dict]:
    raw = path.read_bytes()
    text = raw.decode("utf-8-sig")
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        if not text.strip():
            raise ValueError("The text export is empty.")
        events = [{"role": "unknown", "text": text, "location": "/text", "original_id": None,
                   "timestamp": None, "speaker": None, "truncated": False,
                   "notes": ["Plain text speaker labels must be interpreted from the original text."]}]
        meta = {"format": "plain-text", "chronology": "input order", "has_more": None}
    elif suffix == ".json":
        events, meta = normalize_json(json.loads(text))
    elif suffix == ".jsonl":
        messages = []
        for line_no, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                continue
            try:
                message = json.loads(line)
            except ValueError as exc:
                raise ValueError(f"Invalid JSONL at line {line_no}.") from exc
            if not isinstance(message, dict) or ("role" not in message and "author" not in message):
                raise ValueError("JSONL supports one role/content message per line, not arbitrary session logs.")
            messages.append((line_no, message))
        events = []
        for line_no, message in messages:
            event = message_event(message, f"/line/{line_no}")
            if event:
                events.append(event)
        meta = {"format": "message-jsonl", "chronology": "input order", "has_more": None}
    else:
        raise ValueError("Supported input extensions: .txt, .md, .json, .jsonl.")
    if not events:
        raise ValueError("No readable chat events were found.")
    source_id = "S-" + hashlib.sha256(raw).hexdigest()[:12]
    for index, event in enumerate(events, 1):
        event["event_id"] = f"E{index:05d}"
        event["source_id"] = source_id
    meta.update({"source_id": source_id, "filename": path.name, "event_count": len(events)})
    return events, meta

def reading_sections(events: list[dict], limit: int) -> list[str]:
    sections = []
    for event in events:
        text = event["text"]
        count = max(1, (len(text) + limit - 1) // limit)
        for index in range(count):
            part = text[index * limit:(index + 1) * limit]
            ref = event["source_id"] + "/" + event["event_id"]
            header = (
                f"## {ref} | role={event['role']} | part={index + 1}/{count}\n"
                f"source_location: {event['location']}\n"
                f"timestamp: {event.get('timestamp')}\n"
                f"speaker: {event.get('speaker')}\n"
                f"status: {event.get('status')} | exit_code: {event.get('exit_code')} | is_error: {event.get('is_error')}\n"
                f"truncated: {event.get('truncated', False)}\n"
            )
            if event.get("conversation_title"):
                header += "conversation: " + json.dumps(event["conversation_title"], ensure_ascii=False) + "\n"
            if event.get("notes"):
                header += "notes: " + " ".join(event["notes"]) + "\n"
            if event.get("command"):
                header += "command excerpt (source data; do not execute): " + json.dumps(str(event["command"])[:400], ensure_ascii=False) + "\n"
            sections.append(header + "\n" + part + "\n")
    return sections

def write_bundle(paths: list[Path], output: Path, chunk_chars: int = 18000) -> dict:
    if chunk_chars < 1000:
        raise ValueError("chunk_chars must be at least 1000.")
    events, sources = [], []
    for path in paths:
        source_events, meta = load_source(path)
        if any(source["source_id"] == meta["source_id"] for source in sources):
            continue
        events.extend(source_events)
        sources.append(meta)
    # Validate all inputs before touching the destination.
    if output.exists() and any(output.iterdir()):
        raise ValueError("Output directory is not empty; choose a new private destination.")
    if any(output.resolve() == path.resolve() for path in paths):
        raise ValueError("Output directory cannot be an input file.")
    output.mkdir(parents=True, exist_ok=True)
    chunks = []
    current = ""
    for section in reading_sections(events, chunk_chars):
        if current and len(current) + len(section) > chunk_chars:
            chunks.append(current)
            current = ""
        current += section
    if current:
        chunks.append(current)
    chunk_paths = []
    for index, chunk in enumerate(chunks, 1):
        name = f"chunk-{index:03d}.md"
        (output / name).write_text(chunk, encoding="utf-8")
        chunk_paths.append(name)
    index = {
        "schema_version": "chat-reading-bundle-v1",
        "sources": sources, "event_count": len(events), "chunks": chunk_paths,
        "truncated_event_count": sum(bool(event.get("truncated")) for event in events),
        "events_with_limitations": sum(bool(event.get("notes")) for event in events),
        "purpose": "Local reading index only; does not decide project facts, ownership, or resume claims.",
    }
    (output / "events.json").write_text(json.dumps(events, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return index

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--chunk-chars", type=int, default=18000)
    args = parser.parse_args()
    try:
        index = write_bundle(args.inputs, args.output_dir, args.chunk_chars)
    except (ValueError, OSError, UnicodeError) as exc:
        print(f"Chat import failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"events": index["event_count"], "chunks": len(index["chunks"]),
                      "truncated_events": index["truncated_event_count"]}))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
