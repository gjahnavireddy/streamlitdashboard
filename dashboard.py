"""
From Blind Spots to Baselines — Marketplace Analytics
======================================================
Run:   streamlit run dashboard.py
Deps:  pip install streamlit plotly pandas numpy
Data:  place Mock_orders_data.csv in the same directory
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Marketplace Analytics",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Theme ─────────────────────────────────────────────────────────────────────
PURPLE     = "#6c63ff"
PURPLE_LT  = "#eeedfe"
TEAL       = "#14b8a6"
AMBER      = "#f59e0b"
CORAL      = "#f87171"
GRAY       = "#94a3b8"
GREEN      = "#22c55e"
BG         = "#f8f9fc"

st.markdown(f"""
<style>
  [data-testid="stAppViewContainer"] {{ background: {BG}; }}
  [data-testid="stSidebar"] {{ background: #1a1a2e !important; }}
  [data-testid="stSidebar"] * {{ color: #c8c8e8 !important; }}
  [data-testid="stSidebar"] .stRadio label {{ color: #c8c8e8 !important; }}
  div[data-testid="stSidebarNav"] {{ display: none; }}
  .kpi-row {{ display: flex; gap: 12px; margin-bottom: 20px; }}
  .kpi {{
      flex: 1; background: white; border-radius: 12px;
      padding: 18px 20px; border-top: 3px solid {PURPLE};
      box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  }}
  .kpi-val {{ font-size: 1.9rem; font-weight: 700; color: #1a1a2e; line-height: 1.1; }}
  .kpi-lbl {{ font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.06em; color: #888; margin-bottom: 4px; }}
  .kpi-delta-pos {{ color: {GREEN}; font-size: 0.82rem; font-weight: 600; }}
  .kpi-delta-neg {{ color: {CORAL}; font-size: 0.82rem; font-weight: 600; }}
  .kpi-delta-neu {{ color: {GRAY}; font-size: 0.82rem; }}
  .section-hd {{
      font-size: 0.78rem; font-weight: 700; text-transform: uppercase;
      letter-spacing: 0.08em; color: {PURPLE}; border-bottom: 2px solid {PURPLE_LT};
      padding-bottom: 5px; margin-bottom: 12px;
  }}
  .chart-card {{
      background: white; border-radius: 12px; padding: 18px 20px;
      box-shadow: 0 1px 4px rgba(0,0,0,0.06); margin-bottom: 16px;
  }}
  .insight-box {{
      background: {PURPLE_LT}; border-left: 4px solid {PURPLE};
      border-radius: 0 8px 8px 0; padding: 12px 16px;
      font-size: 0.88rem; color: #3a3560; margin-top: 8px;
  }}
  .warn-box {{
      background: #fff7ed; border-left: 4px solid {AMBER};
      border-radius: 0 8px 8px 0; padding: 12px 16px;
      font-size: 0.88rem; color: #7c4a0a; margin-top: 8px;
  }}
  .page-title {{ font-size: 1.6rem; font-weight: 700; color: #1a1a2e; margin-bottom: 2px; }}
  .page-sub {{ font-size: 0.88rem; color: #888; margin-bottom: 20px; }}
  .merchant-tag-good {{
      display:inline-block; background:#dcfce7; color:#166534;
      border-radius:4px; padding:2px 8px; font-size:0.75rem; font-weight:600;
  }}
  .merchant-tag-bad {{
      display:inline-block; background:#fee2e2; color:#991b1b;
      border-radius:4px; padding:2px 8px; font-size:0.75rem; font-weight:600;
  }}
</style>
""", unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────────────────────────
def kpi(label, value, delta=None, delta_good=True, color=PURPLE):
    if delta is not None:
        is_pos = delta >= 0
        arrow  = "▲" if is_pos else "▼"
        cls    = ("kpi-delta-pos" if (is_pos == delta_good) else "kpi-delta-neg")
        d_html = f'<div class="{cls}">{arrow} {abs(delta):.1%} WoW</div>'
    else:
        d_html = '<div class="kpi-delta-neu">&nbsp;</div>'
    return (
        f'<div class="kpi" style="border-top-color:{color}">'
        f'<div class="kpi-lbl">{label}</div>'
        f'<div class="kpi-val">{value}</div>'
        f'{d_html}</div>'
    )

def section_hd(text):
    st.markdown(f'<div class="section-hd">{text}</div>', unsafe_allow_html=True)

def insight(text, warn=False):
    cls = "warn-box" if warn else "insight-box"
    st.markdown(f'<div class="{cls}">{text}</div>', unsafe_allow_html=True)

def chart_layout(fig, height=300, legend=False, xgrid=False, ygrid=True):
    fig.update_layout(
        height=height,
        margin=dict(l=0, r=0, t=10, b=30),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(size=11)) if legend else None,
        font=dict(size=11, family="Arial"),
        hoverlabel=dict(bgcolor="white", font_size=12),
    )
    fig.update_xaxes(showgrid=xgrid, gridcolor="#f0f0f0", zeroline=False)
    fig.update_yaxes(showgrid=ygrid, gridcolor="#f0f0f0", zeroline=False)
    return fig

def wow(series, weeks):
    if len(weeks) < 2:
        return None
    cur  = series.get(weeks[-2], 0)   # last complete week
    prev = series.get(weeks[-3], 1) if len(weeks) >= 3 else None
    if prev is None or prev == 0:
        return None
    return (cur - prev) / prev

# ── Data loading ──────────────────────────────────────────────────────────────
@st.cache_data
def load_data(path="Mock_orders_data.csv"):
    df = pd.read_csv(path)
    df["order_dt"]    = pd.to_datetime(df["order datetime"])
    df["delivery_dt"] = pd.to_datetime(df["delivery datetime"])
    df["week"]        = df["order_dt"].dt.to_period("W").apply(lambda x: x.start_time)
    df["month"]       = df["order_dt"].dt.to_period("M").apply(lambda x: x.start_time)
    df["date"]        = df["order_dt"].dt.date
    df["hour"]        = df["order_dt"].dt.hour

    df["delivery_minutes"] = (df["delivery_dt"] - df["order_dt"]).dt.total_seconds() / 60

    df["net_revenue"]   = df.apply(
        lambda r: r["subtotal"] * r["Commission Rate"] if r["Order Status"] == "Successful" else 0, axis=1
    )
    df["nps_category"] = pd.cut(
        df["NPS"], bins=[0, 4, 6, 10],
        labels=["Detractor (1–4)", "Passive (5–6)", "Promoter (7–10)"]
    )

    # New vs returning
    first_dt = (
        df[df["Order Status"] == "Successful"]
        .groupby("User ID")["order_dt"].min().rename("first_order_dt")
    )
    df = df.merge(first_dt, on="User ID", how="left")
    df["is_new_user"]   = (df["order_dt"] == df["first_order_dt"]) & (df["Order Status"] == "Successful")
    df["cohort_week"]   = df["first_order_dt"].dt.to_period("W").apply(
        lambda x: x.start_time if pd.notna(x) else pd.NaT
    )
    return df

@st.cache_data
def compute_cohort(df):
    s = df[df["Order Status"] == "Successful"].copy()
    s["wk_num"] = ((s["order_dt"] - s["cohort_week"]).dt.days // 7).clip(lower=0)
    sizes  = s.groupby("cohort_week")["User ID"].nunique()
    counts = s.groupby(["cohort_week", "wk_num"])["User ID"].nunique().unstack(fill_value=0)
    ret    = counts.divide(sizes, axis=0).round(3)
    return ret[sizes >= 20].iloc[:, :13]

@st.cache_data
def merchant_stats(df):
    rows = []
    for m, grp in df.groupby("Merchant"):
        sg = grp[grp["Order Status"] == "Successful"]
        rows.append({
            "Merchant":       m,
            "Orders":         len(grp),
            "Successful":     len(sg),
            "Cancel rate":    round(1 - len(sg) / len(grp), 4),
            "Avg NPS":        round(grp["NPS"].mean(), 2),
            "GMV":            round(sg["subtotal"].sum(), 2),
            "Net revenue":    round(sg["net_revenue"].sum(), 2),
            "Median delivery (min)": round(sg["delivery_minutes"].median(), 1),
            "Commission rate": sg["Commission Rate"].mode()[0] if len(sg) else 0,
        })
    return pd.DataFrame(rows).sort_values("GMV", ascending=False)

df = load_data()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📦 Marketplace Analytics")
    st.markdown("---")
    page = st.radio("", [
        "🏠  Overview",
        "📈  Growth & Retention",
        "⭐  CX Quality",
        "🏪  Merchant Performance",
        "💰  Financial Health",
    ])
    st.markdown("---")
    gran = st.selectbox("Time granularity", ["Weekly", "Daily"])
    gran_col = "week" if gran == "Weekly" else "date"

    merchants = ["All merchants"] + sorted(df["Merchant"].unique().tolist())
    sel_merchant = st.selectbox("Filter by merchant", merchants)

    st.markdown("---")
    st.caption("90-day window · Jan–Mar 2023\n15,000 orders · 4,185 users")

dff = df if sel_merchant == "All merchants" else df[df["Merchant"] == sel_merchant]
s   = dff[dff["Order Status"] == "Successful"]
weeks = sorted(dff["week"].unique())


# ══════════════════════════════════════════════════════════════════════════════
# OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
if "Overview" in page:
    st.markdown('<div class="page-title">Site Overview</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">30-second health check across all four pillars.</div>', unsafe_allow_html=True)

    total_orders   = len(dff)
    success_rate   = (dff["Order Status"] == "Successful").mean()
    total_users    = dff["User ID"].nunique()
    avg_nps        = dff["NPS"].mean()
    med_delivery   = s["delivery_minutes"].median()
    net_rev        = s["net_revenue"].sum()

    w_orders = dff.groupby("week")["Order ID"].count()
    w_nps    = s.groupby("week")["NPS"].mean()

    cols = st.columns(6)
    for col, html in zip(cols, [
        kpi("Total orders",       f"{total_orders:,}",       wow(w_orders, weeks)),
        kpi("Success rate",       f"{success_rate:.1%}",      None, color=TEAL),
        kpi("Unique users",       f"{total_users:,}",         None, color=TEAL),
        kpi("Avg NPS",            f"{avg_nps:.1f} / 10",      wow(w_nps, weeks), color=AMBER),
        kpi("Median delivery",    f"{med_delivery:.0f} min",  None, color=AMBER),
        kpi("Net revenue",        f"${net_rev:,.0f}",         None, color=CORAL),
    ]):
        col.markdown(html, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns([3, 2])
    with col1:
        section_hd("Weekly order volume")
        w = dff.groupby("week")["Order ID"].count().reset_index()
        w["week"] = w["week"].astype(str)
        fig = go.Figure(go.Scatter(
            x=w["week"], y=w["Order ID"],
            mode="lines+markers", fill="tozeroy",
            line=dict(color=PURPLE, width=2.5),
            fillcolor="rgba(108,99,255,0.08)",
            marker=dict(size=5),
        ))
        st.plotly_chart(chart_layout(fig, 260), use_container_width=True)

    with col2:
        section_hd("Order status breakdown")
        status = dff["Order Status"].value_counts()
        fig = go.Figure(go.Pie(
            labels=status.index, values=status.values,
            hole=0.55,
            marker_colors=[TEAL, CORAL, AMBER],
            textinfo="label+percent",
            textfont_size=11,
        ))
        chart_layout(fig, 260)
        st.plotly_chart(fig, use_container_width=True)

    insight("Use the sidebar to drill into each pillar. The four sections below answer: <b>Are we growing? Are customers happy? Which merchants are underperforming? Are we making money?</b>")


# ══════════════════════════════════════════════════════════════════════════════
# GROWTH & RETENTION
# ══════════════════════════════════════════════════════════════════════════════
elif "Growth" in page:
    st.markdown('<div class="page-title">Growth & Retention</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Are we acquiring and keeping customers?</div>', unsafe_allow_html=True)

    total_users     = s["User ID"].nunique()
    new_users       = s[s["is_new_user"]]["User ID"].nunique()
    returning_users = total_users - new_users
    repeat_rate     = (s.groupby("User ID")["Order ID"].count() > 1).mean()
    avg_orders      = s.groupby("User ID")["Order ID"].count().mean()

    w_new = s[s["is_new_user"]].groupby("week")["User ID"].nunique()

    cols = st.columns(5)
    for col, html in zip(cols, [
        kpi("Total users",      f"{total_users:,}"),
        kpi("New users",        f"{new_users:,}",         wow(w_new, weeks), color=TEAL),
        kpi("Returning users",  f"{returning_users:,}",   None, color=TEAL),
        kpi("Repeat rate",      f"{repeat_rate:.1%}",     None, color=AMBER),
        kpi("Avg orders/user",  f"{avg_orders:.1f}×",     None, color=AMBER),
    ]):
        col.markdown(html, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Row 1
    col1, col2 = st.columns([3, 2])
    with col1:
        section_hd("New vs returning users over time")
        g = (
            s.groupby([gran_col, "is_new_user"])["User ID"]
            .nunique().unstack(fill_value=0)
            .rename(columns={True: "New", False: "Returning"})
            .reset_index()
        )
        g.columns.name = None
        g[gran_col] = g[gran_col].astype(str)
        fig = go.Figure()
        fig.add_bar(x=g[gran_col], y=g.get("Returning", 0), name="Returning", marker_color=PURPLE)
        fig.add_bar(x=g[gran_col], y=g.get("New", 0),       name="New",       marker_color=TEAL)
        chart_layout(fig, 280, legend=True)
        fig.update_layout(barmode="stack")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        section_hd("Order frequency distribution")
        oc = s.groupby("User ID")["Order ID"].count()
        buckets = pd.cut(
            oc, bins=[0,1,2,3,5,100],
            labels=["1 order","2 orders","3 orders","4–5 orders","6+ orders"]
        ).value_counts().sort_index()
        fig = go.Figure(go.Bar(
            y=buckets.index.astype(str), x=buckets.values,
            orientation="h",
            marker_color=[TEAL, PURPLE, PURPLE, AMBER, CORAL],
            text=[f"{v:,}" for v in buckets.values],
            textposition="outside",
        ))
        chart_layout(fig, 280, ygrid=False)
        fig.update_xaxes(visible=False)
        st.plotly_chart(fig, use_container_width=True)

    # Row 2: Cohort retention heatmap
    section_hd("Weekly cohort retention — % of cohort re-ordering each week after acquisition")
    retention = compute_cohort(dff)
    cohort_labels = [str(c.date()) for c in retention.index]
    week_labels   = [f"Wk {int(c)}" for c in retention.columns]
    z = retention.values * 100

    fig = go.Figure(go.Heatmap(
        z=z, x=week_labels, y=cohort_labels,
        colorscale=[[0,"#f1f5f9"],[0.1,"#c7d2fe"],[0.25,"#818cf8"],[0.5,PURPLE],[1,"#3730a3"]],
        zmin=0, zmax=50,
        text=[[f"{v:.0f}%" if v > 0 else "" for v in row] for row in z],
        texttemplate="%{text}",
        textfont=dict(size=10, color="white"),
        hovertemplate="Cohort: %{y}<br>%{x}: %{z:.1f}%<extra></extra>",
    ))
    chart_layout(fig, 400)
    fig.update_layout(yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig, use_container_width=True)

    # Row 3
    col1, col2 = st.columns([2, 3])
    with col1:
        section_hd("Days between repeat orders")
        ss = s.sort_values(["User ID","order_dt"])
        ss["prev"] = ss.groupby("User ID")["order_dt"].shift(1)
        ss["gap"]  = (ss["order_dt"] - ss["prev"]).dt.days
        gaps = ss["gap"].dropna()
        med  = gaps.median()
        fig  = go.Figure(go.Histogram(x=gaps.clip(upper=60), nbinsx=30, marker_color=PURPLE, opacity=0.85))
        fig.add_vline(x=med, line_dash="dash", line_color=AMBER,
            annotation_text=f"Median: {med:.0f}d", annotation_position="top right")
        chart_layout(fig, 260)
        fig.update_xaxes(title_text="Days (capped 60)")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        section_hd("Cumulative user growth")
        first_orders = s.groupby("User ID")["order_dt"].min().reset_index()
        first_orders["week"] = first_orders["order_dt"].dt.to_period("W").apply(lambda x: x.start_time)
        cumul = first_orders.groupby("week").size().sort_index().cumsum().reset_index()
        cumul.columns = ["week","users"]
        cumul["week"] = cumul["week"].astype(str)
        fig = go.Figure(go.Scatter(
            x=cumul["week"], y=cumul["users"],
            mode="lines+markers", fill="tozeroy",
            line=dict(color=TEAL, width=2.5), marker=dict(size=5),
            fillcolor="rgba(20,184,166,0.1)",
        ))
        chart_layout(fig, 260)
        fig.update_yaxes(title_text="Cumulative users")
        st.plotly_chart(fig, use_container_width=True)

    # Insights
    w4_ret = float(retention.iloc[:, 4].dropna().mean()) * 100 if retention.shape[1] > 4 else 0
    insight(
        f"<b>Repeat rate is {repeat_rate:.1%}</b> — strong for a 90-day window. "
        f"Median reorder gap is <b>{med:.0f} days</b> (~{round(med/7)} weeks). "
        f"Week-4 cohort retention averages <b>{w4_ret:.1f}%</b>, meaning 4 in 5 users don't return after month 1. "
        f"This is the single most actionable lever for the CCO."
    )


# ══════════════════════════════════════════════════════════════════════════════
# CX QUALITY
# ══════════════════════════════════════════════════════════════════════════════
elif "CX" in page:
    st.markdown('<div class="page-title">CX Quality</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Is the delivery experience meeting customer expectations?</div>', unsafe_allow_html=True)

    cancel_rate   = (dff["Order Status"] != "Successful").mean()
    avg_nps       = dff["NPS"].mean()
    med_delivery  = s["delivery_minutes"].median()
    p90_delivery  = s["delivery_minutes"].quantile(0.9)
    multi_attempt = (dff["Delivery Attempts"] > 1).mean()

    w_cancel = dff.groupby("week").apply(lambda x: (x["Order Status"] != "Successful").mean())
    w_nps    = s.groupby("week")["NPS"].mean()

    cols = st.columns(5)
    for col, html in zip(cols, [
        kpi("Avg NPS",              f"{avg_nps:.1f} / 10",   wow(w_nps, weeks), color=TEAL),
        kpi("Cancellation rate",    f"{cancel_rate:.1%}",     wow(w_cancel, weeks), delta_good=False, color=CORAL),
        kpi("Median delivery",      f"{med_delivery:.0f} min", None, color=AMBER),
        kpi("P90 delivery",         f"{p90_delivery:.0f} min", None, color=AMBER),
        kpi("Multi-attempt rate",   f"{multi_attempt:.1%}",   None, color=CORAL),
    ]):
        col.markdown(html, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Row 1
    col1, col2 = st.columns(2)
    with col1:
        section_hd("NPS distribution")
        nps_counts = dff["nps_category"].value_counts().reindex(
            ["Detractor (1–4)", "Passive (5–6)", "Promoter (7–10)"]
        ).fillna(0)
        pct = nps_counts / nps_counts.sum() * 100
        fig = go.Figure(go.Bar(
            x=nps_counts.index, y=nps_counts.values,
            marker_color=[CORAL, AMBER, TEAL],
            text=[f"{v:.0f}%" for v in pct],
            textposition="outside",
        ))
        chart_layout(fig, 260, ygrid=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        section_hd("Cancellation reasons")
        reasons = dff[dff["Order Status"] != "Successful"]["Cancellation reason"].value_counts()
        fig = go.Figure(go.Bar(
            y=reasons.index, x=reasons.values,
            orientation="h",
            marker_color=CORAL,
            text=[f"{v:,} ({v/reasons.sum():.0%})" for v in reasons.values],
            textposition="outside",
        ))
        chart_layout(fig, 260, ygrid=False)
        fig.update_xaxes(visible=False)
        st.plotly_chart(fig, use_container_width=True)

    # Row 2
    col1, col2 = st.columns(2)
    with col1:
        section_hd("Delivery time distribution (successful orders)")
        fig = go.Figure(go.Histogram(
            x=s["delivery_minutes"].clip(upper=90), nbinsx=45,
            marker_color=PURPLE, opacity=0.85,
        ))
        fig.add_vline(x=med_delivery, line_dash="dash", line_color=AMBER,
            annotation_text=f"Median: {med_delivery:.0f}m", annotation_position="top right")
        fig.add_vline(x=p90_delivery, line_dash="dot", line_color=CORAL,
            annotation_text=f"P90: {p90_delivery:.0f}m", annotation_position="top left")
        chart_layout(fig, 280)
        fig.update_xaxes(title_text="Minutes (capped at 90)")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        section_hd("NPS trend over time")
        nps_trend = s.groupby(gran_col)["NPS"].mean().reset_index()
        nps_trend[gran_col] = nps_trend[gran_col].astype(str)
        fig = go.Figure(go.Scatter(
            x=nps_trend[gran_col], y=nps_trend["NPS"],
            mode="lines+markers",
            line=dict(color=TEAL, width=2.5), marker=dict(size=6),
        ))
        fig.add_hrule(y=7, line_dash="dash", line_color=AMBER,
            annotation_text="Promoter threshold (7)", annotation_position="bottom right")
        chart_layout(fig, 280)
        fig.update_yaxes(range=[5, 10])
        st.plotly_chart(fig, use_container_width=True)

    # Row 3: NPS by merchant (flag outliers)
    section_hd("NPS by merchant — flagging underperformers")
    ms = merchant_stats(df).sort_values("Avg NPS")
    colors = [CORAL if v < 7 else TEAL for v in ms["Avg NPS"]]
    fig = go.Figure(go.Bar(
        y=ms["Merchant"], x=ms["Avg NPS"],
        orientation="h",
        marker_color=colors,
        text=[f"{v:.1f}" for v in ms["Avg NPS"]],
        textposition="outside",
    ))
    fig.add_vline(x=7, line_dash="dash", line_color=AMBER, annotation_text="Promoter threshold")
    chart_layout(fig, 380, ygrid=False)
    fig.update_xaxes(range=[0, 11])
    st.plotly_chart(fig, use_container_width=True)

    low_nps = ms[ms["Avg NPS"] < 7]["Merchant"].tolist()
    insight(
        f"<b>{len(low_nps)} merchants below the promoter threshold (NPS &lt; 7):</b> "
        + ", ".join(f"<b>{m}</b>" for m in low_nps)
        + ". These accounts share a pattern of longer delivery times (24–25 min vs. site median 18 min). "
        "Investigate whether this is a geography/distance issue or a fulfillment reliability issue.",
        warn=True
    )


# ══════════════════════════════════════════════════════════════════════════════
# MERCHANT PERFORMANCE
# ══════════════════════════════════════════════════════════════════════════════
elif "Merchant" in page:
    st.markdown('<div class="page-title">Merchant Performance</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Who are our best and worst merchant partners?</div>', unsafe_allow_html=True)

    ms = merchant_stats(df)
    total_merchants   = len(ms)
    avg_cancel        = ms["Cancel rate"].mean()
    top_merchant      = ms.iloc[0]["Merchant"]
    flagged           = ms[ms["Cancel rate"] > ms["Cancel rate"].quantile(0.75)]

    cols = st.columns(4)
    for col, html in zip(cols, [
        kpi("Active merchants",       f"{total_merchants}"),
        kpi("Avg cancel rate",        f"{avg_cancel:.1%}",   None, color=CORAL),
        kpi("Top merchant by GMV",    top_merchant,           None, color=TEAL),
        kpi("High cancel merchants",  f"{len(flagged)}",     None, color=AMBER),
    ]):
        col.markdown(html, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Row 1
    col1, col2 = st.columns(2)
    with col1:
        section_hd("GMV by merchant")
        fig = go.Figure(go.Bar(
            x=ms["Merchant"], y=ms["GMV"],
            marker_color=PURPLE,
            text=[f"${v/1000:.0f}k" for v in ms["GMV"]],
            textposition="outside",
        ))
        chart_layout(fig, 300, ygrid=False)
        fig.update_xaxes(tickangle=-35)
        fig.update_yaxes(visible=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        section_hd("Cancel rate vs. avg NPS — bubble = order volume")
        fig = go.Figure(go.Scatter(
            x=ms["Cancel rate"] * 100,
            y=ms["Avg NPS"],
            mode="markers+text",
            text=ms["Merchant"],
            textposition="top center",
            textfont=dict(size=9),
            marker=dict(
                size=ms["Orders"] / ms["Orders"].max() * 50 + 8,
                color=ms["Avg NPS"],
                colorscale=[[0, CORAL],[0.5, AMBER],[1, TEAL]],
                showscale=False,
                line=dict(color="white", width=1),
            ),
            hovertemplate="<b>%{text}</b><br>Cancel rate: %{x:.1f}%<br>Avg NPS: %{y:.1f}<extra></extra>",
        ))
        chart_layout(fig, 300)
        fig.update_xaxes(title_text="Cancellation rate (%)")
        fig.update_yaxes(title_text="Avg NPS", range=[4, 10])
        st.plotly_chart(fig, use_container_width=True)

    # Row 2
    col1, col2 = st.columns(2)
    with col1:
        section_hd("Median delivery time by merchant")
        ms_sorted = ms.sort_values("Median delivery (min)")
        colors = [CORAL if v > 20 else TEAL for v in ms_sorted["Median delivery (min)"]]
        fig = go.Figure(go.Bar(
            y=ms_sorted["Merchant"], x=ms_sorted["Median delivery (min)"],
            orientation="h", marker_color=colors,
            text=[f"{v:.0f}m" for v in ms_sorted["Median delivery (min)"]],
            textposition="outside",
        ))
        site_median = s["delivery_minutes"].median()
        fig.add_vline(x=site_median, line_dash="dash", line_color=AMBER,
            annotation_text=f"Site median ({site_median:.0f}m)")
        chart_layout(fig, 380, ygrid=False)
        fig.update_xaxes(visible=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        section_hd("Cancellation rate by merchant")
        ms_cr = ms.sort_values("Cancel rate")
        site_cancel = (dff["Order Status"] != "Successful").mean()
        colors = [CORAL if v > site_cancel * 1.3 else TEAL for v in ms_cr["Cancel rate"]]
        fig = go.Figure(go.Bar(
            y=ms_cr["Merchant"], x=ms_cr["Cancel rate"] * 100,
            orientation="h", marker_color=colors,
            text=[f"{v:.1f}%" for v in ms_cr["Cancel rate"] * 100],
            textposition="outside",
        ))
        fig.add_vline(x=site_cancel * 100, line_dash="dash", line_color=AMBER,
            annotation_text=f"Site avg ({site_cancel:.1%})")
        chart_layout(fig, 380, ygrid=False)
        fig.update_xaxes(visible=False)
        st.plotly_chart(fig, use_container_width=True)

    # Scorecard
    section_hd("Full merchant scorecard")
    display = ms.copy()
    display["Cancel rate"] = display["Cancel rate"].map("{:.1%}".format)
    display["Avg NPS"]     = display["Avg NPS"].map("{:.1f}".format)
    display["GMV"]         = display["GMV"].map("${:,.0f}".format)
    display["Net revenue"] = display["Net revenue"].map("${:,.0f}".format)
    display["Median delivery (min)"] = display["Median delivery (min)"].map("{:.0f} min".format)
    display["Commission rate"] = display["Commission rate"].map("{:.0%}".format)
    st.dataframe(
        display[["Merchant","Orders","Cancel rate","Avg NPS","GMV","Net revenue","Median delivery (min)","Commission rate"]],
        use_container_width=True, hide_index=True,
    )

    slow    = ms[ms["Median delivery (min)"] > 20]["Merchant"].tolist()
    high_cr = ms[ms["Cancel rate"] > site_cancel * 1.3]["Merchant"].tolist()
    if slow or high_cr:
        insight(
            f"<b>Delivery outliers (&gt;20 min):</b> {', '.join(slow) or 'none'}. "
            f"<b>High cancel rate (&gt;30% above site avg):</b> {', '.join(high_cr) or 'none'}. "
            "These merchants warrant an SLA conversation before the next QBR.",
            warn=True
        )


# ══════════════════════════════════════════════════════════════════════════════
# FINANCIAL HEALTH
# ══════════════════════════════════════════════════════════════════════════════
elif "Financial" in page:
    st.markdown('<div class="page-title">Financial Health</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Are we making money — and how efficiently?</div>', unsafe_allow_html=True)

    total_gmv     = s["subtotal"].sum()
    total_net     = s["net_revenue"].sum()
    total_promo   = s["promotion"].sum()
    total_fees    = s["fees"].sum()
    net_margin    = total_net / total_gmv
    avg_order_val = s["subtotal"].mean()

    w_gmv = s.groupby("week")["subtotal"].sum()
    w_net = s.groupby("week")["net_revenue"].sum()

    cols = st.columns(5)
    for col, html in zip(cols, [
        kpi("Total GMV",         f"${total_gmv:,.0f}",      wow(w_gmv, weeks), color=PURPLE),
        kpi("Net revenue",       f"${total_net:,.0f}",       wow(w_net, weeks), color=TEAL),
        kpi("Take rate",         f"{net_margin:.1%}",        None, color=TEAL),
        kpi("Promo spend",       f"${total_promo:,.0f}",     None, delta_good=False, color=AMBER),
        kpi("Avg order value",   f"${avg_order_val:.2f}",    None, color=PURPLE),
    ]):
        col.markdown(html, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Row 1
    col1, col2 = st.columns(2)
    with col1:
        section_hd("Weekly GMV & net revenue")
        weekly = s.groupby("week").agg(gmv=("subtotal","sum"), net=("net_revenue","sum")).reset_index()
        weekly["week"] = weekly["week"].astype(str)
        fig = go.Figure()
        fig.add_bar(x=weekly["week"], y=weekly["gmv"], name="GMV",
            marker_color=PURPLE, opacity=0.5)
        fig.add_scatter(x=weekly["week"], y=weekly["net"], mode="lines+markers",
            name="Net revenue", line=dict(color=TEAL, width=2.5), marker=dict(size=6))
        chart_layout(fig, 300, legend=True)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        section_hd("Net revenue vs. promo cost — weekly waterfall")
        weekly_p = s.groupby("week").agg(net=("net_revenue","sum"), promo=("promotion","sum")).reset_index()
        weekly_p["week"] = weekly_p["week"].astype(str)
        fig = go.Figure()
        fig.add_bar(x=weekly_p["week"], y=weekly_p["net"],
            name="Net revenue", marker_color=TEAL)
        fig.add_bar(x=weekly_p["week"], y=-weekly_p["promo"],
            name="Promo spend", marker_color=CORAL)
        chart_layout(fig, 300, legend=True)
        fig.update_layout(barmode="relative")
        st.plotly_chart(fig, use_container_width=True)

    # Row 2
    col1, col2 = st.columns(2)
    with col1:
        section_hd("Revenue by commission tier")
        tiers = s.groupby("Commission Rate").agg(
            orders=("Order ID","count"),
            gmv=("subtotal","sum"),
            net=("net_revenue","sum"),
        ).reset_index()
        tiers["label"] = tiers["Commission Rate"].map(lambda x: f"{x:.0%} tier")
        fig = go.Figure()
        fig.add_bar(x=tiers["label"], y=tiers["gmv"], name="GMV", marker_color=PURPLE, opacity=0.6)
        fig.add_bar(x=tiers["label"], y=tiers["net"], name="Net revenue", marker_color=TEAL)
        chart_layout(fig, 280, legend=True)
        fig.update_layout(barmode="group")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        section_hd("Order value distribution")
        fig = go.Figure(go.Histogram(
            x=s["subtotal"].clip(upper=90), nbinsx=40,
            marker_color=PURPLE, opacity=0.85,
        ))
        fig.add_vline(x=avg_order_val, line_dash="dash", line_color=AMBER,
            annotation_text=f"Mean: ${avg_order_val:.2f}", annotation_position="top right")
        chart_layout(fig, 280)
        fig.update_xaxes(title_text="Order subtotal ($)")
        st.plotly_chart(fig, use_container_width=True)

    # Row 3: GMV by merchant
    section_hd("Net revenue contribution by merchant")
    ms = merchant_stats(df).sort_values("Net revenue", ascending=True)
    ms["cum_pct"] = ms["Net revenue"].cumsum() / ms["Net revenue"].sum() * 100
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_bar(y=ms["Merchant"], x=ms["Net revenue"],
        orientation="h", marker_color=PURPLE,
        text=[f"${v:,.0f}" for v in ms["Net revenue"]],
        textposition="outside", name="Net revenue", secondary_y=False)
    chart_layout(fig, 400, ygrid=False)
    fig.update_xaxes(visible=False)
    st.plotly_chart(fig, use_container_width=True)

    promo_ratio = total_promo / total_net
    insight(
        f"Promo spend is <b>${total_promo:,.0f}</b> against net revenue of <b>${total_net:,.0f}</b> — "
        f"promotions cost <b>{promo_ratio:.1%} of net revenue</b>. "
        f"The 17% commission tier generates the most GMV (${s[s['Commission Rate']==0.17]['subtotal'].sum():,.0f}) "
        f"but the 20% tier has the best net margin. "
        f"Fees collected (${total_fees:,.0f}) exceed net commission revenue — worth flagging in the Finance review."
    )
