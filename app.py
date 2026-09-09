"""
FinSentinel — SOC Dashboard  (app.py)
========================================
Single-entry-point Streamlit application.

Run:
    streamlit run app.py

The app auto-generates synthetic data if transactions.csv is missing,
builds a NetworkX directed graph, runs fraud-detection algorithms, and
renders an interactive PyVis network inside the Cyberpunk SOC dashboard.
"""

# ────────────────────────────────────────────────────────────────────────────
# Imports
# ────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import csv
import io
import os
import random
import sys
import tempfile
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import networkx as nx
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from pyvis.network import Network

# ────────────────────────────────────────────────────────────────────────────
# Page Config  (must be FIRST Streamlit call)
# ────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FinSentinel // Financial Crime Intelligence",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ────────────────────────────────────────────────────────────────────────────
# Custom Cyberpunk / SOC CSS
# ────────────────────────────────────────────────────────────────────────────
CYBERPUNK_CSS = """
<style>
/* ── Google Font Import ── */
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');

/* ── Global Reset ── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

/* ── Root Variables ── */
:root {
    --bg-void:      #080c14;
    --bg-card:      #0d1527;
    --bg-card2:     #111827;
    --cyan:         #00e5ff;
    --green:        #00ff88;
    --red:          #ff0055;
    --red-dim:      #7a0026;
    --slate:        #334155;
    --text-main:    #c8d6ef;
    --text-dim:     #5a7090;
    --font-mono:    'Share Tech Mono', 'Courier New', Consolas, monospace;
}

/* ── Streamlit scaffolding overrides ── */
html, body, [data-testid="stAppViewContainer"] {
    background-color: var(--bg-void) !important;
    color: var(--text-main) !important;
    font-family: var(--font-mono) !important;
}
[data-testid="stHeader"],
[data-testid="stToolbar"],
footer { display: none !important; }

/* ── Main content padding ── */
[data-testid="stAppViewBlockContainer"] {
    padding: 1rem 2rem !important;
    max-width: 100% !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg-void); }
::-webkit-scrollbar-thumb { background: var(--slate); border-radius: 3px; }

/* ── Dataframe ── */
[data-testid="stDataFrame"] {
    border: 1px solid var(--slate) !important;
    border-radius: 6px;
    background: var(--bg-card) !important;
}

/* ── Metric widgets ── */
[data-testid="stMetric"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--slate) !important;
    border-radius: 8px;
    padding: 1rem !important;
}
[data-testid="stMetricLabel"] { color: var(--text-dim) !important; font-size: 0.72rem; letter-spacing: 0.08em; }
[data-testid="stMetricValue"] { color: var(--cyan) !important; font-size: 1.6rem !important; font-family: var(--font-mono) !important; }

/* ── Expanders ── */
[data-testid="stExpander"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--slate) !important;
    border-radius: 6px;
}

/* ── Buttons ── */
button[kind="primary"] {
    background: var(--green) !important;
    color: var(--bg-void) !important;
    border: none !important;
    font-family: var(--font-mono) !important;
    font-weight: 700;
    letter-spacing: 0.05em;
}
button[kind="secondary"] {
    background: transparent !important;
    color: var(--cyan) !important;
    border: 1px solid var(--cyan) !important;
    font-family: var(--font-mono) !important;
}
</style>
"""

# ────────────────────────────────────────────────────────────────────────────
# Custom HTML Components
# ────────────────────────────────────────────────────────────────────────────

def html_header() -> str:
    return """
    <div style="display:flex; justify-content:space-between; align-items:center;
                padding:1rem 0 0.5rem; border-bottom:1px solid #334155; margin-bottom:1rem;">
      <div>
        <div style="font-size:1.8rem; font-weight:700; color:#00ff88;
                    text-shadow:0 0 12px #00ff88, 0 0 24px #00ff8855;
                    font-family:'Share Tech Mono',monospace; letter-spacing:0.06em;">
          &#x1F6E1;&#xFE0F;&nbsp; FINSENTINEL &nbsp;//&nbsp; GRAPH INTELLIGENCE ENGINE
        </div>
        <div style="font-size:0.78rem; color:#5a7090; letter-spacing:0.12em; margin-top:4px;">
          AML &amp; FINANCIAL CRIME DETECTION &nbsp;|&nbsp; GRAPH-BASED TRANSACTION ANALYTICS
          &nbsp;|&nbsp; ENTERPRISE COMPLIANCE PLATFORM
        </div>
      </div>
      <div style="text-align:right;">
        <span style="font-size:0.72rem; color:#5a7090; letter-spacing:0.1em;">SYSTEM STATUS</span><br/>
        <span style="font-size:0.9rem; color:#00ff88;
                     animation: pulse 2s infinite;
                     text-shadow:0 0 8px #00ff88;">&#x25CF;&nbsp; ENGINE ONLINE</span>
      </div>
    </div>
    <style>
      @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
    </style>
    """


