from pathlib import Path


SCHEMA = Path(__file__).resolve().parents[1] / "src" / "db" / "supabase_schema.sql"


def test_schema_has_source_refs_and_match_summaries_rpc():
    sql = SCHEMA.read_text(encoding="utf-8")

    assert "source_refs JSONB" in sql
    assert "CREATE OR REPLACE FUNCTION match_summaries" in sql
    assert "filter_video_id UUID" in sql


def test_captures_index_does_not_reference_missing_start_ms():
    sql = SCHEMA.read_text(encoding="utf-8")

    assert "idx_captures_video_ts ON captures(video_id, start_ms)" not in sql
    assert "idx_captures_video ON captures(video_id)" in sql
    assert "idx_captures_time_ranges_gin ON captures USING GIN (time_ranges)" in sql
