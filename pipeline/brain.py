"""틈틈이 '두뇌 게임' 문제 만들기 도구

앱은 data/brain.json만 받아 가요. 이 파일에는 정답을 글자로 넣지 않아요.
- h: sha256("tteum-brain|{id}|{정규화한 정답}") — 앱이 입력한 답으로 같은 값을 만들어 맞는지 봐요.
- x: 풀이를 정답에서 만든 열쇠로 잠근 값 — 맞힌 사람의 앱만 풀 수 있어요.
정답이 들어 있는 후보 파일은 work/ 아래에만 두고(공개 저장소에 올리지 않음) 올리지 않아요.

사용
  python3 pipeline/brain.py need [--today YYYY-MM-DD] [--days 2]   채워야 할 판과 추천 종류
  python3 pipeline/brain.py check 후보.json...                      1차 확인: verify 코드 실행(정답 같음 + 경우의 수 1)
  python3 pipeline/brain.py strip 후보.json 풀이용.json              2차 확인용: 정답·풀이·힌트·코드를 뺀 파일
  python3 pipeline/brain.py compare 후보.json 풀이결과.json          2차 확인: 따로 푼 답과 비교
  python3 pipeline/brain.py verdict 후보.json 반박결과.json          3차 확인: 반박 검사 결과 반영
  python3 pipeline/brain.py build 후보.json [--today YYYY-MM-DD] [--days 2] [--dry-run]
                                                                    세 번 다 통과한 후보로 빈 판을 채워 data/brain.json에 합쳐요
  python3 pipeline/brain.py validate [data/brain.json]             형식 검사
  python3 pipeline/brain.py status                                 올라가 있는 판 보기
  python3 pipeline/brain.py try 문제id 답                          (시험용) 답이 맞는지, 맞으면 풀이를 풀어 보여 줘요

후보 파일은 문제 객체 배열이에요(형식은 pipeline/brain_spec.md). 확인 결과는 같은 파일의 _cid, _ok1, _ok2, _ok3, _why 칸에 적어요.
"""
import base64
import datetime
import hashlib
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'
BRAIN = DATA / 'brain.json'
KST = datetime.timezone(datetime.timedelta(hours=9))
START = datetime.date(2026, 9, 27)
KEEP_DAYS = 30
KINDS = ['수열', '행렬', '논리', '참거짓', '수리', '암호', '기호']
INPUTS = ['number', 'choice', 'text']
CYCLE = [
    ('수열', '논리', '수리'),
    ('행렬', '참거짓', '암호'),
    ('기호', '논리', '수열'),
    ('수리', '참거짓', '행렬'),
    ('암호', '논리', '기호'),
    ('수열', '참거짓', '수리'),
]
SLOTS = ['am', 'pm']