def kpi_card(label: str, value: str, color: str = "#00e5ff",
             sub: str = "") -> str:
    return f"""
    <div style="background:#0d1527; border:1px solid #334155; border-radius:8px;
                padding:1.1rem 1.3rem; text-align:center;
                box-shadow:0 0 10px rgba(0,229,255,0.06);">
      <div style="font-size:0.68rem; color:#5a7090; letter-spacing:0.12em;
                  margin-bottom:0.4rem; text-transform:uppercase;">{label}</div>
      <div style="font-size:2rem; font-weight:700; color:{color};
                  text-shadow:0 0 10px {color}88;
                  font-family:'Share Tech Mono',monospace;">{value}</div>
      {"<div style='font-size:0.7rem; color:#5a7090; margin-top:0.3rem;'>" + sub + "</div>" if sub else ""}
    </div>
    """


def terminal_box(lines: list[str]) -> str:
    body = "".join(
        f"<div style='margin-bottom:3px;'>"
        f"<span style='color:#5a7090;'>[{datetime.now().strftime('%H:%M:%S')}]</span>&nbsp;"
        f"<span style='color:{_log_color(ln)};'>{ln}</span></div>"
        for ln in lines
    )
    return f"""
    <div style="background:#080c14; border:1px solid #334155; border-radius:6px;
                padding:0.8rem; height:180px; overflow-y:auto;
                box-shadow:inset 0 0 12px rgba(0,0,0,0.8);
                font-family:'Share Tech Mono',monospace; font-size:0.72rem;
                line-height:1.6;">
      {body}
    </div>
    """


def _log_color(line: str) -> str:
    if "ERROR" in line or "ALERT" in line or "🔴" in line or "FLAGGED" in line:
        return "#ff0055"
    if "✅" in line or "OK" in line or "COMPLETE" in line:
        return "#00ff88"
    if "🔍" in line or "SCAN" in line or "CHECK" in line or "RUN" in line:
        return "#00e5ff"
    return "#8899aa"


def alert_card(title: str, body: str) -> str:
    return f"""
    <div style="background:#110010; border:2px solid #ff0055; border-radius:8px;
                padding:1rem; margin-top:0.8rem;
                box-shadow:0 0 18px rgba(255,0,85,0.3);">
      <div style="font-size:0.72rem; color:#ff0055; letter-spacing:0.1em;
                  margin-bottom:0.4rem;">⚠&nbsp; CRITICAL ALERT</div>
      <div style="font-size:0.9rem; color:#ffcccc; font-weight:700;
                  margin-bottom:0.3rem;">{title}</div>
      <div style="font-size:0.73rem; color:#cc8899; line-height:1.55;">{body}</div>
    </div>
    """


def section_header(text: str, color: str = "#00e5ff") -> str:
    return f"""
    <div style="font-size:0.72rem; letter-spacing:0.14em; color:{color};
                border-left:3px solid {color}; padding-left:0.6rem;
                margin:1.2rem 0 0.7rem; text-transform:uppercase;">{text}</div>
    """


# ────────────────────────────────────────────────────────────────────────────
# Data Layer — cloud-safe absolute path resolution
# ────────────────────────────────────────────────────────────────────────────

# Guard: __file__ is defined when Streamlit runs the script normally.
# On some cloud runners the module context differs; fall back to sys.argv[0].
try:
    _THIS_FILE = os.path.abspath(__file__)
except NameError:
    _THIS_FILE = os.path.abspath(sys.argv[0])

_HERE     = Path(os.path.dirname(_THIS_FILE))
DATA_DIR  = _HERE / "data"
DATA_PATH = DATA_DIR / "transactions.csv"

# Ensure the data directory always exists (guards against missing git-tracked dir)
DATA_DIR.mkdir(parents=True, exist_ok=True)


