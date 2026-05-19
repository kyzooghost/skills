#!/usr/bin/env python3
"""Parse coding assistant session JSONL files and extract structured metadata.

Usage:
    python3 parse_sessions.py --sessions-dir DIR [--output FILE] [--max-sessions N]

Outputs a JSON file with aggregated session data suitable for LLM analysis.
Supports Claude Code JSONL format (each line is a JSON message with type/message/timestamp).
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path


LANGUAGE_MAP = {
    ".ts": "TypeScript", ".tsx": "TypeScript",
    ".js": "JavaScript", ".jsx": "JavaScript",
    ".py": "Python", ".rb": "Ruby", ".go": "Go",
    ".rs": "Rust", ".java": "Java", ".md": "Markdown",
    ".json": "JSON", ".yaml": "YAML", ".yml": "YAML",
    ".sh": "Shell", ".css": "CSS", ".html": "HTML",
    ".kt": "Kotlin", ".swift": "Swift", ".c": "C",
    ".cpp": "C++", ".cs": "C#", ".php": "PHP",
}


def find_default_sessions_dir():
    """Attempt to find a default sessions directory. Returns None if not found."""
    candidates = [
        os.path.join(os.environ.get("CLAUDE_CONFIG_DIR", ""), "projects"),
        os.path.expanduser("~/.claude/projects"),
    ]
    for candidate in candidates:
        if candidate and os.path.isdir(candidate):
            return candidate
    return None


def load_jsonl(path):
    """Load a JSONL file, returning list of parsed JSON objects."""
    entries = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except (OSError, IOError):
        pass
    return entries


def extract_session_metadata(messages):
    """Extract metadata from a list of session messages."""
    tool_counts = defaultdict(int)
    languages = defaultdict(int)
    git_commits = 0
    git_pushes = 0
    input_tokens = 0
    output_tokens = 0
    user_msg_count = 0
    assistant_msg_count = 0
    user_interruptions = 0
    tool_errors = 0
    lines_added = 0
    lines_removed = 0
    files_modified = set()
    message_hours = []
    user_message_timestamps = []
    first_prompt = ""
    uses_task_agent = False
    uses_mcp = False

    for msg in messages:
        msg_type = msg.get("type")
        timestamp = msg.get("timestamp")

        if msg_type == "assistant" and msg.get("message"):
            assistant_msg_count += 1
            usage = msg["message"].get("usage", {})
            input_tokens += usage.get("input_tokens", 0)
            output_tokens += usage.get("output_tokens", 0)

            content = msg["message"].get("content", [])
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        name = block.get("name", "")
                        tool_counts[name] += 1

                        if name in ("Agent", "Task"):
                            uses_task_agent = True
                        if name.startswith("mcp__"):
                            uses_mcp = True

                        inp = block.get("input", {})
                        if isinstance(inp, dict):
                            file_path = inp.get("file_path", "")
                            if file_path:
                                ext = os.path.splitext(file_path)[1].lower()
                                lang = LANGUAGE_MAP.get(ext)
                                if lang:
                                    languages[lang] += 1
                                if name in ("Edit", "Write"):
                                    files_modified.add(file_path)

                            if name == "Write":
                                content_str = inp.get("content", "")
                                if content_str:
                                    lines_added += content_str.count("\n") + 1

                            command = inp.get("command", "")
                            if "git commit" in command:
                                git_commits += 1
                            if "git push" in command:
                                git_pushes += 1

        elif msg_type == "user" and msg.get("message"):
            content = msg["message"].get("content", "")
            has_text = False

            if isinstance(content, str) and content.strip():
                has_text = True
                if not first_prompt:
                    first_prompt = content[:200]
                if "[Request interrupted by user" in content:
                    user_interruptions += 1
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text" and block.get("text", "").strip():
                            has_text = True
                            if not first_prompt:
                                first_prompt = block["text"][:200]
                            if "[Request interrupted by user" in block.get("text", ""):
                                user_interruptions += 1
                        if block.get("type") == "tool_result" and block.get("is_error"):
                            tool_errors += 1

            if has_text:
                user_msg_count += 1
                if timestamp:
                    user_message_timestamps.append(timestamp)
                    try:
                        hour = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).hour
                        message_hours.append(hour)
                    except (ValueError, TypeError):
                        pass

    return {
        "tool_counts": dict(tool_counts),
        "languages": dict(languages),
        "git_commits": git_commits,
        "git_pushes": git_pushes,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "user_message_count": user_msg_count,
        "assistant_message_count": assistant_msg_count,
        "user_interruptions": user_interruptions,
        "tool_errors": tool_errors,
        "lines_added": lines_added,
        "lines_removed": lines_removed,
        "files_modified": len(files_modified),
        "message_hours": message_hours,
        "user_message_timestamps": user_message_timestamps,
        "first_prompt": first_prompt,
        "uses_task_agent": uses_task_agent,
        "uses_mcp": uses_mcp,
    }


def process_session_file(path):
    """Process a single session JSONL file and return session metadata."""
    entries = load_jsonl(path)
    if not entries:
        return None

    # Filter to transcript messages (user/assistant)
    messages = [e for e in entries if e.get("type") in ("user", "assistant")]
    if len(messages) < 2:
        return None

    # Determine timestamps
    timestamps = []
    for e in entries:
        ts = e.get("timestamp")
        if ts:
            timestamps.append(ts)

    if not timestamps:
        return None

    timestamps.sort()
    start_time = timestamps[0]
    end_time = timestamps[-1]

    try:
        start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        duration_minutes = max(1, int((end_dt - start_dt).total_seconds() / 60))
    except (ValueError, TypeError):
        duration_minutes = 0

    meta = extract_session_metadata(messages)

    # Extract session ID from filename
    session_id = Path(path).stem

    # Extract project path from directory structure
    project_path = str(Path(path).parent)

    return {
        "session_id": session_id,
        "project_path": project_path,
        "start_time": start_time,
        "duration_minutes": duration_minutes,
        **meta,
    }


def find_session_files(sessions_dir, max_sessions=200):
    """Find all session JSONL files, sorted by modification time (newest first)."""
    session_files = []
    sessions_path = Path(sessions_dir)

    if not sessions_path.exists():
        return []

    for project_dir in sessions_path.iterdir():
        if not project_dir.is_dir():
            continue
        for f in project_dir.iterdir():
            if f.suffix == ".jsonl" and not f.name.startswith("."):
                try:
                    stat = f.stat()
                    session_files.append((f, stat.st_mtime, stat.st_size))
                except OSError:
                    continue

    # Sort by modification time, newest first
    session_files.sort(key=lambda x: x[1], reverse=True)
    return [(str(f), size) for f, _, size in session_files[:max_sessions]]


def aggregate_sessions(sessions):
    """Aggregate metadata across all sessions."""
    agg = {
        "total_sessions": len(sessions),
        "date_range": {"start": "", "end": ""},
        "total_messages": 0,
        "total_duration_hours": 0,
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "tool_counts": defaultdict(int),
        "languages": defaultdict(int),
        "git_commits": 0,
        "git_pushes": 0,
        "projects": defaultdict(int),
        "total_interruptions": 0,
        "total_tool_errors": 0,
        "total_lines_added": 0,
        "total_lines_removed": 0,
        "total_files_modified": 0,
        "days_active": 0,
        "messages_per_day": 0,
        "message_hours": [],
        "session_summaries": [],
    }

    start_times = []

    for s in sessions:
        start_times.append(s["start_time"])
        agg["total_messages"] += s["user_message_count"]
        agg["total_duration_hours"] += s["duration_minutes"] / 60
        agg["total_input_tokens"] += s["input_tokens"]
        agg["total_output_tokens"] += s["output_tokens"]
        agg["git_commits"] += s["git_commits"]
        agg["git_pushes"] += s["git_pushes"]
        agg["total_interruptions"] += s["user_interruptions"]
        agg["total_tool_errors"] += s["tool_errors"]
        agg["total_lines_added"] += s["lines_added"]
        agg["total_lines_removed"] += s["lines_removed"]
        agg["total_files_modified"] += s["files_modified"]
        agg["message_hours"].extend(s["message_hours"])

        for tool, count in s["tool_counts"].items():
            agg["tool_counts"][tool] += count
        for lang, count in s["languages"].items():
            agg["languages"][lang] += count
        agg["projects"][s["project_path"]] += 1

        if len(agg["session_summaries"]) < 50:
            agg["session_summaries"].append({
                "id": s["session_id"][:8],
                "date": s["start_time"].split("T")[0] if "T" in s["start_time"] else "",
                "first_prompt": s["first_prompt"][:100],
                "duration_min": s["duration_minutes"],
                "messages": s["user_message_count"],
            })

    if start_times:
        start_times.sort()
        agg["date_range"]["start"] = start_times[0].split("T")[0] if "T" in start_times[0] else start_times[0]
        agg["date_range"]["end"] = start_times[-1].split("T")[0] if "T" in start_times[-1] else start_times[-1]

    days = set(t.split("T")[0] for t in start_times if "T" in t)
    agg["days_active"] = len(days)
    if agg["days_active"] > 0:
        agg["messages_per_day"] = round(agg["total_messages"] / agg["days_active"], 1)

    # Convert defaultdicts to regular dicts for JSON serialization
    agg["tool_counts"] = dict(sorted(agg["tool_counts"].items(), key=lambda x: x[1], reverse=True))
    agg["languages"] = dict(sorted(agg["languages"].items(), key=lambda x: x[1], reverse=True))
    agg["projects"] = dict(sorted(agg["projects"].items(), key=lambda x: x[1], reverse=True))
    agg["total_duration_hours"] = round(agg["total_duration_hours"], 1)

    return agg


def main():
    parser = argparse.ArgumentParser(description="Parse coding assistant session logs for insights analysis")
    parser.add_argument("--sessions-dir", required=False, default=None,
                        help="Path to sessions directory containing JSONL files (auto-detects if omitted)")
    parser.add_argument("--output", "-o", default=None,
                        help="Output JSON file path (default: stdout)")
    parser.add_argument("--max-sessions", type=int, default=200,
                        help="Maximum number of sessions to analyze (default: 200)")
    args = parser.parse_args()

    sessions_dir = args.sessions_dir or find_default_sessions_dir()

    if not sessions_dir or not os.path.isdir(sessions_dir):
        print("Error: Sessions directory not found.", file=sys.stderr)
        print("Provide --sessions-dir pointing to the directory containing session JSONL files.", file=sys.stderr)
        print("For Claude Code, this is typically ~/.claude/projects/", file=sys.stderr)
        sys.exit(1)

    print(f"Scanning sessions in: {sessions_dir}", file=sys.stderr)
    session_files = find_session_files(sessions_dir, args.max_sessions)
    print(f"Found {len(session_files)} session files", file=sys.stderr)

    sessions = []
    for path, size in session_files:
        # Skip very large files (>50MB) to avoid memory issues
        if size > 50_000_000:
            continue
        meta = process_session_file(path)
        if meta and meta["user_message_count"] >= 2 and meta["duration_minutes"] >= 1:
            sessions.append(meta)

    print(f"Processed {len(sessions)} valid sessions", file=sys.stderr)

    aggregated = aggregate_sessions(sessions)
    aggregated["individual_sessions"] = sessions[:50]  # Include top 50 for per-session analysis

    output = json.dumps(aggregated, indent=2, default=str)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Written to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
