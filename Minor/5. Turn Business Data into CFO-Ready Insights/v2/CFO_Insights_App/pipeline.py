"""CFO Insights pipeline: clean messy invoices -> KPIs/analytics -> formatted Excel dashboard."""
import re, difflib
import numpy as np
import pandas as pd
from xlsxwriter.utility import xl_rowcol_to_cell

ASOF = pd.Timestamp("2026-10-22")          # "today" for overdue calculations
COLS = ["Invoice_ID", "Client_name", "Issue_date", "Due_date", "Amount", "Payment_status", "Payment_date",
        "Project_type", "Notes", "Overdue_days", "Data_Notes"]
_SUF = r"\b(inc|ltd|llc|corp|corporation|co|company|pvt|and)\b"


def _key(n):
    n = re.sub(_SUF, "", str(n).lower().replace("&", " and "))
    return re.sub(r"[^a-z]", "", n)


def _blank(s):
    s = s.astype(str).str.strip()
    return s.mask(s.str.lower().isin(["", "nan", "none", "nat", "null", "n/a", "-", "not yet"]))


def _date(s):
    s = _blank(s)
    iso = pd.to_datetime(s, format="%Y-%m-%d", errors="coerce")
    other = pd.to_datetime(s.where(iso.isna()), dayfirst=True, errors="coerce", format="mixed")
    return s, iso.fillna(other)


