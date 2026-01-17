from mcp.server.fastmcp import FastMCP
import requests
import psycopg2
import sys  # Import sys to log to stderr correctly

# Initialize
mcp = FastMCP("Nexus-Compliance-Agent")

# Config
ENGINE_URL = "http://localhost:8081/detect_laundering"
DB_CONFIG = {
    "host": "localhost",
    "port": "5432",
    "database": "nexus_bank",
    "user": "admin",
    "password": "password123"
}

# --- 1. Initialize the Freeze Table on Startup ---
def init_db():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        # Create a simple table to track frozen users
        cur.execute("""
            CREATE TABLE IF NOT EXISTS frozen_accounts (
                account_name VARCHAR(255) PRIMARY KEY,
                frozen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reason TEXT
            )
        """)
        conn.commit()
        conn.close()
        # FIX: We write to sys.stderr so we don't break the MCP JSON protocol
        print("✅ Security Database initialized.", file=sys.stderr)
    except Exception as e:
        print(f"⚠️ Warning: Could not init DB: {e}", file=sys.stderr)

init_db()

# --- EXISTING TOOLS ---

@mcp.tool()
def query_ledger(sql_query: str) -> str:
    """Read-only access to the transaction ledger."""
    # Safety: Block dangerous keywords
    if any(x in sql_query.upper() for x in ["DROP", "DELETE", "UPDATE", "INSERT"]):
        return "ERROR: You are an Analyst. You cannot modify the Ledger directly."

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute(sql_query)
        columns = [desc[0] for desc in cur.description]
        results = cur.fetchall()
        conn.close()
        
        if not results:
            return "No records found."
            
        output = f"Columns: {columns}\n"
        for row in results:
            output += str(row) + "\n"
        return output
    except Exception as e:
        return f"Database Error: {str(e)}"

@mcp.tool()
def scan_for_laundering_loops(target_account: str = None) -> str:
    """Triggers the AI Engine to scan for circular money flows."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT source, target, amount FROM transactions ORDER BY id DESC LIMIT 200")
        rows = cur.fetchall()
        conn.close()
        
        payload = {"transactions": [{"source": r[0], "target": r[1], "amount": float(r[2])} for r in rows]}
        response = requests.post(ENGINE_URL, json=payload)
        result = response.json()
        
        if result["status"] == "CLEAN":
            return "✅ Compliance Check Passed."
        
        report = f"🚨 ALERT: {len(result['alerts'])} laundering cycles detected.\n"
        for alert in result['alerts']:
            report += f"- {alert}\n"
        return report
    except Exception as e:
        return f"Engine Error: {str(e)}"

# --- 2. NEW TOOL: THE ACTION ---

@mcp.tool()
def freeze_account(account_name: str, reason: str) -> str:
    """
    LOCKS a bank account to prevent further activity. 
    Use this ONLY when high-confidence fraud is detected.
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Check if already frozen
        cur.execute("SELECT account_name FROM frozen_accounts WHERE account_name = %s", (account_name,))
        if cur.fetchone():
            return f"ℹ️ Account '{account_name}' is ALREADY frozen."

        # Execute Freeze
        cur.execute(
            "INSERT INTO frozen_accounts (account_name, reason) VALUES (%s, %s)",
            (account_name, reason)
        )
        conn.commit()
        conn.close()
        
        return f"🔒 SUCCESS: Account '{account_name}' has been FROZEN. Reason logged: {reason}"

    except Exception as e:
        return f"❌ Failed to freeze account: {str(e)}"

if __name__ == "__main__":
    mcp.run()