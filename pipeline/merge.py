"""새로 쓴 기사를 data/news.json, data/reading.json에 합쳐요.

사용
  python3 pipeline/merge.py --status [--cat stock,world]      지금 올라가 있는 기사 목록 보기(겹침 확인용)
  python3 pipeline/merge.py --news work/new/news_*.json [--reading work/new/reading_*.json] [--today YYYY-MM-DD] [--mode full|quick] [--dry-run]

뉴스를 남기는 규칙(pipeline/categories.json의 keep 값)
- 행사(events)가 아닌 분야: 최근 recentDays일(오늘 포함) 기사는 남기고, 분야별 minPerCat건이 안 되면
  maxAgeDays일 안쪽의 더 오래된 기사로 채워요. 분야별 최대 maxPerCat건(최신 순).
  --dry-run에 나오는 '최근 N일 M건'이 새 기사 목표를 정하는 기준이에요(RUNBOOK 1단계).
- 행사: 끝난 행사(when.end < 오늘)는 빼고, 시작일 순으로 최대 maxEvents건.
- 새 기사에 "replaces": ["옛 id", ...]가 있으면 그 옛 기사는 빼요(같은 사안의 새 소식).
- hot(홈 '오늘의 이슈'): 분야마다 1건. 새 기사 가운데 hot이 있으면 그것, 없으면 남은 기존 hot, 그것도 없으면 가장 최근 기사.
읽을거리(역사·생활)는 지우지 않고 덧붙여요.
합친 뒤 data/version.json(앱이 새 판을 알아채는 작은 파일)도 알아서 고쳐요. --mode는 전체 조사(full)·빠른 조사(quick) 구분이에요.

전체 조사(--mode full) 안전장치 (2026-09-30 새벽 예약이 뉴스 조사를 건너뛰고 0건을 올린 일 뒤에 넣었어요)
- 뉴스 5개 조 파일(work/new/news_A*.json ~ news_E*.json)이 모두 있어야 해요.
- 새 기사가 모두 합쳐 FULL_MIN건 이상이어야 해요.
- 둘 중 하나라도 어기면 아무 파일도 바꾸지 않고 멈춰요. 조를 다시 띄워 조사하세요.
- 조사를 제대로 했는데도 정말 새 소식이 모자랄 때만 --allow-few "이유"로 넘길 수 있어요(보고에 그 이유를 적어요).
"""
import argparse
import datetime
import glob
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import version  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'
CATS = json.loads((ROOT / 'pipeline' / 'categories.json').read_text(encoding='utf-8'))
NEWS_ORDER = [c['key'] for c in CATS['news']]
READ_ORDER = [c['key'] for c in CATS['reading']]
SUBS = {c['key']: c['subs'] for c in CATS['news'] + CATS['reading']}
KEEP = CATS['keep']
KST = datetime.timezone(datetime.timedelta(hours=9))
FULL_TEAMS = ['A', 'B', 'C', 'D', 'E']
FULL_MIN = 8


