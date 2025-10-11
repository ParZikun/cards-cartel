# 🃏 Cards Cartel Sniper

Cards Cartel is a high-speed, automated monitoring tool designed to "snipe" undervalued Pokémon card listings from the Magic Eden marketplace. It operates by continuously fetching the latest listings, enriching them with real-time valuation data from ALT.XYZ, and sending instant alerts to a Discord channel for potentially profitable deals.

The primary goal is to create a robust, 24/7 pipeline that can be deployed on a cloud server (like AWS) for continuous, unattended operation.

---

## ✨ Features

-   **High-Speed Monitoring:** Checks for new Magic Eden listings every 0.6 seconds.
-   **Intelligent Filtering:** Filters for specific grading companies (PSA, BGS) and blacklists irrelevant keywords.
-   **Data Enrichment:** Pulls real-time valuation, population count (supply), and market data from ALT.XYZ for accurate price comparison.
-   **Price Conversion:** Uses a cached price feed from CoinGecko to convert SOL prices to USDC for consistent value comparison.
-   **Configurable Snipe Logic:** Business logic is easily adjustable to define what constitutes a "good deal" (e.g., listed at 15%, 20%, or 30% below market value).
-   **Instant Discord Alerts:** Sends richly formatted, detailed alerts to a designated Discord channel, with role-pinging for high-priority snipes.
-   **Persistent State:** Uses a local SQLite database to track processed listings, ensuring it doesn't re-process items after a restart.
-   **Robust & Resilient:** Designed with comprehensive error handling, API call retries, and self-healing loops to withstand network issues and run reliably for long periods.

---

## 🛠️ Tech Stack

-   **Language:** Python 3.10+
-   **Core Libraries:**
    -   `asyncio` for high-performance, non-blocking I/O.
    -   `requests` for synchronous API calls in threaded executors.
    -   `discord.py` for Discord bot integration.
    -   `PyYAML` for configuration management.
-   **Database:** `sqlite3` for lightweight, local data persistence.

---

## ⚙️ Setup and Installation

1.  **Clone the Repository:**
    ```bash
    git clone <your-repo-url>
    cd cards-cartel-sniper
    ```

2.  **Create a Virtual Environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install Dependencies:**
    Create a `requirements.txt` file with the following content:
    ```
    requests
    discord.py
    python-dotenv
    PyYAML
    pytz
    ```
    Then, install them:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables:**
    Create a `.env` file in the root directory and populate it with your API keys and IDs. **Never commit this file to Git.**
    ```env
    # ALT.XYZ API Credentials
    AUTH_TOKEN="your_alt_auth_token"
    COOKIE="your_alt_cookie_string"

    # Discord Bot Configuration
    DISCORD_BOT_TOKEN="your_discord_bot_token"
    DISCORD_CHANNEL_ID="your_target_channel_id"
    DISCORD_ROLE_ID="role_id_to_ping_on_high_alert"
    ```

5.  **Configure Logging:**
    The `logging_config.yaml` file controls the log output. You can adjust the log levels (`INFO`, `DEBUG`, `ERROR`) as needed.

---

## 🚀 Running the Bot

Once the setup is complete, you can start the sniper bot with a single command:

```bash
python main.py
```

The bot will first check if the database exists. If not, it will perform a one-time "initial population" to fetch and process the 100 most recent listings. Afterward, it will start the high-speed watchdog to monitor for new listings.

---

## 📋 Project Roadmap

A prioritized list of features and tasks for the Cards Cartel project.

---

### 🤖 Backend TODO

| Priority | Task                                       | Description                                                                                             |
| :------- | :----------------------------------------- | :------------------------------------------------------------------------------------------------------ |
| **High** | `[ ]` Implement Core `AUTOBUY` Logic       | Securely handle transaction signing and submission for purchasing cards.                                |
| **High** | `[ ]` Develop Conditional Auto-Snipe Engine| Create a system to store and evaluate user-defined snipe conditions against real-time market data.      |
| **Medium** | `[ ]` Create API for Wallet Holdings       | Develop an endpoint to query and return the NFTs held by a user's wallet.                               |
| **Medium** | `[ ]` Real-time Alert Service              | Implement a WebSocket to push notifications (e.g., successful snipes) to the frontend.                  |
| **Medium** | `[ ]` Implement API Back-off Strategy      | Implement an exponential back-off/circuit breaker pattern for external API calls to improve stability.  |
| **Low**    | `[ ]` Setup Azure Monitoring & Analytics   | Set up basic logging and monitoring on Azure for the deployed application.                              |
| **Low**    | `[ ]` Add DB Re-population Argument        | Add a command-line flag to force a full database refresh for maintenance.                               |

---

### 🎨 Frontend TODO

