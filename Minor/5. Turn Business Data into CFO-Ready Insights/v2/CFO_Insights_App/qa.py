"""Ask-your-invoices engine (v2): 25 questions + 13 graphs, a rule-based matcher and answer composer.
No API key and no external model: every answer is calculated from the loaded data at the moment it is asked."""
import random, re
from datetime import date

MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MONFULL = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
ASOF = "2026-10-22"
FLAG_RE = re.compile(r"estimated|Negative|before issue|assumed|Unreadable|Unknown Client", re.I)

# id, question, key phrases (3 pts each), words (1 pt each)
CATALOG = [
    ("f1", "How much have I invoiced, collected and still have outstanding?", ["how much have i invoiced", "total invoiced", "total collected", "how much have i collected", "how much is outstanding", "overview", "summary", "headline", "how am i doing"], ["invoiced", "collected", "outstanding", "total", "billed", "income", "earned"]),
    ("f2", "What is my collection rate?", ["collection rate", "collection percentage", "percent collected", "% collected", "how much of my billing"], ["collection", "rate", "percentage", "percent", "collected"]),
    ("f3", "Who are my top 3 clients, and what share do they hold?", ["top 3", "top three", "three clients", "best 3"], ["top", "best", "biggest", "largest", "clients", "share"]),
    ("f4", "Who are my top 5 clients?", ["top 5", "top five", "five clients", "best 5"], ["top", "best", "biggest", "largest", "clients"]),
    ("f5", "Which client owes me the most right now?", ["owes me the most", "owe me the most", "who owes", "owes the most", "most outstanding", "biggest debtor"], ["owes", "owe", "owing", "debtor", "unpaid"]),
    ("f6", "Which invoices are overdue, and by how many days?", ["which invoices are overdue", "overdue invoices", "past due", "late invoices", "how many days overdue", "overdue days", "show overdue"], ["overdue", "late", "past", "days", "lapsed"]),
    ("f7", "Which client pays slowest?", ["slowest payer", "pays slowest", "slowest to pay", "pays the slowest", "slow payer", "worst payer"], ["slowest", "slow", "slowly", "delays", "delay"]),
    ("f8", "Which client pays fastest?", ["fastest payer", "pays fastest", "fastest to pay", "pays the fastest", "best payer", "pays on time", "pays quickly"], ["fastest", "fast", "quick", "quickly", "prompt"]),
    ("f9", "What is my average days to get paid?", ["average days to", "days to get paid", "days to pay", "how long to get paid", "how long do clients take", "payment time", "time to get paid"], ["average", "days", "paid", "long", "take"]),
    ("f10", "Which month was my best?", ["best month", "strongest month", "highest month", "top month", "busiest month"], ["best", "strongest", "highest", "peak", "busiest", "month"]),
    ("f11", "Which month was my worst?", ["worst month", "weakest month", "lowest month", "slowest month", "quietest month"], ["worst", "weakest", "lowest", "quietest", "month"]),
    ("f12", "How did revenue change month on month?", ["month on month", "mom", "monthly growth", "revenue change", "growth rate", "how did revenue change", "trend"], ["growth", "growing", "change", "trend", "month", "monthly", "momentum"]),
    ("f13", "Which project type earns the most?", ["project type earns", "which project type", "most profitable project", "top project", "best project type", "revenue by project"], ["project", "type", "earns", "service", "category"]),
    ("f14", "Which project type has the lowest average value?", ["lowest average value", "smallest project", "lowest average invoice", "least valuable project", "lowest value project"], ["lowest", "smallest", "cheapest", "least", "project", "average"]),
    ("f15", "Which clients are growing quarter on quarter?", ["growing quarter", "quarter on quarter", "clients are growing", "growing clients", "fastest growing", "increasing"], ["growing", "grow", "growth", "increase", "rising", "quarter"]),
    ("f16", "Which clients are shrinking quarter on quarter?", ["shrinking", "declining", "clients are shrinking", "falling", "dropping", "decreasing", "losing clients"], ["shrinking", "shrink", "declining", "decline", "falling", "dropping", "decrease", "quarter"]),
    ("f17", "What are my average and largest invoices?", ["average invoice", "largest invoice", "biggest invoice", "invoice size", "average and largest", "typical invoice"], ["average", "largest", "biggest", "median", "size"]),
    ("f18", "How many invoices are paid, pending and overdue?", ["how many invoices", "paid pending", "count of invoices", "invoice count", "number of invoices", "status breakdown", "how many are paid"], ["many", "count", "number", "status", "paid", "pending"]),
    ("f19", "Which invoices were paid late, and by how much?", ["paid late", "paid after due", "late payments", "paid overdue"], ["late", "paid", "after", "delayed"]),
    ("f20", "Which invoices have estimated or corrected data to verify?", ["estimated", "need verification", "verify", "to verify", "corrected data", "data to check", "double check", "flagged"], ["estimated", "verify", "check", "corrected", "flagged", "wrong", "errors", "suspicious"]),
    ("f21", "What did the cleaner fix?", ["what did the cleaner", "what was cleaned", "cleaning", "what was fixed", "data fixes", "data quality", "what did you fix"], ["cleaner", "cleaned", "fixed", "fixes", "cleaning", "quality", "standardised"]),
    ("f22", "What is due in the next 7 and 30 days?", ["due in the next", "due soon", "coming due", "due next week", "due this week", "due this month", "upcoming", "next 7 days", "next 30 days"], ["due", "upcoming", "soon", "next", "week"]),
    ("f23", "Show everything for a given client.", ["everything for", "show everything for", "client details", "all invoices for", "invoices for", "about client"], ["client", "customer", "show"]),
    ("f24", "Show everything for a given invoice ID.", ["invoice id", "details of invoice", "show invoice", "look up invoice", "find invoice"], ["invoice", "details", "lookup"]),
    ("f25", "What should I chase first this week?", ["chase first", "who should i chase", "what should i chase", "chase this week", "follow up first", "collect first", "priority", "follow up"], ["chase", "follow", "priority", "remind", "reminder", "collect"]),
    ("g1", "Monthly revenue: invoiced vs collected", ["monthly revenue", "revenue by month", "invoiced vs collected", "monthly chart"], ["monthly", "revenue", "collected"]),
    ("g2", "Month-on-month growth", ["growth chart", "mom growth", "growth by month"], ["growth", "mom"]),
    ("g3", "Revenue share by client", ["revenue share", "share by client", "client share", "pie", "donut", "share of revenue"], ["share", "pie", "donut"]),
    ("g4", "Top clients ranked", ["top clients chart", "ranked clients", "client ranking", "clients ranked"], ["ranking", "ranked", "leaderboard"]),
    ("g5", "Revenue by project type", ["by project type", "project type chart", "revenue by project"], ["project", "type"]),
    ("g6", "Client x quarter heatmap", ["heatmap", "heat map", "client by quarter", "quarterly matrix", "client quarter"], ["heatmap", "heat", "quarter", "quarterly", "matrix"]),
    ("g7", "Payment status breakdown", ["status breakdown", "payment status", "paid pending overdue chart"], ["status", "breakdown"]),
    ("g8", "Outstanding by client", ["outstanding by client", "who owes chart", "receivables by client"], ["outstanding", "receivables"]),
    ("g9", "Overdue days by client", ["overdue days by client", "overdue by client", "late days by client"], ["overdue", "client"]),
    ("g10", "Overdue days by invoice (top 10)", ["overdue days by invoice", "overdue by invoice", "oldest invoices chart"], ["overdue", "invoice", "oldest"]),
    ("g11", "Days-to-pay distribution", ["days to pay", "payment time distribution", "how fast clients pay"], ["distribution", "histogram", "days"]),
    ("g12", "Cumulative revenue over the year", ["cumulative", "running total", "revenue over the year", "year to date", "ytd"], ["cumulative", "running", "ytd"]),
    ("g13", "Invoice size distribution", ["invoice size", "size distribution", "invoice amounts distribution", "amount distribution"], ["size", "amounts", "distribution"]),
]
TITLES = {c[0]: c[1] for c in CATALOG}
CATALOG_JSON = [{"id": a, "q": b, "ph": c, "w": d} for a, b, c, d in CATALOG]
FOLLOW_DEFAULT = ["f1", "f25", "f6", "g1"]


