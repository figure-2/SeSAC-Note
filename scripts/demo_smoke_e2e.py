"""Local mock E2E smoke test for SeSAC:Note demo mode."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


BASE_URL = os.getenv("DEMO_E2E_BASE_URL", "http://localhost:8080").rstrip("/")
VIDEO_ID = os.getenv("DEMO_E2E_VIDEO_ID", "demo-video-001")


def _request(method: str, path: str, body: dict | None = None) -> tuple[int, str]:
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(f"{BASE_URL}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            return res.status, res.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")


def _json(method: str, path: str, body: dict | None = None) -> dict:
    status, raw = _request(method, path, body)
    if status < 200 or status >= 300:
        raise AssertionError(f"{method} {path} failed: HTTP {status} {raw}")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"{method} {path} returned non-JSON: {raw}") from exc


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    health = _json("GET", "/health")
    _assert(health.get("status") == "ok", "health status is not ok")

    videos = _json("GET", "/api/videos")
    _assert(any(v.get("id") == VIDEO_ID for v in videos.get("videos", [])), "demo video missing")

    status = _json("GET", f"/videos/{VIDEO_ID}/status")
    _assert(status.get("video_status") == "DONE", "demo video is not DONE")

    progress = _json("GET", f"/videos/{VIDEO_ID}/progress")
    _assert(progress.get("progress_percent") == 100, "progress is not 100")

    summaries = _json("GET", f"/videos/{VIDEO_ID}/summaries")
    _assert(summaries.get("count", 0) >= 3, "summaries count is too small")
    first = summaries["items"][0]
    source_refs = first.get("source_refs") or {}
    stt_ids = ",".join(source_refs.get("stt_ids") or [])
    cap_ids = ",".join(source_refs.get("cap_ids") or [])

    evidence_path = f"/videos/{VIDEO_ID}/evidence?{urllib.parse.urlencode({'stt_ids': stt_ids, 'cap_ids': cap_ids})}"
    evidence = _json("GET", evidence_path)
    _assert(len(evidence.get("stt", [])) >= 1, "STT evidence missing")
    _assert(len(evidence.get("vlm", [])) >= 1, "VLM evidence missing")

    process = _json("POST", "/process", {"video_id": VIDEO_ID, "sync_to_db": True})
    _assert(process.get("status") == "started", "process did not start in demo mode")

    chat = _json(
        "POST",
        "/api/chat",
        {"video_id": VIDEO_ID, "message": "Retriever 역할은 뭐야?", "reasoning_mode": "flash"},
    )
    _assert("Retriever" in chat.get("response", ""), "chat response does not mention Retriever")

    print("DEMO E2E SMOKE PASS")
    print(f"base_url={BASE_URL}")
    print(f"video_id={VIDEO_ID}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"DEMO E2E SMOKE FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
