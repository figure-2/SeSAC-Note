from src.services.langgraph_session import _parse_input, _prepare_full


class FakeBackend:
    def __init__(self, semantic):
        self.semantic = semantic

    def get_summary_updates(self, state):
        return {"success": True}

    def get_summary_context(self, state, time_ms=None):
        return {
            "success": True,
            "summary_cache": [
                {
                    "segment_id": "seg-cache",
                    "summary": {"bullets": [{"claim": "캐시 요약"}]},
                    "source_refs": {"stt_ids": ["stt-cache"]},
                }
            ],
            "matches": [],
        }

    def search_semantic_summaries(self, state, *, query, match_count=5, threshold=0.4):
        return self.semantic


def test_content_question_uses_semantic_retrieval_first(monkeypatch):
    monkeypatch.setenv("CHATBOT_ENABLE_SEMANTIC_RETRIEVAL", "true")
    state = {"message": "retriever 역할은 뭐야?", "video_id": "vid-1"}
    state.update(_parse_input(state))
    backend = FakeBackend(
        {
            "success": True,
            "items": [
                {
                    "segment_id": "seg-semantic",
                    "summary": {"bullets": [{"claim": "semantic 요약"}]},
                    "source_refs": {"stt_ids": ["stt-semantic"]},
                    "retrieval_source": "semantic",
                }
            ],
        }
    )

    result = _prepare_full(state, backend)

    assert result["retrieval_source"] == "semantic"
    assert result["answer_records"][0]["segment_id"] == "seg-semantic"


def test_semantic_retrieval_failure_falls_back_to_summary_cache(monkeypatch):
    monkeypatch.setenv("CHATBOT_ENABLE_SEMANTIC_RETRIEVAL", "true")
    state = {"message": "핵심 개념 설명해줘", "video_id": "vid-1"}
    state.update(_parse_input(state))
    backend = FakeBackend({"success": False, "error": "mock rpc failure"})

    result = _prepare_full(state, backend)

    assert result["retrieval_source"] == "summary_cache_fallback"
    assert result["answer_records"][0]["segment_id"] == "seg-cache"
