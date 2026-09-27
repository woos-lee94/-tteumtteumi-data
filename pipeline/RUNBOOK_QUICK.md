# 틈틈이 빠른 업데이트 절차 (저녁 예약 · 관리자 '지금 새로 조사')

목표: 지난 판 이후 새로 나온 **읽을 만한 소식**을 적은 토큰으로 더해서 main에 올린다. 20분 안팎.
읽을거리·카드는 하지 않는다(새벽 전체 업데이트 몫). 새 소식이 정말 없는 분야는 0건. 사소한 후속·반복 보도로 억지로 채우지 않는다.

## 0. 원칙
- RUNBOOK.md 0번 원칙을 그대로 따른다(질문하지 않기, 공개 저장소, 검증 통과 전에는 올리지 않기, `{REPO}`는 절대 경로).
- 조사 에이전트 2개(각 WebSearch 8회 이내) + 검토 에이전트 1개(WebSearch 4회 이내). 새 기사는 모두 합쳐 8건 이하.

## 1. 준비
1. 쉬는 시간 확인: `python3 {REPO}/pipeline/version.py --age`
   - `tooSoon`이 true면(마지막 조사를 마친 지 cooldownMinutes가 안 됨) 아무것도 바꾸지 말고 "방금(N분 전) 조사를 마쳐서 건너뛰었어요"라고 보고하고 끝낸다.
   - `checkedAt` 값을 지난 판 시각 `{since}`로 기억한다.
2. `python3 {REPO}/pipeline/schedule.py` → today, yymmdd, weekday. 지금 시각: `TZ=Asia/Seoul date +%H%M` → `{hhmm}`.
3. `mkdir -p {REPO}/work/new`

## 2. 조사: 에이전트 2개를 한 메시지에서 동시에 띄운다
| 조 | 분야 |
|---|---|
| Q1 | politics, assembly, policy, society, economy, stock, world |
| Q2 | tech, sports, entertainment, culture, fashion, events |

각 에이전트(general-purpose)에게 보낼 지시(중괄호를 채운다):
```
너는 '틈틈이' 앱의 뉴스 기자야. 지금은 {today}({weekday}) {hhmm} 한국 시간이고, 지난 판은 {since}에 나왔어.
1) {REPO}/pipeline/news_spec.md 를 먼저 읽고 따라. 단, 이번은 '빠른 업데이트'라 아래 규칙이 우선이야.
2) 맡은 분야: {분야들}. {since} 이후에 새로 나온 소식 가운데 출퇴근길에 읽을 만한 것(결과·결정·발표·경기 결과·새 일정·큰 사건)을 분야마다 0~1건, 모두 합쳐 최대 4건.
   사소한 후속이나 같은 내용의 반복 보도는 빼. 새 소식이 정말 없는 분야만 0건이야.
   - 검색 색인은 몇 시간 늦어. 최신 소식은 WebFetch로 Bing 뉴스 최신순(https://www.bing.com/news/search?q=검색어&qft=sortbydate%3d%221%22)이나
     news_spec.md에 적힌 잘 열리는 언론사의 최신 기사 목록을 먼저 훑고, 본문에서 날짜·시각을 확인해.
   - 이미 올라간 기사와 같은 사안이면 새 사실(결과·결정·수치)이 있을 때만 새 기사로 쓰고 "replaces": ["옛 id"]를 넣어.
   - 주식: 한국 장 마감(15:30) 뒤라면 그날 국내 증시 마감 소식을 먼저 봐(같은 날 기존 증시 기사가 있으면 replaces).
   - 행사: 끝나지 않은 행사가 5건 미만일 때만 1건 더해.
3) 이미 올라간 기사: python3 {REPO}/pipeline/merge.py --status --cat {분야들}
4) id는 "{cat}-{yymmdd}-q{hhmm}-{n}" (예: stock-{yymmdd}-q{hhmm}-1).
5) hot은 false로 둬. 그날 그 분야에서 가장 큰 뉴스라 홈 '오늘의 이슈'를 바꿔야 할 때만 true.
6) 저장: {REPO}/work/new/news_{조}.json (기사 배열, 0건이면 []). 검증: python3 {REPO}/pipeline/validate.py {그 파일} --today {today} → 오류 0.
7) WebSearch는 8회 이내. 마지막 답변은 짧게: 저장한 기사 id·제목(없으면 "새 소식 없음"), 확인이 부족했던 점.
```

## 3. 새 기사가 모두 0건이면
조사를 마쳤다는 표시만 올리고 7단계 보고로 간다(4~6단계는 건너뛴다). 앱이 '새 소식 없음'을 알 수 있게 꼭 올린다.
```
cd {REPO}
python3 pipeline/version.py --checked quick --added 0
git add data/version.json
git commit -m "빠른 확인 {today} {hhmm}: 새 소식 없음"
git fetch origin main && git rebase origin/main && git push origin HEAD:main
```

## 4. 검토: 에이전트 1개
RUNBOOK.md 4단계 지시문을 그대로 쓰되, `{REPO}/work/new/news_Q*.json`만 고치고 WebSearch는 4회 이내로 한다.

## 5. 합치기와 검증
```
cd {REPO}
python3 pipeline/merge.py --news work/new/news_*.json --today {today} --mode quick
python3 pipeline/validate.py data/news.json data/reading.json --today {today}
```
- merge.py가 data/version.json도 고친다(앱이 새 판을 알아채는 파일).
- 검증 오류가 남으면 work/new 파일을 고친 뒤 `git checkout -- data`로 되돌리고 5단계를 다시 한다. 끝내 못 고치면 올리지 않고 보고한다.

## 6. 올리기
```
cd {REPO}
git add data
git commit -m "빠른 업데이트 {today} {hhmm}: 새 기사 N건"
git fetch origin main && git rebase origin/main
git push origin HEAD:main
```
- rebase가 data 파일 충돌로 멈추면(다른 업데이트가 먼저 올라감): `git rebase --abort && git reset --hard origin/main` 뒤 5단계부터 다시 한다. work/new 파일은 그대로 남아 있다.
- push가 거절되면 RUNBOOK.md 6단계와 같이 한다.

## 7. 마지막 보고(사용자에게 보이는 짧은 메시지)
- 새 기사 id·제목(분야별), 없으면 "새 소식 없음"
- 확인이 부족했던 점 1~3줄
- 커밋 해시
