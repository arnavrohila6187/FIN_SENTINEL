"""
FinSentinel — Data Simulation Engine
=====================================
Generates a synthetic transactions.csv with exactly 500 rows.

Fraud Patterns Injected
-----------------------
1. 3-hop Mule Laundering Loops  — circular fund flow A → B → C → A
2. 4-hop Mule Laundering Loops  — A → B → C → D → A
3. Smurfing / Fan-Out → Fan-In  — a source distributes to 7+ mules,
                                   each mule pushes to a single aggregator

All fraudulent transfers share a common device_fingerprint prefix
"MULE_DEV" to enable the Entity Linkage check.

Usage
-----
    python generate_data.py
Outputs: data/transactions.csv
"""

import csv
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path

# ── Seed for reproducibility ────────────────────────────────────────────────
random.seed(42)

# ── Output path ─────────────────────────────────────────────────────────────
OUTPUT_DIR = Path("data")
OUTPUT_DIR.mkdir(exist_ok=True)
OUTPUT_PATH = OUTPUT_DIR / "transactions.csv"

# ── Constants ────────────────────────────────────────────────────────────────
TOTAL_ROWS        = 500
NORMAL_ACCOUNTS   = [f"ACC_{i:04d}" for i in range(1, 201)]   # 200 legit accounts
BASE_TIME         = datetime(2024, 6, 1, 9, 0, 0)

# ── Fraud Account Pools ──────────────────────────────────────────────────────
# 3-hop loop characters
LOOP_3_A = ["MULE_A1", "MULE_A2", "MULE_A3"]
LOOP_3_B = ["MULE_B1", "MULE_B2", "MULE_B3"]
LOOP_3_C = ["MULE_C1", "MULE_C2", "MULE_C3"]

# 4-hop loop characters
LOOP_4   = ["MULE_D1", "MULE_D2", "MULE_D3", "MULE_D4"]

# Smurfing characters
SMURF_SOURCE      = "MULE_ORIGIN"
SMURF_MULES       = [f"SMURF_{i:02d}" for i in range(1, 9)]   # 8 mule accounts
SMURF_AGGREGATOR  = "MULE_AGG"

# All fraudulent node ids (used later for labelling)
ALL_FRAUD_NODES = (
    LOOP_3_A + LOOP_3_B + LOOP_3_C + LOOP_4
    + [SMURF_SOURCE] + SMURF_MULES + [SMURF_AGGREGATOR]
)

FRAUD_DEVICE_PREFIX = "MULE_DEV"
NORMAL_DEVICES = [f"DEV_{i:05d}" for i in range(1, 5001)]


# ── Helper functions ─────────────────────────────────────────────────────────
def make_txn(sender: str, receiver: str, amount: float,
             ts: datetime, device: str) -> dict:
    return {
        "txn_id":            str(uuid.uuid4()),
        "sender_id":         sender,
        "receiver_id":       receiver,
        "amount_inr":        round(amount, 2),
        "timestamp":         ts.strftime("%Y-%m-%dT%H:%M:%S"),
        "device_fingerprint": device,
    }


def rand_time(base: datetime, window_minutes: int = 1440) -> datetime:
    """Return a random timestamp within *window_minutes* after base."""
    return base + timedelta(minutes=random.randint(0, window_minutes))


def rand_normal_amount() -> float:
    """Typical retail transfer: ₹500 – ₹49,999."""
    return random.uniform(500, 49_999)


def rand_smurf_amount() -> float:
    """
    Smurfing amounts are deliberately kept below ₹10,000 to stay under
    conventional threshold-based alerts — the classic smurfing tell.
    """
    return random.uniform(4_000, 9_999)


# ── Build fraudulent transaction batches ─────────────────────────────────────
def build_3hop_loops(base_ts: datetime) -> list[dict]:
    """
    Injects two independent 3-hop mule laundering loops.
    Loop shape:  A → B → C → A  (cycle of length 3)
    The same device fingerprint is shared to simulate entity linkage.
    """
    rows = []
    # Loop family A
    ts = rand_time(base_ts, 60)
    device = f"{FRAUD_DEVICE_PREFIX}_L3A"
    nodes = LOOP_3_A
    large_amount = random.uniform(80_000, 150_000)
    for i in range(len(nodes)):
        rows.append(make_txn(
            sender   = nodes[i],
            receiver = nodes[(i + 1) % len(nodes)],
            amount   = large_amount * random.uniform(0.6, 1.0),
            ts       = ts + timedelta(minutes=i * random.randint(3, 8)),
            device   = device,
        ))
    # Loop family B
    ts = rand_time(base_ts, 120)
    device = f"{FRAUD_DEVICE_PREFIX}_L3B"
    nodes = LOOP_3_B
    large_amount = random.uniform(50_000, 120_000)
    for i in range(len(nodes)):
        rows.append(make_txn(
            sender   = nodes[i],
            receiver = nodes[(i + 1) % len(nodes)],
            amount   = large_amount * random.uniform(0.6, 1.0),
            ts       = ts + timedelta(minutes=i * random.randint(3, 8)),
            device   = device,
        ))
    # Loop family C
    ts = rand_time(base_ts, 180)
    device = f"{FRAUD_DEVICE_PREFIX}_L3C"
    nodes = LOOP_3_C
    large_amount = random.uniform(60_000, 130_000)
    for i in range(len(nodes)):
        rows.append(make_txn(
            sender   = nodes[i],
            receiver = nodes[(i + 1) % len(nodes)],
            amount   = large_amount * random.uniform(0.6, 1.0),
            ts       = ts + timedelta(minutes=i * random.randint(3, 8)),
            device   = device,
        ))
    return rows


