# 틈틈이 '두뇌 게임' 문제 만들기 절차 (예약 작업 '틈틈이 두뇌 게임', 날마다 새벽 1시 40분)

목표: 앱이 오전 6시·오후 5시에 여는 판(판마다 3문제, 최상 난이도)을 **하루 앞서** 채운다. 보통 내일 두 판 = 6문제.
정답이 딱 하나인지 **세 번 확인**(코드 전수 확인 → 다른 에이전트가 따로 풀기 → 반박 검사)한 문제만 `data/brain.json`에 올린다.
문제 규칙은 `pipeline/brain_spec.md`. 목표 시간 60분 안팎.

## 0. 원칙
- 사용자에게 질문하지 않는다. 판단이 갈리면 그 문제를 버린다(애매한 문제를 올리는 것보다 판을 비우는 게 낫다).
- 공개 저장소다. **정답·풀이·verify가 든 후보 파일은 `{REPO}/work/brain/`에만 둔다**(`work/`는 .gitignore). `data/brain.json`에는 `brain.py build`가 만든 확인값(h)과 잠긴 풀이(x)만 들어간다.
- 마지막 보고에도 정답·풀이·핵심 규칙을 쓰지 않는다(관리자도 이 게임을 푼다).
- 기존 `data/brain.json`을 통째로 지우거나 비우지 않는다. 이미 올라간 판은 고치지 않는다.
- 아래에서 `{REPO}`는 클론한 저장소의 절대 경로다(저장소 이름이 '-'로 시작하니 늘 절대 경로로).

## 1. 준비
```
cd {REPO}
python3 pipeline/brain.py need --days 1     # 채울 판: [{"date", "slot", "kinds"}] (오늘 것이 비었으면 오늘부터)
python3 pipeline/brain.py recent            # 최근 30일 문제(비슷한 문제를 또 내지 않게)
mkdir -p work/brain
```
- `need`가 `[]`이면 채울 판이 없다. "채울 판 없음"으로 8단계 보고만 하고 끝낸다.
- 필요한 문제 수 `{필요}` = 판 수 × 3. 판마다 추천 종류 3개(`kinds`)가 나온다. 추천 종류를 먼저 쓰되, 판 안에서 종류만 겹치지 않으면 된다.
- 후보는 `{필요}`의 2배쯤 만든다(보통 12개). 처음 해 보니 16개 중 7개가 '너무 쉬움'으로 떨어졌다.

## 2. 후보 만들기: 에이전트 2개를 한 메시지에서 동시에 띄운다
| 조 | 종류 | 파일 |
|---|---|---|
| A | 수열·행렬·수리·암호 가운데 필요한 종류 | `work/brain/cand_A.json` |
| B | 논리·참거짓·기호 가운데 필요한 종류 | `work/brain/cand_B.json` |

조마다 만들 종류와 개수를 정해 준다(예: A 수열 2·수리 2·암호 2, B 논리 2·참거짓 2·기호 2). 각 에이전트(general-purpose)에게 보낼 지시(중괄호를 채운다):
```
너는 '틈틈이' 앱의 두뇌 게임 출제자야. 아이큐 140 수준의 사람도 3~10분은 고민해야 하는 최상 난이도 문제를 새로 만들어.
1) {REPO}/pipeline/brain_spec.md 를 먼저 읽고 그대로 따라(형식, 정답은 딱 하나, 공정성, 해요체, 한 화면 분량).
2) 만들 문제: {종류별 개수}. 모두 서로 다른 발상으로.
3) 최근에 낸 문제(비슷한 발상·같은 제목 금지):
{brain.py recent 출력}
4) 너무 쉬우면 버려져. 한눈에 보이는 규칙 하나짜리, 첫 가정 하나로 풀리는 논리, 보기를 하나씩 넣어 보면 1분 안에 맞는 보기형은 탈락이야.
   규칙 두 개 이상이 겹치거나 3단계 이상 추론해야 하고, 그럴듯한 다른 규칙·다른 답이 없어야 해.
5) 문제마다 verify(파이썬 표준 라이브러리만 쓰는 solve())를 쓰고, 저장하기 전에 직접 돌려 answer와 같고 solutions가 1인지 확인해.
   논리·참거짓은 모든 배치를 전수 조사하고, 수열·행렬은 규칙으로 보인 항·칸을 모두 다시 만들어 assert 해. choice는 규칙을 만족하는 보기가 정확히 1개여야 해.
6) 저장: {REPO}/work/brain/cand_{조}.json (문제 객체 배열). 확인: python3 {REPO}/pipeline/brain.py check {그 파일} → 모두 '통과'가 되게 고쳐.
7) 마지막 답변은 짧게: 문제마다 종류·제목·한 줄 요약. 정답은 답변에 쓰지 마.
```

