"""data/version.json 쓰기·읽기

앱은 이 작은 파일(1KB 안팎)만 자주 받아 보고, 바뀐 파일만 새로 받아요.
merge.py(기사 합치기), cards.py merge(카드 더하기), brain.py build(두뇌 게임 문제 더하기)가 알아서 불러요.

사용
  python3 pipeline/version.py                          파일들의 updatedAt만 다시 적어요
  python3 pipeline/version.py --checked quick --added 0   조사를 마쳤다고 적어요(새 기사가 없어도)
  python3 pipeline/version.py --age                    마지막 조사 뒤 몇 분 지났는지(쿨다운 확인)

version.json 칸
  news, reading, daily{분야}, brain: 각 파일의 updatedAt
  times: 조사 예정 시각(pipeline/updates.json), full: 그중 전체 조사 시각, cooldownMinutes: 관리자 '지금 새로 조사' 쉬는 시간
  checkedAt: 마지막으로 조사를 마친 시각(새 기사가 없어도 바뀜), lastRun: {mode, at, added}
"""
import argparse
import datetime
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'
KST = datetime.timezone(datetime.timedelta(hours=9))
DAILY = ['proverb', 'idiom', 'trivia', 'origin', 'word']


def now_iso():
    return datetime.datetime.now(KST).replace(second=0, microsecond=0).isoformat()


def _stamp(path):
    try:
        return json.loads(path.read_text(encoding='utf-8')).get('updatedAt') or ''
    except FileNotFoundError:
        return ''


def load():
    try:
        return json.loads((DATA / 'version.json').read_text(encoding='utf-8'))
    except FileNotFoundError:
        return {}


def write(mode=None, added=None):
    """파일 시각을 다시 적고, mode가 있으면 조사를 마친 시각(checkedAt)과 lastRun도 적어요."""
    cfg = json.loads((ROOT / 'pipeline' / 'updates.json').read_text(encoding='utf-8'))
    v = load()
    v['news'] = _stamp(DATA / 'news.json')
    v['reading'] = _stamp(DATA / 'reading.json')
    v['daily'] = {k: _stamp(DATA / 'daily' / f'{k}.json') for k in DAILY}
    v['brain'] = _stamp(DATA / 'brain.json')
    v['times'] = cfg['times']
    v['full'] = cfg.get('full', cfg['times'][0])
    v['cooldownMinutes'] = cfg['cooldownMinutes']
    if mode:
        t = now_iso()
        v['checkedAt'] = t
        v['lastRun'] = {'mode': mode, 'at': t, 'added': int(added or 0)}
    if not v.get('checkedAt'):
        v['checkedAt'] = v['news']
    (DATA / 'version.json').write_text(json.dumps(v, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    return v


def age():
    v = load()
    cfg = json.loads((ROOT / 'pipeline' / 'updates.json').read_text(encoding='utf-8'))
    t = v.get('checkedAt') or v.get('news')
    minutes = None
    if t:
        minutes = int((datetime.datetime.now(KST) - datetime.datetime.fromisoformat(t)).total_seconds() // 60)
    cool = cfg['cooldownMinutes']
    return {'checkedAt': t, 'minutes': minutes, 'cooldownMinutes': cool, 'tooSoon': minutes is not None and minutes < cool}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--checked', choices=['full', 'quick'])
    ap.add_argument('--added', type=int, default=0)
    ap.add_argument('--age', action='store_true')
    args = ap.parse_args()
    if args.age:
        print(json.dumps(age(), ensure_ascii=False))
        return
    v = write(args.checked, args.added)
    print(json.dumps(v, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