def today_kst():
    return datetime.datetime.now(KST).date()


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def save(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')


def load_brain():
    if BRAIN.exists():
        return load(BRAIN)
    return {'updatedAt': '', 'note': '', 'items': []}


# ---------------------------------------------------------------- 정답 맞추기(앱 app.js의 brainNorm과 똑같이)
def norm(ans, kind):
    s = unicodedata.normalize('NFC', str(ans)).strip()
    if kind == 'number':
        s = re.sub(r'[\s,]', '', s)
        m = re.fullmatch(r'([+-]?)(\d*)(?:\.(\d*))?', s)
        if not m or (m.group(2) == '' and (m.group(3) or '') == ''):
            return s
        sign = '-' if m.group(1) == '-' else ''
        whole = m.group(2).lstrip('0') or '0'
        frac = (m.group(3) or '').rstrip('0')
        res = whole + ('.' + frac if frac else '')
        return ('' if res == '0' else sign) + res
    if kind == 'choice':
        d = re.sub(r'\D', '', s)
        return str(int(d)) if d else s
    return re.sub(r"[\s.,!?·'\"~\-]", '', s).upper()


def answer_hash(pid, ans, kind):
    return hashlib.sha256(f'tteum-brain|{pid}|{norm(ans, kind)}'.encode('utf-8')).hexdigest()


def _keystream(key, n):
    out = b''
    i = 0
    while len(out) < n:
        out += hashlib.sha256(key + i.to_bytes(4, 'big')).digest()
        i += 1
    return out[:n]


def lock(pid, ans, kind, text):
    key = hashlib.sha256(f'tteum-brain-x|{pid}|{norm(ans, kind)}'.encode('utf-8')).digest()
    pt = text.encode('utf-8')
    return base64.b64encode(bytes(a ^ b for a, b in zip(pt, _keystream(key, len(pt))))).decode('ascii')


def unlock(pid, ans, kind, x):
    key = hashlib.sha256(f'tteum-brain-x|{pid}|{norm(ans, kind)}'.encode('utf-8')).digest()
    ct = base64.b64decode(x)
    return bytes(a ^ b for a, b in zip(ct, _keystream(key, len(ct)))).decode('utf-8', errors='replace')


# ---------------------------------------------------------------- 채워야 할 판
def slot_id(date, slot, n):
    return f"b{date.strftime('%y%m%d')}{'a' if slot == 'am' else 'p'}{n}"


def suggest_kinds(date, slot):
    idx = ((date - START).days * 2 + (0 if slot == 'am' else 1)) % len(CYCLE)
    return list(CYCLE[idx])


def need(today, days):
    have = {(it['date'], it['slot']) for it in load_brain()['items']}
    now = datetime.datetime.now(KST)
    out = []
    for d in range(0, days + 1):
        date = today + datetime.timedelta(days=d)
        for slot in SLOTS:
            if date == now.date() and slot == 'am' and now.hour >= 17:
                continue  # 오늘 저녁 판이 이미 열렸으면 오늘 오전 판은 건너뛰어요
            if (date.isoformat(), slot) not in have:
                out.append({'date': date.isoformat(), 'slot': slot, 'kinds': suggest_kinds(date, slot)})
    return out


# ---------------------------------------------------------------- 후보 형식
def check_fields(c):
    errs = []
    for k in ['kind', 'title', 'text', 'ask', 'input', 'answer', 'hint', 'explanation', 'verify']:
        if not str(c.get(k, '')).strip():
            errs.append(f'{k} 없음')
    if c.get('kind') not in KINDS:
        errs.append(f"kind는 {KINDS} 중 하나")
    if c.get('input') not in INPUTS:
        errs.append(f"input은 {INPUTS} 중 하나")
    if c.get('input') == 'choice':
        ch = c.get('choices') or []
        if len(ch) != 5 or len(set(map(str, ch))) != 5:
            errs.append('choice는 서로 다른 보기 5개')
        if norm(c.get('answer', ''), 'choice') not in {'1', '2', '3', '4', '5'}:
            errs.append('choice 정답은 1~5 번호')
    if c.get('input') == 'number' and not re.fullmatch(r'-?\d+(\.\d+)?', norm(c.get('answer', ''), 'number')):
        errs.append('number 정답이 숫자가 아님')
    if len(str(c.get('text', ''))) > 400:
        errs.append('text가 너무 길어요(400자 이하)')
    if len(c.get('clues') or []) > 8:
        errs.append('단서가 너무 많아요(8개 이하)')
    g = c.get('grid')
    if g is not None and not (isinstance(g, list) and all(isinstance(r, list) and r for r in g)):
        errs.append('grid 형식')
    ans = norm(c.get('answer', ''), c.get('input'))
    hint = unicodedata.normalize('NFC', str(c.get('hint', '')))
    if c.get('input') in ('number', 'text') and len(ans) >= 2 and ans in re.sub(r'[\s,]', '', hint).upper():
        errs.append('힌트에 정답이 드러나요')
    return errs


def run_verify(code):
    prog = code + "\n\nimport json as _j\nprint('@@RESULT@@' + _j.dumps(solve(), ensure_ascii=False, default=str))\n"
    try:
        r = subprocess.run([sys.executable, '-c', prog], capture_output=True, text=True, timeout=25)
    except subprocess.TimeoutExpired:
        return None, '시간 초과(25초)'
    if r.returncode != 0:
        return None, '코드 오류: ' + (r.stderr.strip().splitlines() or ['?'])[-1][:200]
    line = [x for x in r.stdout.splitlines() if x.startswith('@@RESULT@@')]
    if not line:
        return None, '결과 없음'
    try:
        return json.loads(line[-1][len('@@RESULT@@'):]), ''
    except Exception as e:  # noqa: BLE001
        return None, f'결과 읽기 실패: {e}'


def cmd_check(paths):
    total = ok = 0
    for p in paths:
        cands = load(p)
        stem = Path(p).stem
        for i, c in enumerate(cands):
            total += 1
            c['_cid'] = c.get('_cid') or f'{stem}-{i + 1}'
            errs = check_fields(c)
            res = None
            if not errs:
                res, err = run_verify(c['verify'])
                if err:
                    errs.append(err)
                else:
                    if norm(res.get('answer'), c['input']) != norm(c['answer'], c['input']):
                        errs.append(f"verify 정답({res.get('answer')})이 answer({c['answer']})와 달라요")
                    if res.get('solutions') != 1:
                        errs.append(f"경우의 수가 1이 아니에요({res.get('solutions')})")
            c['_ok1'] = not errs
            c['_why'] = '; '.join(errs)
            ok += c['_ok1']
            print(f"{'통과' if c['_ok1'] else '탈락'} {c['_cid']:<16} [{c.get('kind')}] {c.get('title')} {('— ' + c['_why']) if errs else ''}")
        save(p, cands)
    print(f'1차 확인: {ok}/{total} 통과')


def cmd_strip(src, dst):
    out = []
    for c in load(src):
        if not c.get('_ok1'):
            continue
        out.append({k: c[k] for k in ['_cid', 'kind', 'title', 'text', 'clues', 'grid', 'ask', 'input', 'choices', 'unit'] if k in c})
    save(dst, out)
    print(f'풀이용 {len(out)}문제 → {dst} (정답·풀이·힌트·코드 없음)')


def cmd_compare(src, solved_path):
    cands = load(src)
    solved = {s['_cid']: s for s in load(solved_path)}
    ok = 0
    for c in cands:
        if not c.get('_ok1'):
            continue
        s = solved.get(c['_cid'])
        if not s:
            c['_ok2'] = False
            c['_why'] = (c.get('_why') + '; ' if c.get('_why') else '') + '따로 풀기 결과 없음'
        else:
            c['_ok2'] = norm(s.get('answer', ''), c['input']) == norm(c['answer'], c['input'])
            if not c['_ok2']:
                c['_why'] = (c.get('_why') + '; ' if c.get('_why') else '') + f"따로 푼 답이 달라요({s.get('answer')})"
        ok += bool(c.get('_ok2'))
        print(f"{'같음' if c.get('_ok2') else '다름'} {c['_cid']:<16} [{c['kind']}] {c['title']}")
    save(src, cands)
    print(f'2차 확인: {ok}개 같은 답')


def cmd_verdict(src, verdict_path):
    cands = load(src)
    vs = {v['_cid']: v for v in load(verdict_path)}
    ok = 0
    for c in cands:
        if not (c.get('_ok1') and c.get('_ok2')):
            continue
        v = vs.get(c['_cid'])
        c['_ok3'] = bool(v and v.get('ok') is True)
        if not c['_ok3']:
            c['_why'] = (c.get('_why') + '; ' if c.get('_why') else '') + ('반박: ' + str((v or {}).get('reason', '결과 없음')))
        ok += c['_ok3']
        print(f"{'통과' if c['_ok3'] else '탈락'} {c['_cid']:<16} [{c['kind']}] {c['title']} {'' if c['_ok3'] else '— ' + str((v or {}).get('reason', ''))}")
    save(src, cands)
    print(f'3차 확인: {ok}개 통과')


# ---------------------------------------------------------------- 합치기
def public_item(c, pid, date, slot, n):
    it = {'id': pid, 'date': date, 'slot': slot, 'n': n, 'kind': c['kind'], 'title': c['title'], 'text': c['text']}
    for k in ['clues', 'grid']:
        if c.get(k):
            it[k] = c[k]
    it['ask'] = c['ask']
    it['input'] = c['input']
    if c['input'] == 'choice':
        it['choices'] = [str(x) for x in c['choices']]
    if c.get('unit'):
        it['unit'] = c['unit']
    it['hint'] = c['hint']
    it['h'] = answer_hash(pid, c['answer'], c['input'])
    it['x'] = lock(pid, c['answer'], c['input'], c['explanation'])
    it['level'] = 5
    return it


def cmd_build(src, today, days, dry):
    all_c = load(src)
    cands = [c for c in all_c if c.get('_ok1') and c.get('_ok2') and c.get('_ok3') and not c.get('_used')]
    doc = load_brain()
    placed = []
    for s in need(today, days):
        pick = []
        for k in s['kinds']:  # 추천 종류 먼저
            m = next((c for c in cands if c['kind'] == k and c not in pick), None)
            if m:
                pick.append(m)
        for c in cands:  # 모자라면 다른 종류로(판 안에서는 종류가 겹치지 않게)
            if len(pick) >= 3:
                break
            if c not in pick and c['kind'] not in {p['kind'] for p in pick}:
                pick.append(c)
        if len(pick) < 3:
            print(f"{s['date']} {s['slot']}: 세 번 다 통과한 후보가 모자라서 비워 둬요({len(pick)}/3)")
            continue
        date = datetime.date.fromisoformat(s['date'])
        for n, c in enumerate(pick, 1):
            pid = slot_id(date, s['slot'], n)
            doc['items'].append(public_item(c, pid, s['date'], s['slot'], n))
            c['_used'] = pid
            cands.remove(c)
        placed.append(f"{s['date']} {s['slot']}: " + ' / '.join(f"{c['kind']} '{c['title']}'" for c in pick))
    cutoff = (today - datetime.timedelta(days=KEEP_DAYS)).isoformat()
    doc['items'] = sorted([it for it in doc['items'] if it['date'] >= cutoff], key=lambda it: (it['date'], SLOTS.index(it['slot']), it['n']))
    doc['updatedAt'] = datetime.datetime.now(KST).replace(second=0, microsecond=0).isoformat()
    doc['note'] = '최상 난이도 두뇌 게임. 정답은 글자로 넣지 않고 확인값(h)만 두고, 풀이(x)는 맞힌 사람만 열려요.'
    for line in placed:
        print('채움 ' + line)
    if dry:
        print('(dry-run: 파일은 그대로예요)')
        return
    if not placed:
        print('새로 채운 판이 없어요')
        return
    errs = validate_doc(doc)
    if errs:
        sys.exit('형식 오류: ' + '; '.join(errs[:10]))
    save(BRAIN, doc)
    save(src, all_c)  # 쓴 후보에 _used 표시
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import version  # noqa: E402
    version.write()
    print(f"data/brain.json: {len(doc['items'])}문제")


def validate_doc(doc):
    errs = []
    ids = set()
    per = {}
    for it in doc.get('items', []):
        pid = it.get('id', '?')
        if pid in ids:
            errs.append(f'{pid}: id 중복')
        ids.add(pid)
        for k in ['id', 'date', 'slot', 'n', 'kind', 'title', 'text', 'ask', 'input', 'hint', 'h', 'x']:
            if k not in it or it[k] in ('', None):
                errs.append(f'{pid}: {k} 없음')
        if 'answer' in it or 'explanation' in it or 'verify' in it:
            errs.append(f'{pid}: 정답·풀이·코드가 그대로 들어 있어요')
        if not re.fullmatch(r'[0-9a-f]{64}', str(it.get('h', ''))):
            errs.append(f'{pid}: h 형식')
        try:
            base64.b64decode(str(it.get('x', '')), validate=True)
        except Exception:  # noqa: BLE001
            errs.append(f'{pid}: x 형식')
        if it.get('slot') not in SLOTS:
            errs.append(f'{pid}: slot')
        if it.get('input') == 'choice' and len(it.get('choices') or []) != 5:
            errs.append(f'{pid}: 보기 5개')
        per.setdefault((it.get('date'), it.get('slot')), []).append(it)
    for (d, s), arr in per.items():
        if len(arr) != 3:
            errs.append(f'{d} {s}: 문제가 {len(arr)}개(3개여야 해요)')
        if len({a.get('kind') for a in arr}) != len(arr):
            errs.append(f'{d} {s}: 같은 종류가 겹쳐요')
    return errs


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        sys.exit(2)
    cmd = a[0]

    def opt(name, default=None):
        return a[a.index(name) + 1] if name in a else default
    today = datetime.date.fromisoformat(opt('--today')) if opt('--today') else today_kst()
    days = int(opt('--days', 2))
    if cmd == 'need':
        print(json.dumps(need(today, days), ensure_ascii=False, indent=1))
    elif cmd == 'check':
        cmd_check([x for x in a[1:] if not x.startswith('--')])
    elif cmd == 'strip':
        cmd_strip(a[1], a[2])
    elif cmd == 'compare':
        cmd_compare(a[1], a[2])
    elif cmd == 'verdict':
        cmd_verdict(a[1], a[2])
    elif cmd == 'build':
        cmd_build(a[1], today, days, '--dry-run' in a)
    elif cmd == 'validate':
        path = a[1] if len(a) > 1 and not a[1].startswith('--') else BRAIN
        errs = validate_doc(load(path))
        print('\n'.join(errs) if errs else f'{path}: 오류 0')
        sys.exit(1 if errs else 0)
    elif cmd == 'status':
        for it in load_brain()['items']:
            print(f"{it['date']} {it['slot']} {it['n']} {it['id']} [{it['kind']}] {it['title']}")
    elif cmd == 'try':
        pid, ans = a[1], a[2]
        it = next((x for x in load_brain()['items'] if x['id'] == pid), None)
        if not it:
            sys.exit('그런 문제가 없어요')
        if answer_hash(pid, ans, it['input']) == it['h']:
            print('맞았어요\n' + unlock(pid, ans, it['input'], it['x']))
        else:
            print('틀렸어요')
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == '__main__':
    main()
