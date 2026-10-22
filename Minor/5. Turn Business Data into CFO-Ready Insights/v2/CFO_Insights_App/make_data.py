"""Generates two deliberately messy sample files.
Sample 1: a year of invoices with inconsistent names/dates, gaps and wrong entries.
Sample 2: the "append" file - new invoices plus payment updates to older ones.
Run:  python make_data.py   (writes data/sample1_messy.csv and data/sample2_messy.csv)"""
import os, random, datetime as dt
import pandas as pd

random.seed(11)
ASOF = dt.date(2026, 10, 22)
COLS = ["Invoice_ID", "Client_name", "Issue_date", "Due_date", "Amount(USD)",
        "Payment_status", "Payment_date", "Project_type", "any_notes_or_remarks"]
CLIENTS = {
    "Acme Corp": (["Acme Corp"] * 6 + ["ACME corp.", "Acme Corporation", "acme"], 1.6),
    "Northwind Traders": (["Northwind Traders"] * 6 + ["Northwnd Traders", "NORTHWIND TRADERS"], 1.3),
    "Lumen Studio": (["Lumen Studio"] * 5 + ["lumen studio", "Lumen Studio "], 0.9),
    "Birch & Co": (["Birch & Co"] * 5 + ["Birch and Co", "BIRCH & CO."], 0.8),
    "Helix Labs": (["Helix Labs"] * 5 + ["Helix Labs Inc", "helix labs "], 1.1),
    "Orchard Media": (["Orchard Media"] * 5 + ["Orchard Media LLC", "Orchad Media"], 0.7),
    "Sable Finance": (["Sable Finance"] * 5 + ["Sable Finance Ltd", "sable finance"], 1.4),
}
TYPES = {"Web Design": (1800, 4200), "Branding": (1200, 3200), "Consulting": (2500, 6000),
         "Content": (600, 1800), "Development": (3000, 7500)}
NOTES = ["", "", "", "", "Partial payment received", "Disputed line item", "Rush job", "Retainer", "Client requested net-45"]


def fmt_date(d):
    if d is None:
        return random.choice(["", ""])
    f = random.choice(["%Y-%m-%d", "%d/%m/%Y", "%b %d, %Y", "%d-%b-%y", "%d %B %Y", "%Y-%m-%d"])
    return d.strftime(f)


def fmt_amt(a):
    return random.choice([f"{a:.2f}", f"{a:,.2f}", f"${a:,.0f}", f"USD {a:,.0f}", f"{a:.0f}"])


def make(n, start, end, first_id):
    rows, span = [], (end - start).days
    days = sorted(random.randrange(span) for _ in range(n))
    for i, off in enumerate(days):
        c = random.choices(list(CLIENTS), weights=[w for _, w in CLIENTS.values()])[0]
        t = random.choice(list(TYPES))
        issue = start + dt.timedelta(days=off)
        due = issue + dt.timedelta(days=random.choice([15, 30, 30, 45]))
        amt = round(random.uniform(*TYPES[t]) * CLIENTS[c][1], -1)
        paid = random.random() < (0.92 if due < ASOF - dt.timedelta(days=60) else 0.35)
        pay = due + dt.timedelta(days=random.randint(-8, 28)) if paid else None
        if pay and pay > ASOF:
            pay = None
        rows.append(dict(id=first_id + i, client=c, issue=issue, due=due, amt=amt, pay=pay, type=t,
                         note=random.choice(NOTES)))
    return rows


def messy(rows):
    out = []
    for r in rows:
        status = "Paid" if r["pay"] else random.choice(["Pending", "Unpaid", "overdue", "Late", "pending"])
        if r["pay"]:
            status = random.choice(["Paid", "paid", "PAID", "Paid ", "Received"])
        out.append([random.choice([f"INV-{r['id']}", f"INV-{r['id']}", f"inv {r['id']}", f"INV{r['id']}"]),
                    random.choice(CLIENTS[r["client"]][0]), fmt_date(r["issue"]), fmt_date(r["due"]),
                    fmt_amt(r["amt"]), status, fmt_date(r["pay"]), r["type"], r["note"]])
    return out


def dirty(out):
    n = len(out)
    pick = lambda k: random.sample(range(n), k)
    for i in pick(5): out[i][4] = ""                       # missing amount
    for i in pick(3): out[i][3] = ""                       # missing due date
    for i in pick(4): out[i][5] = ""                       # missing status
    for i in pick(3): out[i][7] = ""                       # missing project type
    for i in pick(2): out[i][4] = "-" + out[i][4].lstrip("-") if out[i][4] else out[i][4]  # negative amount
    for i in pick(2): out[i][1] = ""                       # missing client
    for i in pick(2): out[i][6] = "not yet"                # unreadable payment date
    for i in pick(2): out.append(list(out[i]))             # duplicate rows
    return out


# ---- Sample 1: Oct 2025 - Jul 2026
r1 = make(62, dt.date(2025, 10, 1), dt.date(2026, 7, 31), 1001)
bad = random.choice([r for r in r1 if r["pay"]])
bad["pay"] = bad["issue"] - dt.timedelta(days=6)  # wrong entry: payment dated before the invoice
o1 = dirty(messy(r1))

# ---- Sample 2: updates to still-open Sample-1 invoices + new Aug-Oct 2026 invoices
open1 = [r for r in r1 if not r["pay"]]
upd = random.sample(open1, min(9, len(open1)))
for r in upd:
    r["pay"] = min(ASOF - dt.timedelta(days=random.randint(1, 40)), r["due"] + dt.timedelta(days=random.randint(40, 120)))
    r["note"] = "Paid after reminder"
r2 = make(26, dt.date(2026, 8, 1), dt.date(2026, 10, 20), 1063)
o2 = dirty(messy(upd + r2))
for row in o2:
    if row[5] in ("Paid ", "Received"):
        row[5] = "paid"

os.makedirs("data", exist_ok=True)
pd.DataFrame(o1, columns=COLS).to_csv("data/sample1_messy.csv", index=False)
pd.DataFrame(o2, columns=COLS).to_csv("data/sample2_messy.csv", index=False)
print(len(o1), "rows sample1;", len(o2), "rows sample2 (", len(upd), "updates +", len(r2), "new )")
