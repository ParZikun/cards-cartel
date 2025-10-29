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

---

## 2. New Discord Bot Features

These features can be tested on Discord before being implemented in the web dashboard.

### 2.3. Feature: Full Database Re-check (`/recheck_all`)

-   **Goal:** Create a command to manually trigger a re-analysis of all currently listed items in the database to find new snipes from old listings.
-   **Implementation Plan:**
    1.  **Create Slash Command:** In `discord_bot.py`, define a new admin-only slash command (e.g., `/recheck_all`).
    2.  **Database Query:** The command handler will fetch all listings from the database where `is_listed = TRUE`.
    3.  **Background Task:** To avoid blocking the bot, it will spawn a new background task.
    4.  **Re-process Loop:** This background task will loop through the list of active listings. For each listing, it will call the `process_listing` function (the same one used by the watchdog). A small `await asyncio.sleep(1)` should be added between each call to avoid API rate-limiting.
    5.  **User Feedback:** The bot should send an initial response like "✅ Starting a re-check of all X active listings. This may take some time." and potentially a final message upon completion.

### 2.4. Enhancement: Automated Re-checking Service - COMPLETED

-   **Note:** The user's idea for a background re-checking service is excellent. This can be an enhancement of the existing `reaper` task.
-   **Proposal:**
    -   The `reaper` task currently checks if a listing has been *delisted*.
    -   We can enhance its logic: if a listing is still active but hasn't been re-analyzed in over 24 hours (we would need to add a `last_analyzed_at` timestamp to the database), the reaper can trigger the `process_listing` function for it.
    -   This would automate the process of finding new snipes in old listings, fully realizing the goal of Feature 2.3 without manual intervention.

### 2.5 Add a command to check a particular card and pull its latest details based on the mint tokn address