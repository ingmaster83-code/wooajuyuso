# -*- coding: utf-8 -*-
"""우아주유소 정적 사이트 생성기 → _site/.  입력: data/highway.json (fetch_highway.py, 한국도로공사 OpenAPI)
오피넷(시군구 최저가·평균가)은 인증키 확보 후 data/opinet.json 으로 추가 예정 — 파일이 있으면 해당 페이지를 함께 만든다."""
import sys, json, re, shutil, time, collections, statistics
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from common import *

H = json.loads((ROOT / "data" / "highway.json").read_text(encoding="utf-8"))
ASOF = H["fetched"]; ASOF_D = ASOF[:10]
BRAND = {"AD": "알뜰주유소(한국도로공사)", "SK": "SK에너지", "S": "S-OIL", "HD": "HD현대오일뱅크", "GS": "GS칼텍스", "NH": "NH농협"}
NOTE = ("가격은 한국도로공사 OpenAPI(고속도로 휴게소 주유소 유가)를 %s에 받아온 값이며 실제 판매가는 수시로 바뀝니다. 휘발유·경유·LPG 가격은 1리터 기준이고 주유 전 현장 가격표를 확인하세요." % ASOF)

def table(heads, rows, num=()):
    th = "".join('<th%s>%s</th>' % (' class="num"' if i in num else "", h) for i, h in enumerate(heads))
    body = "".join("<tr>%s</tr>" % "".join('<td%s>%s</td>' % (' class="num"' if i in num else "", v) for i, v in enumerate(r)) for r in rows)
    return '<div class="tbl-wrap"><table class="tbl"><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>' % (th, body)
def chips(items): return '<div class="chips">%s</div>' % "".join('<a class="chip" href="%s">%s</a>' % (u, esc(t)) for t, u in items)
def sl(s): return re.sub(r"[^0-9A-Za-z가-힣]+", "-", s).strip("-") or "x"
def price(s):
    v = re.sub(r"[^0-9]", "", s or "")
    return int(v) if v and int(v) > 0 else None
def won(x): return "-" if x is None else "{:,}원".format(int(round(x)))
def dif(a, b):
    if a is None or b is None: return ""
    d = a - b
    return "평균과 같음" if round(d) == 0 else ("평균보다 %s원 %s" % ("{:,}".format(abs(int(round(d)))), "비쌈" if d > 0 else "저렴"))

FUELS = [("gasoline", "휘발유", "gas"), ("diesel", "경유", "dsl"), ("lpg", "LPG", "lpg")]
S = []
for r in H["rows"]:
    name = r["serviceAreaName"].strip(); base = re.sub(r"주유소$", "", name)
    d = {"code": r["serviceAreaCode"], "name": name, "short": base, "route": r["routeName"] or ("노선 " + str(r.get("routeCode") or "기타")), "dir": r["direction"] or "양방향", "brand": r["oilCompany"], "tel": r["telNo"], "addr": (r["svarAddr"] or "").strip(),
         "gas": price(r["gasolinePrice"]), "dsl": price(r["diselPrice"]), "lpg": price(r["lpgPrice"]) if r.get("lpgYn") == "Y" else None, "lpgYn": r.get("lpgYn") == "Y"}
    d["bname"] = BRAND.get(d["brand"], d["brand"]); d["path"] = "/highway/%s/" % (sl(base) + "-" + d["code"].lower())
    S.append(d)
ROUTES = collections.OrderedDict()
for d in sorted(S, key=lambda x: (x["route"], x["dir"], x["name"])): ROUTES.setdefault(d["route"], []).append(d)
ROUTE_SLUG = {r: sl(r) for r in ROUTES}
BR = collections.defaultdict(list)
for d in S: BR[d["brand"]].append(d)
def avg(lst, k):
    v = [x[k] for x in lst if x[k]]; return (sum(v) / len(v)) if v else None
