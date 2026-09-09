import os
import tempfile
import streamlit as st
import pandas as pd
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components

# Page Configuration
st.set_page_config(
    page_title="FinSentinel // Graph Intelligence Engine",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Cyberpunk CSS
st.markdown("""
<style>
    .main { background-color: #0d1117; color: #c9d1d9; }
    stApp { background-color: #0d1117; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 10px; }
    h1, h2, h3 { color: #00ff66 !important; font-family: 'Courier New', monospace; }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("# 🛡️ FINSENTINEL // GRAPH INTELLIGENCE ENGINE")
st.markdown("**AML & FINANCIAL CRIME DETECTION** | GRAPH-BASED TRANSACTION ANALYTICS | ENTERPRISE COMPLIANCE PLATFORM")
st.divider()

# In-Memory Data Generator
@st.cache_data
def load_transaction_data():
    data = [
        {"source": "ACC_101", "target": "ACC_102", "amount": 150000, "risk_score": 88, "type": "WIRE"},
        {"source": "ACC_102", "target": "ACC_103", "amount": 145000, "risk_score": 92, "type": "WIRE"},
        {"source": "ACC_103", "target": "ACC_101", "amount": 140000, "risk_score": 95, "type": "CIRCULAR"},
        {"source": "ACC_104", "target": "ACC_105", "amount": 12000, "risk_score": 25, "type": "ACH"},
        {"source": "ACC_105", "target": "ACC_106", "amount": 8500, "risk_score": 15, "type": "ACH"},
        {"source": "ACC_107", "target": "ACC_102", "amount": 500000, "risk_score": 99, "type": "HIGH_RISK_SHELL"},
        {"source": "ACC_108", "target": "ACC_102", "amount": 480000, "risk_score": 97, "type": "HIGH_RISK_SHELL"},
    ]
    return pd.DataFrame(data)

try:
    df = load_transaction_data()

    # Sidebar Controls
    st.sidebar.header("🔍 Filter Analytics")
    min_risk = st.sidebar.slider("Min Risk Score Threshold", 0, 100, 50)
    filtered_df = df[df["risk_score"] >= min_risk]
    
    run_btn = st.sidebar.button("Run Graph Analytics", type="primary")

    # Metrics Row
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Transactions", len(df))
    col2.metric("Flagged High-Risk", len(filtered_df))
    col3.metric("Mule Rings Detected", "1 Ring (3 Nodes)")
    col4.metric("Engine Status", "ONLINE", delta_color="normal")

    # Tabs Interface
    tab1, tab2, tab3 = st.tabs(["🌐 Network Intelligence Graph", "📊 Transaction Matrix", "🚨 Threat Alerts"])

    with tab1:
        st.subheader("Interactive Transaction Network")
        
        # Build NetworkX Graph
        G = nx.DiGraph()
        for _, row in filtered_df.iterrows():
            G.add_edge(row["source"], row["target"], weight=row["amount"], risk=row["risk_score"])

        # PyVis Cloud-Safe Rendering
        net = Network(height="500px", width="100%", bgcolor="#0d1117", font_color="#00ff66", directed=True)
        net.from_nx(G)

        # Tempfile Save Method for Cloud Compatibility
        with tempfile.NamedTemporaryFile(delete=False, suffix=".html", dir=tempfile.gettempdir()) as tmp_file:
            net.save_graph(tmp_file.name)
            with open(tmp_file.name, 'r', encoding='utf-8') as f:
                html_bytes = f.read()
            os.unlink(tmp_file.name)

        components.html(html_bytes, height=520, scrolling=False)

    with tab2:
        st.subheader("Filtered Transaction Records")
        st.dataframe(filtered_df, use_container_width=True)

    with tab3:
        st.subheader("Active Fraud Rings & Mule Networks")
        st.error("🚨 **CRITICAL ALERT:** Circular laundering pattern detected between ACC_101 ➔ ACC_102 ➔ ACC_103")
        st.warning("⚠️ **HIGH RISK:** Shell company structuring behavior detected from ACC_107 and ACC_108")

except Exception as e:
    st.error(f"FATAL APPLICATION ERROR: {e}")