def clean(raw, asof=ASOF):
    """Returns (clean_df, fixes_dict). Every repair is logged in Data_Notes and in fixes."""
    d = (raw.rename(columns=lambda c: c.strip())
            .rename(columns={"Amount(USD)": "Amount", "any_notes_or_remarks": "Notes"})
            .copy().reset_index(drop=True))
    need = [c for c in ["Invoice_ID", "Client_name", "Issue_date", "Amount"] if c not in d.columns]
    if need:
        raise ValueError("Missing column(s): " + ", ".join(need) + ". Expected: Invoice_ID, Client_name, Issue_date, Due_date, "
                         "Amount(USD), Payment_status, Payment_date, Project_type, any_notes_or_remarks")
    if d.empty:
        raise ValueError("The file has no rows.")
    for c in ["Due_date", "Payment_status", "Payment_date", "Project_type", "Notes"]:
        if c not in d.columns:
            d[c] = np.nan
    d["Raw_client"], d["Raw_issue"], d["Raw_amount"] = (d.Client_name.fillna("").astype(str), d.Issue_date.fillna("").astype(str),
                                                       d.Amount.fillna("").astype(str))
    d["_n"] = [[] for _ in range(len(d))]
    fixes = {}

    def flag(mask, msg):
        mask = pd.Series(np.asarray(mask), index=d.index).fillna(False).astype(bool)
        for i in d.index[mask]:
            d.at[i, "_n"].append(msg)
        if mask.sum():
            fixes[msg] = fixes.get(msg, 0) + int(mask.sum())

    # 1. invoice ids + duplicates (later rows win, so appended updates override old data)
    d["Invoice_ID"] = (d.Invoice_ID.astype(str).str.upper().str.replace(r"[^A-Z0-9]", "", regex=True)
                       .str.replace(r"^INV-?(\d+)$", r"INV-\1", regex=True))
    dup = d.duplicated("Invoice_ID", keep="last")
    if dup.sum():
        fixes["Duplicate / superseded invoice rows merged"] = int(dup.sum())
    d = d[~dup].reset_index(drop=True)

    # 2. client names: merge spelling / case / suffix variants
    nm = _blank(d.Client_name).fillna("Unknown Client").str.replace(r"\s+", " ", regex=True).str.strip(" .")
    canon, mp = {}, {}
    for name in nm.value_counts().index:
        k = _key(name) or name.lower()
        m = difflib.get_close_matches(k, list(canon), n=1, cutoff=0.85)
        if m:
            k = m[0]
        else:
            canon[k] = name.title() if (name.isupper() or name.islower()) else name
        mp[name] = canon[k]
    d["Client_name"] = nm.map(mp)
    flag(d.Client_name != d.Raw_client.str.strip(), "Client name standardised")

    # 3. dates
    for c in ["Issue_date", "Due_date", "Payment_date"]:
        s, p = _date(d[c])
        flag(s.notna() & p.notna() & ~s.str.match(r"\d{4}-\d{2}-\d{2}$", na=False), f"{c} format standardised")
        flag(s.notna() & p.isna(), f"Unreadable {c} cleared")
        d[c] = p
    m = d.Issue_date.isna() & d.Due_date.notna()
    d.loc[m, "Issue_date"] = d.Due_date - pd.Timedelta(days=30)
    flag(m, "Missing issue date filled (due date - 30d)")
    m = d.Due_date.isna()
    d.loc[m, "Due_date"] = d.Issue_date + pd.Timedelta(days=30)
    flag(m, "Missing due date filled (issue date + 30d)")
    gone = d.Issue_date.isna()
    if gone.any():
        fixes["Rows dropped (no usable issue or due date)"] = int(gone.sum())
        d = d[~gone].reset_index(drop=True)

    # 4. amounts
    txt = d.Amount.astype(str)
    a = pd.to_numeric(txt.str.replace(r"[^0-9.\-]", "", regex=True), errors="coerce")
    flag(a.notna() & ~txt.str.fullmatch(r"-?[0-9.]+", na=False), "Amount format standardised")
    flag(a < 0, "Negative amount corrected to positive")
    a = a.abs()
    miss = a.isna()
    a = a.fillna(a.groupby(d.Client_name).transform("median")).fillna(a.median())
    flag(miss, "Missing amount estimated from client median - verify")
    d["Amount"] = a.round(2)

    # 5. payment status (always re-derived from the dates)
    st = d.Payment_status.fillna("").astype(str).str.lower().str.strip()
    blank = st.isin(["", "nan", "none"])
    raw_paid = st.str.contains("paid|settled|received|cleared") & ~st.str.contains("unpaid|not")
    m = raw_paid & d.Payment_date.isna()
    d.loc[m, "Payment_date"] = d.Due_date
    flag(m, "Marked paid without payment date - due date assumed")
    flag(d.Payment_date.notna() & (d.Payment_date < d.Issue_date), "Payment date is before issue date - please verify")
    final = np.where(d.Payment_date.notna(), "Paid", np.where(d.Due_date < asof, "Overdue", "Pending"))
    raw_final = np.select([raw_paid, st.str.contains("overdue|late")], ["Paid", "Overdue"], "Pending")
    flag(blank, "Missing status derived from dates")
    flag(~blank & (raw_final != final), "Status recalculated from dates")
    d["Payment_status"] = final

    # 6. project type
    pt = _blank(d.Project_type).str.replace("-", " ").str.title()
    mode = pt.groupby(d.Client_name).agg(lambda s: s.mode().iat[0] if s.notna().any() else np.nan)
    m = pt.isna()
    d["Project_type"] = pt.fillna(d.Client_name.map(mode)).fillna("Unspecified")
    flag(m, "Missing project type filled (client's most common)")
    flag(d.Client_name.eq("Unknown Client"), "Missing client name - set to Unknown Client")

    # 7. overdue days (days late if paid late, days past due if still open)
    late = np.where(d.Payment_date.notna(), (d.Payment_date - d.Due_date).dt.days, (asof - d.Due_date).dt.days)
    d["Overdue_days"] = np.clip(late, 0, None).astype(int)
    d["Notes"] = _blank(d.Notes).fillna("")
    d["Data_Notes"] = d["_n"].map("; ".join)
    d["Month"] = d.Issue_date.dt.strftime("%Y-%m")
    d["Quarter"] = d.Issue_date.dt.to_period("Q").astype(str)
    d = d.sort_values(["Issue_date", "Invoice_ID"]).reset_index(drop=True)
    return d[COLS + ["Month", "Quarter", "Raw_client", "Raw_issue", "Raw_amount"]], fixes


def sync(*raws):
    """Append further raw files to the earlier ones and re-clean everything together."""
    return clean(pd.concat(raws, ignore_index=True))


def _rec(df):
    df = df.copy()
    for c in df.columns:
        if str(df[c].dtype).startswith("datetime"):
            df[c] = df[c].dt.strftime("%Y-%m-%d")
    return df.round(2).astype(object).where(df.notna(), None).to_dict("records")