## 3. 1차 확인: 코드
```
python3 pipeline/brain.py check work/brain/cand_A.json work/brain/cand_B.json
```
- verify를 실행해 정답이 같고 경우의 수가 1인지 본다. 형식·힌트에 정답이 드러나는지도 본다. 결과는 후보 파일의 `_ok1`, `_why`에 적힌다.
- 탈락한 문제는 버린다(4단계로 가져가지 않는다).

## 4. 2차 확인: 따로 풀기 — 에이전트 1개(새로 띄움, 정답을 모르는 상태)
```
python3 pipeline/brain.py strip work/brain/cand_A.json work/brain/q_A.json
python3 pipeline/brain.py strip work/brain/cand_B.json work/brain/q_B.json
```
`q_*.json`에는 정답·풀이·힌트·코드가 없다. 에이전트에게는 **q 파일 경로만** 알려 주고 cand 파일은 절대 알려 주지 않는다.
```
너는 퍼즐 검산 담당이야. {REPO}/work/brain/q_A.json, q_B.json 에 있는 문제를 처음부터 직접 풀어(다른 파일은 열지 마).
- 문제마다 문장을 꼼꼼히 읽고 풀어. 파이썬으로 모든 경우를 따져 봐도 돼.
- 답은 number면 수, text면 낱말, choice면 보기 번호(1~5)로.
- 답이 둘 이상 되거나 문장이 두 가지로 읽히면 note에 적어.
- 저장: {REPO}/work/brain/solved_A.json, solved_B.json
  형식: [{"_cid": "문제의 _cid", "answer": "...", "confidence": "high|mid|low", "note": "..."}]
마지막 답변은 짧게: 문제마다 _cid와 confidence, 걸리는 점. 답은 쓰지 마.
```
```
python3 pipeline/brain.py compare work/brain/cand_A.json work/brain/solved_A.json
python3 pipeline/brain.py compare work/brain/cand_B.json work/brain/solved_B.json
```
- 따로 푼 답이 다르면 `_ok2`가 false가 되어 버려진다. note에 '답이 둘 이상'이 있으면 답이 같아도 5단계에서 꼭 따지게 한다.