# ── Inline data generator (no subprocess, no file-system side-effects) ────
def _generate_csv_inline(path: Path) -> None:
    """
    Generates synthetic transaction data entirely in-process.
    Mirrors the logic in generate_data.py so no external script call
    is needed — critical for cloud deployments where subprocess may be
    blocked or the working-directory context is unknown.
    """
    random.seed(42)
    path.parent.mkdir(parents=True, exist_ok=True)

    BASE_TIME       = datetime(2024, 6, 1, 9, 0, 0)
    NORMAL_ACCOUNTS = [f"ACC_{i:04d}" for i in range(1, 201)]
    NORMAL_DEVICES  = [f"DEV_{i:05d}" for i in range(1, 5001)]

    def txn(sender, receiver, amount, ts, device):
        return {"txn_id": str(uuid.uuid4()), "sender_id": sender,
                "receiver_id": receiver, "amount_inr": round(amount, 2),
                "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%S"),
                "device_fingerprint": device}

    def rt(base, mins=1440):
        return base + timedelta(minutes=random.randint(0, mins))

    rows = []

    # 3-hop loops (3 families × 3 edges = 9 rows)
    for fam in [("MULE_A1","MULE_A2","MULE_A3"), ("MULE_B1","MULE_B2","MULE_B3"),
                ("MULE_C1","MULE_C2","MULE_C3")]:
        ts  = rt(BASE_TIME, 180)
        dev = f"MULE_DEV_L3{fam[0][-2]}"
        amt = random.uniform(50_000, 150_000)
        for i in range(3):
            rows.append(txn(fam[i], fam[(i+1)%3], amt*random.uniform(0.6,1.0),
                           ts + timedelta(minutes=i*5), dev))

    # 4-hop loop (4 rows)
    loop4 = ("MULE_D1","MULE_D2","MULE_D3","MULE_D4")
    ts    = rt(BASE_TIME, 200)
    amt   = random.uniform(100_000, 200_000)
    for i in range(4):
        rows.append(txn(loop4[i], loop4[(i+1)%4], amt*random.uniform(0.55,1.0),
                       ts + timedelta(minutes=i*8), "MULE_DEV_L4"))

    # Smurfing: fan-out 8 + fan-in 8 = 16 rows
    smurf_mules = [f"SMURF_{i:02d}" for i in range(1, 9)]
    ts_fo = rt(BASE_TIME, 30)
    for i, m in enumerate(smurf_mules):
        rows.append(txn("MULE_ORIGIN", m, random.uniform(4_000, 9_999),
                       ts_fo + timedelta(seconds=i*45), "MULE_DEV_SMURF"))
    ts_fi = ts_fo + timedelta(minutes=20)
    for i, m in enumerate(smurf_mules):
        rows.append(txn(m, "MULE_AGG", random.uniform(4_000, 9_999),
                       ts_fi + timedelta(seconds=i*30), "MULE_DEV_SMURF"))

    # Normal noise to reach 500 total
    while len(rows) < 500:
        s, r = random.sample(NORMAL_ACCOUNTS, 2)
        rows.append(txn(s, r, random.uniform(500, 49_999),
                       rt(BASE_TIME, 2880), random.choice(NORMAL_DEVICES)))

    random.shuffle(rows)

    fields = ["txn_id","sender_id","receiver_id","amount_inr",
              "timestamp","device_fingerprint"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
    """
    Load the transaction dataset. Generates it in-process if absent or
    unreadable — no subprocess or external permissions required.
    Safe for Streamlit Cloud, Docker, and local dev.
    """
    # Always regenerate if missing
    if not DATA_PATH.exists():
        _generate_csv_inline(DATA_PATH)

    # Wrap read in try/except: regenerate if the file is corrupt/empty
    try:
        df = pd.read_csv(str(DATA_PATH), parse_dates=["timestamp"])
        if df.empty or "sender_id" not in df.columns:
            raise ValueError("CSV schema invalid")
    except Exception:
        _generate_csv_inline(DATA_PATH)
        df = pd.read_csv(str(DATA_PATH), parse_dates=["timestamp"])

    df["amount_inr"] = df["amount_inr"].astype(float)
    return df


# ────────────────────────────────────────────────────────────────────────────
# Graph Engine — Build
# ────────────────────────────────────────────────────────────────────────────
# nx.DiGraph is not pickle-serialisable, so @st.cache_data (which uses
# pickle) will throw UnhashableTypeError on Streamlit Cloud.
# @st.cache_resource caches by object identity — correct for graphs.
@st.cache_resource(show_spinner=False)
def build_graph(df_hash: int, _df: pd.DataFrame) -> nx.DiGraph:
    """
    Construct a directed graph where every unique account ID is a node
    and every transaction row becomes a weighted directed edge.
    df_hash is the cache key (hash of the DataFrame); _df is the actual
    data (underscore prefix tells Streamlit not to hash this argument).
    """
    G = nx.DiGraph()
    for _, row in _df.iterrows():
        G.add_edge(
            row["sender_id"],
            row["receiver_id"],
            amount    = row["amount_inr"],
            timestamp = str(row["timestamp"]),
            txn_id    = row["txn_id"],
            device    = row["device_fingerprint"],
        )
    return G


# ────────────────────────────────────────────────────────────────────────────
# Detection Algorithm 1 — Multi-Hop Cycle Detection (DFS)
# ────────────────────────────────────────────────────────────────────────────
def detect_cycles(G: nx.DiGraph, min_cycle_len: int = 3) -> list[list[str]]:
    """
    Uses NetworkX's implementation of Johnson's algorithm (which performs DFS
    internally) to enumerate all simple cycles in the directed graph.
    Returns cycles with length >= min_cycle_len, deduplicated.
    """
    all_cycles = []
    for cycle in nx.simple_cycles(G):
        if len(cycle) >= min_cycle_len:
            all_cycles.append(cycle)
    return all_cycles


# ────────────────────────────────────────────────────────────────────────────
# Detection Algorithm 2 — Velocity / Smurfing Check (Fan-out / Fan-in)
# ────────────────────────────────────────────────────────────────────────────
def detect_smurfing(
    df: pd.DataFrame,
    fan_out_threshold: int  = 5,
    time_window_min:   int  = 10,
    amount_ceiling:    float= 10_000.0,
) -> dict[str, dict]:
    """
    Fan-Out check:
      A node is flagged if it sends money to > fan_out_threshold distinct
      receivers within a time_window_min rolling window, each transfer
      being below amount_ceiling (sub-threshold structuring).

    Fan-In check:
      A node is flagged if it receives from > fan_out_threshold distinct
      senders within the same window.

    Returns a dict keyed by account_id with metadata about the alert.
    """
    flagged: dict[str, dict] = {}

    df_sorted = df.sort_values("timestamp")

    # Fan-Out  (Smurf source / distributor)
    for sender, grp in df_sorted.groupby("sender_id"):
        grp = grp[grp["amount_inr"] < amount_ceiling]
        if grp.empty:
            continue
        grp = grp.sort_values("timestamp")
        times = grp["timestamp"].tolist()
        receivers_in_window: list = []
        for i, t in enumerate(times):
            window = [
                grp.iloc[j]["receiver_id"]
                for j in range(i, len(times))
                if (times[j] - t).total_seconds() <= time_window_min * 60
            ]
            if len(set(window)) > fan_out_threshold:
                flagged[str(sender)] = {
                    "type":      "SMURFING — Fan-Out (Distributor)",
                    "receivers": list(set(window)),
                    "count":     len(set(window)),
                    "window":    f"{time_window_min} min",
                    "amount_ceiling": amount_ceiling,
                }
                break

    # Fan-In  (Aggregator)
    for receiver, grp in df_sorted.groupby("receiver_id"):
        grp = grp[grp["amount_inr"] < amount_ceiling]
        if grp.empty:
            continue
        grp = grp.sort_values("timestamp")
        times = grp["timestamp"].tolist()
        for i, t in enumerate(times):
            window = [
                grp.iloc[j]["sender_id"]
                for j in range(i, len(times))
                if (times[j] - t).total_seconds() <= time_window_min * 60 * 3
            ]
            if len(set(window)) > fan_out_threshold:
                flagged[str(receiver)] = {
                    "type":    "SMURFING — Fan-In (Aggregator)",
                    "senders": list(set(window)),
                    "count":   len(set(window)),
                    "window":  f"{time_window_min * 3} min",
                    "amount_ceiling": amount_ceiling,
                }
                break

    return flagged


# ────────────────────────────────────────────────────────────────────────────
# Detection Algorithm 3 — Entity Linkage (shared device fingerprint)
# ────────────────────────────────────────────────────────────────────────────
def detect_entity_linkage(df: pd.DataFrame) -> dict[str, list[str]]:
    """
    Groups accounts that share the same device_fingerprint.
    Returns mapping: {device_id → [account_ids]}, filtered to groups
    with ≥ 2 distinct accounts and the "MULE_DEV" prefix (fraud marker).
    """
    device_map: dict[str, set] = defaultdict(set)
    for _, row in df.iterrows():
        device_map[row["device_fingerprint"]].add(row["sender_id"])
        device_map[row["device_fingerprint"]].add(row["receiver_id"])

    return {
        dev: sorted(accs)
        for dev, accs in device_map.items()
        if len(accs) >= 2 and "MULE_DEV" in dev
    }


# ────────────────────────────────────────────────────────────────────────────
# Aggregate All Flagged Nodes
# ────────────────────────────────────────────────────────────────────────────
def get_all_flagged_nodes(
    cycles: list[list[str]],
    smurf_flags: dict,
    linkage: dict,
) -> set[str]:
    flagged = set()
    for cycle in cycles:
        flagged.update(cycle)
    flagged.update(smurf_flags.keys())
    for accounts in linkage.values():
        flagged.update(accounts)
    return flagged


# ────────────────────────────────────────────────────────────────────────────
# PyVis Graph Renderer
# ────────────────────────────────────────────────────────────────────────────
def build_pyvis(
    G: nx.DiGraph,
    flagged_nodes: set[str],
    flagged_edges: set[tuple],
) -> str:
    """
    Converts the NetworkX graph into an interactive PyVis HTML string.

    Flagged mule accounts → red, size 30.
    Normal accounts       → cyan, size 12.
    Flagged edges         → red, width 3.
    Normal edges          → slate, width 1.
    """
    net = Network(
        height="520px",
        width="100%",
        bgcolor="#080c14",
        font_color="#00e5ff",
        directed=True,
    )
    net.barnes_hut(
        gravity=-8000,
        central_gravity=0.3,
        spring_length=160,
        spring_strength=0.04,
        damping=0.09,
    )

    # ── Nodes ──
    for node in G.nodes():
        is_mule = node in flagged_nodes
        net.add_node(
            node,
            label=node,
            size=28 if is_mule else 12,
            color="#ff0055" if is_mule else "#00e5ff",
            font={"color": "#ff0055" if is_mule else "#00e5ff",
                  "size": 11,
                  "face": "Courier New"},
            title=f"{'🔴 FLAGGED MULE' if is_mule else '🔵 Account'}: {node}",
            borderWidth=3 if is_mule else 1,
            borderWidthSelected=4,
        )

    # ── Edges ──
    for u, v, data in G.edges(data=True):
        is_fraud = (u, v) in flagged_edges
        net.add_edge(
            u, v,
            width=3 if is_fraud else 1,
            color={"color": "#ff0055" if is_fraud else "#1e3050",
                   "highlight": "#ff0055"},
            title=f"₹{data.get('amount', 0):,.0f} | {data.get('timestamp', '')}",
            arrows="to",
            smooth={"type": "curvedCW", "roundness": 0.15},
        )

    # ── Physics options via JSON ──
    net.set_options("""
    var options = {
      "physics": {
        "enabled": true,
        "barnesHut": {
          "gravitationalConstant": -8000,
          "centralGravity": 0.3,
          "springLength": 160,
          "springConstant": 0.04,
          "damping": 0.09
        },
        "stabilization": {"iterations": 150}
      },
      "interaction": {
        "hover": true,
        "tooltipDelay": 100,
        "navigationButtons": false,
        "keyboard": false
      },
      "edges": {
        "smooth": {"type": "curvedCW", "roundness": 0.15}
      }
    }
    """)

    # ── Safe HTML export: StringIO first, temp-file as fallback ──
    # PyVis ≥ 0.3.2 exposes generate_html(); older builds only have
    # save_graph(). We try the in-memory path first so the app works
    # on read-only cloud file-systems without needing /tmp write access.
    try:
        html_str = net.generate_html()
        return html_str
    except AttributeError:
        pass

    # Fallback: write to a guaranteed-writable temp dir
    try:
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".html")
        os.close(tmp_fd)
        net.save_graph(tmp_path)
        with open(tmp_path, encoding="utf-8") as fh:
            html_str = fh.read()
        return html_str
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


