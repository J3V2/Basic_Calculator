FROM python:3.11-slim

WORKDIR /app

# copy only needed files
COPY requirements.txt .
RUN python -m pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# use a production WSGI server
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "api.app:app", "--workers", "2", "--threads", "4", "--timeout", "30"]