def metrics(d):
    paid, tot = d[d.Payment_status == "Paid"], d.Amount.sum()
    openi = d[d.Payment_status != "Paid"]
    late_open = openi[openi.Overdue_days > 0]
    months = sorted(d.Month.unique())
    mo = d.groupby("Month").agg(invoiced=("Amount", "sum"), count=("Amount", "size")).reindex(months)
    mo["collected"] = paid.groupby("Month").Amount.sum().reindex(months).fillna(0)
    mo["mom"] = mo.invoiced.pct_change() * 100
    g = d.groupby("Client_name")
    cl = pd.DataFrame({"invoiced": g.Amount.sum(), "count": g.size(),
                       "collected": paid.groupby("Client_name").Amount.sum(),
                       "avg_overdue": g.Overdue_days.mean()}).fillna(0)
    cl["outstanding"] = cl.invoiced - cl.collected
    cl["share"] = cl.invoiced / tot * 100
    sp = d.pivot_table(index="Client_name", columns="Month", values="Amount", aggfunc="sum").reindex(columns=months).fillna(0)
    cl["spark"] = [sp.loc[i].round(0).tolist() for i in cl.index]
    cl = cl.sort_values("invoiced", ascending=False).reset_index()
    ty = d.groupby("Project_type").agg(amount=("Amount", "sum"), count=("Amount", "size")).sort_values("amount", ascending=False)
    ty["share"] = ty.amount / tot * 100
    qs = sorted(d.Quarter.unique())
    qm = d.pivot_table(index="Client_name", columns="Quarter", values="Amount", aggfunc="sum").reindex(index=cl.Client_name, columns=qs).fillna(0)
    og = late_open.groupby("Client_name")
    lp = paid[paid.Overdue_days > 0].groupby("Client_name").Overdue_days.mean()
    oc = pd.DataFrame({"open_overdue_invoices": og.size(), "open_overdue_amount": og.Amount.sum(),
                       "max_days_open": og.Overdue_days.max(),
                       "total_overdue_days": d.groupby("Client_name").Overdue_days.sum(),
                       "avg_days_late_when_paid": lp}).reindex(cl.Client_name).fillna(0)
    oc = oc.sort_values("open_overdue_amount", ascending=False).reset_index()
    inv_over = d[d.Overdue_days > 0].sort_values(["Overdue_days", "Invoice_ID"], ascending=[False, True])[
        ["Invoice_ID", "Client_name", "Amount", "Payment_status", "Due_date", "Overdue_days"]]
    k = dict(total_invoiced=tot, total_collected=paid.Amount.sum(), total_outstanding=openi.Amount.sum(),
             collection_pct=paid.Amount.sum() / tot * 100, avg_invoice=d.Amount.mean(), invoices=len(d),
             overdue_open_amount=late_open.Amount.sum(), overdue_open_count=len(late_open),
             avg_days_to_pay=float((paid.Payment_date - paid.Issue_date).dt.days.mean()))
    top, last = cl.iloc[0], mo.dropna(subset=["mom"]).iloc[-1] if mo.mom.notna().any() else None
    ins = [f"{top.Client_name} is your largest client at {top.share:.0f}% of billings; the top 3 clients make up "
           f"{cl.share.head(3).sum():.0f}%.",
           f"{ty.index[0]} leads revenue by project type ({ty.share.iloc[0]:.0f}% of billings).",
           f"Collection rate is {k['collection_pct']:.0f}%; ${k['total_outstanding']:,.0f} is still outstanding, "
           f"of which ${k['overdue_open_amount']:,.0f} across {k['overdue_open_count']} invoices is past due."]
    if last is not None:
        ins.append(f"Latest month ({last.name}) billings moved {last.mom:+.0f}% vs the month before.")
    if len(oc) and oc.open_overdue_amount.iloc[0] > 0:
        ins.append(f"Chase {oc.Client_name.iloc[0]} first: ${oc.open_overdue_amount.iloc[0]:,.0f} overdue, up to "
                   f"{int(oc.max_days_open.iloc[0])} days late.")
    sug = ["Send payment reminders at day 1, 7 and 14 past due; 3 reminders usually recover most late invoices.",
           "Move your slowest payers to shorter terms (net-15) or require a deposit on large projects.",
           "Keep one master invoice sheet and append new rows monthly; this pipeline re-cleans and re-syncs everything.",
           "Use a fixed client list (dropdown) and ISO dates (YYYY-MM-DD) when entering data to avoid cleanup work.",
           "Review the Data Quality log each month; estimated amounts should be confirmed against the real invoice."]
    return dict(kpis={x: round(float(v), 2) for x, v in k.items()}, monthly=_rec(mo.reset_index()),
                clients=_rec(cl), types=_rec(ty.reset_index()), quarters=qs,
                quarterly=_rec(qm.reset_index()), overdue_clients=_rec(oc), overdue_invoices=_rec(inv_over),
                insights=ins, suggestions=sug, months=months)


