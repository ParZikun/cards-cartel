# Project Upgrade & Feature Roadmap

This document outlines the plan for significant architectural upgrades and new feature implementations for the Cards Cartel bot.

---

## 1. Architecture & Infrastructure Upgrades

Before adding more complex features, we should strengthen the application's foundation.

### 1.1. Database Migration: SQLite to PostgreSQL

-   **Goal:** Replace the local SQLite database with a robust, production-grade PostgreSQL database.
-   **Why:**
    -   **Scalability:** PostgreSQL can handle many more concurrent connections and larger datasets, which will be essential for the web dashboard and future features.
    -   **Robustness:** It provides better data integrity, transactions, and reliability.
    -   **Professional Standard:** It's the standard for professional web applications.
-   **High-Level Implementation Plan:**
    1.  **Add PostgreSQL Service:** Add a `postgres` service to the `docker-compose.yml` file, including a volume to persist data.
    2.  **Update Dependencies:** Add a database driver library like `psycopg2-binary` to `requirements.txt`.
    3.  **Introduce an ORM (Recommended):** Adopt `SQLAlchemy` to manage database interactions. This makes the code cleaner, more secure, and database-agnostic. It also has powerful migration tools.
    4.  **Schema Migration:** Use `Alembic` (SQLAlchemy's migration tool) to create a script that generates the database schema (tables, columns, etc.) in the new PostgreSQL database.
    5.  **Data Migration:** Create a one-time Python script to read all data from the old `cards.db` SQLite file and insert it into the new PostgreSQL database.

### 1.2. Evolve Backend Architecture

-   **Goal:** Refine the backend architecture to better support a separate web frontend and background workers.
-   **Proposal:** Move towards a more defined Service-Oriented Architecture.
    -   **`Worker Service` (current `bot` container):** Its sole responsibility will be background tasks: watching Magic Eden for new listings, processing items from a queue, and running the reaper/re-analyzer task.
    -   **`Web API Service` (current `api` container):** This will be a dedicated web server (e.g., using FastAPI) that the future Next.js dashboard will communicate with. Its only job is to read data from the PostgreSQL database and present it via API endpoints (e.g., `/api/v1/deals`). It will not contain any scraping or bot logic.
-   **Why:** This separation of concerns makes the system much cleaner, easier to maintain, and allows us to scale the web application and the background worker independently.

### 1.3 Add Certificate to the API so that we can read it officially from https and not http so it is more secure


----

### Rough TODO

- Wallet holdings ?? in dc 
- convert the links to buttons below embed for cc, alt, me, buy
- add token copy button too below embed or grade id copy button
- cant add to many buttons so need to see which ones are imp
- 