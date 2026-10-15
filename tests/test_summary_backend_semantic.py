from types import SimpleNamespace

from src.services.summary_backend import ProcessApiBackend


class FakeRpc:
    def execute(self):
        return SimpleNamespace(
            data=[
                {
                    "summary_id": "sum-1",
                    "video_id": "vid-1",
                    "segment_id": "seg-1",
                    "segment_index": 3,
                    "start_ms": 15000,
                    "end_ms": 30000,
                    "summary": {"title": "RAG", "bullets": [{"claim": "retriever 설명"}]},
                    "source_refs": {"stt_ids": ["stt-1"], "cap_ids": ["cap-1"]},
                    "similarity": 0.82,
                }
            ]
        )


class FakeClient:
    def __init__(self):
        self.called = None

    def rpc(self, name, params):
        self.called = (name, params)
        return FakeRpc()


class FakeAdapter:
    def __init__(self):
        self.client = FakeClient()


def test_semantic_summary_results_are_normalized(monkeypatch):
    adapter = FakeAdapter()
    monkeypatch.setattr("src.db.supabase_adapter.get_supabase_adapter", lambda: adapter)
    monkeypatch.setattr("src.db.embedding.generate_embedding", lambda query: [0.1] * 1024)

    backend = ProcessApiBackend("http://unused")
    result = backend.search_semantic_summaries(
        {"video_id": "vid-1"},
        query="retriever 역할은?",
        match_count=3,
        threshold=0.4,
    )

    assert result["success"] is True
    assert result["source"] == "semantic"
    assert adapter.client.called[0] == "match_summaries"
    assert adapter.client.called[1]["filter_video_id"] == "vid-1"
    assert result["items"][0]["retrieval_source"] == "semantic"
    assert result["items"][0]["source_refs"]["stt_ids"] == ["stt-1"]
