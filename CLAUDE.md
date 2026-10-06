# 틈틈이 데이터 저장소

아이폰 앱 '틈틈이'(App Store)가 읽는 뉴스·읽을거리 데이터예요. 앱에는 관리자 기능이 없어요. 앱은 `data/news.json`, `data/reading.json`을 raw.githubusercontent.com에서 바로 받아 가요.

- 새벽 전체 업데이트: `pipeline/RUNBOOK.md`, 저녁·관리자 요청 빠른 업데이트: `pipeline/RUNBOOK_QUICK.md` 순서를 그대로 따라요. 조사 시각은 `pipeline/updates.json`.
- `data/version.json`: 앱이 자주 받아 보는 작은 파일(각 파일 updatedAt, 조사 마친 시각). merge.py·cards.py가 고쳐요. 새 기사 없이 조사만 마쳤으면 `python3 pipeline/version.py --checked quick --added 0`.
- 관리자 '지금 새로 조사': 개발자(관리자)가 Claude에서 예약 작업 '틈틈이 빠른 업데이트'를 바로 실행해요(RUNBOOK_QUICK.md). 앱에서 시작하는 단추는 없어요. 저장소에는 비밀 키가 필요 없어요.
- 기사 형식·작성 규칙: `pipeline/news_spec.md`(뉴스), `pipeline/reading_spec.md`(역사·생활), `pipeline/cards_spec.md`(상식·유래 카드).
- 두뇌 게임: `pipeline/RUNBOOK_BRAIN.md`(예약 작업 '틈틈이 두뇌 게임'), 문제 규칙 `pipeline/brain_spec.md`, 도구 `pipeline/brain.py`. 정답·풀이는 `work/brain/`에만 두고 절대 올리지 않아요(`data/brain.json`에는 확인값 h와 잠긴 풀이 x만). 보고에도 정답을 쓰지 않아요.
- 오늘 할 일(읽을거리는 일요일, 카드는 이틀마다): `python3 pipeline/schedule.py`
- 카드 보기·검증·더하기: `python3 pipeline/cards.py status|validate|merge ...` (카드는 지우지 않고 덧붙이기만)
- 검증: `python3 pipeline/validate.py 파일 --today YYYY-MM-DD` (오류 0이어야 올려요).
- 합치기: `python3 pipeline/merge.py ...` (오래된 기사 정리, 분야별 hot 1건, 끝난 행사 빼기).
- 공개 저장소예요. 개인 정보·비밀 키·메모리 내용을 올리지 마세요.
- 데이터 파일을 손으로 고칠 때도 올리기 전에 검증을 돌려요.
