# 🃏 Cards Cartel

## Description

Cards Cartel is a tool for monitoring and purchasing NFT card listings from the Magic Eden marketplace. It includes a web dashboard to view listings and wallet holdings.

## Architecture

The project is composed of three main parts:

-   **Frontend:** A Next.js and React application located in the `dashboard` directory. It provides the user interface for viewing listings and wallet holdings.
-   **Backend API:** A Python Flask application in the `api` directory. It serves listing data from a database and proxies requests to the Magic Eden API.
-   **Bot:** A Python script in the `bot` directory that continuously scrapes Magic Eden for new listings, enriches them with external data, and stores them in a local SQLite database.

## Working

1.  The **Bot** runs continuously, finds new card listings on Magic Eden, and saves them to a local SQLite database (`data/listings.db`).
2.  The **Frontend** (Next.js app) makes API calls to its own backend (`/api/...`).
3.  These frontend API routes proxy the requests to the **Backend API** (Python/Flask), adding an API key for security.
4.  The **Backend API** serves listing data from the SQLite database and forwards wallet-related requests to the Magic Eden API.
5.  The user can view listings, connect their Solana wallet, and see their own card holdings in the web dashboard.

## TODO

-   **[TODO] Database Concurrency:** The use of SQLite for the listings database might lead to "database is locked" errors if the bot and the API try to access it at the same time. This is a potential scalability issue. For a production environment, consider migrating to a more robust database like PostgreSQL.
