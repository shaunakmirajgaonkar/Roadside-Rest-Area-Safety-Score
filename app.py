import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from datetime import datetime

st.set_page_config(page_title="Roadside Rest-Area Safety Score", page_icon="🛣️", layout="wide")

# -----------------------------
# Theme / visual system
# -----------------------------
st.markdown("""
<style>
:root { --ink:#17324d; --muted:#58718a; --line:#dbe7f0; --panel:#ffffff; --bg:#f4f8fb; }
.stApp { background:linear-gradient(135deg,#f4f8fb 0%,#eef7f5 52%,#f8f4fb 100%); color:var(--ink); }
.block-container { max-width:1450px; padding-top:1.2rem; }
h1,h2,h3,h4 { color:#17324d !important; }
.hero { background:linear-gradient(110deg,#17324d,#286b7d 55%,#5d4c8d); padding:28px 32px; border-radius:24px; color:white; box-shadow:0 14px 35px rgba(23,50,77,.16); }
.hero h1,.hero p { color:white !important; }
.card { background:rgba(255,255,255,.94); border:1px solid var(--line); border-radius:18px; padding:18px 20px; box-shadow:0 8px 24px rgba(35,65,90,.07); }
.kpi { font-size:29px; font-weight:800; color:#17324d; }
.kpi-label { font-size:13px; color:#58718a; }
.badge { display:inline-block; padding:6px 11px; border-radius:999px; font-weight:700; font-size:12px; }
.small { color:#58718a; font-size:13px; }
div[data-testid="stMetric"] { background:#fff; border:1px solid #dbe7f0; padding:12px; border-radius:15px; }
</style>
""", unsafe_allow_html=True)

BASE = Path(__file__).parent
DATA = BASE / "data"
ASSETS = BASE / "assets"

DEFAULT_SCORE_WEIGHTS = {
    "Lighting": 0.18, "Sanitation": 0.15, "Accessibility": 0.15,
    "Crowding": 0.12, "Emergency Support": 0.20,
    "User Report Verification": 0.20
}

def classify(score):
    if score >= 80: return "Excellent"
    if score >= 65: return "Good"
    if score >= 50: return "Watch"
    return "Priority Review"

def risk_from_score(score):
    if score >= 80: return "Low"
    if score >= 65: return "Moderate"
    if score >= 50: return "High"
    return "Critical"

def load_csv(uploaded, fallback):
    if uploaded is not None:
        return pd.read_csv(uploaded)
    return pd.read_csv(DATA / fallback)

def normalize_report_score(x):
    # verified report quality: higher means stronger confidence in the available user-report signal
    return np.clip(pd.to_numeric(x, errors="coerce").fillna(50), 0, 100)

def prepare(rests):
    d = rests.copy()
    numeric = ["lighting_score","sanitation_score","accessibility_score","crowding_score",
               "emergency_support_score","verified_report_score","night_traffic_index",
               "occupancy_index","inspection_age_days","incident_count_12m","response_time_min",
               "cleaning_frequency_weekly"]
    for c in numeric:
        d[c] = pd.to_numeric(d[c], errors="coerce").fillna(0)
    # Crowding score is already normalized: 100 = favorable capacity/crowding conditions.
    d["safety_score"] = (
        d["lighting_score"]*DEFAULT_SCORE_WEIGHTS["Lighting"] +
        d["sanitation_score"]*DEFAULT_SCORE_WEIGHTS["Sanitation"] +
        d["accessibility_score"]*DEFAULT_SCORE_WEIGHTS["Accessibility"] +
        d["crowding_score"]*DEFAULT_SCORE_WEIGHTS["Crowding"] +
        d["emergency_support_score"]*DEFAULT_SCORE_WEIGHTS["Emergency Support"] +
        normalize_report_score(d["verified_report_score"])*DEFAULT_SCORE_WEIGHTS["User Report Verification"]
    ).round(1)
    d["classification"] = d["safety_score"].map(classify)
    d["risk_level"] = d["safety_score"].map(risk_from_score)
    d["priority_gap"] = (80-d["safety_score"]).clip(lower=0).round(1)
    d["review_flag"] = np.where(
        (d["incident_count_12m"] >= 3) | (d["inspection_age_days"] > 120) | (d["safety_score"] < 50),
        "Review", "Routine"
    )
    d["top_gap"] = d[["lighting_score","sanitation_score","accessibility_score","crowding_score","emergency_support_score","verified_report_score"]].idxmin(axis=1)
    return d

