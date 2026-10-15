# SeSAC:Note 로컬 시연 시나리오

## 시연 목적

유료 STT/VLM/LLM API 없이 로컬 demo mode에서 다음 사용자 흐름을 보여준다.

- 로그인
- 메인 페이지와 라이브러리 확인
- 영상 업로드
- 분석 진행 상태 확인
- 분석 완료 페이지에서 실제 영상 재생
- 재생 시점에 따른 요약 세그먼트 확인
- 오른쪽 채팅창에서 질문 입력 후 답변 생성
- Markdown export

## 시연 환경

- Frontend: http://127.0.0.1:5173/
- Backend: http://127.0.0.1:8080/
- Demo mode: enabled
- Demo file: `demo_assets/langgraph-academy-introduction-6min-demo.webm`
- File size: about 25MB
- Upload limit: 200MB

## 발표 순서

1. 로그인 화면 진입

   - URL: http://127.0.0.1:5173/
   - demo mode에서는 세션이 자동 준비된다.
   - 시연용 로그인 정보:

   ```text
   ID: sasacnote
   PW: demo1234
   ```

2. 메인 페이지 설명

   - `내 라이브러리`
   - `전체 / 분석 완료 / 진행 중` 필터
   - 업로드 영역

3. 영상 업로드

   - 아래 파일을 업로드한다.

   ```text
   demo_assets/langgraph-academy-introduction-6min-demo.webm
   ```

   - 업로드 후 분석 진행 페이지로 이동한다.
   - 진행 단계는 demo mode에서 빠르게 전환된다.

4. 분석 완료 페이지 확인

   - 영상이 실제 `<video>`로 재생되는지 확인한다.
   - 아래 `Real-time Summary`에 3개 세그먼트가 표시되는지 확인한다.

5. 영상 재생 시점과 요약 세그먼트 연결 확인

   - 영상 재생 중 현재 시점에 해당하는 요약 세그먼트가 강조된다.
   - 요약의 시간 버튼을 누르면 해당 영상 구간으로 이동한다.

6. 상세 보기 확인

   - `상세 보기` 클릭
   - 정의, 해설, 열린 질문이 표시되는지 확인한다.

7. 채팅 QA 시연

   아래 질문을 순서대로 입력하거나 추천 질문을 클릭한다.

   ```text
   이 영상은 무엇을 설명하나요?
   ```

   ```text
   검색/치환 기능은 어느 구간에서 확인할 수 있나요?
   ```

   ```text
   이 답변의 근거는 어떻게 추적하나요?
   ```

   기대 동작:

   - 질문 입력 후 약 0.3초 후 답변이 생성되기 시작한다.
   - 답변은 짧은 chunk 단위로 스트리밍처럼 출력된다.
   - 답변 안에 관련 시간 구간과 근거 설명이 포함된다.

8. Export 확인

   - 우측 상단 `Export`
   - `Markdown (.md)` 저장
   - 분석 결과를 문서화할 수 있음을 보여준다.

## 현재 준비된 분석 페이지

최근 로컬 API 업로드로 생성된 분석 페이지:

```text
http://127.0.0.1:5173/analysis/demo-upload-03c14df3
```

기존 fallback 분석 페이지:

```text
http://127.0.0.1:5173/analysis/demo-upload-21593f75
```

## 발표 멘트

```text
이 시연은 유료 API를 호출하지 않는 로컬 demo mode입니다.
실제 서비스 흐름과 동일한 UI 동선으로 업로드, 분석 진행, 영상 재생, 구간별 요약, QA 답변 생성을 보여줍니다.
분석 결과는 mock 데이터이지만, 영상 파일 재생과 프론트엔드 사용자 흐름은 실제로 동작합니다.
```

## 피해야 할 표현

- 실제 AI 분석 완료
- 실제 STT/VLM/LLM 처리 완료
- production 검증 완료
- 실제 서비스 운영 성공

## 안전한 표현

- 로컬 demo mode에서 업로드부터 QA까지 사용자 흐름을 재현
- 유료 API 없이 mock summary와 demo QA로 시연 가능
- 실제 영상 파일 재생과 구간별 요약 UI 연동 확인

