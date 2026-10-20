#!/usr/bin/env python3
"""Local project evidence hub: capture, grounded milestones, search and export.

Python 3.10+, standard library only. No network, model calls or background service.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import tempfile

import import_chat

SCHEMA_VERSION = 1
KINDS = {"决策", "实现", "验证", "交付", "问题", "计划", "修正"}
STATUSES = {"待确认", "已确认", "计划", "不采用"}
BLOCKED = {".git", ".ssh", ".aws", "node_modules", ".venv", "__pycache__"}
ID_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,99}$")


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def redact(text):
    # Best-effort minimization, not a claim that arbitrary documents are public-safe.
    text = re.sub(r"(?im)((?:api[_-]?key|access[_-]?token|password|secret)\s*[:=]\s*)[^\r\n]+",
                  r"\1[REDACTED]", text)
    text = re.sub(r"\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9_]{20,})\b", "[REDACTED]", text)
    return re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[EMAIL]", text)


def atomic_write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                     prefix=path.name + ".", suffix=".tmp", delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(text)
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def database(path, create=False):
    path = Path(path)
    if not create and not path.is_file():
        raise ValueError("Hub database does not exist; collect sources first.")
    if create:
        path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    try:
        version = con.execute("PRAGMA user_version").fetchone()[0]
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if version not in {0, SCHEMA_VERSION} or (version == 0 and tables):
            raise ValueError("Not an empty database or a supported project-hub schema.")
        con.execute("PRAGMA foreign_keys=ON")
        if version == 0:
            if not create:
                raise ValueError("Hub database has not been initialized.")
            con.executescript("""
                CREATE TABLE projects(id TEXT PRIMARY KEY, name TEXT NOT NULL, root TEXT NOT NULL);
                CREATE TABLE snapshots(id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
                    source_key TEXT NOT NULL, kind TEXT NOT NULL, origin TEXT NOT NULL,
                    content TEXT NOT NULL, metadata TEXT NOT NULL, observed_at TEXT NOT NULL);
                CREATE TABLE sources(source_key TEXT PRIMARY KEY, snapshot_id TEXT NOT NULL REFERENCES snapshots(id),
                    project_id TEXT NOT NULL REFERENCES projects(id), kind TEXT NOT NULL, active INTEGER NOT NULL);
                CREATE TABLE milestones(id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
                    payload TEXT NOT NULL, revision INTEGER NOT NULL, updated_at TEXT NOT NULL,
                    superseded_by TEXT REFERENCES milestones(id));
                CREATE TABLE milestone_history(id TEXT NOT NULL REFERENCES milestones(id), revision INTEGER NOT NULL,
                    payload TEXT NOT NULL, updated_at TEXT NOT NULL, PRIMARY KEY(id,revision));
                CREATE TABLE runs(id INTEGER PRIMARY KEY, observed_at TEXT NOT NULL, report TEXT NOT NULL);
                PRAGMA user_version=1;
            """)
        yield con
    finally:
        con.close()


def read_config(path):
    path = Path(path).resolve()
    config = json.loads(path.read_text(encoding="utf-8-sig"))
    projects = config.get("projects") if isinstance(config, dict) else None
    if not isinstance(projects, list) or not projects:
        raise ValueError("Configuration requires a nonempty projects list.")
    seen = set()
    for project in projects:
        if not isinstance(project, dict) or not ID_PATTERN.fullmatch(str(project.get("id", ""))):
            raise ValueError("Each project needs a stable alphanumeric id.")
        if project["id"] in seen:
            raise ValueError("Duplicate project id.")
        seen.add(project["id"])
        if not isinstance(project.get("root"), str) or not project["root"]:
            raise ValueError("Each project needs a root directory.")
        project["root"] = str((path.parent / project["root"]).resolve())
        project.setdefault("name", project["id"])
        for field in ("documents", "chats"):
            project.setdefault(field, [])
            if not isinstance(project[field], list):
                raise ValueError(f"{field} must be a list of relative patterns.")
            for pattern in project[field]:
                if not isinstance(pattern, str) or Path(pattern).is_absolute() or ".." in Path(pattern).parts:
                    raise ValueError("Source patterns must stay within the project root.")
        if not isinstance(project.get("git", False), bool):
            raise ValueError("git must be true or false.")
    for key, default in (("max_file_bytes", 98304), ("max_files_per_project", 30), ("git_limit", 30)):
        config.setdefault(key, default)
        if type(config[key]) is not int or not 1 <= config[key] <= (10_000_000 if key == "max_file_bytes" else 500):
            raise ValueError(f"Invalid {key} limit.")
    if config.get("git_since"):
        date.fromisoformat(config["git_since"])
    return config


def eligible(root, file):
    resolved = file.resolve()
    if not resolved.is_relative_to(root) or file.is_symlink() or not file.is_file():
        return False
    parts = file.relative_to(root).parts
    return not any(p.lower() in BLOCKED or p.lower().startswith(".env") for p in parts)


def snapshot(con, project, kind, key, origin, content, metadata):
    source_key = f"{project['id']}:{kind}:{key}"
    identity = digest(source_key + "\0" + content + "\0" + canonical(metadata))
    sid = "S-" + identity[:24]
    added = con.execute("INSERT OR IGNORE INTO snapshots VALUES(?,?,?,?,?,?,?,?)", (
        sid, project["id"], source_key, kind, origin, redact(content), canonical(metadata), now(),
    )).rowcount
    con.execute("INSERT INTO sources VALUES(?,?,?,?,1) ON CONFLICT(source_key) DO UPDATE SET "
                "snapshot_id=excluded.snapshot_id,active=1", (source_key, sid, project["id"], kind))
    return sid, added


def git_records(root, config):
    # The root was explicitly selected in local config. Trust it only for this read,
    # without changing the user's global Git configuration.
    command = ["git", "-c", "safe.directory=" + str(root), "-C", str(root), "--no-pager", "log", f"-n{config['git_limit']}",
               "--format=%H%x00%aI%x00%s%x00%b%x00"]
    if config.get("git_since"):
        command.append("--since=" + config["git_since"])
    result = subprocess.run(command, capture_output=True, timeout=30, check=False)
    if result.returncode:
        raise ValueError("Git history unavailable (not a repository, ownership restriction, or unreadable HEAD).")
    fields = result.stdout.decode("utf-8", errors="replace").split("\0")
    for offset in range(0, len(fields) - 3, 4):
        sha, stamp, subject, body = fields[offset:offset + 4]
        sha = sha.strip()
        if not re.fullmatch(r"[0-9a-f]{40,64}", sha):
            raise ValueError("Invalid Git log record.")
        yield sha, f"commit: {sha}\ndate: {stamp}\nsubject: {subject}\n\n{body}", {"commit": sha, "date": stamp}


def collect(config_path, db_path, bundle_path):
    config = read_config(config_path)
    report = {"observed_at": now(), "new_snapshots": 0, "projects": [],
              "boundary": "Selected text and bounded Git history only; documents and commits do not prove personal contribution or live acceptance."}
    with database(db_path, create=True) as con, con:
        for project in config["projects"]:
            root = Path(project["root"])
            coverage = {"id": project["id"], "snapshots": [], "warnings": [], "files_read": 0}
            report["projects"].append(coverage)
            con.execute("INSERT INTO projects VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,root=excluded.root",
                        (project["id"], project["name"], str(root)))
            if not root.is_dir():
                con.execute("UPDATE sources SET active=0 WHERE project_id=? AND kind!='git'", (project["id"],))
                coverage["warnings"].append("Project root is unavailable; previous snapshots retained.")
                continue
            # Disable prior text sources only when a project's directory was actually accessible.
            con.execute("UPDATE sources SET active=0 WHERE project_id=? AND kind!='git'", (project["id"],))
            seen = set()
            for field in ("documents", "chats"):
                for pattern in project[field]:
                    matched = False
                    for file in sorted(root.glob(pattern)):
                        if not eligible(root, file):
                            coverage["warnings"].append(f"Skipped unsafe or non-file path: {file.relative_to(root)}")
                            continue
                        matched = True
                        rel = file.relative_to(root).as_posix()
                        if rel in seen:
                            continue
                        seen.add(rel)
                        if coverage["files_read"] >= config["max_files_per_project"]:
                            coverage["warnings"].append("File count limit reached; remaining files were not read.")
                            break
                        try:
                            if field == "chats":
                                if file.stat().st_size > config["max_file_bytes"]:
                                    raise ValueError("Chat export exceeds configured size; split with import_chat first.")
                                events, meta = import_chat.load_source(file)
                                lines = []
                                for event in events:
                                    lines.append(f"[{event['event_id']} role={event['role']} location={event['location']}]\n"
                                                 + event["text"] + "\nmetadata: " + canonical({
                                                     k: v for k, v in event.items() if k != "text"}) + "\n")
                                content = "\n".join(lines)
                                meta["limitations"] = sum(bool(e.get("notes") or e.get("truncated")) for e in events)
                            else:
                                if file.suffix.lower() not in {".md", ".txt"}:
                                    raise ValueError("Unsupported document type; use a text extraction first.")
                                with file.open("rb") as stream:
                                    raw = stream.read(config["max_file_bytes"] + 1)
                                truncated = len(raw) > config["max_file_bytes"]
                                content = raw[:config["max_file_bytes"]].decode("utf-8-sig", errors="replace")
                                meta = {"truncated": truncated, "date": None,
                                        "date_boundary": "File modification time is not a project milestone date."}
                                if "\ufffd" in content:
                                    meta["decoding_warning"] = "Invalid UTF-8 bytes were replaced; interpret this source cautiously."
                                    coverage["warnings"].append(f"UTF-8 replacement characters: {rel}")
                                if truncated:
                                    coverage["warnings"].append(f"Truncated text: {rel}")
                            sid, added = snapshot(con, project, "chat" if field == "chats" else "document",
                                                  rel, str(file), content, meta)
                            coverage["files_read"] += 1
                            coverage["snapshots"].append(sid)
                            report["new_snapshots"] += added
                        except (OSError, ValueError, UnicodeError) as exc:
                            coverage["warnings"].append(f"Not read: {rel}: {exc}")
                    if not matched:
                        coverage["warnings"].append(f"No readable source matched: {pattern}")
            if project.get("git"):
                try:
                    for sha, content, meta in git_records(root, config):
                        sid, added = snapshot(con, project, "git", sha, str(root) + "@" + sha, content, meta)
                        coverage["snapshots"].append(sid)
                        report["new_snapshots"] += added
                    coverage["warnings"].append("Git history is bounded by git_limit/git_since; authorship is not personal ownership evidence.")
                except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
                    coverage["warnings"].append(str(exc))
        con.execute("INSERT INTO runs(observed_at,report) VALUES(?,?)", (report["observed_at"], canonical(report)))
    write_reading_bundle(db_path, bundle_path, report)
    return report


def write_reading_bundle(db_path, bundle_path, report):
    bundle = Path(bundle_path)
    bundle.mkdir(parents=True, exist_ok=True)
    ids = {sid for project in report["projects"] for sid in project["snapshots"]}
    with database(db_path) as con:
        sources = [dict(row) for row in con.execute("SELECT * FROM snapshots ORDER BY project_id,observed_at,id") if row["id"] in ids]
    for source in sources:
        numbered = "\n".join(f"{i:04d}: {line}" for i, line in enumerate(source["content"].splitlines(), 1))
        atomic_write(bundle / (source["id"] + ".md"),
                     f"# {source['id']}\nproject: {source['project_id']}\nkind: {source['kind']}\n"
                     f"origin: {source['origin']}\nmetadata: {source['metadata']}\n\n{numbered}\n")
    atomic_write(bundle / "index.json", json.dumps({"report": report, "sources": [
        {k: source[k] for k in ("id", "project_id", "kind", "origin", "metadata")} for source in sources
    ]}, ensure_ascii=False, indent=2) + "\n")


def validate_nodes(con, payload):
    if not isinstance(payload, dict) or payload.get("schema_version") != "project-milestones-v1":
        raise ValueError("Expected project-milestones-v1 JSON.")
    nodes = payload.get("milestones")
    if not isinstance(nodes, list) or not nodes:
        raise ValueError("milestones must be a nonempty list.")
    projects = {row[0] for row in con.execute("SELECT id FROM projects")}
    current = {row["id"]: dict(row) for row in con.execute("SELECT * FROM milestones")}
    validated, seen = [], set()
    required = {"id", "project_id", "title", "summary", "evidence"}
    allowed = required | {"date", "kind", "stage", "ownership", "verification", "status", "supersedes"}
    for raw in nodes:
        if not isinstance(raw, dict) or not required.issubset(raw) or set(raw) - allowed:
            raise ValueError("Invalid milestone fields.")
        node = dict(raw)
        mid = node["id"]
        if not isinstance(mid, str) or not ID_PATTERN.fullmatch(mid) or mid in seen:
            raise ValueError("Invalid or duplicate milestone id.")
        seen.add(mid)
        if node["project_id"] not in projects:
            raise ValueError("Unknown milestone project.")
        if mid in current and current[mid]["project_id"] != node["project_id"]:
            raise ValueError("A stable milestone id cannot change project.")
        for field, maximum in (("title", 180), ("summary", 3000)):
            if not isinstance(node[field], str) or not node[field].strip() or len(node[field]) > maximum:
                raise ValueError(f"Invalid {field}.")
        node.setdefault("date", None)
        if node["date"] is not None:
            if not isinstance(node["date"], str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", node["date"]):
                raise ValueError("Milestone date must be YYYY-MM-DD or null.")
            date.fromisoformat(node["date"])
        node.setdefault("kind", "实现")
        node.setdefault("status", "待确认")
        if node["kind"] not in KINDS or node["status"] not in STATUSES:
            raise ValueError("Invalid milestone kind or status.")
        for field, default in (("stage", "材料记载，阶段待核对"), ("ownership", "个人归属未确认"),
                               ("verification", "仅材料记载，本轮未重跑")):
            node.setdefault(field, default)
            if not isinstance(node[field], str) or not node[field].strip() or len(node[field]) > 2000:
                raise ValueError(f"Invalid {field}.")
        if node["status"] == "已确认" and (node["ownership"] == "个人归属未确认" or
                                           node["verification"] == "仅材料记载，本轮未重跑"):
            raise ValueError("Confirmed claims require explicit ownership and verification scope.")
        refs = node["evidence"]
        if not isinstance(refs, list) or not refs:
            raise ValueError("Every milestone requires captured evidence.")
        for ref in refs:
            if not isinstance(ref, dict) or set(ref) != {"snapshot_id", "start_line", "end_line"}:
                raise ValueError("Evidence requires snapshot_id, start_line, end_line.")
            source = con.execute("SELECT * FROM snapshots WHERE id=?", (ref["snapshot_id"],)).fetchone()
            if source is None or source["project_id"] != node["project_id"]:
                raise ValueError("Evidence is missing or belongs to another project.")
            a, b = ref["start_line"], ref["end_line"]
            if type(a) is not int or type(b) is not int or not 1 <= a <= b <= len(source["content"].splitlines()):
                raise ValueError("Evidence line range is outside the stored snapshot.")
        node.setdefault("supersedes", [])
        if not isinstance(node["supersedes"], list) or len(set(node["supersedes"])) != len(node["supersedes"]):
            raise ValueError("supersedes must be a list of unique earlier milestone ids.")
        for prior in node["supersedes"]:
            if prior not in current or current[prior]["project_id"] != node["project_id"] or prior == mid:
                raise ValueError("Supersession requires a distinct existing milestone of the same project.")
            if current[prior]["superseded_by"] not in {None, mid}:
                raise ValueError("Earlier milestone already has another successor.")
        if mid in current:
            old = json.loads(current[mid]["payload"])
            if old.get("supersedes", []) != node["supersedes"]:
                raise ValueError("Supersession links are immutable; add another correction node.")
        validated.append(node)
    # Evaluate all proposed edges together; reject conflicting targets and cycles atomically.
    edges = {key: row["superseded_by"] for key, row in current.items()}
    targets = set()
    for node in validated:
        for prior in node["supersedes"]:
            if prior in targets:
                raise ValueError("Two incoming milestones supersede the same earlier node.")
            targets.add(prior)
            edges[prior] = node["id"]
    for start in edges:
        chain = set()
        at = start
        while at:
            if at in chain:
                raise ValueError("Cyclic supersession.")
            chain.add(at)
            at = edges.get(at)
    return validated


def import_milestones(db_path, input_path):
    payload = json.loads(Path(input_path).read_text(encoding="utf-8-sig"))
    changed = 0
    with database(db_path) as con, con:
        nodes = validate_nodes(con, payload)
        for node in nodes:
            text = canonical(node)
            old = con.execute("SELECT * FROM milestones WHERE id=?", (node["id"],)).fetchone()
            if old is not None and old["payload"] == text:
                continue
            revision = old["revision"] + 1 if old else 1
            stamp = now()
            con.execute("INSERT INTO milestones(id,project_id,payload,revision,updated_at) VALUES(?,?,?,?,?) "
                        "ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,revision=excluded.revision,updated_at=excluded.updated_at",
                        (node["id"], node["project_id"], text, revision, stamp))
            con.execute("INSERT INTO milestone_history VALUES(?,?,?,?)", (node["id"], revision, text, stamp))
            changed += 1
        for node in nodes:
            for prior in node["supersedes"]:
                con.execute("UPDATE milestones SET superseded_by=? WHERE id=?", (node["id"], prior))
    return {"imported_or_updated": changed, "unchanged": len(nodes) - changed}


def hub_data(db_path):
    with database(db_path) as con:
        projects = [dict(row) for row in con.execute("SELECT * FROM projects ORDER BY name")]
        snapshots = {row["id"]: dict(row) for row in con.execute("SELECT * FROM snapshots")}
        current = {row["source_key"]: dict(row) for row in con.execute("SELECT * FROM sources")}
        nodes = []
        for row in con.execute("SELECT * FROM milestones"):
            node = json.loads(row["payload"])
            node.update(revision=row["revision"], updated_at=row["updated_at"], superseded_by=row["superseded_by"])
            details = []
            stale = False
            for ref in node["evidence"]:
                source = snapshots[ref["snapshot_id"]]
                latest = current[source["source_key"]]
                outdated = not latest["active"] or latest["snapshot_id"] != source["id"]
                stale |= outdated
                lines = source["content"].splitlines()[ref["start_line"] - 1:ref["end_line"]]
                details.append({**ref, "kind": source["kind"], "origin": source["origin"],
                                "excerpt": "\n".join(lines), "outdated": outdated,
                                "metadata": json.loads(source["metadata"])})
            node["evidence"] = details
            node["needs_review"] = stale
            nodes.append(node)
        nodes.sort(key=lambda item: (item["date"] or "", item["id"]), reverse=True)
        last_run = con.execute("SELECT report FROM runs ORDER BY id DESC LIMIT 1").fetchone()
        return {"schema_version": "project-hub-export-v1", "generated_at": now(), "projects": projects,
                "milestones": nodes, "snapshot_count": len(snapshots),
                "last_collection": json.loads(last_run[0]) if last_run else None}


def table_cell(value):
    return str(value).replace("|", "\\|").replace("\r", " ").replace("\n", "<br>")


def export_hub(db_path, output_path):
    data = hub_data(db_path)
    output = Path(output_path)
    template = Path(__file__).resolve().parent.parent / "assets/project-hub.html"
    embedded = json.dumps(data, ensure_ascii=False).replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
    embedded = embedded.replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    html = template.read_text(encoding="utf-8").replace("__PROJECT_HUB_DATA__", embedded)
    atomic_write(output / "index.html", html)
    atomic_write(output / "hub.json", json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    names = {p["id"]: p["name"] for p in data["projects"]}
    context = ["# 项目关键节点素材", "", "以下是来源材料支持的项目记录；个人职责与未确认事实不可自动升级为简历成果。", ""]
    ledger = ["# 素材库事实账本（私有）", "", "沿用素材库节点 ID；正式简历只采用已确认、允许公开且未失效的事实。", "",
              "| 稳定 ID / 项目 | 原始事实 | 来源 / 位置 / 日期 / 版本 | 本人动作与团队边界 | 验证范围 / 实际结果 | 候选表述 / 适用岗位 | 表述状态 | 指标口径 / 冲突 / 公开范围 | 能回答的追问 |",
              "|---|---|---|---|---|---|---|---|---|"]
    for node in data["milestones"]:
        if node["superseded_by"] or node["status"] == "不采用":
            continue
        status = "待确认" if node["needs_review"] else node["status"]
        if node["kind"] == "计划":
            # Confirming that a plan exists must not turn it into completed work.
            status = "计划"
        refs = "; ".join(f"{r['snapshot_id']}:L{r['start_line']}-L{r['end_line']}" for r in node["evidence"])
        context.extend([f"## {names[node['project_id']]} · {node['title']}",
                        f"- ID：{node['id']}；事件日期：{node['date'] or '未确认'}；性质：{node['kind']}；表述状态：{status}",
                        f"- 关键进展：{node['summary']}", f"- 阶段：{node['stage']}",
                        f"- 个人边界：{node['ownership']}", f"- 验证范围：{node['verification']}",
                        f"- 来源：{refs}", f"- 来源更新待复核：{'是' if node['needs_review'] else '否'}", ""])
        ledger.append("| " + " | ".join(table_cell(value) for value in [
            node["id"] + " / " + names[node["project_id"]], node["summary"], refs + " / " + (node["date"] or "日期未知"),
            node["ownership"], node["stage"] + " / " + node["verification"], "待按目标 JD 提炼", status,
            "私有材料；公开前核对；" + ("来源已变化" if node["needs_review"] else "来源已定位"), "依据现有机制与验证范围准备",
        ]) + " |")
    atomic_write(output / "resume-context.md", "\n".join(context))
    atomic_write(output / "claim-ledger.md", "\n".join(ledger) + "\n")
    return {"projects": len(data["projects"]), "milestones": len(data["milestones"]), "snapshots": data["snapshot_count"],
            "dashboard": str((output / "index.html").resolve())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    capture = commands.add_parser("collect", help="Capture selected sources; does not infer resume facts.")
    capture.add_argument("--config", type=Path, required=True)
    capture.add_argument("--db", type=Path, required=True)
    capture.add_argument("--bundle", type=Path, required=True)
    ingest = commands.add_parser("import", help="Store source-grounded milestone JSON after semantic review.")
    ingest.add_argument("--db", type=Path, required=True)
    ingest.add_argument("--input", type=Path, required=True)
    export = commands.add_parser("export", help="Write a local searchable page and resume source material.")
    export.add_argument("--db", type=Path, required=True)
    export.add_argument("--output", type=Path, required=True)
    search = commands.add_parser("search", help="Search milestones; no external requests.")
    search.add_argument("--db", type=Path, required=True)
    search.add_argument("--query", required=True)
    search.add_argument("--project")
    args = parser.parse_args()
    try:
        if args.command == "collect":
            report = collect(args.config, args.db, args.bundle)
            result = {"new_snapshots": report["new_snapshots"], "projects": [
                {"id": p["id"], "snapshots": len(p["snapshots"]), "warnings": p["warnings"]} for p in report["projects"]]}
        elif args.command == "import":
            result = import_milestones(args.db, args.input)
        elif args.command == "export":
            result = export_hub(args.db, args.output)
        else:
            data = hub_data(args.db)
            result = [node for node in data["milestones"] if not node["superseded_by"] and
                      (not args.project or node["project_id"] == args.project) and
                      args.query.casefold() in canonical(node).casefold()]
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, TypeError, KeyError, OSError, sqlite3.Error) as exc:
        print(f"Project hub failed: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