def load_all(device_upload=None, reports_upload=None, inspections_upload=None):
    rests = load_csv(device_upload, "sample_rest_areas.csv")
    reports = load_csv(reports_upload, "sample_user_reports.csv")
    inspections = load_csv(inspections_upload, "sample_inspections.csv")
    return prepare(rests), reports, inspections

rests, reports, inspections = load_all()

# -----------------------------
# Header
# -----------------------------
st.markdown("""
<div class="hero">
  <div style="font-size:13px;letter-spacing:.12em;text-transform:uppercase;opacity:.82;">LOCAL-FIRST HIGHWAY SAFETY INTELLIGENCE</div>
  <h1>🛣️ Roadside Rest-Area Safety Score</h1>
  <p style="font-size:16px;margin-bottom:0;">A transparent command center for screening lighting, sanitation, accessibility, crowding, emergency support and verified user-report signals.</p>
</div>
""", unsafe_allow_html=True)

st.write("")
with st.sidebar:
    st.markdown("### ⚙️ Data workspace")
    up1 = st.file_uploader("Rest-area records", type=["csv"], key="rests")
    up2 = st.file_uploader("Verified user reports", type=["csv"], key="reports")
    up3 = st.file_uploader("Inspection records", type=["csv"], key="inspections")
    if st.button("↻ Reset to bundled samples", use_container_width=True):
        st.rerun()

rests, reports, inspections = load_all(up1, up2, up3)

# -----------------------------
# Controls
# -----------------------------
with st.container():
    c1,c2,c3,c4,c5 = st.columns([1.2,1.2,1.2,1.1,1.4])
    with c1: zones = st.multiselect("Zone", sorted(rests["zone"].unique()), default=sorted(rests["zone"].unique()))
    with c2: types = st.multiselect("Rest-area type", sorted(rests["rest_area_type"].unique()), default=sorted(rests["rest_area_type"].unique()))
    with c3: risk = st.multiselect("Risk level", ["Low","Moderate","High","Critical"], default=["Low","Moderate","High","Critical"])
    with c4: min_score = st.slider("Minimum score", 0, 100, 0)
    with c5: search = st.text_input("🔎 Search facility", placeholder="Name, highway or code")

filtered = rests[
    rests["zone"].isin(zones) & rests["rest_area_type"].isin(types) &
    rests["risk_level"].isin(risk) & (rests["safety_score"] >= min_score)
].copy()
if search.strip():
    q = search.strip().lower()
    mask = filtered.astype(str).apply(lambda col: col.str.lower().str.contains(q, regex=False, na=False)).any(axis=1)
    filtered = filtered[mask]

# -----------------------------
# KPI ribbon
# -----------------------------
avg = filtered["safety_score"].mean() if len(filtered) else 0
priority = int((filtered["risk_level"].isin(["High","Critical"])).sum()) if len(filtered) else 0
review = int((filtered["review_flag"]=="Review").sum()) if len(filtered) else 0
reports_verified = int(reports["verification_status"].astype(str).str.lower().eq("verified").sum()) if len(reports) else 0

a,b,c,d,e = st.columns(5)
a.metric("Safety score", f"{avg:.1f}/100")
b.metric("Facilities screened", f"{len(filtered)}")
c.metric("High / Critical", f"{priority}")
d.metric("Review queue", f"{review}")
e.metric("Verified reports", f"{reports_verified}")

tabs = st.tabs(["🎯 Command Center","🗺️ Safety Matrix","🧭 Facility Explorer","🧾 Evidence & Reports","🧪 Scenario Lab","📤 Data Export"])

