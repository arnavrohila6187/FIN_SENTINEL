import pandas as pd
import os
from flask import Flask, render_template, request, jsonify, session, redirect, url_for

app = Flask(__name__)
app.secret_key = 'hackathon_key'

# Load Data from CSV
DATA_PATH = os.path.join(os.path.dirname(__file__), 'data', 'transactions.csv')

def load_transaction_data() -> pd.DataFrame:
    if os.path.exists(DATA_PATH):
        try:
            return pd.read_csv(DATA_PATH)
        except Exception as e:
            print(f"Error loading CSV: {e}")
    # Fallback to empty dataframe with expected columns
    return pd.DataFrame(columns=['txn_id', 'sender_id', 'receiver_id', 'amount_inr', 'timestamp', 'device_fingerprint'])

df_global = load_transaction_data()

# Calculate risk level column upfront for efficiency
if not df_global.empty:
    def calculate_risk(row):
        # MULE_DEV in fingerprint is high risk
        if pd.notna(row.get('device_fingerprint')) and str(row['device_fingerprint']).startswith('MULE_DEV'):
            return 'High'
        amount = row.get('amount_inr', 0)
        try:
            amount = float(amount)
        except:
            amount = 0
        if amount > 100000:
            return 'High'
        elif amount > 50000:
            return 'Medium'
        else:
            return 'Low'
            
    df_global['risk_level'] = df_global.apply(calculate_risk, axis=1)
else:
    df_global['risk_level'] = []

@app.route('/')
def index():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['logged_in'] = True
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/api/data', methods=['POST'])
def api_data():
    try:
        # Check if empty
        if df_global.empty:
            high_risk = 0
            medium_risk = 0
            low_risk = 0
            total = 0
        else:
            high_risk = len(df_global[df_global['risk_level'] == 'High'])
            medium_risk = len(df_global[df_global['risk_level'] == 'Medium'])
            low_risk = len(df_global[df_global['risk_level'] == 'Low'])
            total = len(df_global)

        metrics = {
            "total": total,
            "high_risk": high_risk,
            "medium_risk": medium_risk,
            "low_risk": low_risk,
            "flagged": high_risk + medium_risk
        }

        return jsonify({
            "status": "success",
            "chart_data": {
                "labels": ["High Risk", "Medium Risk", "Low Risk"],
                "values": [high_risk, medium_risk, low_risk]
            },
            "metrics": metrics
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

if __name__ == '__main__':
    # Run locally if executed directly
    app.run(host='0.0.0.0', port=8501, debug=True, use_reloader=False)