AVG = {k: avg(S, k) for _, _, k in FUELS}
def rank(d, lst, k, rev=False):
    s = sorted([x for x in lst if x[k]], key=lambda x: (-x[k] if rev else x[k], x["code"]))
    for i, x in enumerate(s):
        if x is d: return i + 1, len(s)
def link(d, t=None): return '<a href="%s">%s</a>' % (d["path"], esc(t or d["name"]))
def prow(d): return [link(d), esc(d["route"]), esc(d["dir"]) + " 방향", esc(d["bname"]), won(d["gas"]), won(d["dsl"]), won(d["lpg"]) if d["lpgYn"] else "-"]
PH = ["주유소", "노선", "방향", "정유사", "휘발유", "경유", "LPG"]
def ld_station(d):
    o = {"@context": "https://schema.org", "@type": "GasStation", "name": d["name"], "address": {"@type": "PostalAddress", "streetAddress": d["addr"], "addressCountry": "KR"}}
    if d["tel"]: o["telephone"] = d["tel"]
    return [o]

# ───────────────────────── 주유소 상세 ─────────────────────────
def page_station(d):
    rt = ROUTES[d["route"]]; r_g = rank(d, S, "gas"); r_rg = rank(d, rt, "gas"); r_d = rank(d, S, "dsl")
    parts = []
    if d["gas"]: parts.append("휘발유 <b>%s</b>(%s)" % (won(d["gas"]), dif(d["gas"], AVG["gas"])))
    if d["dsl"]: parts.append("경유 <b>%s</b>(%s)" % (won(d["dsl"]), dif(d["dsl"], AVG["dsl"])))
    if d["lpg"]: parts.append("LPG <b>%s</b>" % won(d["lpg"]))
    lead = "<b>%s</b>은(는) %s %s 방향에 있는 %s 고속도로 주유소입니다. %s 기준 %s입니다.%s" % (esc(d["name"]), esc(d["route"]), esc(d["dir"]), esc(d["bname"]), ASOF_D, ", ".join(parts) or "가격 정보가 없습니다",
        (" 전국 고속도로 주유소 %d곳 중 휘발유가 %d번째로 저렴하고 같은 노선(%s) %d곳 중에서는 %d번째입니다." % (r_g[1], r_g[0], esc(d["route"]), r_rg[1], r_rg[0])) if r_g and r_rg else "")
    rows = [["휘발유", won(d["gas"]), won(AVG["gas"]), won(avg(rt, "gas")), "%d위 / %d곳" % r_g if r_g else "-"], ["경유", won(d["dsl"]), won(AVG["dsl"]), won(avg(rt, "dsl")), "%d위 / %d곳" % r_d if r_d else "-"]]
    if d["lpg"]: rl = rank(d, S, "lpg"); rows.append(["LPG", won(d["lpg"]), won(AVG["lpg"]), won(avg(rt, "lpg")), "%d위 / %d곳" % rl if rl else "-"])
    t1 = table(["유종", "이 주유소", "고속도로 전체 평균", "%s 평균" % esc(d["route"]), "저렴한 순위(전국)"], rows, (1, 2, 3, 4))
    info = table(["항목", "내용"], [["주유소", esc(d["name"])], ["노선·방향", esc(d["route"]) + " " + esc(d["dir"]) + " 방향"], ["정유사", esc(d["bname"])], ["주소", esc(d["addr"] or "-")], ["전화", ('<a href="tel:%s">%s</a>' % (re.sub(r"[^0-9]", "", d["tel"]), esc(d["tel"]))) if d["tel"] else "-"], ["LPG 취급", "취급" if d["lpgYn"] else "미취급"], ["가격 기준", ASOF]])
    near = [x for x in rt if x is not d][:12]
    near_t = ('<h2 class="group-title">🛣️ %s의 다른 주유소</h2>' % esc(d["route"]) + table(PH, [prow(x) for x in near], (4, 5, 6))) if near else ""
    body = f"""
<div class="page-head"><h1>{esc(d['name'])} 유가 — {esc(d['route'])} {esc(d['dir'])} 방향</h1><p>{esc(d['bname'])} · 고속도로 주유소 · {ASOF_D} 기준</p></div>
<p class="lead">{lead}</p>
{ad()}
<h2 class="group-title">⛽ 유종별 가격 비교</h2>
{t1}
<h2 class="group-title">📋 주유소 정보</h2>
{info}
{near_t}
<p class="note">{NOTE}</p>
{chips([(d['route'] + ' 주유소', '/highway/route/%s/' % ROUTE_SLUG[d['route']]), (d['bname'] + ' 주유소', '/brand/%s/' % d['brand']), ('휘발유 저렴한 순', '/rank/gasoline/'), ('고속도로 주유소 전체', '/highway/')])}
"""
    faq = [("%s 휘발유 가격은 얼마인가요?" % d["name"], "%s 기준 %s입니다(고속도로 주유소 평균 %s)." % (ASOF_D, won(d["gas"]), won(AVG["gas"]))), ("%s 전화번호는?" % d["name"], d["tel"] or "공개된 전화번호가 없습니다."),
           ("고속도로 주유소 기름값은 매일 바뀌나요?", "가격은 수시로 바뀌며 이 사이트는 하루 한 번 한국도로공사 자료를 받아 갱신합니다.")]
    write(d["path"], layout(d["path"], "%s 유가 — %s %s 방향 (휘발유 %s)" % (d["name"], d["route"], d["dir"], won(d["gas"])), "%s(%s %s 방향) 휘발유 %s·경유 %s%s. 고속도로 평균·같은 노선 주유소와 가격 비교(%s)." % (d["name"], d["route"], d["dir"], won(d["gas"]), won(d["dsl"]), (" LPG " + won(d["lpg"])) if d["lpg"] else "", ASOF_D), body, faq,
          [("홈", "/"), ("고속도로 주유소", "/highway/"), (d["route"], "/highway/route/%s/" % ROUTE_SLUG[d["route"]]), (d["short"], d["path"])], extra_ld=ld_station(d)), "0.6")