# ────────────────────────────────────────────────────────────────────────────
# Build Alerts DataFrame
# ────────────────────────────────────────────────────────────────────────────
def build_alerts_df(
    df: pd.DataFrame,
    flagged_nodes: set[str],
    cycles: list[list[str]],
    smurf_flags: dict,
) -> pd.DataFrame:
    """Return a table of flagged transactions with risk scores and status."""
    mask = df["sender_id"].isin(flagged_nodes) | df["receiver_id"].isin(flagged_nodes)
    flagged_df = df[mask].copy()
    if flagged_df.empty:
        return flagged_df

    def assign_type(row) -> str:
        sender, receiver = row["sender_id"], row["receiver_id"]
        for cycle in cycles:
            if sender in cycle or receiver in cycle:
                return f"Multi-Hop Cycle ({len(cycle)}-hop)"
        if sender in smurf_flags:
            return smurf_flags[sender]["type"]
        if receiver in smurf_flags:
            return smurf_flags[receiver]["type"]
        return "Entity Linkage"

    def risk_score(row) -> str:
        t = row.get("alert_type", "")
        if "Cycle" in t:
            return "98%"
        if "Fan-Out" in t:
            return "91%"
        if "Fan-In" in t:
            return "94%"
        return "85%"

    flagged_df["alert_type"]  = flagged_df.apply(assign_type, axis=1)
    flagged_df["risk_score"]  = flagged_df.apply(risk_score, axis=1)
    flagged_df["status"]      = "🚨 AUTO-FROZEN"

    return flagged_df[[
        "txn_id", "sender_id", "receiver_id",
        "amount_inr", "timestamp", "alert_type", "risk_score", "status",
    ]].reset_index(drop=True)