## 5. 3차 확인: 반박 검사 — 에이전트 1개(또 새로 띄움)
2차까지 통과한 문제를 정답·풀이·verify와 함께 보여 주고 흠을 찾게 한다.
```
너는 까다로운 퍼즐 심사위원이야. {REPO}/work/brain/cand_A.json, cand_B.json 에서 _ok1과 _ok2가 true인 문제만 심사해.
{REPO}/pipeline/brain_spec.md 기준으로, 하나라도 걸리면 ok=false:
1) 다른 답: 보인 정보에 똑같이 맞는 다른 그럴듯한 규칙이나 해석이 있는가(직접 찾아보고, 찾으면 그 답을 reason에).
2) 문장: 두 가지로 읽히는 말(왼쪽·사이·이웃·보다 크다 등)이 정의 없이 쓰였는가.
3) 난이도: 잘 푸는 사람이 2분 안에 풀면 탈락. 한눈에 보이는 규칙, 첫 가정 하나로 끝나는 논리, 보기에서 거꾸로 맞히기 쉬움, 힌트가 핵심을 다 말해 줌.
4) 공정성: 전문 지식·암기·외국어 실력이 필요하거나, 종이로 하기 벅찬 큰 계산이 필요한가.
5) 힌트에 정답이나 핵심 계산 결과가 드러나는가. 풀이(explanation)가 정답까지 맞게 설명하는가.
6) 최근 문제와 발상이 거의 같은가: {brain.py recent 출력}
저장: {REPO}/work/brain/verdict_A.json, verdict_B.json
형식: [{"_cid": "...", "ok": true|false, "reason": "탈락이면 이유(통과면 빈 문자열)"}]
마지막 답변은 짧게: 통과·탈락 수와 탈락 이유 요약. 정답은 쓰지 마.
```
```
python3 pipeline/brain.py verdict work/brain/cand_A.json work/brain/verdict_A.json
python3 pipeline/brain.py verdict work/brain/cand_B.json work/brain/verdict_B.json
```

## 6. 모자라면 한 번 더
- 세 번 다 통과한 문제가 `{필요}`보다 적거나, 판마다 서로 다른 종류 3개를 맞추기 어려우면 2~5단계를 한 번 더 한다(모자란 종류 위주로, 모자란 수 × 2개).
  파일 이름은 `cand_A2.json`, `cand_B2.json`처럼 바꾼다(_cid가 겹치지 않게).
- 두 번째에도 모자라면 채울 수 있는 판만 채운다(판은 3문제가 다 있어야 올라간다). 오늘 판이 비어 있었다면 오늘 판부터 채워진다.

## 7. 합치기·검사·올리기
```
cd {REPO}
python3 pipeline/brain.py merge work/brain/cand_all.json work/brain/cand_A.json work/brain/cand_B.json   # 2회차 파일이 있으면 뒤에 더
python3 pipeline/brain.py build work/brain/cand_all.json --days 1 --dry-run
python3 pipeline/brain.py build work/brain/cand_all.json --days 1
python3 pipeline/brain.py validate
python3 pipeline/brain.py status
git status --short        # data/brain.json, data/version.json만 바뀌어야 한다(work/는 나오지 않음)
git add data/brain.json data/version.json
git commit -m "두뇌 게임 {채운 판}: {N}문제"
git fetch origin main && git rebase origin/main
git push origin HEAD:main
```
- `build`는 세 번 다 통과한 후보로 빈 판을 채우고(추천 종류 먼저, 판 안에서 종류가 겹치지 않게), 30일 지난 문제를 정리하고, `data/version.json`의 brain 시각도 고친다.
- rebase가 `data/version.json` 충돌로 멈추면(뉴스 업데이트가 먼저 올라감):
  ```
  git checkout --ours data/version.json && python3 pipeline/version.py > /dev/null
  git add data/version.json && GIT_EDITOR=true git rebase --continue
  git push origin HEAD:main
  ```
  (rebase 중 `--ours`는 먼저 올라간 쪽이다. version.py가 파일들의 시각을 다시 적어 brain 시각도 들어간다.)
- `data/brain.json`이 충돌하면 `git rebase --abort && git reset --hard origin/main` 뒤 7단계를 다시 한다(work/brain 파일은 남아 있다).
- push가 거절되면 fetch·rebase를 한 번 더 하고 다시 올린다.

## 8. 마지막 보고(사용자에게 보이는 짧은 메시지) — 정답·풀이·규칙은 쓰지 않는다
- 채운 판: `9월 29일 오전 판: 수열 '제목' · 논리 '제목' · 기호 '제목'` 식으로
- 후보 수 → 1차·2차·3차 통과 수, 탈락 이유 요약(예: 너무 쉬움 3, 다른 답 1)
- 비워 둔 판이 있으면 그 판과 이유
- 커밋 해시
