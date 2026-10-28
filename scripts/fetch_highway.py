# -*- coding: utf-8 -*-
"""한국도로공사 OpenAPI 고속도로 주유소 유가(curStateStation) → data/highway.json.
인증 없이 key=test 로 호출 가능(2026-10 확인). 실패하거나 건수가 이상하면 기존 파일을 유지하고 종료 코드 1."""
import sys, json, time, pathlib, datetime, requests
sys.stdout.reconfigure(encoding="utf-8")
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "highway.json"
rows = []; p = 1; count = 0
while True:
    r = None
    for t in range(3):
        try:
            r = requests.get("https://data.ex.co.kr/openapi/business/curStateStation", params=dict(key="test", type="json", numOfRows=100, pageNo=p), headers={"User-Agent": "Mozilla/5.0"}, timeout=60).json(); break
        except Exception: time.sleep(3)
    if not r: sys.exit("fetch failed")
    L = r.get("list") or []; count = r.get("count", 0); rows += L
    if len(rows) >= count or not L: break
    p += 1
if len(rows) < 150 or len(rows) != count:
    sys.exit("unexpected count %s/%s — keep old file" % (len(rows), count))
kst = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) + datetime.timedelta(hours=9)
OUT.parent.mkdir(exist_ok=True)
OUT.write_text(json.dumps({"fetched": kst.strftime("%Y-%m-%d %H:%M"), "rows": rows}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
print("highway stations", len(rows), kst.strftime("%Y-%m-%d %H:%M"))
