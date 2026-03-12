# Lightweight Streamlit image
FROM python:3.11-slim

WORKDIR /app

# Install requirements
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code and data
COPY src/ ./src/
COPY Data/ ./Data/

EXPOSE 8501

CMD ["streamlit", "run", "src/app.py", "--server.port=8501", "--server.address=0.0.0.0"]