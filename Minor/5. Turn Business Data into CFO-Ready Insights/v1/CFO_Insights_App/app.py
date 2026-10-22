"""CFO Insights (v1) - Streamlit app. Run:  streamlit run app.py"""
import html, io, os, tempfile
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import pipeline as p

SAGE, PALE, RED = "#8A9A86", "#C9D2C5", "#C98E82"
HERE = os.path.dirname(os.path.abspath(__file__))
st.set_page_config(page_title="CFO Insights", page_icon="📊", layout="wide")
st.markdown("""<style>
html,body,[class*="css"]{font-family:-apple-system,"Segoe UI",Helvetica,sans-serif}
h1,h2,h3{font-family:Georgia,serif!important;font-weight:400!important}
[data-testid="stMetricValue"]{font-family:Georgia,serif;font-weight:400}
[data-testid="stMetric"]{border-top:1px solid #8A9A86;padding-top:10px}
.block-container{max-width:1200px;padding-top:2rem}</style>""", unsafe_allow_html=True)


@st.cache_data
def load(choice, upload_bytes=None):
    r1 = pd.read_csv(os.path.join(HERE, "data", "sample1_messy.csv"))
    r2 = pd.read_csv(os.path.join(HERE, "data", "sample2_messy.csv"))
    if choice == "Sample 1 (cleaned)":
        d, fx = p.clean(r1)
    elif choice == "Sample 1 + 2 (synced)":
        d, fx = p.sync(r1, r2)
    else:                                            # your own file, appended to nothing: cleaned on its own
        d, fx = p.clean(pd.read_csv(io.BytesIO(upload_bytes)))
    return d, fx


def money(x):
    return f"${x:,.0f}"


