# 틈틈이 데이터

출퇴근길 아이폰 웹앱 **틈틈이**가 받아 가는 뉴스·읽을거리 파일이에요.

| 파일 | 내용 | 바뀌는 때 |
|---|---|---|
| `data/news.json` | 13개 분야 뉴스(정치·국회·생활정책·사회·경제·주식·국제·IT과학·스포츠·연예·문화·패션·행사) | 새벽 4시 20분(전체), 저녁 5시 20분(빠른 업데이트), 관리자 요청 때 |
| `data/reading.json` | 역사(한국사·현대사·우리 동네 역사)·생활(세탁·청소) 읽을거리 | 매주 일요일에 더해짐 |
| `data/daily/*.json` | '오늘의 한 장' 카드(속담·사자성어·상식·유래·우리말) | 상식·유래가 이틀마다 5장씩 더해짐 |
| `data/version.json` | 위 파일들이 언제 바뀌었는지, 조사를 마친 시각, 다음 조사 시각 | 조사할 때마다 |

- 앱 주소 설정: 앱 `index.html`의 `<meta name="tteum-data-base">`에
  `https://raw.githubusercontent.com/woos-lee94/-tteumtteumi-data/main/data/` 가 들어 있어요.
- 앱은 작은 `version.json`만 자주(열 때, 켜 둔 동안 10분마다) 받아 보고, 바뀐 파일만 새로 받아요. 조사(토큰)를 쓰지 않아요.
- 조사는 Claude 예약 작업이 해요.
  - 새벽 4시 20분 '틈틈이 뉴스 업데이트': `pipeline/RUNBOOK.md` (분야마다 새 기사 2건 안팎, 일요일 읽을거리, 이틀마다 카드)
  - 저녁 5시 20분 '틈틈이 빠른 업데이트': `pipeline/RUNBOOK_QUICK.md` (지난 판 이후 큰 소식만, 없으면 0건)
- 기사는 여러 언론 보도를 교차 확인해 쉬운 말로 새로 쓴 요약이고, 기사마다 원문 출처를 달았어요.
- 오래된 기사는 자동으로 정리돼요(최근 3일 기사 중심, 분야별 5건 안팎, 끝난 행사는 빠짐).

## 관리자 '지금 새로 조사'
앱 관리자 화면 → GitHub Actions `지금 새로 조사 (관리자)`(`.github/workflows/owner-refresh.yml`) → Claude 루틴 '틈틈이 빠른 업데이트' API.
- 저장소에 쓰기 권한이 있는 GitHub 열쇠로만 시작할 수 있어서, 다른 사람은 조사를 시작할 수 없어요.
- 마지막 조사를 마친 지 50분이 안 됐으면 건너뛰어요(`pipeline/updates.json`의 cooldownMinutes).
- 처음 한 번 준비
  1. claude.ai/code/routines → '틈틈이 빠른 업데이트' → 편집 → 트리거 추가 → API → 토큰 만들기(한 번만 보여요).
  2. 이 저장소 Settings → Secrets and variables → Actions → New repository secret: 이름 `ROUTINE_TOKEN`, 값은 1의 토큰.
  3. GitHub → Settings → Developer settings → Fine-grained tokens → 이 저장소만, 권한 Actions: Read and write → 만든 열쇠를 앱 관리자 화면에 붙여넣기(그 폰에만 저장).
