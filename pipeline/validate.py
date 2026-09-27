"""틈틈이 기사 검증기

사용: python3 pipeline/validate.py 파일.json [파일2.json ...] [--today YYYY-MM-DD]
- 파일은 기사 배열([...])이거나 {"articles": [...]} 모두 받아요.
- 오류(ERROR)가 하나라도 있으면 종료 코드 1이에요. 경고(WARN)는 되도록 고쳐요.
"""
import datetime
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CATS = json.loads((HERE / 'categories.json').read_text(encoding='utf-8'))
ALLOWED = {c['key']: c['subs'] for c in CATS['news'] + CATS['reading']}
READING = {c['key'] for c in CATS['reading']}
DATE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
# 읽는 날에 따라 뜻이 바뀌는 말(날짜로 바꿔 써야 해요). '오늘날'은 괜찮아요.
RELATIVE = re.compile(r'오늘(?!날)|내일|어제|(?<!아)모레(?!노)|그저께|그제|이번 ?주(?!간)|지난 ?주(?!간)|다음 ?주(?!간)|이달|지난달|다음 ?달')


def kst_today():
    return (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)).strftime('%Y-%m-%d')


def articles_of(data):
    if isinstance(data, dict) and isinstance(data.get('articles'), list):
        return data['articles']
    if isinstance(data, list):
        return data
    raise ValueError('기사 배열이나 {"articles": [...]} 형식이 아니에요')


def body_text(a):
    out = []
    for s in a.get('sections', []):
        out += s.get('p', []) + s.get('ol', []) + s.get('li', [])
    return ''.join(out)


def all_text(a):
    parts = [a.get('title', ''), a.get('dek', ''), a.get('why', '')] + a.get('summary3', []) + [body_text(a)]
    parts += [f.get('v', '') for f in a.get('facts', []) or []]
    return '\n'.join(parts)