# ───────────────────────── 노선 · 정유사 ─────────────────────────
def page_route(rt):
    lst = ROUTES[rt]; path = "/highway/route/%s/" % ROUTE_SLUG[rt]
    cheap = min([x for x in lst if x["gas"]], key=lambda x: x["gas"]) if any(x["gas"] for x in lst) else None
    body = f"""
<div class="page-head"><h1>{esc(rt)} 고속도로 주유소 {len(lst)}곳 — 휘발유·경유 가격 비교</h1><p>{ASOF_D} 기준</p></div>
<p class="lead"><b>{esc(rt)}</b>에는 고속도로 주유소 {len(lst)}곳이 있습니다. 휘발유 평균은 {won(avg(lst, 'gas'))}, 경유 평균은 {won(avg(lst, 'dsl'))}이며{(' 휘발유가 가장 저렴한 곳은 %s(%s)입니다.' % (link(cheap), won(cheap['gas']))) if cheap else ''} 전국 고속도로 평균은 휘발유 {won(AVG['gas'])}입니다.</p>
{ad()}
{table(PH, [prow(x) for x in lst], (4, 5, 6))}
<p class="note">{NOTE}</p>
{chips([("고속도로 노선 전체", "/highway/"), ("휘발유 저렴한 순", "/rank/gasoline/"), ("경유 저렴한 순", "/rank/diesel/")])}
"""
    faq = [("%s 주유소는 몇 곳인가요?" % rt, "%s 기준 %d곳입니다." % (ASOF_D, len(lst))), ("%s 휘발유 평균 가격은?" % rt, "%s입니다." % won(avg(lst, "gas")))]
    write(path, layout(path, "%s 고속도로 주유소 %d곳 — 휘발유·경유 가격 (%s)" % (rt, len(lst), ASOF_D), "%s 고속도로 주유소 %d곳의 휘발유·경유·LPG 가격 비교. 휘발유 평균 %s (%s 기준)." % (rt, len(lst), won(avg(lst, "gas")), ASOF_D), body, faq, [("홈", "/"), ("고속도로 주유소", "/highway/"), (rt, path)]), "0.7")
