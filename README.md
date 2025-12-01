# Homework1

Progetto per l'esame di **Sistemi Distribuiti e Big Data**.

Il sistema implementa un'architettura a **microservizi dockerizzati** per la registrazione di utenti e il monitoraggio automatizzato del traffico aereo tramite l'API di *OpenSky Network*.

## Architettura del Sistema

Il sistema è composto da 4 container orchestrati tramite Docker Compose:

1.  **User Manager Service** (`user-manager`): Gestisce la registrazione utenti. Implementa logica REST per il client e gRPC Server per la verifica interna.
2.  **Data Collector Service** (`data-collector`): Gestisce la raccolta dati. Implementa uno Scheduler ciclico e agisce come Client gRPC.
3.  **User DB** (`user-db`): Database MySQL per dati anagrafici e log di idempotenza.
4.  **Data DB** (`data-db`): Database MySQL per memorizzare interessi e storico voli.


## Istruzioni per l'Avvio (Deploy)
1.  Avviare il sistema (build automatica):
    ```bash
    docker compose up --build
    ```


>  All'avvio, il Data Collector forza un primo scaricamento dati immediato per dimostrazione, dopodiché prosegue con cicli di 12 ore come da specifiche.

## API  (Documentazione)

### 1. User Manager (Porta 5001)

#### Registrazione Utente (Idempotente)
* **Endpoint:** `POST http://localhost:5001/register`
* **Descrizione:** Registra un utente implementando la politica **At-Most-Once** tramite `request_id`.
* **Body (JSON):**
    ```json
    {
      "email": "giorgia@test.com",
      "first_name": "Giorgia",
      "last_name": "Musumeci",
      "request_id": "req-univoco-001"
    }
    ```

### 2. Data Collector (Porta 5002)

#### Aggiungi Interesse
* **Endpoint:** `POST http://localhost:5002/add_interest`
* **Descrizione:** Aggiunge un aeroporto da monitorare (verifica prima l'utente via gRPC).
* **Body (JSON):**
    ```json
    {
      "email": "giorgia@test.com",
      "airport_code": "KJFK"
    }
    ```

#### Statistiche: Ultimo Volo
* **Endpoint:** `GET /stats/last/<codice_aeroporto>`
* **Esempio:** `http://localhost:5002/stats/last/KJFK`
* **Descrizione:** Restituisce i dati dell'ultimo scaricamento effettuato.

#### Statistiche: Media
* **Endpoint:** `GET /stats/average/<codice_aeroporto>/<giorni>`
* **Esempio:** `http://localhost:5002/stats/average/KJFK/7`
* **Descrizione:** Calcola la media dei voli arrivati negli ultimi X giorni.