# ---------------------------------------------------------------- helpers
def money(x): return f"${x:,.0f}"
def pct(x): return f"{x:.1f}%"
def ml(m): return f"{MON[int(m[5:7]) - 1]} '{m[2:4]}"
def O(v, *o): return o[(v if v is not None else random.randrange(len(o))) % len(o)]
def T(cols, rows): return {"cols": cols, "rows": rows}
def ssum(rows, k): return sum(r[k] for r in rows)
def plural(n, w): return f"{n} {w}{'' if n == 1 else 's'}"
def days_between(a, b): return (date.fromisoformat(a) - date.fromisoformat(b)).days
def sortd(rows, key, desc=True, name="Client_name"):
    rows = sorted(rows, key=lambda r: str(r.get(name, "")))
    return sorted(rows, key=key, reverse=desc)
def median(a):
    a = sorted(a)
    if not a: return 0
    h = len(a) // 2
    return a[h] if len(a) % 2 else (a[h - 1] + a[h]) / 2
def sgn(x): return ("+" if x >= 0 else "-") + money(abs(x))


def build_ctx(inv, m, fixes):
    """Precompute everything the answers need, once per dataset. inv = list of invoice dicts (dates as ISO strings)."""
    pays = {}
    for r in inv:
        if r["Payment_status"] == "Paid" and r["Payment_date"] and days_between(r["Payment_date"], r["Issue_date"]) >= 0:
            pays.setdefault(r["Client_name"], []).append(days_between(r["Payment_date"], r["Issue_date"]))
    pay = [{"Client_name": c, "avg": sum(v) / len(v), "n": len(v)} for c, v in pays.items()]
    alld = [x for v in pays.values() for x in v]
    return dict(inv=inv, m=m, fixes=fixes, k=m["kpis"], pay=pay, dtp=alld, clients=[c["Client_name"] for c in m["clients"]],
                types=[t["Project_type"] for t in m["types"]])


# ---------------------------------------------------------------- matching
def norm(q):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9%$.\s]", " ", q.lower().replace("-", " "))).strip()