def page_brand(code):
    lst = sorted(BR[code], key=lambda x: (x["gas"] or 1e9)); path = "/brand/%s/" % code; nm = BRAND.get(code, code)
    body = f"""
<div class="page-head"><h1>{esc(nm)} 고속도로 주유소 {len(lst)}곳 — 가격 비교</h1><p>{ASOF_D} 기준</p></div>
<p class="lead">{esc(nm)} 브랜드 고속도로 주유소는 {len(lst)}곳이며 휘발유 평균 {won(avg(lst, 'gas'))}, 경유 평균 {won(avg(lst, 'dsl'))}입니다(전국 고속도로 평균 휘발유 {won(AVG['gas'])}). 휘발유가 저렴한 순서로 정렬했습니다.</p>
{ad()}
{table(PH, [prow(x) for x in lst[:250]], (4, 5, 6))}
<p class="note">{NOTE}</p>
{chips([("정유사 전체", "/brand/"), ("고속도로 주유소 전체", "/highway/")])}
"""
    write(path, layout(path, "%s 고속도로 주유소 %d곳 — 휘발유·경유 가격 (%s)" % (nm, len(lst), ASOF_D), "%s 고속도로 주유소 %d곳의 가격 비교. 휘발유 평균 %s·경유 평균 %s." % (nm, len(lst), won(avg(lst, "gas")), won(avg(lst, "dsl"))), body, [("%s 주유소는 몇 곳인가요?" % nm, "%s 기준 고속도로에 %d곳입니다." % (ASOF_D, len(lst)))], [("홈", "/"), ("정유사별", "/brand/"), (nm, path)]), "0.6")
def hub_brand():
    rows = [['<a href="/brand/%s/">%s</a>' % (c, esc(BRAND.get(c, c))), len(BR[c]), won(avg(BR[c], "gas")), won(avg(BR[c], "dsl"))] for c in sorted(BR, key=lambda c: -len(BR[c]))]
    body = f"""
<div class="page-head"><h1>정유사별 고속도로 주유소 가격 비교</h1><p>{ASOF_D} 기준</p></div>
<p class="lead">고속도로 주유소를 운영 정유사(브랜드)별로 나눠 평균 가격을 비교했습니다. 알뜰주유소는 한국도로공사가 운영하는 고속도로 알뜰주유소입니다.</p>
{ad()}
{table(['정유사', '주유소 수', '휘발유 평균', '경유 평균'], rows, (1, 2, 3))}
<p class="note">{NOTE}</p>
{chips([("고속도로 주유소 전체", "/highway/"), ("휘발유 순위", "/rank/gasoline/")])}
"""
    write("/brand/", layout("/brand/", "정유사별 고속도로 주유소 가격 비교 — 알뜰·SK·S-OIL·HD현대오일뱅크", "고속도로 주유소를 정유사별로 비교한 휘발유·경유 평균 가격(%s 기준)." % ASOF_D, body, None, [("홈", "/"), ("정유사별", "/brand/")], coupang=True), "0.8")

