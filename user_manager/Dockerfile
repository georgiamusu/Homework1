FROM python:3.9-slim

WORKDIR /app

# Copia le dipendenze e installa
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia tutto il codice
COPY . .

# Espone le porte (REST + gRPC)
EXPOSE 5001 50051

# Avvia l'app in modalità senza buffer (-u)
CMD ["python", "-u", "app.py"]