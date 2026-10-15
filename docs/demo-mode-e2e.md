# Demo Mode Mock E2E

유료 AI API, Supabase, R2 없이 로컬에서 UI/API 흐름을 확인하기 위한 mock E2E 모드입니다.

## 목적

- 업로드 API 모양 유지
- 비디오 목록 조회
- 상태/SSE 스트림
- 요약 세그먼트 표시
- source_refs 기반 evidence 조회
- LangGraph QA 화면 흐름 대체 응답
- 업로드 후 PREPROCESSING -> VLM_RUNNING -> SUMMARY_RUNNING -> JUDGE_RUNNING -> DONE 단계 시뮬레이션

## Backend 실행

```powershell
pip install -r requirements.txt
$env:SESAC_NOTE_DEMO_MODE="1"
$env:MEDIA_TICKET_SECRET="demo-secret"
uvicorn src.process_api:app --host 0.0.0.0 --port 8080 --reload
```

## Frontend 실행

```powershell
cd frontend
$env:VITE_SESAC_NOTE_DEMO_MODE="1"
$env:VITE_API_BASE_URL="http://localhost:8080"
npm run dev
```

브라우저:

```text
http://localhost:5173/
http://localhost:5173/analysis/demo-video-001
```

## API smoke E2E

Backend가 실행된 상태에서:

```powershell
python scripts/demo_smoke_e2e.py
```

성공 시:

```text
DEMO E2E SMOKE PASS
```

## Claim Boundary

- 이 모드는 유료 API 호출, 실제 Supabase DB, 실제 R2 Storage, 실제 영상 처리 파이프라인을 검증하지 않습니다.
- 검증 범위는 mock 데이터 기반 API/UI 흐름입니다.
- 업로드한 실제 영상의 내용을 분석하지 않고, demo job lifecycle과 fixture summary를 연결합니다.
- 포트폴리오에는 "유료 API 없이 mock fixture로 로컬 E2E smoke 흐름을 구성했다" 정도로 표현합니다.

