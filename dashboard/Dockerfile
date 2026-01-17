FROM python:3.9-slim
WORKDIR /app
# Install system tools for Graphviz and Postgres
RUN apt-get update && apt-get install -y graphviz libpq-dev gcc && rm -rf /var/lib/apt/lists/*
RUN pip install streamlit requests graphviz pandas psycopg2-binary
COPY app.py .
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]