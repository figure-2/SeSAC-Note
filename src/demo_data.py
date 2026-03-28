"""Deterministic demo data for local mock E2E runs.

This module is used only when SESAC_NOTE_DEMO_MODE is enabled. It avoids paid AI
APIs, Supabase, and object storage while preserving the API response shapes used
by the frontend.
"""

from __future__ import annotations

import os
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


DEMO_VIDEO_ID = "demo-video-001"
DEMO_USER_ID = "demo-user"
DEMO_CREATED_AT = "2026-06-14T00:00:00+09:00"
DEMO_ASSET_DIR = Path(__file__).resolve().parents[1] / "demo_assets"
DEMO_UPLOAD_DIR = DEMO_ASSET_DIR / "uploads"
DEMO_UPLOAD_MANIFEST = DEMO_UPLOAD_DIR / "demo_uploads.json"
LANGGRAPH_FALLBACK_VIDEO = DEMO_ASSET_DIR / "langgraph-academy-introduction-6min-demo.webm"

_demo_uploads: Dict[str, Dict[str, Any]] = {}


def is_demo_mode() -> bool:
    return os.getenv("SESAC_NOTE_DEMO_MODE", "").strip().lower() in {"1", "true", "yes", "on"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _save_demo_uploads() -> None:
    DEMO_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    serializable = {}
    for video_id, record in _demo_uploads.items():
        serializable[video_id] = {
            key: value
            for key, value in record.items()
            if key != "demo_pipeline_started_at"
        }
    DEMO_UPLOAD_MANIFEST.write_text(
        json.dumps(serializable, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _load_demo_uploads() -> None:
    if not DEMO_UPLOAD_MANIFEST.exists():
        return
    try:
        data = json.loads(DEMO_UPLOAD_MANIFEST.read_text(encoding="utf-8"))
    except Exception:
        return
    if not isinstance(data, dict):
        return
    for video_id, record in data.items():
        if not isinstance(record, dict):
            continue
        record["status"] = "DONE" if record.get("status") != "FAILED" else "FAILED"
        record["duration_sec"] = record.get("duration_sec") or 3300
        _demo_uploads[str(video_id)] = record


def _fallback_upload_record(video_id: str) -> Optional[Dict[str, Any]]:
    if not str(video_id).startswith("demo-upload-") or not LANGGRAPH_FALLBACK_VIDEO.exists():
        return None
    record = {
        "id": video_id,
        "user_id": DEMO_USER_ID,
        "name": LANGGRAPH_FALLBACK_VIDEO.stem,
        "original_filename": LANGGRAPH_FALLBACK_VIDEO.name,
        "status": "DONE",
        "duration_sec": 386,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "thumbnail_url": None,
        "video_storage_key": f"{video_id}/videos/{LANGGRAPH_FALLBACK_VIDEO.name}",
        "demo_upload_path": str(LANGGRAPH_FALLBACK_VIDEO),
        "current_preprocess_job_id": f"{video_id}-preprocess",
        "current_processing_job_id": f"{video_id}-processing",
    }
    _demo_uploads[video_id] = record
    return record


_load_demo_uploads()


def _base_video() -> Dict[str, Any]:
    return {
        "id": DEMO_VIDEO_ID,
        "user_id": DEMO_USER_ID,
        "name": "SeSAC:Note Demo Lecture",
        "original_filename": "sesac_note_demo.mp4",
        "status": "DONE",
        "duration_sec": 3300,
        "created_at": DEMO_CREATED_AT,
        "updated_at": DEMO_CREATED_AT,
        "thumbnail_url": None,
        "current_preprocess_job_id": "demo-preprocess-job-001",
        "current_processing_job_id": "demo-processing-job-001",
    }


def list_demo_videos() -> List[Dict[str, Any]]:
    videos = [_base_video()]
    for upload in _demo_uploads.values():
        videos.append(upload.copy())
    return sorted(videos, key=lambda row: row.get("created_at") or "", reverse=True)


def get_demo_video(video_id: str) -> Optional[Dict[str, Any]]:
    if video_id == DEMO_VIDEO_ID:
        return _base_video()
    video = _demo_uploads.get(video_id) or _fallback_upload_record(video_id)
    if video:
        _apply_demo_pipeline_state(video)
    return video.copy() if video else None


def create_demo_upload(filename: str) -> Dict[str, Any]:
    safe_name = filename or "demo-upload.mp4"
    video_id = f"demo-upload-{uuid.uuid4().hex[:8]}"
    video_name = safe_name.rsplit(".", 1)[0]
    storage_key = f"{video_id}/videos/{safe_name}"
    record = {
        "id": video_id,
        "user_id": DEMO_USER_ID,
        "name": video_name,
        "original_filename": safe_name,
        "status": "PREPROCESSING",
        "duration_sec": 0,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "thumbnail_url": None,
        "video_storage_key": storage_key,
        "demo_upload_path": str(DEMO_UPLOAD_DIR / f"{video_id}_{safe_name}"),
        "current_preprocess_job_id": f"{video_id}-preprocess",
        "current_processing_job_id": f"{video_id}-processing",
    }
    _demo_uploads[video_id] = record
    _save_demo_uploads()
    return {"video_id": video_id, "video_name": video_name, "storage_key": storage_key}


def get_demo_upload_save_path(video_id: str) -> str:
    record = _demo_uploads.get(video_id) or _fallback_upload_record(video_id)
    if not record:
        record = mark_demo_upload_received(video_id)
    path = record.get("demo_upload_path")
    if not path:
        path = str(DEMO_UPLOAD_DIR / f"{video_id}.webm")
        record["demo_upload_path"] = path
    DEMO_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    return path


def get_demo_video_file_path(video_id: str) -> Optional[str]:
    video = get_demo_video(video_id)
    if not video:
        return None
    path = video.get("demo_upload_path")
    if path and Path(path).exists():
        return str(path)
    if LANGGRAPH_FALLBACK_VIDEO.exists():
        return str(LANGGRAPH_FALLBACK_VIDEO)
    return None


def mark_demo_upload_received(video_id: str, size_bytes: int = 0) -> Dict[str, Any]:
    record = _demo_uploads.get(video_id)
    if not record:
        safe_name = f"{video_id}.webm"
        storage_key = f"{video_id}/videos/{safe_name}"
        record = {
            "id": video_id,
            "user_id": DEMO_USER_ID,
            "name": Path(safe_name).stem,
            "original_filename": safe_name,
            "status": "PREPROCESSING",
            "duration_sec": 0,
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
            "thumbnail_url": None,
            "video_storage_key": storage_key,
            "demo_upload_path": str(DEMO_UPLOAD_DIR / f"{video_id}_{safe_name}"),
            "current_preprocess_job_id": f"{video_id}-preprocess",
            "current_processing_job_id": f"{video_id}-processing",
        }
        _demo_uploads[video_id] = record
    record["uploaded_bytes"] = size_bytes
    record["updated_at"] = _now_iso()
    _save_demo_uploads()
    return record


def complete_demo_upload(video_id: str, storage_key: str) -> Dict[str, Any]:
    record = _demo_uploads.get(video_id)
    if not record:
        record = mark_demo_upload_received(video_id)
    record["video_storage_key"] = storage_key
    record["status"] = "PREPROCESSING"
    record["duration_sec"] = 3300
    record["demo_pipeline_started_at"] = time.monotonic()
    record["updated_at"] = _now_iso()
    _save_demo_uploads()
    return record


def _demo_pipeline_snapshot(record: Dict[str, Any]) -> Dict[str, Any]:
    started_at = record.get("demo_pipeline_started_at")
    if not started_at:
        return {
            "video_status": record.get("status") or "DONE",
            "preprocess_status": "DONE",
            "processing_status": "DONE",
            "progress_current": 5,
            "progress_total": 5,
            "summary_count": 3,
        }

    elapsed = max(0.0, time.monotonic() - float(started_at))
    if elapsed < 2:
        return {
            "video_status": "PREPROCESSING",
            "preprocess_status": "RUNNING",
            "processing_status": "WAITING",
            "progress_current": 0,
            "progress_total": 5,
            "summary_count": 0,
        }
    if elapsed < 4:
        return {
            "video_status": "PROCESSING",
            "preprocess_status": "DONE",
            "processing_status": "VLM_RUNNING",
            "progress_current": 1,
            "progress_total": 5,
            "summary_count": 0,
        }
    if elapsed < 6:
        return {
            "video_status": "PROCESSING",
            "preprocess_status": "DONE",
            "processing_status": "SUMMARY_RUNNING",
            "progress_current": 2,
            "progress_total": 5,
            "summary_count": 1,
        }
    if elapsed < 8:
        return {
            "video_status": "PROCESSING",
            "preprocess_status": "DONE",
            "processing_status": "JUDGE_RUNNING",
            "progress_current": 4,
            "progress_total": 5,
            "summary_count": 2,
        }
    return {
        "video_status": "DONE",
        "preprocess_status": "DONE",
        "processing_status": "DONE",
        "progress_current": 5,
        "progress_total": 5,
        "summary_count": 3,
    }


def _apply_demo_pipeline_state(record: Dict[str, Any]) -> Dict[str, Any]:
    snapshot = _demo_pipeline_snapshot(record)
    record["status"] = snapshot["video_status"]
    record["demo_pipeline_snapshot"] = snapshot
    record["updated_at"] = _now_iso()
    return snapshot


def delete_demo_video(video_id: str) -> bool:
    if video_id == DEMO_VIDEO_ID:
        return True
    return _demo_uploads.pop(video_id, None) is not None


def demo_status_payload(video_id: str) -> Optional[Dict[str, Any]]:
    video = get_demo_video(video_id)
    if not video:
        return None
    snapshot = video.get("demo_pipeline_snapshot") or _demo_pipeline_snapshot(video)
    return {
        "video_id": video_id,
        "video_name": video.get("name"),
        "video_status": snapshot["video_status"],
        "error_message": None,
        "preprocess_job": {
            "id": video.get("current_preprocess_job_id") or f"{video_id}-preprocess",
            "status": snapshot["preprocess_status"],
            "started_at": DEMO_CREATED_AT,
            "ended_at": DEMO_CREATED_AT if snapshot["preprocess_status"] == "DONE" else None,
        },
        "processing_job": {
            "id": video.get("current_processing_job_id") or f"{video_id}-processing",
            "status": snapshot["processing_status"],
            "progress_current": snapshot["progress_current"],
            "progress_total": snapshot["progress_total"],
            "started_at": DEMO_CREATED_AT,
            "ended_at": DEMO_CREATED_AT if snapshot["processing_status"] == "DONE" else None,
        },
        "pipeline_mode": "async",
    }


def demo_progress_payload(video_id: str) -> Optional[Dict[str, Any]]:
    video = get_demo_video(video_id)
    if not video:
        return None
    snapshot = video.get("demo_pipeline_snapshot") or _demo_pipeline_snapshot(video)
    total = snapshot["progress_total"] or 1
    current = snapshot["progress_current"] or 0
    return {
        "video_id": video_id,
        "has_processing_job": True,
        "processing_job_id": f"{video_id}-processing",
        "status": snapshot["processing_status"],
        "progress_current": current,
        "progress_total": total,
        "progress_percent": round((current / total) * 100, 1),
        "is_complete": snapshot["video_status"] in ("DONE", "FAILED"),
    }


def demo_summary_items(video_id: str) -> List[Dict[str, Any]]:
    video = get_demo_video(video_id)
    video_name = (video or {}).get("name", "").lower()
    if "langgraph" in video_name or "langgraph" in video_id.lower():
        return [
            {
                "summary_id": f"{video_id}-summary-001",
                "segment_id": f"{video_id}-seg-001",
                "segment_index": 1,
                "start_ms": 0,
                "end_ms": 130000,
                "source_refs": {"stt_ids": [f"{video_id}-stt-001"], "cap_ids": [f"{video_id}-cap-001"]},
                "summary": {
                    "bullets": [
                        {"bullet_id": "B1", "claim": "영상은 Kate 텍스트 편집기의 생산성 팁을 소개하며, 코드 편집 화면과 예제 파일을 함께 보여줍니다."},
                        {"bullet_id": "B2", "claim": "초반부에서는 편집기 화면 구성, 파일 탐색, 기본 편집 흐름처럼 사용자가 바로 따라 할 수 있는 작업 맥락을 제시합니다."},
                    ],
                    "definitions": [
                        {"term": "Kate", "definition": "KDE 환경에서 사용하는 텍스트/코드 편집기로, 파일 편집과 탐색 기능을 제공합니다."},
                        {"term": "구간별 근거", "definition": "현재 답변이 참조한 영상 시간, 화면 내용, 음성 설명을 함께 묶은 근거 단위입니다."},
                    ],
                    "explanations": [
                        {"point": "이 구간은 화면에 보이는 편집기와 제목 정보를 근거로 영상의 주제와 학습 목표를 파악하는 데 사용됩니다."}
                    ],
                    "open_questions": [
                        {"question": "사용자가 특정 기능을 질문하면 어느 시간 구간으로 되돌려 보여주는 것이 좋을까요?"}
                    ],
                },
                "created_at": DEMO_CREATED_AT,
            },
            {
                "summary_id": f"{video_id}-summary-002",
                "segment_id": f"{video_id}-seg-002",
                "segment_index": 2,
                "start_ms": 130000,
                "end_ms": 260000,
                "source_refs": {"stt_ids": [f"{video_id}-stt-002"], "cap_ids": [f"{video_id}-cap-002"]},
                "summary": {
                    "bullets": [
                        {"bullet_id": "B1", "claim": "중반부에서는 줄 편집, 검색/치환, 파일 이동처럼 반복 작업을 줄이는 편집기 기능을 중심으로 설명합니다."},
                        {"bullet_id": "B2", "claim": "화면에 표시되는 코드 조각과 편집 동작을 함께 봐야 기능의 사용 의도와 효과를 이해할 수 있습니다."},
                    ],
                    "definitions": [
                        {"term": "검색/치환", "definition": "문서 안의 특정 문자열을 찾고 필요한 경우 다른 문자열로 바꾸는 편집 기능입니다."},
                        {"term": "화면 근거", "definition": "STT 텍스트만으로는 부족한 코드 위치, UI 상태, 편집 결과를 설명하는 시각 정보입니다."},
                    ],
                    "explanations": [
                        {"point": "이 구간은 사용자가 '검색 기능은 어디서 설명했나요?'처럼 묻는 경우 관련 시간대를 찾아 답변하는 데 사용됩니다."}
                    ],
                    "open_questions": [
                        {"question": "STT에는 남지 않는 마우스 이동이나 메뉴 클릭은 어떤 방식으로 근거화할 수 있을까요?"}
                    ],
                },
                "created_at": DEMO_CREATED_AT,
            },
            {
                "summary_id": f"{video_id}-summary-003",
                "segment_id": f"{video_id}-seg-003",
                "segment_index": 3,
                "start_ms": 260000,
                "end_ms": 386000,
                "source_refs": {"stt_ids": [f"{video_id}-stt-003"], "cap_ids": [f"{video_id}-cap-003"]},
                "summary": {
                    "bullets": [
                        {"bullet_id": "B1", "claim": "후반부에서는 여러 편집 팁을 실제 화면 조작 흐름으로 이어 보여주며, 사용자가 복습할 수 있는 기준점을 남깁니다."},
                        {"bullet_id": "B2", "claim": "SeSAC:Note는 이처럼 영상의 화면 변화와 시간 구간을 함께 저장해 요약과 QA 답변의 근거로 사용할 수 있습니다."},
                    ],
                    "definitions": [
                        {"term": "answer_records", "definition": "검색된 요약, 시간 구간, STT/VLM 근거 참조를 답변 생성 노드가 사용하기 쉽게 정규화한 구조입니다."},
                        {"term": "source_refs", "definition": "요약이나 답변이 참조한 STT, 화면 캡처, segment id를 연결하는 근거 참조입니다."},
                    ],
                    "explanations": [
                        {"point": "최종 답변에는 관련 시간대와 근거 요약을 함께 보여주면 사용자가 실제 영상으로 돌아가 내용을 확인할 수 있습니다."}
                    ],
                    "open_questions": [
                        {"question": "QA 답변에서 근거 시간대와 답변 본문을 어떤 UI로 분리하면 이해하기 쉬울까요?"}
                    ],
                },
                "created_at": DEMO_CREATED_AT,
            },
        ]
    return [
        {
            "summary_id": f"{video_id}-summary-001",
            "segment_id": f"{video_id}-seg-001",
            "segment_index": 1,
            "start_ms": 0,
            "end_ms": 900000,
            "source_refs": {"stt_ids": [f"{video_id}-stt-001"], "cap_ids": [f"{video_id}-cap-001"]},
            "summary": {
                "bullets": [
                    {"bullet_id": "B1", "claim": "강의 영상은 음성, 화면, 시간 정보가 함께 있어야 정확히 복습할 수 있습니다."},
                    {"bullet_id": "B2", "claim": "STT-only 요약은 수식, 표, 슬라이드 구조 같은 화면 맥락을 놓칠 수 있습니다."},
                ],
                "definitions": [
                    {"term": "구간별 근거 맥락", "definition": "같은 시간 구간의 음성 STT와 화면 VLM 결과를 함께 묶은 QA/노트 생성 입력입니다."}
                ],
                "explanations": [
                    {"point": "timestamp 기준으로 음성과 화면을 묶으면 답변의 근거 구간을 사용자에게 다시 보여줄 수 있습니다."}
                ],
                "open_questions": [
                    {"question": "화면 정보가 없는 구간은 어떤 fallback 전략을 적용해야 할까요?"}
                ],
            },
            "created_at": DEMO_CREATED_AT,
        },
        {
            "summary_id": f"{video_id}-summary-002",
            "segment_id": f"{video_id}-seg-002",
            "segment_index": 2,
            "start_ms": 900000,
            "end_ms": 1800000,
            "source_refs": {"stt_ids": [f"{video_id}-stt-002"], "cap_ids": [f"{video_id}-cap-002"]},
            "summary": {
                "bullets": [
                    {"bullet_id": "B1", "claim": "LangGraph QA는 질문 유형을 판단하고 관련 요약을 먼저 검색한 뒤 답변을 생성합니다."},
                    {"bullet_id": "B2", "claim": "semantic retrieval이 실패하면 기존 summary cache로 fallback하여 QA 흐름을 유지합니다."},
                ],
                "definitions": [
                    {"term": "semantic retrieval", "definition": "사용자 질문과 의미적으로 가까운 요약 구간을 embedding 검색으로 찾는 방식입니다."}
                ],
                "explanations": [
                    {"point": "검색 결과를 answer_records 형태로 정규화하면 LangGraph 노드가 일관된 입력을 받을 수 있습니다."}
                ],
                "open_questions": [
                    {"question": "retrieval threshold를 낮추면 recall과 hallucination risk가 어떻게 달라질까요?"}
                ],
            },
            "created_at": DEMO_CREATED_AT,
        },
        {
            "summary_id": f"{video_id}-summary-003",
            "segment_id": f"{video_id}-seg-003",
            "segment_index": 3,
            "start_ms": 1800000,
            "end_ms": 3300000,
            "source_refs": {"stt_ids": [f"{video_id}-stt-003"], "cap_ids": [f"{video_id}-cap-003"]},
            "summary": {
                "bullets": [
                    {"bullet_id": "B1", "claim": "Judge 점검은 답변이 제공된 근거와 맞는지 1차로 확인하는 품질 통제 장치입니다."},
                    {"bullet_id": "B2", "claim": "pHash+ORB와 OCR-first 전략은 중복 캡처와 불필요한 VLM 입력 비용을 줄이는 데 사용됩니다."},
                ],
                "definitions": [
                    {"term": "Judge", "definition": "생성 결과의 근거성, 노트 품질, 멀티모달 활용 여부를 점검하는 평가 단계입니다."}
                ],
                "explanations": [
                    {"point": "Judge는 품질을 보장하는 장치가 아니라 위험을 완화하는 자동 점검 흐름으로 보는 것이 안전합니다."}
                ],
                "open_questions": [
                    {"question": "Judge 결과를 사용자가 이해할 수 있는 UI로 어떻게 노출할 수 있을까요?"}
                ],
            },
            "created_at": DEMO_CREATED_AT,
        },
    ]


def demo_summaries_payload(video_id: str) -> Optional[Dict[str, Any]]:
    video = get_demo_video(video_id)
    if not video:
        return None
    snapshot = video.get("demo_pipeline_snapshot") or _demo_pipeline_snapshot(video)
    items = demo_summary_items(video_id)[: snapshot["summary_count"]]
    return {"video_id": video_id, "count": len(items), "items": items}


def demo_summary_payload(video_id: str) -> Optional[Dict[str, Any]]:
    if not get_demo_video(video_id):
        return None
    return {
        "video_id": video_id,
        "has_summary": True,
        "summary_id": f"{video_id}-full-summary",
        "format": "json",
        "status": "DONE",
        "is_complete": True,
        "payload": {"title": "강의 영상 기반 멀티모달 AI 노트", "sections": demo_summary_items(video_id)},
        "created_at": DEMO_CREATED_AT,
    }


def demo_evidence_payload(video_id: str, stt_ids: List[str], cap_ids: List[str]) -> Optional[Dict[str, Any]]:
    if not get_demo_video(video_id):
        return None
    return {
        "video_id": video_id,
        "stt": [
            {
                "id": stt_id,
                "start_ms": [0, 130000, 260000][index] if index < 3 else index * 130000,
                "end_ms": [130000, 260000, 386000][index] if index < 3 else (index + 1) * 130000,
                "text": "Kate 편집기 사용 팁을 설명하며, 화면에 보이는 코드 편집 흐름과 함께 기능 사용 맥락을 제공합니다.",
            }
            for index, stt_id in enumerate(stt_ids)
        ],
        "vlm": [
            {
                "id": cap_id,
                "cap_id": cap_id,
                "time_ranges": [{
                    "start_ms": [0, 130000, 260000][index] if index < 3 else index * 130000,
                    "end_ms": [130000, 260000, 386000][index] if index < 3 else (index + 1) * 130000,
                }],
                "caption": "Kate 편집기 화면, 코드 조각, 검색/치환 UI가 함께 보이는 데모 장면입니다.",
            }
            for index, cap_id in enumerate(cap_ids)
        ],
    }


def demo_chat_answer(message: str) -> str:
    query = (message or "").strip()
    if "검색" in query or "치환" in query or "찾" in query:
        return (
            "검색/치환 기능은 중반 구간인 02:10-04:20에서 확인할 수 있습니다. "
            "이 구간은 화면에 보이는 편집기 UI와 코드 조각을 함께 근거로 사용해야 기능 흐름을 이해하기 쉽습니다."
        )
    if "근거" in query or "시간" in query or "구간" in query:
        return (
            "이 답변은 00:00-02:10의 영상 주제 소개, 02:10-04:20의 편집 기능 설명, "
            "04:20-06:26의 후반 실습 구간을 근거로 구성됩니다. SeSAC:Note는 이 시간 구간을 source_refs로 연결해 답변 근거를 추적합니다."
        )
    return (
        "이 영상은 Kate 텍스트 편집기의 생산성 팁을 실제 화면 조작과 함께 보여주는 데모입니다. "
        "SeSAC:Note는 영상의 음성, 화면, 시간 정보를 구간별 근거 맥락으로 묶어 AI 노트와 QA에 사용합니다."
    )


def demo_suggestions() -> List[str]:
    return [
        "검색/치환 기능은 어느 구간에서 설명하나요?",
        "답변 근거는 어떤 시간 구간인가요?",
    ]

