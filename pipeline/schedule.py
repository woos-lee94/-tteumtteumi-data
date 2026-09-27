"""오늘 할 일 알려 주기(매일 절차 1단계에서 실행)

- news: 매일
- reading(역사·생활 읽을거리): 일요일(한국 시간)
- cards(상식·유래 카드): 2026-09-28부터 이틀마다
사용: python3 pipeline/schedule.py [--today YYYY-MM-DD]
"""
import datetime
import json
import sys

CARDS_START = datetime.date(2026, 9, 28)
CARDS_EVERY = 2
CARDS_PER_RUN = {'trivia': 5, 'origin': 5}

args = sys.argv[1:]
if '--today' in args:
    today = datetime.date.fromisoformat(args[args.index('--today') + 1])
else:
    today = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)).date()
plan = {
    'today': today.isoformat(),
    'yymmdd': today.strftime('%y%m%d'),
    'weekday': '월화수목금토일'[today.weekday()] + '요일',
    'news': True,
    'reading': today.weekday() == 6,
    'cards': (today - CARDS_START).days >= 0 and (today - CARDS_START).days % CARDS_EVERY == 0,
    'cards_per_run': CARDS_PER_RUN,
}
print(json.dumps(plan, ensure_ascii=False, indent=1))