st.title("Financial Overview")
with st.sidebar:
    st.header("Data")
    choice = st.radio("Dataset", ["Sample 1 (cleaned)", "Sample 1 + 2 (synced)", "Upload my own CSV"])
    up = None
    if choice == "Upload my own CSV":
        f = st.file_uploader("Messy invoice CSV (same 9 columns)", type="csv")
        up = f.getvalue() if f else None
        if up is None:
            st.info("Upload a CSV with: Invoice_ID, Client_name, Issue_date, Due_date, Amount(USD), Payment_status, "
                    "Payment_date, Project_type, any_notes_or_remarks")
            st.stop()
    try:
        d, fixes = load(choice, up)
    except Exception as e:                              # bad / unreadable upload: show a message instead of a traceback
        st.error(f"Could not read that file: {e}")
        st.stop()
    m = p.metrics(d)
    st.caption(f"Overdue days are counted as of {p.ASOF:%d %b %Y}.")
    path = os.path.join(tempfile.gettempdir(), "CFO_Dashboard.xlsx")
    p.export_xlsx(d, path)
    st.download_button("⬇ Download Excel dashboard", open(path, "rb").read(), "CFO_Dashboard.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

tabs = st.tabs(["Dashboard", "Invoices", "Analytics", "Overdue", "Data quality"])
k, mo = m["kpis"], pd.DataFrame(m["monthly"])
cl = pd.DataFrame(m["clients"])

with tabs[0]:
    st.caption(f"{m['months'][0]} to {m['months'][-1]}  ·  {int(k['invoices'])} invoices")
    a = st.columns(4)
    a[0].metric("Total invoiced", money(k["total_invoiced"])); a[1].metric("Collected", money(k["total_collected"]))
    a[2].metric("Outstanding", money(k["total_outstanding"])); a[3].metric("Collection rate", f"{k['collection_pct']:.1f}%")
    b = st.columns(4)
    b[0].metric("Average invoice", money(k["avg_invoice"])); b[1].metric("Invoices", int(k["invoices"]))
    b[2].metric("Overdue (open)", money(k["overdue_open_amount"])); b[3].metric("Avg days to pay", f"{k['avg_days_to_pay']:.0f}")
    st.subheader("Monthly revenue")
    fig = go.Figure([go.Bar(x=mo.Month, y=mo.invoiced, name="Invoiced", marker_color=PALE),
                     go.Bar(x=mo.Month, y=mo.collected, name="Collected", marker_color=SAGE)])
    fig.update_layout(barmode="overlay", height=320, margin=dict(l=0, r=0, t=10, b=0), legend=dict(orientation="h"))
    st.plotly_chart(fig, width="stretch")
    c1, c2 = st.columns([1.6, 1])
    with c1:
        st.subheader("Clients, by revenue")
        t = cl[["Client_name", "invoiced", "share", "collected", "outstanding", "spark"]]
        st.dataframe(t, hide_index=True, width="stretch", column_config={
            "Client_name": "Client", "invoiced": st.column_config.NumberColumn("Invoiced", format="$%d"),
            "share": st.column_config.ProgressColumn("Share", format="%.0f%%", min_value=0, max_value=100),
            "collected": st.column_config.NumberColumn("Paid", format="$%d"),
            "outstanding": st.column_config.NumberColumn("Open", format="$%d"),
            "spark": st.column_config.LineChartColumn("Trend")})
    with c2:
        st.subheader("Notes")
        for s in m["insights"]:
            st.markdown(f"— {s}")
    st.subheader("Revenue by project type")
    ty = pd.DataFrame(m["types"]).sort_values("amount")
    f2 = go.Figure(go.Bar(x=ty.amount, y=ty.Project_type, orientation="h", marker_color=SAGE))
    f2.update_layout(height=260, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(f2, width="stretch")

with tabs[1]:
    c = st.columns([2, 1, 1])
    q = c[0].text_input("Search invoice, client, project, note")
    sts = c[1].multiselect("Status", ["Paid", "Pending", "Overdue"])
    cls = c[2].multiselect("Client", sorted(d.Client_name.unique()))
    v = d[p.COLS].copy()
    if q:
        v = v[v[["Invoice_ID", "Client_name", "Project_type", "Notes"]].astype(str).agg(" ".join, axis=1).str.contains(q, case=False)]
    if sts: v = v[v.Payment_status.isin(sts)]
    if cls: v = v[v.Client_name.isin(cls)]
    st.caption(f"{len(v)} invoices · {money(v.Amount.sum())}  (click a column header to sort)")
    st.dataframe(v, hide_index=True, width="stretch", height=560, column_config={
        "Amount": st.column_config.NumberColumn(format="$%d"),
        "Issue_date": st.column_config.DateColumn(), "Due_date": st.column_config.DateColumn(),
        "Payment_date": st.column_config.DateColumn(),
        "Data_Notes": st.column_config.TextColumn("Cleaning notes", width="large")})

with tabs[2]:
    st.subheader("Trend: invoiced vs collected")
    f3 = go.Figure([go.Scatter(x=mo.Month, y=mo.invoiced, name="Invoiced", line=dict(color=SAGE, width=3), mode="lines+markers"),
                    go.Scatter(x=mo.Month, y=mo.collected, name="Collected", line=dict(color=RED, dash="dash"), mode="lines+markers")])
    f3.update_layout(height=320, margin=dict(l=0, r=0, t=10, b=0), legend=dict(orientation="h"))
    st.plotly_chart(f3, width="stretch")
    st.subheader("Month-on-month growth")
    g = mo[["Month", "invoiced", "collected", "count", "mom"]].rename(columns={"count": "invoices"})
    st.dataframe(g, hide_index=True, width="stretch", column_config={
        "invoiced": st.column_config.NumberColumn(format="$%d"), "collected": st.column_config.NumberColumn(format="$%d"),
        "mom": st.column_config.NumberColumn("MoM %", format="%+.0f%%")})
    st.subheader("Client performance by quarter")
    qm = pd.DataFrame(m["quarterly"]).set_index("Client_name")
    hm = go.Figure(go.Heatmap(z=qm.values, x=list(qm.columns), y=list(qm.index), colorscale=[[0, "#FFFFFF"], [1, SAGE]],
                              text=[[f"${v:,.0f}" for v in r] for r in qm.values], texttemplate="%{text}", showscale=False))
    hm.update_layout(height=60 + 40 * len(qm), margin=dict(l=0, r=0, t=10, b=0), yaxis=dict(autorange="reversed"))
    st.plotly_chart(hm, width="stretch")
    st.subheader("Suggestions to manage your data better")
    for s in m["suggestions"]:
        st.markdown(f"— {s}")

with tabs[3]:
    st.subheader("Overdue days by client")
    oc = pd.DataFrame(m["overdue_clients"])
    st.dataframe(oc, hide_index=True, width="stretch", column_config={
        "open_overdue_amount": st.column_config.ProgressColumn("Open overdue $", format="$%d", min_value=0,
                                                                max_value=float(max(oc.open_overdue_amount.max(), 1))),
        "avg_days_late_when_paid": st.column_config.NumberColumn("Avg days late when paid", format="%.1f")})
    st.subheader("Overdue days by invoice")
    st.dataframe(pd.DataFrame(m["overdue_invoices"]), hide_index=True, width="stretch",
                 column_config={"Amount": st.column_config.NumberColumn(format="$%d")})

with tabs[4]:
    st.subheader("What was cleaned")
    st.dataframe(pd.DataFrame({"Fix": list(fixes), "Rows": list(fixes.values())}).sort_values("Rows", ascending=False),
                 hide_index=True, width="stretch")
    st.subheader("Raw vs cleaned (rows that needed fixes)")
    fx = d[d.Data_Notes != ""][["Invoice_ID", "Raw_client", "Client_name", "Raw_issue", "Issue_date", "Raw_amount", "Amount"]]
    st.dataframe(fx, hide_index=True, width="stretch")

# ---- sticky note: always visible below the tabs
def _li(items):
    return "".join(f"<li>{html.escape(x)}</li>" for x in items)


st.markdown("""<style>
.sticky{position:relative;margin:56px auto 24px;max-width:600px;background:#F7EDB5;color:#3A3420;padding:28px 30px 22px;
transform:rotate(-1deg);box-shadow:0 12px 26px rgba(0,0,0,.16),inset 0 -26px 34px -28px rgba(0,0,0,.2);
font-family:"Segoe Print","Bradley Hand","Comic Sans MS",Georgia,cursive}
.sticky:before{content:"";position:absolute;top:-12px;left:50%;width:96px;height:24px;background:rgba(138,154,134,.6);transform:translateX(-50%) rotate(2deg)}
.sticky h3{margin:0 0 6px;font-size:19px;font-weight:600;color:#3A3420}
.sticky h4{margin:14px 0 4px;font-size:12px;letter-spacing:.1em;text-transform:uppercase;opacity:.7;color:#3A3420}
.sticky ul{margin:0;padding-left:18px}.sticky li{margin:5px 0;font-size:13.5px;line-height:1.45;color:#3A3420}</style>""" +
            f"""<div class="sticky"><h3>📝 Notes &amp; suggestions</h3><h4>What the data says</h4><ul>{_li(m["insights"])}</ul>
<h4>To manage your data better</h4><ul>{_li(m["suggestions"])}</ul></div>""", unsafe_allow_html=True)