def now_kst():
    return datetime.datetime.now(KST).replace(second=0, microsecond=0)


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def save(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')


def days_between(a, b):
    return (datetime.date.fromisoformat(a) - datetime.date.fromisoformat(b)).days


def read_new(patterns):
    out = []
    for pat in patterns or []:
        for f in sorted(glob.glob(pat)):
            data = load(f)
            out += data['articles'] if isinstance(data, dict) else data
    return out


def status(cats):
    news = load(DATA / 'news.json')['articles']
    reading = load(DATA / 'reading.json')['articles']
    for a in news + reading:
        if cats and a['cat'] not in cats:
            continue
        extra = f" 행사 {a['when']['start']}~{a['when']['end']}" if a.get('when') else ''
        print(f"{a['cat']:<13} {a['id']:<22} {a['date']} [{a.get('sub', '')}] {'★' if a.get('hot') else ' '} {a['title']}{extra}")


def merge_news(old, new, today):
    replaced = {rid for a in new for rid in (a.get('replaces') or [])}
    new_ids = {a['id'] for a in new}
    clash = [a['id'] for a in old if a['id'] in new_ids]
    if clash:
        sys.exit(f'id가 이미 있어요: {clash}')
    pool = [a for a in old if a['id'] not in replaced] + new
    out, report = [], {}
    for cat in NEWS_ORDER:
        items = [a for a in pool if a['cat'] == cat]
        if cat == 'events':
            keep = [a for a in items if a.get('when') and a['when'].get('end', '') >= today]
            keep.sort(key=lambda a: (a['when']['start'], a['id']))
            keep = keep[:KEEP['maxEvents']]
        else:
            items.sort(key=lambda a: (a['date'], a['id'] in new_ids, a['id']), reverse=True)
            recent = [a for a in items if days_between(today, a['date']) < KEEP['recentDays']]
            older = [a for a in items if a not in recent and days_between(today, a['date']) <= KEEP['maxAgeDays']]
            keep = recent + older[:max(0, KEEP['minPerCat'] - len(recent))]
            keep = keep[:KEEP['maxPerCat']]
        # hot: 분야마다 1건
        hot_new = [a for a in keep if a['id'] in new_ids and a.get('hot')]
        hot_old = [a for a in keep if a['id'] not in new_ids and a.get('hot')]
        pick = (hot_new or hot_old or (sorted(keep, key=lambda a: a['date'], reverse=True)[:1] if cat != 'events' else keep[:1]))
        pick_id = pick[0]['id'] if pick else None
        for a in keep:
            a['hot'] = a['id'] == pick_id
            a.pop('replaces', None)
        if cat == 'events':
            keep.sort(key=lambda a: (a['when']['start'], a['id']))
        else:  # hot 먼저, 그다음 최신 순
            keep.sort(key=lambda a: a['id'])
            keep.sort(key=lambda a: a['date'], reverse=True)
            keep.sort(key=lambda a: not a['hot'])
        out += keep
        fresh = len(keep) if cat == 'events' else sum(1 for a in keep if days_between(today, a['date']) < KEEP['recentDays'])
        report[cat] = (len(keep), sum(1 for a in keep if a['id'] in new_ids), fresh)
    return out, report


def merge_reading(old, new):
    ids = {a['id'] for a in old}
    clash = [a['id'] for a in new if a['id'] in ids]
    if clash:
        sys.exit(f'id가 이미 있어요: {clash}')
    allr = old + new
    for a in allr:
        a['hot'] = False

    def key(a):
        subs = SUBS.get(a['cat'], [])
        return (READ_ORDER.index(a['cat']), subs.index(a['sub']) if a['sub'] in subs else 99, a['id'])
    allr.sort(key=key)
    return allr


def check_full(patterns, new_news, allow_few):
    names = [Path(f).name for pat in patterns or [] for f in glob.glob(pat)]
    missing = [t for t in FULL_TEAMS if not any(n.startswith(f'news_{t}') for n in names)]
    problems = []
    if missing:
        problems.append(f"뉴스 조 파일이 없어요: {', '.join('news_' + t + '.json' for t in missing)}")
    if len(new_news) < FULL_MIN:
        problems.append(f'새 기사가 {len(new_news)}건뿐이에요(전체 조사는 {FULL_MIN}건 이상)')
    if not problems:
        return
    if allow_few.strip():
        print('안전장치 넘김(--allow-few): ' + allow_few.strip() + ' / ' + ' · '.join(problems))
        return
    sys.exit('전체 조사 안전장치: ' + ' · '.join(problems) + '\n'
             'RUNBOOK 2단계대로 뉴스 5개 조(A~E) 에이전트를 모두 띄워 조사하고, 모두 끝난 뒤 다시 합치세요. '
             '직전 조사가 몇 시간 전이었어도 건너뛰지 않아요. 아무 파일도 바꾸지 않았어요.')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--status', action='store_true')
    ap.add_argument('--cat', default='')
    ap.add_argument('--news', nargs='*', default=[])
    ap.add_argument('--reading', nargs='*', default=[])
    ap.add_argument('--today', default='')
    ap.add_argument('--mode', choices=['full', 'quick'], default='full')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--allow-few', default='', help='전체 조사 안전장치를 넘길 이유(정말 새 소식이 모자랄 때만)')
    args = ap.parse_args()
    if args.status:
        status([c for c in args.cat.split(',') if c])
        return
    now = now_kst()
    today = args.today or now.strftime('%Y-%m-%d')
    news_doc = load(DATA / 'news.json')
    read_doc = load(DATA / 'reading.json')
    new_news = read_new(args.news)
    new_read = read_new(args.reading)
    for a in new_news:
        if a['cat'] not in NEWS_ORDER:
            sys.exit(f"뉴스 파일에 뉴스 분야가 아닌 글이 있어요: {a['id']}")
    for a in new_read:
        if a['cat'] not in READ_ORDER:
            sys.exit(f"읽을거리 파일에 읽을거리 분야가 아닌 글이 있어요: {a['id']}")
    if args.mode == 'full' and not args.dry_run:
        check_full(args.news, new_news, args.allow_few)
    arts, report = merge_news(news_doc['articles'], new_news, today)
    news_doc.update({
        'edition': today,
        'updatedAt': now.isoformat(),
        'note': '하루 두 번(새벽·저녁) 조사해 쉽게 다시 쓴 기사예요. 기사마다 원문 출처를 달았어요.',
        'articles': arts,
    })
    print(f'뉴스 {len(arts)}건 (기준일 {today}, 새 기사 {len(new_news)}건)')
    for cat in NEWS_ORDER:
        n, k, fresh = report[cat]
        flag = '  ← 5건 미만' if n < KEEP['minPerCat'] else ''
        recent = '' if cat == 'events' else f" · 최근 {KEEP['recentDays']}일 {fresh}건"
        print(f'  {cat:<13} {n}건 (새 {k}건{recent}){flag}')
    if new_read:
        read_doc['articles'] = merge_reading(read_doc['articles'], new_read)
        read_doc['updatedAt'] = now.isoformat()
        print(f"읽을거리 {len(read_doc['articles'])}편 (새 글 {len(new_read)}편)")
    if args.dry_run:
        print('(dry-run: 파일은 그대로예요)')
        return
    save(DATA / 'news.json', news_doc)
    if new_read:
        save(DATA / 'reading.json', read_doc)
    v = version.write(args.mode, len(new_news) + len(new_read))
    print(f"version.json: 뉴스 {v['news']} · 조사 마침 {v['checkedAt']} ({args.mode})")


if __name__ == '__main__':
    main()
