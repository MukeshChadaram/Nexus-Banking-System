from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from neo4j import GraphDatabase
import os

app = FastAPI()

# Connect to Neo4j Container
URI = "bolt://neo4j:7687"
AUTH = ("neo4j", "password123")

class Transaction(BaseModel):
    source: str
    target: str
    amount: float

class BatchRequest(BaseModel):
    transactions: List[Transaction]

@app.post("/detect_laundering")
def detect_laundering(batch: BatchRequest):
    driver = GraphDatabase.driver(URI, auth=AUTH)
    alerts = []
    
    with driver.session() as session:
        # 1. LOAD DATA (Ingest the batch into Neo4j)
        # We use MERGE so we don't create duplicate nodes
        # This query creates the nodes and the relationship (PAYMENT)
        ingest_query = """
        UNWIND $batch as t
        MERGE (a:Account {name: t.source})
        MERGE (b:Account {name: t.target})
        MERGE (a)-[r:PAYMENT {amount: t.amount}]->(b)
        """
        # Convert Pydantic models to dicts for Neo4j
        tx_data = [t.dict() for t in batch.transactions]
        session.run(ingest_query, batch=tx_data)

        # 2. DETECT CYCLES (The "Match" Query)
        # This one line replaces your entire NetworkX logic.
        # It looks for a path of 2 to 4 hops that returns to start.
        cycle_query = """
        MATCH path = (n)-[:PAYMENT*2..4]->(n)
        RETURN nodes(path) as entities, relationships(path) as txs
        """
        result = session.run(cycle_query)
        
        for record in result:
            entities = [node["name"] for node in record["entities"]]
            alerts.append(f"Money Laundering Cycle Detected: {entities}")

        # 3. CLEANUP (Optional for this demo, usually you keep history)
        # session.run("MATCH (n) DETACH DELETE n")

    driver.close()
    
    return {"status": "SUSPICIOUS" if alerts else "CLEAN", "alerts": alerts}