def check(path, today):
    errs, warns = [], []
    try:
        arts = articles_of(json.loads(Path(path).read_text(encoding='utf-8')))
    except Exception as e:  # noqa: BLE001
        return [f'JSON을 읽을 수 없어요: {e}'], []
    ids, hot = set(), {}
    for a in arts:
        i = a.get('id', '?')
        E = lambda m, i=i: errs.append(f'[{i}] {m}')  # noqa: E731
        W = lambda m, i=i: warns.append(f'[{i}] {m}')  # noqa: E731
        for k in ['id', 'cat', 'sub', 'title', 'dek', 'date', 'summary3', 'sections', 'why', 'glossary', 'sources', 'readMin']:
            if k not in a or a[k] in (None, '', []):
                E(f'필수 칸 없음: {k}')
        if i in ids:
            E('id 중복')
        ids.add(i)
        cat = a.get('cat')
        if cat not in ALLOWED:
            E(f'cat 값이 잘못됨: {cat}')
        elif a.get('sub') not in ALLOWED[cat]:
            E(f"sub 값이 잘못됨: {a.get('sub')} (허용: {', '.join(ALLOWED[cat])})")
        if not re.match(rf'^{re.escape(str(cat))}-[0-9a-z-]+$', str(i)):
            E('id는 "분야-번호" 형식이어야 해요(예: stock-260928-1)')
        d = str(a.get('date', ''))
        if not DATE.match(d):
            E('date는 YYYY-MM-DD')
        elif cat not in READING and d > today:
            E(f'date가 미래예요({d}). 사건·보도 날짜를 넣어요(앞으로 열릴 일정은 본문·facts에)')
        if len(a.get('title', '')) > 34:
            W(f"title {len(a['title'])}자(32자 이내)")
        if len(a.get('dek', '')) > 64:
            W(f"dek {len(a['dek'])}자(60자 이내)")
        s3 = a.get('summary3', [])
        if len(s3) != 3:
            E('summary3는 정확히 3개')
        for s in s3:
            if len(s) > 50:
                W(f'summary3 항목 {len(s)}자(45자 이내)')
        secs = a.get('sections', [])
        if not (2 <= len(secs) <= 5):
            W(f'sections {len(secs)}개(3~4개)')
        for s in secs:
            if not s.get('h'):
                E('섹션 소제목(h) 없음')
            if not (s.get('p') or s.get('ol') or s.get('li')):
                E(f"섹션 '{s.get('h')}'에 내용(p/ol/li) 없음")
            for key in ('p', 'ol', 'li'):
                if key in s and not isinstance(s[key], list):
                    E(f'{key}는 문자열 배열이어야 해요')
        body = body_text(a)
        if len(body) < 550:
            W(f'본문 {len(body)}자로 짧아요')
        if len(body) > 1400:
            W(f'본문 {len(body)}자로 길어요')
        m = RELATIVE.findall(all_text(a))
        if m:
            W(f"읽는 날에 따라 뜻이 바뀌는 말: {', '.join(sorted(set(m)))} → 'N월 N일'처럼 날짜로")
        gl = a.get('glossary', [])
        if not (2 <= len(gl) <= 6):
            W(f'glossary {len(gl)}개(3~5개)')
        for g in gl:
            for k in ('term', 'short', 'long'):
                if not g.get(k):
                    E(f'glossary 항목에 {k} 없음')
            if g.get('term') and g['term'] not in body:
                E(f"glossary term '{g['term']}'이 본문(p/ol/li)에 글자 그대로 없어요")
        src = a.get('sources', [])
        if len(src) < 2:
            W('출처는 2개 이상')
        for s in src:
            if not re.match(r'^https?://', str(s.get('url', ''))):
                E('출처 url은 http(s)://로 시작해야 해요')
            for k in ('name', 'title'):
                if not s.get(k):
                    E(f'출처에 {k} 없음')
        for f in a.get('facts', []) or []:
            if not f.get('k') or not f.get('v'):
                E('facts 항목은 k와 v가 필요해요')
            elif len(f['v']) > 48:
                W(f"facts '{f['k']}' 값이 {len(f['v'])}자(40자 이내)")
            if f.get('url') and not re.match(r'^https?://', str(f['url'])):
                E('facts url은 http(s)://로 시작해야 해요')
        if cat == 'events':
            w = a.get('when') or {}
            if not DATE.match(str(w.get('start', ''))) or not DATE.match(str(w.get('end', ''))):
                E('행사는 when.start / when.end(YYYY-MM-DD) 필수')
            else:
                if w['end'] < w['start']:
                    E('when.end가 start보다 빨라요')
                if w['end'] < today:
                    E('이미 끝난 행사예요')
        if cat == 'history' and not a.get('era'):
            W('역사 글은 era(시대·연도) 권장')
        if cat == 'history' and a.get('sub') == '우리 동네 역사' and not a.get('place'):
            E('우리 동네 역사는 place 필수')
        rep = a.get('replaces')
        if rep is not None and not (isinstance(rep, list) and all(isinstance(x, str) for x in rep)):
            E('replaces는 옛 기사 id 문자열 배열이어야 해요')
        if a.get('hot'):
            hot[cat] = hot.get(cat, 0) + 1
        try:
            if int(a.get('readMin', 0)) < 1:
                E('readMin은 1 이상')
        except Exception:  # noqa: BLE001
            E('readMin은 숫자')
    for c, k in hot.items():
        if k > 1:
            errs.append(f'{c}: hot이 {k}개(분야마다 최대 1개)')
    return errs, warns


if __name__ == '__main__':
    args = sys.argv[1:]
    today = kst_today()
    if '--today' in args:
        k = args.index('--today')
        today = args[k + 1]
        del args[k:k + 2]
    total = 0
    for p in args:
        e, w = check(p, today)
        total += len(e)
        print(f'== {p}: 오류 {len(e)}개, 경고 {len(w)}개 (기준일 {today})')
        for m in e:
            print('ERROR', m)
        for m in w:
            print('WARN ', m)
    sys.exit(1 if total else 0)
