import streamlit as st
import psycopg2
import requests
import pandas as pd
import graphviz
import os
import random
import shutil

# --- CONFIGURATION ---
DB_HOST = os.getenv("DB_HOST", "db")
DB_PASS = os.getenv("DB_PASS", "password123")

def get_db_connection():
    return psycopg2.connect(host=DB_HOST, database="nexus_bank", user="admin", password=DB_PASS)

# --- GENERATOR ---
def populate_data(n=50): # <--- REDUCED DEFAULT TO 50 FOR SPEED
    conn = get_db_connection()
    cur = conn.cursor()
    # Force clear the table
    cur.execute("TRUNCATE TABLE transactions RESTART IDENTITY")
    
    legit_users = [f"User_{i}" for i in range(1, 20)]
    bad_actors = ["Cartel_Ops", "Shell_Alpha", "Shell_Beta", "Clean_Co"]
    transactions = []
    
    for _ in range(n):
        if random.random() < 0.1: # 10% Crime
            # Create a loop: A -> B -> C -> A
            amt = random.randint(10000, 50000)
            transactions.append((bad_actors[0], bad_actors[1], amt))
            transactions.append((bad_actors[1], bad_actors[2], amt - 500))
            transactions.append((bad_actors[2], bad_actors[0], amt - 1000))
        else:
            src = random.choice(legit_users)
            tgt = random.choice(legit_users)
            transactions.append((src, tgt, random.randint(10, 500)))

    args_str = ','.join(cur.mogrify("(%s,%s,%s)", x).decode('utf-8') for x in transactions)
    cur.execute("INSERT INTO transactions (source, target, amount) VALUES " + args_str)
    conn.commit()
    conn.close()
    return len(transactions)

st.set_page_config(layout="wide", page_title="Nexus BaaS")
st.title("🏦 Nexus Banking System (Debug Mode)")

# --- DIAGNOSTICS CHECK ---
if shutil.which("dot") is None:
    st.error("❌ CRITICAL ERROR: Graphviz is not installed.")
    st.info("Stop the container and run: docker-compose up --build")
    st.stop() # Stop execution here

# --- TABS ---
tab1, tab2 = st.tabs(["⚡ Generator", "🕵️‍♂️ Compliance Officer"])

with tab1:
    st.write("Click below to clear DB and add fresh data.")
    # Reduce count to 50 to prevent Engine Timeout during math calculation
    if st.button("Generate 50 Transactions"):
        with st.spinner("Injecting data..."):
            count = populate_data(50) 
        st.success(f"Database Reset. Current Count: {count}")

with tab2:
    if st.button("🔄 Sync & Scan Ledger"):
        status_box = st.empty()
        
        try:
            # 1. FETCH DATA
            status_box.info("Step 1: Fetching data from Postgres...")
            conn = get_db_connection()
            # LIMIT limit to 100 to prevent browser crash
            df = pd.read_sql("SELECT * FROM transactions ORDER BY id DESC LIMIT 100", conn)
            conn.close()
            st.dataframe(df.head(5))

            # 2. CALL ENGINE
            status_box.info("Step 2: Sending data to AI Engine (Calculating cycles)...")
            payload = {"transactions": df[['source', 'target', 'amount']].to_dict(orient='records')}
            response = requests.post("http://aml-engine:80/detect_laundering", json=payload, timeout=5) # 5s timeout
            result = response.json()

            # 3. RENDER GRAPH
            status_box.info("Step 3: Rendering Network Graph...")
            
            # Show Alerts
            if result['status'] == "SUSPICIOUS":
                st.error(f"🚨 FOUND {len(result['alerts'])} RISKS")
                for a in result['alerts']:
                    st.write(f"- {a}")
            else:
                st.success("✅ Clean Ledger")

            # Draw Graph
            graph = graphviz.Digraph()
            graph.attr(rankdir='LR')
            for _, row in df.iterrows():
                color = "red" if "Cartel" in row['source'] or "Shell" in row['source'] else "black"
                graph.edge(row['source'], row['target'], color=color)
            
            st.graphviz_chart(graph)
            status_box.success("Processing Complete!")

        except requests.exceptions.Timeout:
            status_box.error("❌ The Engine timed out! (Too many transactions to analyze at once)")
        except Exception as e:
            status_box.error(f"❌ Error: {e}")