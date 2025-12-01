import os
import time
import requests

# --- CONFIGURAZIONE DEI COLLEGHI (OAUTH2) ---
TOKEN_URL = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"
CLIENT_ID = os.getenv("OPEN_SKY_CLIENT_ID")
CLIENT_SECRET = os.getenv("OPEN_SKY_CLIENT_SECRET")

# Variabili globali per la cache del token
CACHED_TOKEN = None
TOKEN_EXPIRATION_TIME = 0

def is_token_expired():
    """Controlla se il token è scaduto o sta per scadere (margine 60s)"""
    return CACHED_TOKEN is None or time.time() >= (TOKEN_EXPIRATION_TIME - 60)

def get_opensky_token():
    """Richiede un nuovo token al server OpenSky"""
    if not CLIENT_ID or not CLIENT_SECRET:
        print("⚠️ CLIENT_ID o CLIENT_SECRET mancanti. Usare Basic Auth o controllare .env")
        return None

    payload = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }

    try:
        print("🔄 Richiesta rinnovo Token OpenSky...")
        response = requests.post(
            TOKEN_URL,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10
        )
        response.raise_for_status()
        return response.json()

    except requests.RequestException as e:
        print(f"❌ Errore richiesta token: {e}")
        return None

def get_token():
    """Restituisce un token valido (aggiornandolo se necessario)"""
    global CACHED_TOKEN, TOKEN_EXPIRATION_TIME

    if is_token_expired():
        token_data = get_opensky_token()
        if token_data and 'access_token' in token_data:
            CACHED_TOKEN = token_data['access_token']
            # Imposta scadenza (default 1800s = 30 min)
            TOKEN_EXPIRATION_TIME = time.time() + token_data.get('expires_in', 1800)
            print("✅ Token OpenSky aggiornato con successo!")
        else:
            print("⚠️ Impossibile ottenere il token.")
            return None

    return CACHED_TOKEN

# --- FUNZIONE SCARICAMENTO VOLI (Modificata per usare il Token) ---

def get_arrivals_count(airport_code):
    """
    Scarica i voli usando il Token OAuth2 invece di User/Pass.
    """
    end_time = int(time.time())
    begin_time = end_time - 3600 # Ultima ora

    url = "https://opensky-network.org/api/flights/arrival"
    params = {
        'airport': airport_code,
        'begin': begin_time,
        'end': end_time
    }

    # 1. Recuperiamo il token valido
    token = get_token()

    # 2. Prepariamo l'Header di autorizzazione
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    else:
        print("⚠️ Nessun token disponibile, provo senza autenticazione (rischio 429).")

    print(f"   📡 Chiamata OpenSky (OAuth) per {airport_code}...")

    try:
        # Nota: passiamo 'headers' invece di 'auth'
        response = requests.get(url, params=params, headers=headers, timeout=10)

        if response.status_code == 200:
            flights = response.json()
            return len(flights), None

        elif response.status_code == 404:
            return 0, None # Nessun volo trovato

        elif response.status_code == 429:
            return -1, "Troppe richieste (429)"

        else:
            return -1, f"Errore API: {response.status_code}"

    except requests.exceptions.RequestException as e:
        return -1, f"Errore rete: {e}"