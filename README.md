# Cards Cartel - Backend Service

This directory contains the Python FastAPI backend and the Worker service for Cards Cartel.

## Structure

- `src/api`: FastAPI application handling:
    - User Authentication (SIWS)
    - User Settings (Encrypted)
    - Data Fetching (Deals, Holdings, Manual Buy Transaction Creation)
- `src/worker`: Background worker (not fully integrated here yet, mostly separate scripts or `process_listing` logic).
- `src/database`: Database models and connection logic (`Listing`, `User`, `UserSettings`).

## Setup

1.  **Environment Variables**:
    Ensure `.env` exists in `src/api` or root.
    ```env
    POSTGRES_USER=...
    POSTGRES_PASSWORD=...
    POSTGRES_DB=cards_cartel
    MAGIC_EDEN_API_KEY=...
    SECRET_KEY=... (for encryption/JWT)
    ```

2.  **Install Dependencies**:
    ```bash
    pip install -r src/api/requirements.txt
    ```

## Running the API

Use the `Makefile` in the root of this directory:

```bash
# Run locally (Port 5000)
make local-api

# Check logs
make local-logs
```

## Key Endpoints

-   `POST /api/auth/login`: Sign-In with Solana.
-   `GET /api/get-listings`: Fetch active deals.
-   `POST /api/buy/create-tx`: Generate a Buy Transaction for the frontend.
-   `GET /api/user/settings/{wallet}`: Fetch encrypted settings.