# ───────────────────────── 순위 · 허브 · 홈 ─────────────────────────
def page_rank(slug, label, k):
    cheap = sorted([x for x in S if x[k]], key=lambda x: (x[k], x["code"])); dear = cheap[::-1]; path = "/rank/%s/" % slug
    body = f"""
<div class="page-head"><h1>고속도로 {label} 가격 순위 — 저렴한 주유소 TOP 30</h1><p>{ASOF_D} 기준 · 전국 {len(cheap)}곳</p></div>
<p class="lead">고속도로 주유소 {len(cheap)}곳 중 {label}가 가장 저렴한 곳은 <b>{link(cheap[0])}</b>({esc(cheap[0]['route'])} {esc(cheap[0]['dir'])} 방향, {won(cheap[0][k])})이고 가장 비싼 곳은 {link(dear[0])}({won(dear[0][k])})입니다. 전국 고속도로 평균은 {won(AVG[k])}입니다.</p>
{ad()}
<h2 class="group-title">💰 {label} 저렴한 주유소 TOP 30</h2>
{table(['순위'] + PH, [[str(i + 1)] + prow(x) for i, x in enumerate(cheap[:30])], (0, 5, 6, 7))}
<h2 class="group-title">📈 {label} 비싼 주유소 TOP 10</h2>
{table(['순위'] + PH, [[str(i + 1)] + prow(x) for i, x in enumerate(dear[:10])], (0, 5, 6, 7))}
<p class="note">{NOTE}</p>
{chips([(l2 + " 순위", "/rank/%s/" % s2) for s2, l2, _ in FUELS if s2 != slug] + [("정유사별", "/brand/"), ("고속도로 주유소 전체", "/highway/")])}
"""
    faq = [("고속도로에서 %s가 가장 싼 주유소는?" % label, "%s 기준 %s(%s)입니다." % (ASOF_D, cheap[0]["name"], won(cheap[0][k])))]
    write(path, layout(path, "고속도로 %s 가격 순위 — 저렴한 주유소 TOP 30 (%s)" % (label, ASOF_D), "고속도로 주유소 %d곳의 %s 가격 순위. 최저가 %s(%s)." % (len(cheap), label, cheap[0]["name"], won(cheap[0][k])), body, faq, [("홈", "/"), ("순위", "/rank/gasoline/"), (label, path)], coupang=True), "0.9")
def hub_highway():
    rows = [['<a href="/highway/route/%s/">%s</a>' % (ROUTE_SLUG[r], esc(r)), len(l), won(avg(l, "gas")), won(avg(l, "dsl"))] for r, l in ROUTES.items()]
    body = f"""
<div class="page-head"><h1>고속도로 주유소 유가 — 노선별 {len(S)}곳 가격 비교</h1><p>{ASOF_D} 기준 · 한국도로공사</p></div>
<p class="lead">전국 고속도로 휴게소 주유소 {len(S)}곳의 휘발유·경유·LPG 가격을 노선별로 정리했습니다. 전국 고속도로 평균은 휘발유 {won(AVG['gas'])}, 경유 {won(AVG['dsl'])}이며 노선을 누르면 방향별 주유소와 가격을 볼 수 있습니다.</p>
{ad()}
{table(['노선', '주유소 수', '휘발유 평균', '경유 평균'], rows, (1, 2, 3))}
<p class="note">{NOTE}</p>
{chips([("휘발유 순위", "/rank/gasoline/"), ("경유 순위", "/rank/diesel/"), ("LPG 순위", "/rank/lpg/"), ("정유사별", "/brand/")])}
"""
    write("/highway/", layout("/highway/", "고속도로 주유소 유가 — 노선별 휘발유·경유 가격 비교 (%s)" % ASOF_D, "전국 고속도로 주유소 %d곳의 휘발유·경유·LPG 가격을 노선별로 비교. 휘발유 평균 %s (%s 기준)." % (len(S), won(AVG["gas"]), ASOF_D), body, None, [("홈", "/"), ("고속도로 주유소", "/highway/")], coupang=True), "0.9")
def mini(k, n=5):
    c = sorted([x for x in S if x[k]], key=lambda x: (x[k], x["code"]))[:n]
    return table(["순위", "주유소", "노선", "가격"], [[str(i + 1), link(x), esc(x["route"]) + " " + esc(x["dir"]), won(x[k])] for i, x in enumerate(c)], (0, 3))