def build_4hop_loop(base_ts: datetime) -> list[dict]:
    """
    Injects one 4-hop mule laundering loop.
    Loop shape:  D1 → D2 → D3 → D4 → D1
    """
    rows = []
    ts = rand_time(base_ts, 200)
    device = f"{FRAUD_DEVICE_PREFIX}_L4"
    nodes = LOOP_4
    large_amount = random.uniform(100_000, 200_000)
    for i in range(len(nodes)):
        rows.append(make_txn(
            sender   = nodes[i],
            receiver = nodes[(i + 1) % len(nodes)],
            amount   = large_amount * random.uniform(0.55, 1.0),
            ts       = ts + timedelta(minutes=i * random.randint(5, 12)),
            device   = device,
        ))
    return rows


def build_smurfing_pattern(base_ts: datetime) -> list[dict]:
    """
    Classic smurfing pattern:
      Phase 1 – Fan-Out: MULE_ORIGIN sends sub-threshold amounts to 8 mule accounts.
      Phase 2 – Fan-In:  All 8 mule accounts funnel to MULE_AGG within minutes.
    A single shared device fingerprint links them all.
    """
    rows = []
    device = f"{FRAUD_DEVICE_PREFIX}_SMURF"
    ts_fanout = rand_time(base_ts, 30)

    # Phase 1: Fan-Out (all within a 10-minute window → triggers velocity check)
    for i, mule in enumerate(SMURF_MULES):
        rows.append(make_txn(
            sender   = SMURF_SOURCE,
            receiver = mule,
            amount   = rand_smurf_amount(),
            ts       = ts_fanout + timedelta(seconds=i * 45),  # rapid-fire
            device   = device,
        ))

    # Phase 2: Fan-In (shortly after fan-out)
    ts_fanin = ts_fanout + timedelta(minutes=random.randint(15, 30))
    for i, mule in enumerate(SMURF_MULES):
        rows.append(make_txn(
            sender   = mule,
            receiver = SMURF_AGGREGATOR,
            amount   = rand_smurf_amount(),
            ts       = ts_fanin + timedelta(seconds=i * 30),
            device   = device,
        ))

    return rows


# ── Normal / noise transactions ───────────────────────────────────────────────
def build_normal_transactions(n: int, base_ts: datetime) -> list[dict]:
    rows = []
    for _ in range(n):
        sender, receiver = random.sample(NORMAL_ACCOUNTS, 2)
        rows.append(make_txn(
            sender   = sender,
            receiver = receiver,
            amount   = rand_normal_amount(),
            ts       = rand_time(base_ts, 2880),
            device   = random.choice(NORMAL_DEVICES),
        ))
    return rows


# ── Assemble & write CSV ──────────────────────────────────────────────────────
def main():
    all_rows: list[dict] = []

    # 1. Inject fraud patterns
    fraud_rows  = (
        build_3hop_loops(BASE_TIME)   # 9 rows (3 loops × 3 edges)
        + build_4hop_loop(BASE_TIME)  # 4 rows
        + build_smurfing_pattern(BASE_TIME)  # 16 rows (8 fan-out + 8 fan-in)
    )
    # Total fraud rows ≈ 29

    # 2. Fill the rest with normal noise to reach exactly 500 rows
    normal_count = TOTAL_ROWS - len(fraud_rows)
    normal_rows  = build_normal_transactions(normal_count, BASE_TIME)

    all_rows = fraud_rows + normal_rows

    # 3. Shuffle so fraud isn't trivially at the top (tests the detection engine)
    random.shuffle(all_rows)

    # 4. Write to CSV
    fieldnames = ["txn_id", "sender_id", "receiver_id",
                  "amount_inr", "timestamp", "device_fingerprint"]
    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    # 5. Print summary
    fraud_nodes_in_csv = set(ALL_FRAUD_NODES)
    print(f"[FinSentinel] [OK]    Generated {len(all_rows)} transactions -> {OUTPUT_PATH}")
    print(f"[FinSentinel] [ALERT] Fraud rows injected   : {len(fraud_rows)}")
    print(f"[FinSentinel] [OK]    Normal rows generated : {len(normal_rows)}")
    print(f"[FinSentinel] [INFO]  Unique fraud nodes    : {len(fraud_nodes_in_csv)}")


if __name__ == "__main__":
    main()
