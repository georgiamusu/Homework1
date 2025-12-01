FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Espone solo la porta REST (non ha server gRPC, è un client)
EXPOSE 5002

CMD ["python", "-u", "app.py"]