def export_xlsx(d, path):
    """Formatted Excel dashboard: Dashboard / Invoices / Analytics / Overdue, with sparklines + comments."""
    m = metrics(d)
    SAGE, INK, MUTE, PALE = "#8A9A86", "#2B2B28", "#8C8C84", "#F1F3EE"
    with pd.ExcelWriter(path, engine="xlsxwriter", datetime_format="yyyy-mm-dd") as xw:
        wb = xw.book
        f = lambda **k: wb.add_format({"font_name": "Georgia", "font_color": INK, **k})
        title, sub = f(font_size=22), f(font_size=10, font_color=MUTE, italic=True)
        lab, hdr = f(font_size=9, font_color=MUTE, bold=False, top=1, top_color=SAGE), f(font_size=10, bold=True, bg_color=SAGE, font_color="white")
        usd, pct, txt = f(num_format="$#,##0"), f(num_format="0.0%"), f()
        big = f(font_size=18, num_format="$#,##0")
        bigp, bign = f(font_size=18, num_format="0.0%"), f(font_size=18, num_format="0")
        # ---------- Invoices
        inv = d[COLS].copy()
        inv.to_excel(xw, sheet_name="Invoices", startrow=1, header=False, index=False)
        wi = xw.sheets["Invoices"]
        wi.add_table(0, 0, len(inv), len(COLS) - 1, {"columns": [{"header": c, "header_format": hdr} for c in COLS],
                                                       "style": "Table Style Light 1", "autofilter": True})
        for i, w in enumerate([11, 20, 12, 12, 12, 13, 12, 16, 26, 13, 46]):
            wi.set_column(i, i, w, f(num_format="$#,##0") if i == 4 else None)
        wi.freeze_panes(1, 0)
        for st, col in [("Paid", "#DDE6D8"), ("Pending", "#F3EBD6"), ("Overdue", "#EFD9D4")]:
            wi.conditional_format(1, 5, len(inv), 5, {"type": "cell", "criteria": "==", "value": f'"{st}"',
                                                       "format": wb.add_format({"bg_color": col})})
        wi.conditional_format(1, 9, len(inv), 9, {"type": "data_bar", "bar_color": "#D9B8B0", "bar_solid": True})
        for r, n in enumerate(d.Data_Notes, start=1):
            if n:
                wi.write_comment(r, 4, "Data cleaning notes:\n" + n.replace("; ", "\n"), {"x_scale": 2, "y_scale": 1.6})
        # ---------- Analytics
        wa = wb.add_worksheet("Analytics")
        months, cl = m["months"], m["clients"]
        wa.write_row(0, 0, ["Client \\ Month"] + months + ["Trend"], hdr)
        for i, c in enumerate(cl, start=1):
            wa.write(i, 0, c["Client_name"], txt)
            wa.write_row(i, 1, c["spark"], usd)
            wa.add_sparkline(i, len(months) + 1, {"range": f"Analytics!{xl_rowcol_to_cell(i, 1)}:{xl_rowcol_to_cell(i, len(months))}", "markers": True,
                                                  "series_color": SAGE, "high_point": True})
        q0 = len(cl) + 3
        wa.write_row(q0, 0, ["Client \\ Quarter"] + m["quarters"], hdr)
        for i, row in enumerate(m["quarterly"], start=q0 + 1):
            wa.write(i, 0, row["Client_name"], txt)
            wa.write_row(i, 1, [row[q] for q in m["quarters"]], usd)
        wa.conditional_format(q0 + 1, 1, q0 + len(cl), len(m["quarters"]),
                              {"type": "2_color_scale", "min_color": "#FFFFFF", "max_color": SAGE})
        t0 = q0 + len(cl) + 3
        wa.write_row(t0, 0, ["Project type", "Revenue", "Share", "Invoices"], hdr)
        for i, t in enumerate(m["types"], start=t0 + 1):
            wa.write(i, 0, t["Project_type"], txt); wa.write(i, 1, t["amount"], usd)
            wa.write(i, 2, t["share"] / 100, pct); wa.write(i, 3, t["count"], txt)
        wa.set_column(0, 0, 22); wa.set_column(1, len(months) + 1, 12)
        ch = wb.add_chart({"type": "bar"})
        ch.add_series({"categories": ["Analytics", t0 + 1, 0, t0 + len(m["types"]), 0],
                       "values": ["Analytics", t0 + 1, 1, t0 + len(m["types"]), 1], "fill": {"color": SAGE}})
        ch.set_title({"name": "Revenue by project type", "name_font": {"name": "Georgia", "size": 11}})
        ch.set_legend({"none": True}); ch.set_size({"width": 480, "height": 280})
        wa.insert_chart(t0, 6, ch)
        # ---------- Overdue
        wo = wb.add_worksheet("Overdue")
        wo.write_row(0, 0, ["Client", "Open overdue invoices", "Open overdue $", "Max days open", "Total overdue days",
                            "Avg days late when paid"], hdr)
        for i, r in enumerate(m["overdue_clients"], start=1):
            wo.write_row(i, 0, [r["Client_name"], r["open_overdue_invoices"], r["open_overdue_amount"], r["max_days_open"],
                                r["total_overdue_days"], r["avg_days_late_when_paid"]], txt)
        n = len(m["overdue_clients"])
        wo.conditional_format(1, 2, n, 2, {"type": "data_bar", "bar_color": "#D9B8B0", "bar_solid": True})
        i0 = n + 3
        wo.write_row(i0, 0, ["Invoice", "Client", "Amount", "Status", "Due date", "Overdue days"], hdr)
        for i, r in enumerate(m["overdue_invoices"], start=i0 + 1):
            wo.write_row(i, 0, [r["Invoice_ID"], r["Client_name"], r["Amount"], r["Payment_status"], r["Due_date"], r["Overdue_days"]], txt)
        wo.set_column(0, 5, 22)
        # ---------- Dashboard
        w = wb.add_worksheet("Dashboard")
        w.hide_gridlines(2); w.set_column(0, 0, 3); w.set_column(1, 12, 15)
        w.write(1, 1, "Financial Overview", title)
        w.write(2, 1, f"Invoices {months[0]} to {months[-1]}  ·  as of {ASOF:%d %b %Y}", sub)
        k = m["kpis"]
        for j, (lb, v, fm) in enumerate([("TOTAL INVOICED", k["total_invoiced"], big), ("COLLECTED", k["total_collected"], big),
                                          ("OUTSTANDING", k["total_outstanding"], big),
                                          ("COLLECTION RATE", k["collection_pct"] / 100, bigp)]):
            w.write(4, 1 + j * 3, lb, lab); w.write(5, 1 + j * 3, v, fm)
        for j, (lb, v, fm) in enumerate([("AVG INVOICE", k["avg_invoice"], big), ("INVOICES", k["invoices"], bign),
                                          ("OVERDUE (OPEN)", k["overdue_open_amount"], big),
                                          ("AVG DAYS TO PAY", k["avg_days_to_pay"], bign)]):
            w.write(7, 1 + j * 3, lb, lab); w.write(8, 1 + j * 3, v, fm)
        w.write_row(11, 1, ["Month", "Invoiced", "Collected", "MoM"], hdr)
        for i, r in enumerate(m["monthly"], start=12):
            w.write(i, 1, r["Month"], txt); w.write(i, 2, r["invoiced"], usd); w.write(i, 3, r["collected"], usd)
            if r["mom"] is not None:
                w.write(i, 4, r["mom"] / 100, f(num_format="+0%;-0%"))
        ne = 11 + len(m["monthly"])
        w.write(11, 6, "Trend", hdr)
        w.add_sparkline(12, 6, {"range": f"Dashboard!$C$13:$C${ne + 1}", "type": "column", "series_color": SAGE,
                                "high_point": True})
        ch = wb.add_chart({"type": "column"})
        ch.add_series({"name": "Invoiced", "categories": ["Dashboard", 12, 1, ne, 1], "values": ["Dashboard", 12, 2, ne, 2], "fill": {"color": SAGE}})
        ch.add_series({"name": "Collected", "categories": ["Dashboard", 12, 1, ne, 1], "values": ["Dashboard", 12, 3, ne, 3], "fill": {"color": "#C9D2C5"}})
        ch.set_title({"name": "Monthly revenue", "name_font": {"name": "Georgia", "size": 11}})
        ch.set_legend({"position": "bottom"}); ch.set_size({"width": 520, "height": 280})
        w.insert_chart(11, 7, ch)
        c0 = ne + 3
        w.write_row(c0, 1, ["Client", "Invoiced", "Share", "Paid", "Outstanding", "Invoices"], hdr)
        for i, r in enumerate(cl, start=c0 + 1):
            w.write(i, 1, r["Client_name"], txt); w.write(i, 2, r["invoiced"], usd); w.write(i, 3, r["share"] / 100, pct)
            w.write(i, 4, r["collected"], usd); w.write(i, 5, r["outstanding"], usd); w.write(i, 6, r["count"], txt)
        w.conditional_format(c0 + 1, 3, c0 + len(cl), 3, {"type": "data_bar", "bar_color": SAGE, "bar_solid": True})
        n0 = c0 + len(cl) + 3
        w.write(n0, 1, "Notes", f(font_size=12))
        for i, t in enumerate(m["insights"], start=n0 + 1):
            w.write(i, 1, "·  " + t, txt)
        order = ["Dashboard", "Invoices", "Analytics", "Overdue"]
        wb.worksheets_objs.sort(key=lambda x: order.index(x.name))
        w.activate(); w.set_first_sheet()
    return m