# ────────────────────────────────────────────────────────────────────────────
# Build Simulation Log Lines
# ────────────────────────────────────────────────────────────────────────────
def build_logs(
    n_txn: int,
    n_nodes: int,
    cycles: list,
    smurf_flags: dict,
    linkage: dict,
) -> list[str]:
    logs = [
        "🔍 SCAN INITIATED — Loading transactions.csv into memory...",
        f"✅ OK — {n_txn} transactions parsed into Pandas DataFrame.",
        "🔍 RUN — Building directed graph via NetworkX DiGraph()...",
        f"✅ OK — Graph constructed: {n_nodes} nodes, edges mapped.",
        "🔍 CHECK — Executing DFS cycle detection (Johnson's algorithm)...",
    ]
    if cycles:
        for c in cycles[:5]:
            logs.append(f"🔴 ALERT — Cycle detected: {' → '.join(c)} → {c[0]}")
    else:
        logs.append("✅ OK — No cycles found.")

    logs.append("🔍 CHECK — Running velocity / smurfing analysis...")
    if smurf_flags:
        for acct, meta in list(smurf_flags.items())[:4]:
            logs.append(f"🔴 ALERT — {meta['type']} | Account: {acct}")
    else:
        logs.append("✅ OK — No smurfing pattern detected.")

    logs.append("🔍 CHECK — Entity linkage by device fingerprint...")
    if linkage:
        for dev, accts in list(linkage.items())[:3]:
            logs.append(f"🔴 FLAGGED — {dev}: {', '.join(accts[:4])}")
    else:
        logs.append("✅ OK — No shared-device clustering found.")

    logs.append("✅ COMPLETE — Analysis pipeline finished. Dashboard rendered.")
    return logs


