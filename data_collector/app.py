import time
import os
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_apscheduler import APScheduler
import mysql.connector
import grpc

from db import get_db_connection, init_db
from opensky_client import get_arrivals_count  # <--- NUOVO IMPORT
import user_service_pb2
import user_service_pb2_grpc

app = Flask(__name__)

# CLIENT gRPC
def check_user_exists_grpc(email):
    target = os.getenv('USER_MANAGER_HOST', 'user-manager:50051')
    try:
        with grpc.insecure_channel(target) as channel:
            stub = user_service_pb2_grpc.UserManagerStub(channel)
            request = user_service_pb2.UserRequest(email=email)
            response = stub.CheckUserExists(request)
            return response.exists
    except grpc.RpcError as e:
        print(f" Errore gRPC: {e}")
        return False

# SCHEDULER (Logica di Business)
def job_scarica_voli():
    print(f" [{datetime.now()}] Scheduler attivo: aggiornamento dati...")
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 1. Recupera lista aeroporti da monitorare
        cursor.execute("SELECT DISTINCT airport_code FROM interests")
        rows = cursor.fetchall()
        airports = [row['airport_code'] for row in rows]

        if not airports:
            print("   Nessun interesse trovato nel DB.")
            return

        # 2. Per ogni aeroporto
        for code in airports:
            count, error = get_arrivals_count(code)

            if error:
                print(f" Saltato {code}: {error}")
                continue # Passa al prossimo

            print(f"  {code}: trovati {count} voli. Salvataggio...")

            # 3. Salva nel DB
            cursor.execute("""
                INSERT INTO flight_data (airport_code, query_time, arrivals_count, departures_count)
                VALUES (%s, %s, %s, %s)
            """, (code, datetime.now(), count, 0))
            conn.commit()

    except Exception as e:
        print(f" Errore generale nello scheduler: {e}")
    finally:
        if conn and conn.is_connected(): conn.close()

# --- API REST ---

@app.route('/add_interest', methods=['POST'])
def add_interest():
    data = request.json
    email = data.get('email')
    airport = data.get('airport_code')

    if not email or not airport:
        return jsonify({"error": "Dati mancanti"}), 400

    # 1. Verifica Utente (gRPC)
    if not check_user_exists_grpc(email):
        return jsonify({"error": "Utente non trovato"}), 404

    # 2. Salva Interesse (MySQL)
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT 1 FROM interests WHERE user_email=%s AND airport_code=%s", (email, airport))
        if cursor.fetchone():
            return jsonify({"message": "Interesse già presente"}), 200

        cursor.execute("INSERT INTO interests (user_email, airport_code) VALUES (%s, %s)", (email, airport))
        conn.commit()
        return jsonify({"message": f"Interesse aggiunto: {airport}"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

@app.route('/stats/last/<code>', methods=['GET'])
def get_last_stats(code):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT * FROM flight_data 
            WHERE airport_code = %s 
            ORDER BY query_time DESC LIMIT 1
        """, (code,))
        row = cursor.fetchone()
        if row:
            return jsonify(row), 200
        return jsonify({"message": "Nessun dato ancora scaricato"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

@app.route('/stats/average/<code>/<int:days>', methods=['GET'])
def get_average_stats(code, days):
    """
    Calcola la media dei voli (arrivi) negli ultimi X giorni.
    Requisito: "Calcolo della Media degli ultimi X giorni"
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Calcoliamo la data limite (oggi - X giorni)
        cutoff_date = datetime.now() - timedelta(days=days)

        # Query SQL Pura per fare la media
        cursor.execute("""
            SELECT AVG(arrivals_count) as media
            FROM flight_data 
            WHERE airport_code = %s AND query_time >= %s
        """, (code, cutoff_date))

        result = cursor.fetchone()

        # Se non ci sono dati, la media è None
        media = result['media'] if result and result['media'] is not None else 0.0

        return jsonify({
            "airport": code,
            "days_analyzed": days,
            "average_arrivals": float(round(media, 2)) # Arrotondiamo a 2 decimali
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

# --- AVVIO ---
"""if __name__ == '__main__':
    init_db()

    # Configura Scheduler
    scheduler = APScheduler()
    scheduler.init_app(app)
    scheduler.start()

    # Esegue ogni 15 minuti (900 secondi)
    scheduler.add_job(id='fetch_flights', func=job_scarica_voli, trigger='interval', seconds=900)

    print("Data Collector attivo sulla porta 5002")
    app.run(host='0.0.0.0', port=5002, debug=False) """

# ...

# --- AVVIO ---
if __name__ == '__main__':
    init_db()

    # Configura e avvia scheduler
    scheduler = APScheduler()
    scheduler.init_app(app)
    scheduler.start()

    # MODIFICA QUI: Imposta l'intervallo a 12 ore (come da specifiche PDF)
    scheduler.add_job(id='fetch_flights', func=job_scarica_voli, trigger='interval', hours=12)

    # IMPORTANTE: Lascia questa riga!
    # Serve per scaricare i dati SUBITO appena accendi il container.
    # Così il prof vede che funziona, poi il sistema si mette a dormire per 12 ore.
    print("🚀 Forzo scaricamento dati all'avvio (Demo Mode)...", flush=True)
    job_scarica_voli()

    print("✅ Data Collector attivo sulla porta 5002")
    app.run(host='0.0.0.0', port=5002, debug=False)