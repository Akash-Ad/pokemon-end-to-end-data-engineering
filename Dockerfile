FROM python:3.10-slim

# 1) Set working directory inside conatiner
WORKDIR /app

# 2) Avoid .pyc files, get unbuffered logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# 3) Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4) Copy project files from the host machine into the container
COPY  . .

# 5) Streamlit runs on 8501 by default
EXPOSE 8501

# 6) Command that runs when the container starts
CMD ["streamlit", "run", "UI/streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501"]