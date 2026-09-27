"""오늘의 한 장 카드(상식·유래 등) 목록 보기·검증·더하기

사용
  python3 pipeline/cards.py status trivia            지금 있는 카드 제목(겹침 확인용)
  python3 pipeline/cards.py validate work/new/cards_K.json
  python3 pipeline/cards.py merge work/new/cards_K.json [--dry-run]

새 카드 파일 형식: {"trivia": [카드...], "origin": [카드...]}
- id는 비워 두거나 아무 값이나 넣어도 돼요. 합칠 때 tv33, or33처럼 차례로 새로 붙여요.
- 카드를 지우지 않고 덧붙이기만 해요(사람들이 넘긴 기록이 id로 남아 있어서).
"""
import datetime
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import version  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DAILY = ROOT / 'data' / 'daily'
KST = datetime.timezone(datetime.timedelta(hours=9))
PREFIX = {'trivia': 'tv', 'origin': 'or', 'proverb': 'pv', 'idiom': 'id', 'word': 'wd'}
KINDS = ['말', '물건·음식', '관습']
RELIABILITY = ['정설', '유력한 설', '여러 설', '속설 바로잡기']
SUPPORTED = ['trivia', 'origin']  # 자동으로 더하는 분야


def load_pool(cat):
    return json.loads((DAILY / f'{cat}.json').read_text(encoding='utf-8'))


def norm(t):
    return re.sub(r"[\s'\"‘’“”?!.,·…]", '', t or '')


def status(cat):
    for it in load_pool(cat)['items']:
        print(f"{it['id']:<6} L{it.get('level', '?')} {it.get('title') or it.get('text') or it.get('word')} — {it.get('answer', '')}")


def check_card(cat, it, existing_titles):
    errs, warns = [], []
    title = it.get('title', '')
    for k in ('title', 'answer', 'body', 'tags', 'level', 'source'):
        if not it.get(k):
            errs.append(f'필수 칸 없음: {k}')
    if title and not title.endswith('?'):
        warns.append('title은 질문(?)으로 끝나요')
    if len(title) > 26:
        warns.append(f'title {len(title)}자(24자 이내)')
    if len(it.get('answer', '')) > 42:
        warns.append(f"answer {len(it.get('answer', ''))}자(40자 이내)")
    blen = len(it.get('body', ''))
    if not 90 <= blen <= 240:
        warns.append(f'body {blen}자(100~220자)')
    if it.get('level') not in (1, 2, 3):
        errs.append('level은 1·2·3 중 하나')
    tags = it.get('tags') or []
    if not (isinstance(tags, list) and 1 <= len(tags) <= 3):
        errs.append('tags는 1~3개 배열')
    src = it.get('source') or {}
    if not src.get('name') or not re.match(r'^https?://', str(src.get('url', ''))):
        errs.append('source는 name과 http(s) url이 필요해요')
    if cat == 'origin':
        if it.get('kind') not in KINDS:
            errs.append(f"kind는 {' / '.join(KINDS)} 중 하나")
        if it.get('reliability') not in RELIABILITY:
            errs.append(f"reliability는 {' / '.join(RELIABILITY)} 중 하나")
    if norm(title) in existing_titles:
        errs.append('이미 있는 카드와 제목이 같아요')
    return errs, warns


def read_new(path):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise SystemExit('새 카드 파일은 {"trivia": [...], "origin": [...]} 형식이어야 해요')
    bad = [k for k in data if k not in SUPPORTED]
    if bad:
        raise SystemExit(f'지원하지 않는 분야: {bad} (가능: {SUPPORTED})')
    return data


def validate(path):
    data = read_new(path)
    total = 0
    for cat, items in data.items():
        titles = {norm(it.get('title')) for it in load_pool(cat)['items']}
        seen = set()
        for n, it in enumerate(items, 1):
            e, w = check_card(cat, it, titles)
            if norm(it.get('title')) in seen:
                e.append('같은 파일 안에 같은 제목이 있어요')
            seen.add(norm(it.get('title')))
            total += len(e)
            for m in e:
                print(f'ERROR [{cat} {n}] {m}')
            for m in w:
                print(f'WARN  [{cat} {n}] {m}')
        print(f'== {cat}: {len(items)}장')
    return total


def merge(path, dry):
    if validate(path):
        raise SystemExit('검증 오류가 있어서 합치지 않았어요')
    data = read_new(path)
    now = datetime.datetime.now(KST).replace(second=0, microsecond=0).isoformat()
    for cat, items in data.items():
        if not items:
            continue
        pool = load_pool(cat)
        nums = [int(m.group(1)) for it in pool['items'] if (m := re.match(rf"^{PREFIX[cat]}(\d+)$", it['id']))]
        nxt = max(nums, default=0) + 1
        keys = ['id', 'title', 'answer', 'body'] + (['kind', 'reliability'] if cat == 'origin' else []) + ['tags', 'level', 'source']
        for it in items:
            card = {k: it[k] for k in keys if k != 'id' and k in it}
            pool['items'].append({'id': f'{PREFIX[cat]}{nxt:02d}', **card})
            nxt += 1
        pool['updatedAt'] = now
        print(f"{cat}: {len(items)}장 더함 → 모두 {len(pool['items'])}장")
        if not dry:
            (DAILY / f'{cat}.json').write_text(json.dumps(pool, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    if dry:
        print('(dry-run: 파일은 그대로예요)')
    else:
        version.write()  # 카드 파일 시각을 version.json에 반영(앱이 새 카드를 알아채게)


if __name__ == '__main__':
    a = sys.argv[1:]
    if len(a) >= 2 and a[0] == 'status':
        status(a[1])
    elif len(a) >= 2 and a[0] == 'validate':
        sys.exit(1 if validate(a[1]) else 0)
    elif len(a) >= 2 and a[0] == 'merge':
        merge(a[1], '--dry-run' in a)
    else:
        print(__doc__)
        sys.exit(2)