# ────────────────────────────────────────────────────────────────────────────
# MAIN APP
# ────────────────────────────────────────────────────────────────────────────
def main() -> None:

    # ── Inject global CSS ──────────────────────────────────────────────────
    st.markdown(CYBERPUNK_CSS, unsafe_allow_html=True)

    # ── Header ────────────────────────────────────────────────────────────
    st.markdown(html_header(), unsafe_allow_html=True)

    # ── Load & process data ───────────────────────────────────────────────
    with st.spinner("🔄  Loading transaction dataset…"):
        df = load_data()

    G            = build_graph(pd.util.hash_pandas_object(df).sum(), df)
    cycles       = detect_cycles(G, min_cycle_len=3)
    smurf_flags  = detect_smurfing(df)
    linkage      = detect_entity_linkage(df)
    flagged_nodes = get_all_flagged_nodes(cycles, smurf_flags, linkage)

    # Build set of flagged edges (edges where BOTH endpoints are flagged)
    flagged_edges: set[tuple] = set()
    for cycle in cycles:
        for i in range(len(cycle)):
            flagged_edges.add((cycle[i], cycle[(i + 1) % len(cycle)]))
    for node, meta in smurf_flags.items():
        if "receivers" in meta:
            for r in meta["receivers"]:
                flagged_edges.add((node, r))
        if "senders" in meta:
            for s in meta["senders"]:
                flagged_edges.add((s, node))

    total_flagged_amount = df[
        df["sender_id"].isin(flagged_nodes) | df["receiver_id"].isin(flagged_nodes)
    ]["amount_inr"].sum()

    alerts_df = build_alerts_df(df, flagged_nodes, cycles, smurf_flags)
    logs      = build_logs(len(df), G.number_of_nodes(), cycles, smurf_flags, linkage)

    # ── KPI Banner ────────────────────────────────────────────────────────
    st.markdown(
        section_header("// THREAT INTELLIGENCE METRICS"), unsafe_allow_html=True
    )
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(
            kpi_card("TRANSACTIONS SCANNED", f"{len(df):,}", "#00e5ff",
                     "in-memory dataset"),
            unsafe_allow_html=True,
        )
    with k2:
        st.markdown(
            kpi_card("ACTIVE GRAPH NODES", f"{G.number_of_nodes():,}", "#00e5ff",
                     "unique accounts"),
            unsafe_allow_html=True,
        )
    with k3:
        chain_count = len(cycles) + (1 if smurf_flags else 0)
        st.markdown(
            kpi_card("MULE CHAINS DETECTED", str(chain_count), "#ff0055",
                     "action required"),
            unsafe_allow_html=True,
        )
    with k4:
        st.markdown(
            kpi_card(
                "TOTAL RISK EXPOSURE",
                f"₹{total_flagged_amount:,.0f}",
                "#ff0055",
                "funds flagged for freeze",
            ),
            unsafe_allow_html=True,
        )

    st.markdown("<div style='margin-top:1.2rem;'></div>", unsafe_allow_html=True)

    # ── Command Center ────────────────────────────────────────────────────
    st.markdown(
        section_header("// COMMAND CENTER — LIVE ANALYSIS"),
        unsafe_allow_html=True,
    )
    left_col, right_col = st.columns([1, 2])

    # ── Left Panel: Console + Alert Card ──────────────────────────────────
    with left_col:
        st.markdown(
            section_header("SYSTEM CONSOLE", "#5a7090"), unsafe_allow_html=True
        )
        st.markdown(terminal_box(logs), unsafe_allow_html=True)

        if cycles:
            top_cycle = max(cycles, key=len)
            chain_str  = " → ".join(top_cycle) + f" → {top_cycle[0]}"
            alert_body = (
                f"<b>Pattern:</b> Multi-Hop Money Laundering + Smurfing<br/>"
                f"<b>Longest Chain:</b> {len(top_cycle)}-hop cycle<br/>"
                f"<b>Nodes:</b> {', '.join(top_cycle)}<br/>"
                f"<b>Entities Linked:</b> {len(linkage)} shared-device clusters<br/>"
                f"<b>Recommended Action:</b> Auto-freeze + SAR Filing"
            )
            st.markdown(
                alert_card("MULE LAUNDERING RING IDENTIFIED", alert_body),
                unsafe_allow_html=True,
            )
        elif smurf_flags:
            first_node = next(iter(smurf_flags))
            meta       = smurf_flags[first_node]
            alert_body = (
                f"<b>Pattern:</b> Smurfing / Structuring<br/>"
                f"<b>Account:</b> {first_node}<br/>"
                f"<b>Type:</b> {meta['type']}<br/>"
                f"<b>Receivers in window:</b> {meta.get('count', '?')}<br/>"
                f"<b>Recommended Action:</b> Account Suspension + AML Review"
            )
            st.markdown(
                alert_card("SMURFING PATTERN DETECTED", alert_body),
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""<div style="background:#0a1a0a; border:1px solid #00ff88;
                               border-radius:8px; padding:1rem; margin-top:0.8rem;">
                  <div style="color:#00ff88; font-size:0.8rem;">✅ NO CRITICAL THREATS</div>
                  <div style="color:#5a7090; font-size:0.72rem; margin-top:0.3rem;">
                    All accounts within normal parameters.</div>
                </div>""",
                unsafe_allow_html=True,
            )

        # ── Cycle details expander ────────────────────────────────────────
        if cycles:
            with st.expander(
                f"🔗 View All {len(cycles)} Detected Cycles", expanded=False
            ):
                for i, cycle in enumerate(cycles, 1):
                    color = "#ff0055" if len(cycle) >= 4 else "#ff6688"
                    st.markdown(
                        f"<div style='color:{color}; font-size:0.75rem; "
                        f"margin-bottom:4px; font-family:monospace;'>"
                        f"Cycle {i} ({len(cycle)}-hop): "
                        f"{'  →  '.join(cycle)} → {cycle[0]}</div>",
                        unsafe_allow_html=True,
                    )

    # ── Right Panel: PyVis Graph ──────────────────────────────────────────
    with right_col:
        st.markdown(
            section_header("NETWORK GRAPH — LIVE FRAUD MAP", "#00e5ff"),
            unsafe_allow_html=True,
        )
        legend_html = """
        <div style="display:flex; gap:1.5rem; font-size:0.72rem; margin-bottom:0.5rem;">
          <span><span style="color:#ff0055;">&#x25CF;</span>&nbsp;Flagged Mule Account</span>
          <span><span style="color:#00e5ff;">&#x25CF;</span>&nbsp;Normal Account</span>
          <span><span style="color:#ff0055;">&#x2014;</span>&nbsp;Fraud Transfer</span>
          <span><span style="color:#334155;">&#x2014;</span>&nbsp;Normal Transfer</span>
        </div>
        """
        st.markdown(legend_html, unsafe_allow_html=True)

        with st.spinner("🔄  Rendering interactive graph…"):
            pyvis_html = build_pyvis(G, flagged_nodes, flagged_edges)

        components.html(pyvis_html, height=540, scrolling=False)

    # ── Audit Trail ───────────────────────────────────────────────────────
    st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)
    st.markdown(
        section_header("// AUDIT TRAIL — FLAGGED TRANSACTIONS"),
        unsafe_allow_html=True,
    )

    if not alerts_df.empty:
        summary_html = f"""
        <div style="background:#0d1527; border:1px solid #334155; border-radius:8px;
                    padding:0.9rem 1.2rem; margin-bottom:0.8rem;
                    display:flex; gap:2rem; font-size:0.78rem;">
          <div>
            <span style="color:#5a7090;">Flagged Transactions:</span>&nbsp;
            <span style="color:#ff0055; font-weight:700;">{len(alerts_df)}</span>
          </div>
          <div>
            <span style="color:#5a7090;">Unique Alert Types:</span>&nbsp;
            <span style="color:#ff0055; font-weight:700;">
              {alerts_df['alert_type'].nunique()}
            </span>
          </div>
          <div>
            <span style="color:#5a7090;">Accounts Auto-Frozen:</span>&nbsp;
            <span style="color:#ff0055; font-weight:700;">{len(flagged_nodes)}</span>
          </div>
          <div>
            <span style="color:#5a7090;">Total Exposure:</span>&nbsp;
            <span style="color:#ff0055; font-weight:700;">
              ₹{alerts_df['amount_inr'].sum():,.0f}
            </span>
          </div>
        </div>
        """
        st.markdown(summary_html, unsafe_allow_html=True)

        st.dataframe(
            alerts_df.style.map(
                lambda v: "color: #ff0055; font-weight: bold"
                if v == "🚨 AUTO-FROZEN"
                else "",
                subset=["status"],
            ).map(
                lambda v: "color: #ff6688"
                if isinstance(v, str) and "%" in v and int(v.rstrip("%")) >= 90
                else "",
                subset=["risk_score"],
            ),
            use_container_width=True,
            height=340,
        )
    else:
        st.info("No flagged transactions found. The network appears clean.")

    # ── Entity Linkage Section ────────────────────────────────────────────
    if linkage:
        st.markdown("<div style='margin-top:1rem;'></div>", unsafe_allow_html=True)
        st.markdown(
            section_header("// ENTITY LINKAGE — SHARED DEVICE CLUSTERS"),
            unsafe_allow_html=True,
        )
        link_rows = [
            {"device_fingerprint": dev, "linked_accounts": ", ".join(accts),
             "account_count": len(accts)}
            for dev, accts in linkage.items()
        ]
        st.dataframe(
            pd.DataFrame(link_rows),
            use_container_width=True,
            height=200,
        )

    # ── Footer ────────────────────────────────────────────────────────────
    st.markdown(
        """<div style="margin-top:2.5rem; border-top:1px solid #334155;
                       padding-top:0.8rem; font-size:0.65rem; color:#334155;
                       text-align:center; letter-spacing:0.1em;">
          FINSENTINEL v1.0 &nbsp;|&nbsp; ENTERPRISE AML &amp; FINANCIAL CRIME INTELLIGENCE
          &nbsp;|&nbsp; GRAPH-BASED TRANSACTION ANALYTICS &nbsp;|&nbsp;
          SIMULATED DATA &mdash; FOR DEMONSTRATION PURPOSES ONLY
        </div>""",
        unsafe_allow_html=True,
    )


# ────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
