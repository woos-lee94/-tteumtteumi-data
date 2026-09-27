# 틈틈이 데이터 매일 업데이트 절차

목표: 13개 뉴스 분야에 새 기사를 더하고(분야마다 2건 안팎), 일요일에는 역사·생활 읽을거리도 더한 뒤 `data/news.json`(과 `data/reading.json`)을 main 브랜치에 올린다.
앱은 이 파일을 `https://raw.githubusercontent.com/woos-lee94/-tteumtteumi-data/main/data/` 에서 바로 받아 간다(올린 뒤 5분 안팎이면 반영).

## 0. 원칙
- 사용자에게 질문하지 않는다. 판단이 갈리면 보수적으로(빼거나 조심스럽게) 쓰고 마지막 보고에 적는다.
- 공개 저장소다. 개인 정보·비밀 키·메모리 내용을 파일에 쓰지 않는다.
- 검증을 통과하지 못하면 올리지 않는다. 기존 데이터 파일을 통째로 지우거나 비우지 않는다.
- 목표 시간 60분 안팎. 조사 에이전트는 WebSearch 12회 이내(읽을거리는 10회).
- 아래에서 `{REPO}`는 클론한 저장소의 절대 경로다.

## 1. 준비
1. 날짜: `TZ=Asia/Seoul date +%F`(TODAY), `TZ=Asia/Seoul date +%y%m%d`(YYMMDD), `TZ=Asia/Seoul date +%A`(요일).
2. `mkdir -p {REPO}/work/new`
3. 지금 상태: `python3 {REPO}/pipeline/merge.py --dry-run --today TODAY`
   - 새 기사 없이 합쳤을 때 분야별로 남는 건수가 나온다. 분야마다 새 기사 목표는 `max(2단계 기본 목표, 5 − 남는 건수)`로 하되 분야당 최대 4건.

## 2. 조사·작성: 하위 에이전트 5개를 한 메시지에서 동시에 띄운다
| 조 | 분야와 새 기사 목표 |
|---|---|
| A | politics 2, assembly 0~2(국회는 새 소식이 있을 때만) |
| B | policy 2, society 2, economy 2 |
| C | stock 2, world 2 |
| D | tech 2, sports 2, entertainment 2 |
| E | culture 2, fashion 2, events: 끝나지 않은 행사가 5건 이상 되도록 필요한 만큼(최대 3) |

각 에이전트(general-purpose)에게 보낼 지시(중괄호를 채운다):
```
너는 '틈틈이' 앱의 뉴스 기자야. 오늘은 {TODAY}({요일}) 한국 시간이야.
1) {REPO}/pipeline/news_spec.md 를 먼저 읽고 그대로 따라.
2) 맡은 분야와 새 기사 수: {목록}
3) 이미 올라간 기사(같은 사건 금지): python3 {REPO}/pipeline/merge.py --status --cat {분야들}
4) id는 "{cat}-{YYMMDD}-{n}" (n은 분야마다 1부터).
5) 저장: {REPO}/work/new/news_{조}.json (기사 배열). 검증: python3 {REPO}/pipeline/validate.py {그 파일} --today {TODAY} → 오류 0, 경고도 되도록 0.
6) 마지막 답변은 짧게: 저장한 기사 id·제목, 확인이 부족했던 점.
```

## 3. 일요일만: 읽을거리 에이전트 2개를 2단계와 같은 메시지에서 함께 띄운다
| 조 | 분야와 새 글 |
|---|---|
| H | history: 한국사 1, 현대사 1, 우리 동네 역사 1 |
| L | living: 세탁 1, 청소 1 |

지시는 2단계와 같되 1)은 `{REPO}/pipeline/reading_spec.md`(그리고 거기서 가리키는 news_spec.md의 형식), 저장은 `{REPO}/work/new/reading_{조}.json`.

## 4. 검토: 모든 작성 에이전트가 끝나면 검토 에이전트 1개
```
너는 '틈틈이' 앱의 교열·사실 점검 담당이야. 오늘은 {TODAY} 한국 시간이야.
{REPO}/work/new/ 의 새 기사 파일만 고쳐(구조·id·hot은 그대로). 비교용으로 {REPO}/data/news.json 과 reading.json 을 읽어.
볼 것: ① 기사끼리·기존 기사와 어긋나는 숫자·날짜·이름 ② 정치 균형(양쪽 입장, 주어 밝히기, 무죄 추정)
③ 주식 권유·단정 표현 ④ 생활 글의 위험한 혼합 경고 ⑤ 일반인 실명 ⑥ 오늘·내일·이번 주 같은 말 → 날짜로
⑦ 이미 지난 일을 앞으로 할 일처럼 쓴 문장 ⑧ 기존 기사와 같은 사건(겹치면 그 기사 파일에서 빼거나 replaces 추가)
⑨ 해요체·오탈자. 의심스러운 사실은 WebSearch 8회 이내로 확인하고, 확인 안 되면 빼거나 조심스럽게.
glossary term은 본문에 글자 그대로 남겨. 끝나면 python3 {REPO}/pipeline/validate.py {REPO}/work/new/*.json --today {TODAY} 오류 0.
보고는 짧게: 고친 곳 id별 한 줄.
```

## 5. 합치기와 검증
```
cd {REPO}
python3 pipeline/merge.py --news work/new/news_*.json --reading work/new/reading_*.json --today TODAY   # 읽을거리 파일이 없으면 --reading 부분은 빼요
python3 pipeline/validate.py data/news.json data/reading.json --today TODAY
```
- merge가 id 충돌로 멈추면 새 파일의 id를 고쳐 다시 한다.
- 검증 오류가 남으면 work/new 파일을 고친 뒤 `git checkout -- data`로 되돌리고 5단계를 다시 한다. 끝내 못 고치면 올리지 않고 보고한다.

## 6. 올리기
```
cd {REPO}
git add data/news.json data/reading.json
git commit -m "뉴스 업데이트 TODAY: 새 기사 N건"
git fetch origin main && git rebase origin/main
git push origin HEAD:main
```
- work/ 폴더는 올리지 않는다(.gitignore).
- push가 거절되면 fetch·rebase 후 한 번만 다시 한다.

## 7. 마지막 보고(사용자에게 보이는 짧은 메시지)
- 분야별 기사 수(새 기사 수), 5건 미만인 분야와 이유
- 확인이 부족했던 점 2~5줄
- 커밋 해시
