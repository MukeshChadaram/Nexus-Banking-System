FROM python:3.9-slim
WORKDIR /app
# Swap networkx for neo4j driver
RUN pip install fastapi uvicorn neo4j 
COPY main.py .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]