def page_home():
    body = f"""
<div class="hero"><h1>⛽ 고속도로 주유소 유가 — 가장 싼 곳은?</h1><p>전국 {len(S)}곳 휘발유·경유·LPG 가격 · {ASOF_D} 기준 매일 갱신</p></div>
{ad()}
<div class="card-grid">
<a class="card" href="/highway/"><b>🛣️ 노선별 주유소</b><span>경부선·서해안선 등 {len(ROUTES)}개 노선</span></a>
<a class="card" href="/rank/gasoline/"><b>⛽ 휘발유 순위</b><span>가장 저렴한 주유소</span></a>
<a class="card" href="/rank/diesel/"><b>🚚 경유 순위</b><span>가장 저렴한 주유소</span></a>
<a class="card" href="/rank/lpg/"><b>🔥 LPG 순위</b><span>LPG 취급 주유소</span></a>
<a class="card" href="/brand/"><b>🏷️ 정유사별</b><span>알뜰·SK·S-OIL·HD현대</span></a>
</div>
<h2 class="group-title">💰 휘발유 가장 저렴한 고속도로 주유소 TOP 5</h2>{mini('gas')}
<h2 class="group-title">🚚 경유 가장 저렴한 고속도로 주유소 TOP 5</h2>{mini('dsl')}
<p class="lead">우아주유소는 한국도로공사 OpenAPI의 고속도로 휴게소 주유소 유가를 하루 한 번 받아 정리한 사이트입니다. 전국 고속도로 평균 가격은 휘발유 {won(AVG['gas'])}, 경유 {won(AVG['dsl'])}, LPG {won(AVG['lpg'])}입니다. 일반 도로 주유소 가격과 시군구별 최저가는 자료를 확보하는 대로 추가할 예정입니다. 자세한 기준은 <a href="/about/">데이터 설명</a>을 참고하세요.</p>
"""
    faq = [("가격은 얼마나 자주 갱신되나요?", "하루 한 번(새벽) 한국도로공사 OpenAPI에서 받아 갱신하며 기준 시각은 각 페이지에 표시됩니다."), ("일반 주유소 가격도 볼 수 있나요?", "현재는 고속도로 주유소만 제공하며 일반 주유소와 시군구별 최저가는 추후 추가될 예정입니다.")]
    write("/", layout("/", "우아주유소 — 고속도로 주유소 유가 비교 (휘발유·경유·LPG 최저가)", "전국 고속도로 주유소 %d곳의 휘발유·경유·LPG 가격을 노선·정유사별로 비교. 휘발유 평균 %s (%s 기준, 매일 갱신)." % (len(S), won(AVG["gas"]), ASOF_D), body, faq), "1.0")
def page_about():
    body = f"""
<div class="page-head"><h1>데이터 설명</h1><p>정보의 출처와 한계</p></div>
<h2 class="group-title">📚 출처</h2><p class="lead">한국도로공사 고속도로 공공데이터 포털 OpenAPI ‘고속도로 휴게소 주유소 현황(curStateStation)’의 주유소별 휘발유·경유·LPG 판매가격, 정유사, 노선·방향, 주소, 전화번호를 사용합니다. 하루 한 번 새벽에 자동으로 받아 사이트를 다시 만들며 최근 기준 시각은 {ASOF}입니다.</p>
<h2 class="group-title">⚠️ 한계</h2><p class="lead">주유소 가격은 수시로 바뀌며 실제 판매가와 차이가 있을 수 있습니다. 일반 도로 주유소와 시군구별 최저가는 아직 포함되어 있지 않습니다. 주유 전 현장 가격표를 확인하세요.</p>
<h2 class="group-title">📬 문의·정정</h2><p class="lead">오류 제보는 <a href="mailto:ingmaster83@gmail.com">ingmaster83@gmail.com</a> 으로 보내 주세요.</p>
"""
    write("/about/", layout("/about/", "데이터 설명 — 출처와 한계", "우아주유소 데이터 출처(한국도로공사 OpenAPI)와 갱신 주기, 한계.", body, None, [("홈", "/"), ("데이터 설명", "/about/")]), "0.5")
