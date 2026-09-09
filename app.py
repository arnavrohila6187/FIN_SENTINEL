import os
import tempfile
import pandas as pd
import networkx as nx
from flask import Flask, render_template, request, jsonify
from pyvis.network import Network

app = Flask(__name__)

# Mock Data Generator (Reusing logic for demonstration)
def load_transaction_data() -> pd.DataFrame:
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

df_global = load_transaction_data()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/graph', methods=['POST'])
def api_graph():
    try:
        data = request.get_json()
        min_risk = float(data.get('min_risk', 0))

        # Filter dataset
        filtered_df = df_global[df_global['risk_score'] >= min_risk]

        # Build NetworkX Graph
        G = nx.DiGraph()
        for _, row in filtered_df.iterrows():
            G.add_edge(row["source"], row["target"], weight=row["amount"], risk=row["risk_score"])

        # Detect rings (Mock metric logic based on original design)
        # Assuming cycles detection logic is simple for demo purpose
        cycles = list(nx.simple_cycles(G))
        rings_detected = len([c for c in cycles if len(c) >= 3])

        # PyVis Rendering
        net = Network(height="100%", width="100%", bgcolor="#0d1117", font_color="#00ff66", directed=True)
        # Remove navigation buttons for a cleaner iframe integration
        net.toggle_physics(True)
        net.from_nx(G)

        # Temporary file save for HTML extraction
        with tempfile.NamedTemporaryFile(delete=False, suffix=".html", dir=tempfile.gettempdir()) as tmp_file:
            net.save_graph(tmp_file.name)
            with open(tmp_file.name, 'r', encoding='utf-8') as f:
                html_bytes = f.read()
            os.unlink(tmp_file.name)

        # Metrics Payload
        metrics = {
            "total": len(df_global),
            "flagged": len(filtered_df),
            "rings": rings_detected
        }

        return jsonify({
            "status": "success",
            "html": html_bytes,
            "metrics": metrics
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

if __name__ == '__main__':
    # Run locally if executed directly
    app.run(host='0.0.0.0', port=8501, debug=True)