| Priority | Task                                 | Description                                                                                             |
| :------- | :----------------------------------- | :------------------------------------------------------------------------------------------------------ |
| **High** | `[ ]` Implement Card Detail Modal      | Create a responsive modal that appears on card click to show detailed information.                      |
| **High** | `[ ]` Fetch & Display Live Card Data   | Connect the main grid to the backend API to show real listings instead of placeholder data.             |
| **High** | `[ ]` Implement "Instant Buy" UI       | Add a "Buy" button to the card detail modal, including a confirmation step.                             |
| **Medium** | `[ ]` Display Wallet Holdings          | Create a new UI section/page to display the user's NFT holdings fetched from the backend.               |
| **Medium** | `[ ]` Create UI for Auto-Snipe Rules   | Design a form in the sidebar for users to set and save their auto-snipe conditions.                     |
| **Medium** | `[ ]` Add Priority Fee Controls        | Add UI elements (e.g., a slider) in the sidebar for setting transaction priority fees.                  |
| **Low**    | `[ ]` Implement Web Notifications      | Add logic to receive and display real-time alerts from the backend.                                     |
| **Low**    | `[ ]` General UI/UX Cleanup            | A collection of smaller tasks to improve the look and feel of the dashboard.                            |
|          | `[ ]` Add logo and align header        |                                                                                                         |
|          | `[ ]` Improve sidebar design           |                                                                                                         |
|          | `[ ]` Add `# 🃏 Cards Cartel Sniper

Cards Cartel is a high-speed, automated monitoring tool designed to "snipe" undervalued Pokémon card listings from the Magic Eden marketplace. It operates by continuously fetching the latest listings, enriching them with real-time valuation data from ALT.XYZ, and sending instant alerts to a Discord channel for potentially profitable deals.

The primary goal is to create a robust, 24/7 pipeline that can be deployed on a cloud server (like AWS) for continuous, unattended operation.

---

## ✨ Features

-   **High-Speed Monitoring:** Checks for new Magic Eden listings every 0.6 seconds.
-   **Intelligent Filtering:** Filters for specific grading companies (PSA, BGS) and blacklists irrelevant keywords.
-   **Data Enrichment:** Pulls real-time valuation, population count (supply), and market data from ALT.XYZ for accurate price comparison.
-   **Price Conversion:** Uses a cached price feed from CoinGecko to convert SOL prices to USDC for consistent value comparison.
-   **Configurable Snipe Logic:** Business logic is easily adjustable to define what constitutes a "good deal" (e.g., listed at 15%, 20%, or 30% below market value).
-   **Instant Discord Alerts:** Sends richly formatted, detailed alerts to a designated Discord channel, with role-pinging for high-priority snipes.
-   **Persistent State:** Uses a local SQLite database to track processed listings, ensuring it doesn't re-process items after a restart.
-   **Robust & Resilient:** Designed with comprehensive error handling, API call retries, and self-healing loops to withstand network issues and run reliably for long periods.

---

## 🛠️ Tech Stack

-   **Language:** Python 3.10+
-   **Core Libraries:**
    -   `asyncio` for high-performance, non-blocking I/O.
    -   `requests` for synchronous API calls in threaded executors.
    -   `discord.py` for Discord bot integration.
    -   `PyYAML` for configuration management.
-   **Database:** `sqlite3` for lightweight, local data persistence.

---

## ⚙️ Setup and Installation

1.  **Clone the Repository:**
    ```bash
    git clone <your-repo-url>
    cd cards-cartel-sniper
    ```

2.  **Create a Virtual Environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install Dependencies:**
    Create a `requirements.txt` file with the following content:
    ```
    requests
    discord.py
    python-dotenv
    PyYAML
    pytz
    ```
    Then, install them:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables:**
    Create a `.env` file in the root directory and populate it with your API keys and IDs. **Never commit this file to Git.**
    ```env
    # ALT.XYZ API Credentials
    AUTH_TOKEN="your_alt_auth_token"
    COOKIE="your_alt_cookie_string"

    # Discord Bot Configuration
    DISCORD_BOT_TOKEN="your_discord_bot_token"
    DISCORD_CHANNEL_ID="your_target_channel_id"
    DISCORD_ROLE_ID="role_id_to_ping_on_high_alert"
    ```

5.  **Configure Logging:**
    The `logging_config.yaml` file controls the log output. You can adjust the log levels (`INFO`, `DEBUG`, `ERROR`) as needed.

---

## 🚀 Running the Bot

Once the setup is complete, you can start the sniper bot with a single command:

```bash
python main.py
```

The bot will first check if the database exists. If not, it will perform a one-time "initial population" to fetch and process the 100 most recent listings. Afterward, it will start the high-speed watchdog to monitor for new listings.

---

 to USDC prices           |                                                                                                         |
|          | `[ ]` Relocate "Live Status" indicator |                                                                                                         |
|          | `[ ]` Remove background animation      |                                                                                                         |