# -----------------------------
# Command center
# -----------------------------
with tabs[0]:
    left,right = st.columns([1.35,1])
    with left:
        st.subheader("Safety distribution")
        dist = filtered["risk_level"].value_counts().reindex(["Low","Moderate","High","Critical"], fill_value=0).reset_index()
        dist.columns=["Risk level","Facilities"]
        fig = px.bar(dist, x="Risk level", y="Facilities", text="Facilities",
                     color="Risk level", color_discrete_sequence=px.colors.qualitative.Set2)
        fig.update_layout(template="plotly_white", height=360, margin=dict(l=10,r=10,t=20,b=10))
        st.plotly_chart(fig, use_container_width=True)
    with right:
        st.subheader("Priority queue")
        q = filtered.sort_values(["safety_score","incident_count_12m"], ascending=[True,False]).head(8)
        show = q[["rest_area_name","highway","zone","safety_score","risk_level","top_gap","review_flag"]].copy()
        show.columns=["Facility","Highway","Zone","Score","Risk","Top gap","Action"]
        st.dataframe(show, use_container_width=True, hide_index=True, height=360)

    st.subheader("Six-pillar safety profile")
    pillars = ["lighting_score","sanitation_score","accessibility_score","crowding_score","emergency_support_score","verified_report_score"]
    p = filtered[pillars].mean().reset_index()
    p.columns=["Pillar","Score"]
    names = {"lighting_score":"Lighting","sanitation_score":"Sanitation","accessibility_score":"Accessibility",
             "crowding_score":"Crowding","emergency_support_score":"Emergency Support","verified_report_score":"Verified Reports"}
    p["Pillar"] = p["Pillar"].map(names)
    fig = px.line_polar(p, r="Score", theta="Pillar", line_close=True, markers=True)
    fig.update_traces(fill="toself")
    fig.update_layout(template="plotly_white", height=430, polar=dict(radialaxis=dict(range=[0,100])))
    st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# Matrix
# -----------------------------
with tabs[1]:
    st.subheader("Safety matrix")
    xcol = st.selectbox("Horizontal axis", ["lighting_score","sanitation_score","accessibility_score","crowding_score","emergency_support_score","verified_report_score"], format_func=lambda x:x.replace("_score","").replace("_"," ").title())
    ycol = st.selectbox("Vertical axis", ["safety_score","night_traffic_index","occupancy_index","incident_count_12m"], format_func=lambda x:x.replace("_"," ").title())
    fig = px.scatter(filtered, x=xcol, y=ycol, size="daily_visitors_estimate",
                     color="risk_level", hover_name="rest_area_name",
                     hover_data=["highway","zone","safety_score","top_gap"],
                     color_discrete_sequence=px.colors.qualitative.Safe)
    fig.update_layout(template="plotly_white", height=520, margin=dict(l=10,r=10,t=20,b=10))
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Zone benchmark")
    zb = filtered.groupby("zone").agg(
        facilities=("rest_area_id","count"), avg_score=("safety_score","mean"),
        incidents=("incident_count_12m","sum"), visitors=("daily_visitors_estimate","sum")
    ).reset_index().sort_values("avg_score")
    fig = px.bar(zb, x="zone", y="avg_score", text="avg_score", color="avg_score",
                 color_continuous_scale="Teal")
    fig.update_layout(template="plotly_white", height=360)
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(zb.round(1), use_container_width=True, hide_index=True)

# -----------------------------
# Explorer
# -----------------------------
with tabs[2]:
    st.subheader("Facility explorer")
    if len(filtered):
        selected = st.selectbox("Select a facility", filtered["rest_area_name"].tolist())
        row = filtered[filtered["rest_area_name"]==selected].iloc[0]
        x1,x2,x3 = st.columns(3)
        x1.metric("Safety score", f"{row.safety_score:.1f}")
        x2.metric("Risk", row.risk_level)
        x3.metric("Top gap", str(row.top_gap).replace("_score","").replace("_"," ").title())

        st.markdown(f"""
        <div class="card">
        <b>{row.rest_area_name}</b><br>
        <span class="small">{row.highway} · {row.direction} · {row.zone} · {row.rest_area_type}</span>
        <hr>
        <span class="small">Visitors/day</span> <b>{int(row.daily_visitors_estimate):,}</b> &nbsp;&nbsp;
        <span class="small">Incidents/12m</span> <b>{int(row.incident_count_12m)}</b> &nbsp;&nbsp;
        <span class="small">Response</span> <b>{row.response_time_min:.0f} min</b>
        </div>
        """, unsafe_allow_html=True)

        radar = pd.DataFrame({"pillar":["Lighting","Sanitation","Accessibility","Crowding","Emergency Support","Verified Reports"],
                             "score":[row.lighting_score,row.sanitation_score,row.accessibility_score,row.crowding_score,row.emergency_support_score,row.verified_report_score]})
        fig = px.bar(radar, x="pillar", y="score", text="score", color="score", color_continuous_scale="Viridis")
        fig.update_yaxes(range=[0,100])
        fig.update_layout(template="plotly_white", height=380, margin=dict(l=10,r=10,t=20,b=10))
        st.plotly_chart(fig, use_container_width=True)

        recs=[]
        if row.lighting_score < 65: recs.append("Review lighting coverage and nighttime illumination consistency.")
        if row.sanitation_score < 65: recs.append("Review sanitation service frequency and cleanliness observations.")
        if row.accessibility_score < 65: recs.append("Inspect accessible routes, parking and restroom usability.")
        if row.crowding_score < 65: recs.append("Assess peak crowding, circulation and capacity pressure.")
        if row.emergency_support_score < 65: recs.append("Review emergency call points, response readiness and signage.")
        if row.verified_report_score < 65: recs.append("Increase verified feedback coverage before drawing strong conclusions.")
        if row.incident_count_12m >= 3: recs.append("Review incident history with the responsible road-safety team.")
        st.subheader("Recommended review actions")
        for r in recs or ["Maintain routine inspection cadence; no major pillar gap detected."]:
            st.info(r)
    else:
        st.warning("No facilities match the current filters.")

