FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --index-url http://pypi.org/simple/ -r requirements.txt

COPY . .

EXPOSE 8002

ENV PYTHONPATH=/app

CMD ["python", "http_api/main.py"]
