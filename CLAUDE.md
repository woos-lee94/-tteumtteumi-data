# 틈틈이 데이터 저장소

아이폰 웹앱 '틈틈이'가 읽는 뉴스·읽을거리 데이터예요. 앱은 `data/news.json`, `data/reading.json`을 raw.githubusercontent.com에서 바로 받아 가요.

- 매일 업데이트: `pipeline/RUNBOOK.md` 순서를 그대로 따라요.
- 기사 형식·작성 규칙: `pipeline/news_spec.md`(뉴스), `pipeline/reading_spec.md`(역사·생활).
- 검증: `python3 pipeline/validate.py 파일 --today YYYY-MM-DD` (오류 0이어야 올려요).
- 합치기: `python3 pipeline/merge.py ...` (오래된 기사 정리, 분야별 hot 1건, 끝난 행사 빼기).
- 공개 저장소예요. 개인 정보·비밀 키·메모리 내용을 올리지 마세요.
- 데이터 파일을 손으로 고칠 때도 올리기 전에 검증을 돌려요.