def lev(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def tok_match(t, w):
    return t == w or (len(w) >= 4 and t.startswith(w)) or (len(w) >= 5 and len(t) >= 5 and lev(t, w) <= 1)


def score_all(qn):
    toks = qn.split()
    graphy = bool(re.search(r"\b(chart|graph|plot|visual\w*|show me|draw|heatmap|diagram)\b", qn))
    out = []
    for i, (cid, _, ph, w) in enumerate(CATALOG):
        s = sum(3 for x in ph if norm(x) in qn) + sum(1 for x in w if any(tok_match(t, x) for t in toks))
        if s and cid[0] == "g" and graphy: s += 1
        out.append((s, i, cid))
    return out


def find_client(q, clients):
    qn = re.sub(r"[^a-z]", "", q.lower())
    toks = re.findall(r"[a-z]+", q.lower())
    best, bl = None, 0
    for c in clients:
        key = re.sub(r"[^a-z]", "", re.sub(r"\b(inc|ltd|llc|corp|corporation|co|company|pvt|and)\b", "", c.lower().replace("&", " and ")))
        first = re.findall(r"[a-z]+", c.lower())[0] if re.findall(r"[a-z]+", c.lower()) else ""
        hit = (len(key) >= 4 and key in qn) or (len(first) >= 4 and any(tok_match(t, first) for t in toks if len(t) >= 4))
        if hit and len(key) > bl:
            best, bl = c, len(key)
    return best


def parse_filters(q, qn, c):
    f = {}
    ql = q.lower().replace(",", "")
    mt = re.search(r"(over|above|more than|greater than|at least|>)\s*\$?\s*(\d+(?:\.\d+)?)\s*(k?)", ql)
    if mt: f["min"] = float(mt.group(2)) * (1000 if mt.group(3) else 1)
    mt = re.search(r"(under|below|less than|at most|<)\s*\$?\s*(\d+(?:\.\d+)?)\s*(k?)", ql)
    if mt: f["max"] = float(mt.group(2)) * (1000 if mt.group(3) else 1)
    toks = qn.split()
    if "overdue" in toks or "late" in toks: f["status"] = "Overdue"
    elif "pending" in toks: f["status"] = "Pending"
    elif "unpaid" in toks or "outstanding" in toks: f["status"] = "Open"
    elif "paid" in toks: f["status"] = "Paid"
    for t in c["types"]:
        if t.lower() in qn: f["type"] = t
    for i, mn in enumerate(MONFULL):
        if mn in toks or (len(mn) > 3 and mn[:3] in toks): f["month"] = i + 1
    cl = find_client(q, c["clients"])
    if cl: f["client"] = cl
    return f


def route(q, c):
    qn = norm(q)
    mid = re.search(r"\binv\s?(\d+)\b", qn)
    if mid: return {"type": "faq", "id": "f24", "arg": f"INV-{mid.group(1)}"}
    sc = sorted(score_all(qn), key=lambda x: (-x[0], x[1]))
    best = sc[0]
    cl = find_client(q, c["clients"])
    if cl and (best[0] < 6 or best[2] == "f23"): return {"type": "faq", "id": "f23", "arg": cl}
    f = parse_filters(q, qn, c)
    if (set(f) & {"min", "max"} and best[0] < 6) or (set(f) & {"type", "month"} and best[0] < 4): return {"type": "lookup", "filters": f}
    if best[0] >= 2: return {"type": "graph" if best[2][0] == "g" else "faq", "id": best[2]}
    return {"type": "none", "suggest": [x[2] for x in sc[:3] if x[0] > 0] or FOLLOW_DEFAULT[:3]}


# ---------------------------------------------------------------- answers
def f1(c, v, a=None):
    k = c["k"]
    t = O(v, "Here's the headline:", "In total,", "Across the whole book,")
    return dict(text=f"{t} you've invoiced **{money(k['total_invoiced'])}** over {int(k['invoices'])} invoices. **{money(k['total_collected'])}** has come in and **{money(k['total_outstanding'])}** is still outstanding, of which {money(k['overdue_open_amount'])} is past due.",
                table=T(["Measure", "Amount"], [["Invoiced", money(k["total_invoiced"])], ["Collected", money(k["total_collected"])], ["Outstanding", money(k["total_outstanding"])], ["Past due (open)", money(k["overdue_open_amount"])]]),
                chart="g1", follow=["f2", "f5", "f25"])


def f2(c, v, a=None):
    k = c["k"]; r = k["collection_pct"]
    j = "That's healthy." if r >= 90 else "That's decent, but there's room to tighten." if r >= 75 else "That's on the low side, so chasing overdue invoices should be a priority."
    return dict(text=f"{O(v, 'Your collection rate is', 'So far you have collected')} **{pct(r)}** of what you've billed ({money(k['total_collected'])} of {money(k['total_invoiced'])}). {j}",
                table=None, chart="g7", follow=["f18", "f6", "f25"])


def _top(c, v, n):
    cl = c["m"]["clients"][:n]
    names = ", ".join(f"**{x['Client_name']}** ({pct(x['share'])})" for x in cl)
    return dict(text=f"{O(v, 'Your top', 'The top')} {len(cl)} clients {'is' if len(cl) == 1 else 'are'} {names}, together **{pct(sum(x['share'] for x in cl))}** of everything you've billed.",
                table=T(["Client", "Invoiced", "Share", "Open"], [[x["Client_name"], money(x["invoiced"]), pct(x["share"]), money(x["outstanding"])] for x in cl]),
                chart="g4", follow=["g3", "f5", "f15"])
def f3(c, v, a=None): return _top(c, v, 3)
def f4(c, v, a=None): return _top(c, v, 5)


def f5(c, v, a=None):
    cl = sortd([x for x in c["m"]["clients"]], lambda x: x["outstanding"])
    top = cl[0]
    if top["outstanding"] <= 0:
        return dict(text="Nothing is outstanding right now. Every invoice has been paid.", table=None, chart=None, follow=["f1", "f19"])
    o = [r for r in c["inv"] if r["Client_name"] == top["Client_name"] and r["Payment_status"] != "Paid"]
    od = ssum([r for r in o if r["Overdue_days"] > 0], "Amount")
    return dict(text=f"{O(v, 'Right now,', 'At the moment,', 'As of today,')} **{top['Client_name']}** owes you the most: **{money(top['outstanding'])}** across {plural(len(o), 'open invoice')}, {money(od)} of it already past due.",
                table=T(["Client", "Outstanding", "Share of total outstanding"], [[x["Client_name"], money(x["outstanding"]), pct(x["outstanding"] / c["k"]["total_outstanding"] * 100)] for x in cl[:5] if x["outstanding"] > 0]),
                chart="g8", follow=["f6", "f25", "f7"])


def f6(c, v, a=None):
    oi = c["m"]["overdue_invoices"]
    if not oi:
        return dict(text="Nothing is overdue right now. Every invoice is paid or still within terms.", table=None, chart=None, follow=["f22", "f1"])
    op = [r for r in oi if r["Payment_status"] != "Paid"]; first = oi[0]
    return dict(text=f"{O(v, 'There are', 'I count')} **{plural(len(op), 'unpaid invoice')} past due** (worth {money(ssum(op, 'Amount'))}), and {len(oi) - len(op)} more were paid late. The longest overdue is **{first['Invoice_ID']}** ({first['Client_name']}) at **{first['Overdue_days']} days**.",
                table=T(["Invoice", "Client", "Amount", "Status", "Overdue days"], [[r["Invoice_ID"], r["Client_name"], money(r["Amount"]), r["Payment_status"], str(r["Overdue_days"])] for r in oi[:10]]),
                chart="g10", follow=["f25", "g9", "f19"])


def _speed(c, v, slow):
    pay = sortd(c["pay"], lambda x: x["avg"], slow)
    if not pay:
        return dict(text="No invoices have been paid yet, so there's no payment speed to compare.", table=None, chart=None, follow=["f6"])
    t = pay[0]; allavg = sum(c["dtp"]) / len(c["dtp"])
    return dict(text=f"**{t['Client_name']}** is your {'slowest' if slow else 'fastest'} payer: **{t['avg']:.0f} days** on average from invoice to payment, against **{allavg:.0f} days** across all clients ({plural(t['n'], 'paid invoice')}).",
                table=T(["Client", "Avg days to pay", "Invoices paid"], [[x["Client_name"], f"{x['avg']:.0f}", str(x["n"])] for x in pay]),
                chart="g11", follow=["f9", "f25", "f6"])
def f7(c, v, a=None): return _speed(c, v, True)
def f8(c, v, a=None): return _speed(c, v, False)


def f9(c, v, a=None):
    if not c["dtp"]:
        return dict(text="No invoices have been paid yet, so there's no payment time to measure.", table=None, chart=None, follow=["f6"])
    d = c["dtp"]
    return dict(text=f"{O(v, 'On average', 'Typically')} you get paid **{sum(d) / len(d):.0f} days** after issuing an invoice (median **{median(d):.0f}**). The quickest took {min(d)} days and the slowest {max(d)}.",
                table=None, chart="g11", follow=["f7", "f8", "f19"])


def _month(c, v, best):
    mo = c["m"]["monthly"]
    srt = sortd(mo, lambda x: x["invoiced"], best, name="Month")
    t = srt[0]; avg = sum(x["invoiced"] for x in mo) / len(mo)
    diff = abs((t["invoiced"] / avg - 1) * 100)
    return dict(text=f"**{ml(t['Month'])}** was your {'strongest' if best else 'quietest'} month: **{money(t['invoiced'])}** invoiced across {plural(t['count'], 'invoice')}, {diff:.0f}% {'above' if best else 'below'} your monthly average of {money(avg)}.",
                table=T(["Month", "Invoiced", "Invoices"], [[ml(x["Month"]), money(x["invoiced"]), str(x["count"])] for x in srt[:3]]),
                chart="g1", follow=["f12", "g2", "f13"])
def f10(c, v, a=None): return _month(c, v, True)
def f11(c, v, a=None): return _month(c, v, False)


def f12(c, v, a=None):
    mo = c["m"]["monthly"]; rows = [x for x in mo if x["mom"] is not None]
    if not rows:
        return dict(text="I need at least two months of data to compare growth.", table=None, chart=None, follow=["f10"])
    last = rows[-1]; up = sortd(rows, lambda x: x["mom"], True, "Month")[0]; dn = sortd(rows, lambda x: x["mom"], False, "Month")[0]
    tail = f" and the sharpest drop was {ml(dn['Month'])} ({dn['mom']:+.0f}%)" if dn["mom"] < 0 else "; there hasn't been a month-on-month decline"
    return dict(text=f"Billings in **{ml(last['Month'])}** moved **{last['mom']:+.0f}%** versus the month before. The biggest jump was {ml(up['Month'])} ({up['mom']:+.0f}%){tail}.",
                table=T(["Month", "Invoiced", "Change"], [[ml(x["Month"]), money(x["invoiced"]), "-" if x["mom"] is None else f"{x['mom']:+.0f}%"] for x in mo]),
                chart="g2", follow=["f10", "f11", "g12"])


def f13(c, v, a=None):
    ty = c["m"]["types"]; t = ty[0]
    return dict(text=f"**{t['Project_type']}** brings in the most: **{money(t['amount'])}** ({pct(t['share'])} of billings) from {plural(t['count'], 'invoice')}.",
                table=T(["Project type", "Revenue", "Share", "Invoices"], [[x["Project_type"], money(x["amount"]), pct(x["share"]), str(x["count"])] for x in ty]),
                chart="g5", follow=["f14", "f10", "f3"])


def f14(c, v, a=None):
    ty = sortd([dict(x, avg=x["amount"] / x["count"]) for x in c["m"]["types"]], lambda x: x["avg"], False, "Project_type")
    t = ty[0]
    return dict(text=f"**{t['Project_type']}** has the lowest average invoice at **{money(t['avg'])}** ({plural(t['count'], 'invoice')}); {ty[-1]['Project_type']} has the highest at {money(ty[-1]['avg'])}.",
                table=T(["Project type", "Avg invoice", "Invoices"], [[x["Project_type"], money(x["avg"]), str(x["count"])] for x in ty]),
                chart="g5", follow=["f13", "f17"])


def _qoq(c, v, grow):
    qs = c["m"]["quarters"]
    mq = {}
    for r in c["inv"]:
        mq.setdefault(r["Quarter"], set()).add(r["Month"])
    full = [q for q in qs if len(mq[q]) >= 3]
    use = full if len(full) >= 2 else qs
    if len(use) < 2:
        return dict(text="I need at least two quarters of data to compare.", table=None, chart=None, follow=["f12"])
    pq, lq = use[-2], use[-1]
    skipped = [q for q in qs if q not in use]
    note = f" ({', '.join(skipped)} {'is' if len(skipped) == 1 else 'are'} still in progress and left out.)" if skipped and use is full else ""
    rows = [dict(Client_name=r["Client_name"], p=r[pq], l=r[lq], ch=r[lq] - r[pq]) for r in c["m"]["quarterly"]]
    sel = sortd([r for r in rows if (r["ch"] > 0 if grow else r["ch"] < 0)], lambda r: r["ch"], grow)
    if not sel:
        return dict(text=f"No client {'grew' if grow else 'shrank'} in {lq} versus {pq}.{note}", table=None, chart="g6", follow=["f16" if grow else "f15", "g6"])
    t = sel[0]; pc = "new" if t["p"] == 0 else f"{(t['l'] / t['p'] - 1) * 100:+.0f}%"
    return dict(text=f"In **{lq}**, **{plural(len(sel), 'client')}** billed {'more' if grow else 'less'} than in {pq}. The biggest {'gain' if grow else 'drop'} is **{t['Client_name']}** ({sgn(t['ch'])}, {pc}).{note}",
                table=T(["Client", pq, lq, "Change"], [[r["Client_name"], money(r["p"]), money(r["l"]), sgn(r["ch"])] for r in sel]),
                chart="g6", follow=["f16" if grow else "f15", "f3"])
def f15(c, v, a=None): return _qoq(c, v, True)
def f16(c, v, a=None): return _qoq(c, v, False)


def f17(c, v, a=None):
    amts = [r["Amount"] for r in c["inv"]]; big = sortd(c["inv"], lambda r: r["Amount"], True, "Invoice_ID")
    b = big[0]
    return dict(text=f"Your average invoice is **{money(sum(amts) / len(amts))}** and the median is {money(median(amts))}. The largest is **{b['Invoice_ID']}** for **{money(b['Amount'])}** ({b['Client_name']}, {b['Project_type']}).",
                table=T(["Invoice", "Client", "Project", "Amount"], [[r["Invoice_ID"], r["Client_name"], r["Project_type"], money(r["Amount"])] for r in big[:5]]),
                chart="g13", follow=["f14", "f3"])


def _status(c):
    out = {}
    for s in ["Paid", "Pending", "Overdue"]:
        rs = [r for r in c["inv"] if r["Payment_status"] == s]
        out[s] = (len(rs), ssum(rs, "Amount"))
    return out


def f18(c, v, a=None):
    s = _status(c)
    return dict(text=f"Of **{len(c['inv'])}** invoices, **{s['Paid'][0]} are paid**, **{s['Pending'][0]} pending** and **{s['Overdue'][0]} overdue**.",
                table=T(["Status", "Invoices", "Amount"], [[k, str(n), money(a_)] for k, (n, a_) in s.items()]),
                chart="g7", follow=["f6", "f2", "f22"])


def f19(c, v, a=None):
    paid = [r for r in c["inv"] if r["Payment_status"] == "Paid"]; late = sortd([r for r in paid if r["Overdue_days"] > 0], lambda r: r["Overdue_days"], True, "Invoice_ID")
    if not late:
        return dict(text="Every paid invoice arrived on or before its due date.", table=None, chart=None, follow=["f7", "f9"])
    return dict(text=f"**{len(late)} of {len(paid)}** paid invoices arrived late, **{sum(r['Overdue_days'] for r in late) / len(late):.0f} days** late on average. The worst was **{late[0]['Invoice_ID']}** ({late[0]['Client_name']}), **{late[0]['Overdue_days']} days** late.",
                table=T(["Invoice", "Client", "Amount", "Days late"], [[r["Invoice_ID"], r["Client_name"], money(r["Amount"]), str(r["Overdue_days"])] for r in late[:10]]),
                chart=None, follow=["f7", "f9", "f25"])


def f20(c, v, a=None):
    fl = [r for r in c["inv"] if FLAG_RE.search(r["Data_Notes"] or "")]
    if not fl:
        return dict(text="Nothing needs a second look. No estimated or corrected values were flagged.", table=None, chart=None, follow=["f21"])
    cats = [("estimated amount", "Missing amount estimated"), ("negative amount", "Negative amount"), ("payment dated before issue", "before issue"), ("assumed payment date", "assumed"), ("unknown client", "Unknown Client")]
    parts = [f"{sum(1 for r in fl if k in r['Data_Notes'])} with {n}" for n, k in cats if any(k in r["Data_Notes"] for r in fl)]
    def what(r): return "; ".join(x for x in r["Data_Notes"].split("; ") if FLAG_RE.search(x))
    return dict(text=f"**{plural(len(fl), 'invoice')}** carry values worth a second look: {', '.join(parts)}. Confirm them against the original invoices.",
                table=T(["Invoice", "Client", "Amount", "What to check"], [[r["Invoice_ID"], r["Client_name"], money(r["Amount"]), what(r)] for r in fl[:15]]),
                chart=None, follow=["f21", "f25"])


def f21(c, v, a=None):
    fx = c["fixes"]
    if not fx:
        return dict(text="The data was already clean, so nothing needed fixing.", table=None, chart=None, follow=["f20"])
    rows = sortd([{"n": k, "c": v_} for k, v_ in fx.items()], lambda r: r["c"], True, "n")
    return dict(text=f"The cleaner made **{sum(fx.values())} corrections** across **{plural(len(fx), 'kind')}** of problem. The most common was “{rows[0]['n']}” ({rows[0]['c']} rows). Every change is also noted on the invoice itself.",
                table=T(["Fix", "Rows"], [[r["n"], str(r["c"])] for r in rows]), chart=None, follow=["f20", "f1"])


def f22(c, v, a=None):
    op = [dict(r, dd=days_between(r["Due_date"], ASOF)) for r in c["inv"] if r["Payment_status"] != "Paid"]
    soon = sortd([r for r in op if 0 <= r["dd"] <= 30], lambda r: r["dd"], False, "Invoice_ID")
    d7 = [r for r in soon if r["dd"] <= 7]; od = [r for r in op if r["dd"] < 0]
    tail = f" Separately, **{len(od)}** are already overdue ({money(ssum(od, 'Amount'))})." if od else ""
    head = (f"**{plural(len(d7), 'invoice')} ({money(ssum(d7, 'Amount'))})** fall due in the next 7 days and **{len(soon)} ({money(ssum(soon, 'Amount'))})** in the next 30." if soon
            else "Nothing falls due in the next 30 days.")
    return dict(text=head + tail,
                table=T(["Invoice", "Client", "Amount", "Due", "In (days)"], [[r["Invoice_ID"], r["Client_name"], money(r["Amount"]), r["Due_date"], str(r["dd"])] for r in soon]) if soon else None,
                chart=None, follow=["f25", "f6"])


def f23(c, v, a=None):
    if not a:
        return dict(text="Which client? Tap one below.", table=None, chart=None, follow=[["f23", n, n] for n in c["clients"]])
    rs = [r for r in c["inv"] if r["Client_name"] == a]
    if not rs:
        return dict(text=f"I can't find a client called **{a}**.", table=None, chart=None, follow=[["f23", n, n] for n in c["clients"][:6]])
    paid = [r for r in rs if r["Payment_status"] == "Paid"]; op = [r for r in rs if r["Payment_status"] != "Paid"]
    od = ssum([r for r in op if r["Overdue_days"] > 0], "Amount")
    pd_ = [x for x in c["pay"] if x["Client_name"] == a]
    speed = f" They typically pay in **{pd_[0]['avg']:.0f} days**." if pd_ else ""
    return dict(text=f"**{a}**: {plural(len(rs), 'invoice')} worth **{money(ssum(rs, 'Amount'))}**. {money(ssum(paid, 'Amount'))} is paid and **{money(ssum(op, 'Amount'))}** is open ({money(od)} past due).{speed}",
                table=T(["Invoice", "Issued", "Amount", "Status", "Overdue days"], [[r["Invoice_ID"], r["Issue_date"], money(r["Amount"]), r["Payment_status"], str(r["Overdue_days"])] for r in rs[:20]]),
                chart=None, follow=["f25", "f5"])


def f24(c, v, a=None):
    if not a:
        ids = [x["Invoice_ID"] for x in (c["m"]["overdue_invoices"] or c["inv"])[:4]]
        return dict(text="Type an invoice ID (for example **" + ids[0] + "**) and I'll pull up everything on it.", table=None, chart=None, follow=[["f24", i, i] for i in ids])
    r = next((x for x in c["inv"] if x["Invoice_ID"] == a), None)
    if not r:
        ids = sorted(x["Invoice_ID"] for x in c["inv"])
        return dict(text=f"I can't find **{a}** in this data. IDs run from **{ids[0]}** to **{ids[-1]}**.", table=None, chart=None, follow=["f6", "f1"])
    extra = (f"paid {r['Payment_date']}" + (f", {r['Overdue_days']} days late" if r["Overdue_days"] else "")) if r["Payment_status"] == "Paid" else (f"{r['Overdue_days']} days overdue" if r["Overdue_days"] else "within terms")
    rows = [["Client", r["Client_name"]], ["Project", r["Project_type"]], ["Amount", money(r["Amount"])], ["Issued", r["Issue_date"]], ["Due", r["Due_date"]], ["Status", r["Payment_status"]],
            ["Paid on", r["Payment_date"] or "-"], ["Overdue days", str(r["Overdue_days"])], ["Notes", r["Notes"] or "-"], ["Cleaning notes", r["Data_Notes"] or "-"]]
    return dict(text=f"**{r['Invoice_ID']}** is a {r['Project_type']} invoice for **{r['Client_name']}**: **{money(r['Amount'])}**, issued {r['Issue_date']}, due {r['Due_date']}. Status: **{r['Payment_status']}** ({extra}).",
                table=T(["Field", "Value"], rows), chart=None, follow=[["f23", r["Client_name"], "All of " + r["Client_name"]], "f25"])


def f25(c, v, a=None):
    op = [dict(r, dd=days_between(r["Due_date"], ASOF)) for r in c["inv"] if r["Payment_status"] != "Paid"]
    od = sortd([r for r in op if r["Overdue_days"] > 0], lambda r: r["Amount"] * r["Overdue_days"], True, "Invoice_ID")
    d7 = [r for r in op if 0 <= r["dd"] <= 7]
    nudge = f" Also, {plural(len(d7), 'invoice')} fall{'s' if len(d7) == 1 else ''} due within a week, so a friendly pre-due reminder is worth sending." if d7 else ""
    if not od:
        return dict(text=f"Nothing is overdue, so there's nobody to chase.{nudge}", table=None, chart=None, follow=["f22", "f1"])
    act = lambda n: "Call today" if n >= 45 else "Firm reminder" if n >= 15 else "Gentle nudge"
    t = od[0]; top = od[:5]
    return dict(text=f"{O(v, 'Start with', 'I would begin with')} **{t['Invoice_ID']}**: **{t['Client_name']}**, {money(t['Amount'])}, **{t['Overdue_days']} days** overdue. The top {len(top)} below add up to **{money(ssum(top, 'Amount'))}**.{nudge}",
                table=T(["Invoice", "Client", "Amount", "Days overdue", "Suggested action"], [[r["Invoice_ID"], r["Client_name"], money(r["Amount"]), str(r["Overdue_days"]), act(r["Overdue_days"])] for r in top]),
                chart=None, follow=["f6", "f5", "f22"])


def lookup(c, f, v):
    rs = c["inv"]; bits = []
    if "client" in f: rs = [r for r in rs if r["Client_name"] == f["client"]]; bits.append(f"client {f['client']}")
    if "min" in f: rs = [r for r in rs if r["Amount"] > f["min"]]; bits.append(f"amount over {money(f['min'])}")
    if "max" in f: rs = [r for r in rs if r["Amount"] < f["max"]]; bits.append(f"amount under {money(f['max'])}")
    if "status" in f:
        rs = [r for r in rs if (r["Payment_status"] != "Paid" if f["status"] == "Open" else r["Payment_status"] == f["status"])]; bits.append(f"status {f['status'].lower()}")
    if "type" in f: rs = [r for r in rs if r["Project_type"] == f["type"]]; bits.append(f"project {f['type']}")
    if "month" in f: rs = [r for r in rs if int(r["Issue_date"][5:7]) == f["month"]]; bits.append(f"issued in {MON[f['month'] - 1]}")
    if not rs:
        return dict(text=f"No invoices match {', '.join(bits)}.", table=None, chart=None, follow=FOLLOW_DEFAULT)
    return dict(text=f"I found **{plural(len(rs), 'invoice')}** matching {', '.join(bits)}, worth **{money(ssum(rs, 'Amount'))}** in total.",
                table=T(["Invoice", "Client", "Issued", "Amount", "Status", "Overdue days"], [[r["Invoice_ID"], r["Client_name"], r["Issue_date"], money(r["Amount"]), r["Payment_status"], str(r["Overdue_days"])] for r in rs[:15]]),
                chart=None, follow=["f6", "f25"])


HANDLERS = {f"f{i}": globals()[f"f{i}"] for i in range(1, 26)}


# ---------------------------------------------------------------- graphs
def graph_spec(gid, c):
    m, k = c["m"], c["k"]; mo = m["monthly"]; labs = [ml(x["Month"]) for x in mo]
    if gid == "g1": return dict(kind="col", title="Monthly revenue", labels=labs, series=[dict(name="Invoiced", values=[x["invoiced"] for x in mo]), dict(name="Collected", values=[x["collected"] for x in mo])], fmt="usd")
    if gid == "g2":
        r = [x for x in mo if x["mom"] is not None]
        return dict(kind="col", title="Month-on-month growth (%)", labels=[ml(x["Month"]) for x in r], series=[dict(name="MoM %", values=[x["mom"] for x in r])], fmt="pct")
    if gid == "g3": return dict(kind="hbar", title="Revenue share by client", labels=[x["Client_name"] for x in m["clients"]], series=[dict(name="Share", values=[x["share"] for x in m["clients"]])], fmt="pct")
    if gid == "g4":
        cl = m["clients"][:8]
        return dict(kind="hbar", title="Top clients by revenue", labels=[x["Client_name"] for x in cl], series=[dict(name="Invoiced", values=[x["invoiced"] for x in cl])], fmt="usd")
    if gid == "g5": return dict(kind="hbar", title="Revenue by project type", labels=[x["Project_type"] for x in m["types"]], series=[dict(name="Revenue", values=[x["amount"] for x in m["types"]])], fmt="usd")
    if gid == "g6": return dict(kind="heat", title="Client x quarter revenue", labels=[r["Client_name"] for r in m["quarterly"]], cols=m["quarters"], z=[[r[q] for q in m["quarters"]] for r in m["quarterly"]], fmt="usd")
    if gid == "g7":
        s = _status(c)
        return dict(kind="hbar", title="Payment status (amount)", labels=list(s), series=[dict(name="Amount", values=[a for _, a in s.values()])], fmt="usd")
    if gid == "g8":
        cl = sortd([x for x in m["clients"] if x["outstanding"] > 0], lambda x: x["outstanding"])
        return dict(kind="hbar", title="Outstanding by client", labels=[x["Client_name"] for x in cl], series=[dict(name="Outstanding", values=[x["outstanding"] for x in cl])], fmt="usd")
    if gid == "g9":
        oc = sortd(m["overdue_clients"], lambda x: x["total_overdue_days"])
        return dict(kind="hbar", title="Total overdue days by client", labels=[x["Client_name"] for x in oc], series=[dict(name="Days", values=[x["total_overdue_days"] for x in oc])], fmt="num")
    if gid == "g10":
        oi = m["overdue_invoices"][:10]
        return dict(kind="hbar", title="Overdue days by invoice (top 10)", labels=[f"{x['Invoice_ID']} · {x['Client_name']}" for x in oi], series=[dict(name="Days", values=[x["Overdue_days"] for x in oi])], fmt="num")
    if gid == "g11":
        edges = [(0, 15, "0-15"), (16, 30, "16-30"), (31, 45, "31-45"), (46, 60, "46-60"), (61, 90, "61-90"), (91, 10 ** 6, "90+")]
        return dict(kind="col", title="Days from invoice to payment", labels=[e[2] for e in edges], series=[dict(name="Invoices", values=[sum(1 for x in c["dtp"] if a <= x <= b) for a, b, _ in edges])], fmt="num")
    if gid == "g12":
        a, b, ca, cb = [], [], 0, 0
        for x in mo:
            ca += x["invoiced"]; cb += x["collected"]; a.append(round(ca, 2)); b.append(round(cb, 2))
        return dict(kind="line", title="Cumulative revenue", labels=labs, series=[dict(name="Invoiced", values=a), dict(name="Collected", values=b)], fmt="usd")
    edges = [(0, 1000, "<$1k"), (1000, 2000, "$1-2k"), (2000, 3000, "$2-3k"), (3000, 4000, "$3-4k"), (4000, 5000, "$4-5k"), (5000, 6000, "$5-6k"), (6000, 10 ** 12, "$6k+")]
    return dict(kind="col", title="Invoice size distribution", labels=[e[2] for e in edges], series=[dict(name="Invoices", values=[sum(1 for r in c["inv"] if a <= r["Amount"] < b) for a, b, _ in edges])], fmt="num")


def fmtv(x, fmt): return money(x) if fmt == "usd" else pct(x) if fmt == "pct" else f"{x:,.0f}"


def graph_answer(gid, c, v):
    sp = graph_spec(gid, c); t = sp["title"]
    if sp["kind"] == "heat":
        flat = [(sp["z"][i][j], sp["labels"][i], sp["cols"][j]) for i in range(len(sp["labels"])) for j in range(len(sp["cols"]))]
        top = sorted(flat, key=lambda x: -x[0])[0]
        take = f"The strongest cell is **{top[1]}** in {top[2]} at {money(top[0])}."
    else:
        s0 = sp["series"][0]; vals = s0["values"]
        if sp["kind"] == "line":
            take = f"By the end, **{fmtv(vals[-1], sp['fmt'])}** has been invoiced" + (f" and **{fmtv(sp['series'][1]['values'][-1], sp['fmt'])}** collected." if len(sp["series"]) > 1 else ".")
        elif not vals:
            take = "There's nothing to plot yet."
        else:
            i = max(range(len(vals)), key=lambda j: (vals[j], -j))
            take = f"The highest is **{sp['labels'][i]}** at {fmtv(vals[i], sp['fmt'])}."
    return dict(text=f"{O(v, 'Here is', 'Here you go:', 'This is')} the **{t.lower()}** chart. {take}", table=None, chart=gid, follow=[x for x in FOLLOW_DEFAULT if x != gid][:3])


def respond(q=None, c=None, faq=None, arg=None, v=None):
    """Answer a typed question (q) or a catalog pick (faq id, optional arg). Returns text/table/chart/follow."""
    if faq is None:
        r = route(q, c)
        if r["type"] == "none":
            return dict(text="I couldn't match that to something I can work out from your invoices. These are the closest questions:", table=None, chart=None, follow=r["suggest"], matched=None)
        if r["type"] == "lookup":
            out = lookup(c, r["filters"], v); out["matched"] = "lookup"; return out
        faq, arg = r["id"], r.get("arg")
    out = graph_answer(faq, c, v) if faq[0] == "g" else HANDLERS[faq](c, v, arg)
    out["matched"] = faq
    return out


def make_ctx(d, fixes):
    """Build the context from a cleaned DataFrame (used by the Streamlit app)."""
    import pipeline as p
    return build_ctx(p._rec(d[p.COLS + ["Month", "Quarter"]]), p.metrics(d), fixes)