def page_privacy():
    body = """
<div class="page-head"><h1>개인정보처리방침</h1></div>
<p class="lead">우아주유소(wooajuyuso.wooahouse.com, 이하 “서비스”)는 회원가입·로그인을 요구하지 않으며 이용자의 개인정보를 직접 수집하지 않습니다.</p>
<h3>자동 수집 정보</h3><p class="lead">서비스 개선을 위해 Google Analytics로 방문자 수·페이지뷰 등 익명 통계를 수집하며, Google AdSense와 쿠팡 파트너스는 맞춤 광고를 위해 쿠키를 사용할 수 있습니다. 쿠키는 브라우저 설정에서 비활성화할 수 있습니다. (<a href="https://policies.google.com/privacy">Google 개인정보처리방침</a>, <a href="https://policies.google.com/technologies/ads">Google 광고 정책</a>)</p>
<h3>쿠팡 파트너스</h3><p class="lead">일부 페이지에는 쿠팡 파트너스 활동의 일환으로 광고가 포함되어 있으며 이에 따른 수수료를 제공받을 수 있습니다.</p>
<h3>문의</h3><p class="lead"><a href="mailto:ingmaster83@gmail.com">ingmaster83@gmail.com</a></p>
<p class="note">최종 수정일: 2026년 10월 28일</p>
"""
    write("/privacy/", layout("/privacy/", "개인정보처리방침", "우아주유소 개인정보처리방침", body, None, [("홈", "/"), ("개인정보처리방침", "/privacy/")]), sitemap=False)
def make_og():
    f = ROOT / "assets" / "og-image.png"
    if f.exists(): return
    try: from PIL import Image, ImageDraw, ImageFont
    except Exception: return
    im = Image.new("RGB", (1200, 630), (220, 38, 38)); dr = ImageDraw.Draw(im)
    def font(sz):
        for n_ in ("malgunbd.ttf", "malgun.ttf", "NanumGothicBold.ttf"):
            try: return ImageFont.truetype(n_, sz)
            except Exception: pass
        return ImageFont.load_default()
    dr.rounded_rectangle((90, 90, 1110, 540), 40, fill=(255, 255, 255))
    dr.text((150, 150), "우아주유소", font=font(110), fill=(153, 27, 27))
    dr.text((150, 310), "고속도로 주유소 유가 비교", font=font(54), fill=(31, 41, 55))
    dr.text((150, 390), "휘발유 · 경유 · LPG 최저가", font=font(54), fill=(31, 41, 55))
    dr.text((150, 480), "wooajuyuso.wooahouse.com", font=font(34), fill=(107, 114, 128))
    im.save(f)
def main():
    t0 = time.time(); make_og()
    if OUT.exists(): shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copytree(ROOT / "assets", OUT / "assets", dirs_exist_ok=True)
    for nf in ROOT.glob("naver*.html"): shutil.copy(nf, OUT / nf.name)
    for d in S: page_station(d)
    for rt in ROUTES: page_route(rt)
    for c in BR: page_brand(c)
    hub_brand(); hub_highway()
    for slug, label, k in FUELS: page_rank(slug, label, k)
    page_home(); page_about(); page_privacy()
    urls = "".join("<url><loc>%s%s</loc><lastmod>%s</lastmod><priority>%s</priority></url>" % (BASE, q(p), ASOF_D, pr_) for p, pr_ in WRITTEN)
    (OUT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">%s</urlset>\n' % urls, encoding="utf-8")
    (OUT / "robots.txt").write_text("User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n" % BASE, encoding="utf-8")
    (OUT / "CNAME").write_text("wooajuyuso.wooahouse.com\n", encoding="utf-8")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    nf = layout("/404.html", "페이지를 찾을 수 없습니다", "요청한 페이지를 찾을 수 없습니다.", '<div class="page-head"><h1>페이지를 찾을 수 없습니다</h1></div><div class="chips"><a class="chip" href="/">홈</a><a class="chip" href="/highway/">고속도로 주유소</a></div>', None, None, noindex=True)
    (OUT / "404.html").write_text(nf, encoding="utf-8")
    print("pages", len(WRITTEN), "elapsed", round(time.time() - t0), "s")

if __name__ == "__main__":
    main()