# -----------------------------
# Evidence
# -----------------------------
with tabs[3]:
    st.subheader("Verified user-report intelligence")
    if len(reports):
        rc1,rc2,rc3 = st.columns(3)
        rc1.metric("Total reports", len(reports))
        rc2.metric("Verified", int(reports["verification_status"].astype(str).str.lower().eq("verified").sum()))
        rc3.metric("Avg confidence", f"{pd.to_numeric(reports['verification_confidence_pct'], errors='coerce').mean():.1f}%")
        trend = reports.copy()
        trend["report_date"] = pd.to_datetime(trend["report_date"], errors="coerce")
        trend["month"] = trend["report_date"].dt.to_period("M").astype(str)
        tr = trend.groupby("month").size().reset_index(name="reports")
        fig = px.area(tr, x="month", y="reports", markers=True)
        fig.update_layout(template="plotly_white", height=320)
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(reports, use_container_width=True, hide_index=True)
    st.subheader("Inspection freshness")
    ins = inspections.copy()
    ins["inspection_date"] = pd.to_datetime(ins["inspection_date"], errors="coerce")
    st.dataframe(ins.sort_values("inspection_date", ascending=False), use_container_width=True, hide_index=True)

# -----------------------------
# Scenario
# -----------------------------
with tabs[4]:
    st.subheader("🧪 Scenario lab")
    st.caption("Transparent what-if analysis. Scenario outputs are screening estimates, not engineering predictions.")
    if len(filtered):
        selected = st.selectbox("Facility", filtered["rest_area_name"].tolist(), key="scenario_facility")
        row = filtered[filtered["rest_area_name"]==selected].iloc[0]
        s1,s2,s3 = st.columns(3)
        light_gain = s1.slider("Lighting improvement", 0, 30, 10)
        emergency_gain = s2.slider("Emergency support improvement", 0, 30, 10)
        sanitation_gain = s3.slider("Sanitation improvement", 0, 30, 10)
        before = row.safety_score
        after = (
            min(100,row.lighting_score+light_gain)*.18 +
            min(100,row.sanitation_score+sanitation_gain)*.15 +
            row.accessibility_score*.15 + row.crowding_score*.12 +
            min(100,row.emergency_support_score+emergency_gain)*.20 +
            row.verified_report_score*.20
        )
        m1,m2,m3 = st.columns(3)
        m1.metric("Current score", f"{before:.1f}")
        m2.metric("Scenario score", f"{after:.1f}", f"{after-before:+.1f}")
        m3.metric("Scenario class", classify(after))
        scen = pd.DataFrame({"State":["Current","Scenario"],"Score":[before,after]})
        fig = px.bar(scen, x="State", y="Score", text="Score", range_y=[0,100])
        fig.update_layout(template="plotly_white", height=340)
        st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# Export
# -----------------------------
with tabs[5]:
    st.subheader("📤 Local data export")
    export_cols = ["rest_area_id","rest_area_name","highway","direction","zone","rest_area_type","safety_score","risk_level","classification","top_gap","review_flag"]
    csv = filtered[export_cols].to_csv(index=False).encode("utf-8")
    st.download_button("Download filtered safety screening CSV", csv, "rest_area_safety_screening.csv", "text/csv")
    st.dataframe(filtered[export_cols], use_container_width=True, hide_index=True)

st.divider()
st.caption("LOCAL-FIRST • CSV + Pandas + NumPy + Plotly • No external APIs required • Screening and decision-support only.")
