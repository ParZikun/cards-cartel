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

## 📋 To-Do List & Known Issues

This section tracks the current bugs and planned improvements for the bot.

-   [ ] Implement a more sophisticated back-off strategy for when external APIs (Magic Eden, ALT) are down for extended periods. (Non priority)
-   [ ] Add a command-line argument to force a full re-population of the database.  (Non priority)
-   [ ] Implement the `AUTOBUY` logic when a `GOLD` tier snipe is detected.
-   [ ] Also set up alerts, monitoring and analytics n shit on azure too  (After V1 is complete)
-   [ ] do we need to gib alerts on the dashboard
-   [x] WalletConnect for autobuy and a slider for setting priority and fees for aping quickly 
-   [ ] wallet connection and add priority fees n other fees jitto stuff that is adjustable near the sort filter btns on the side bar
-   [ ] implement instant buy on click 🔥 just one confirmation which can be disable using a checkbox which will be placed near the jitto priority fees section
-   [ ] need to give one more section to show Wallet cards holdings rn
-   [ ] can giv option for autobuy on certain conditions like if price below this n meets this conditions yhen autosnipe, sset the condition from the side bar and and the bot will remember to autosnipe for us 
-   [ ] Notifications alerts on web



-   [ ] Dollar Sign on the price which is in USDC
-   [ ] add the logo, align header, change the connect wallet btn design
-   [ ] edit the sidebar make it look good
-   [ ] make the new card and also make them resposive
-   [ ] Shift live n status update on the sidebar below the logo
-   [ ] remove the keyframes fro the background the hexagon pattern is enough texture 
-   [ ] Add a btn on the side bar that loads the wallet/ ME profile cards that we have in it 

# Project Roadmap

Here is a breakdown of the planned features, separated into backend and frontend tasks.

---

### Backend Development

These tasks involve the server-side logic, database management, API interactions, and the core bot functionality.

| Task                                     | Complexity | Notes                                                                                                                                                                                          |
| :--------------------------------------- | :--------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Implement `AUTOBUY` Logic**            | **High**   | This is a critical and complex task. It requires secure wallet integration, transaction signing, and robust error handling to prevent loss of funds.                                             |
| **Conditional Auto-snipe Rules**         | **High**   | Involves creating a system for users to define complex conditions (e.g., price, traits). The backend must persistently store these rules and have an efficient engine to evaluate them against real-time market data. |
| **Wallet Connection & Transactions**     | **High**   | The backend needs to securely handle wallet connections passed from the frontend, manage keys (or sessions), and execute transactions for buying. This includes calculating and adding priority fees (Jito). |
| **Sophisticated API Back-off Strategy**  | **Medium** | Implementing an exponential back-off or circuit breaker pattern to handle external API downtime gracefully. This improves bot stability.                                                      |
| **Azure Monitoring & Analytics**         | **Medium** | Setting up logging, monitoring, and alerts on Azure. The complexity can grow depending on how deep the analytics requirements are.                                                              |
| **Web Notifications Service**            | **Medium** | Requires a backend service (e.g., using WebSockets) to push real-time alerts (like successful snipes) to the web frontend.                                                                       |
| **Endpoint for Wallet Holdings**         | **Low-Medium** | Creating a new API endpoint that can query the blockchain for the assets held by a connected wallet and serve that data to the frontend.                                                        |
| **Force DB Re-population Argument**      | **Low**    | Adding a command-line flag to trigger a full database refresh. This is useful for development and maintenance.                                                                                 |

---

### Frontend Development

These tasks involve the user interface and user experience on the web dashboard.

| Task                             | Complexity | Notes                                                                                                                                        |
| :------------------------------- | :--------- | :------------------------------------------------------------------------------------------------------------------------------------------- |
| **Wallet Connection UI**         | **High**   | Implementing the UI and logic for connecting a user's wallet (e.g., via WalletConnect). This is the entry point for all wallet-related features. |
| **"Instant Buy" Button & Logic** | **Medium** | Creating the UI for a one-click buy button, including a confirmation modal and a checkbox to disable it. This will trigger the backend autobuy logic. |
| **UI for Conditional Auto-snipe**| **Medium** | Designing and building a form or section in the sidebar where users can set and save their auto-snipe conditions (e.g., price, traits).      |
| **Display Wallet Holdings**      | **Medium** | Creating a new section or component in the UI to display the user's current NFT holdings fetched from the new backend endpoint.                |
| **Priority Fee Controls**        | **Low-Medium** | Adding a slider or input fields in the sidebar for users to set their desired priority fees for transactions.                                |
| **Web Notifications Display**    | **Low-Medium** | Implementing the client-side logic to receive and display real-time notifications sent from the backend.                                     |

---
---

Based on your README.md and the API documentation, here are the high-priority backend tasks and their relation to the Magic Eden API:

AUTOBUY Logic (High Complexity): This is the core feature where the Magic Eden API is essential. The API provides an /instructions/buy endpoint. Your bot would call this endpoint with the token mint address, price, and buyer's wallet address. The API then returns the necessary transaction instructions.

Wallet Connection & Transactions (High Complexity): You are correct. A library like WalletConnect or another Solana-specific wallet adapter would handle the frontend UI for connecting the user's wallet. However, the transaction part is where the Magic Eden API comes back in. The AUTOBUY instructions generated by the API need to be signed by the user's wallet and submitted to the Solana network.

Conditional Auto-snipe Rules (High Complexity): This is primarily application logic you'll build. The Magic Eden API's /collections/{symbol}/listings endpoint provides the real-time data feed that your rules engine will process. When a listing meets your conditions, it will then trigger the AUTOBUY logic.

Regarding Your Concerns:
Auto-Buy Speed: This is a valid concern. The speed of an auto-buy depends on two things:

API Response Time: How fast the Magic Eden API gives you the transaction instructions. This is usually very fast.
Blockchain Confirmation Time: How fast your transaction is processed on the Solana network. This is the real bottleneck. To be competitive, you need to pay a priority fee. Your README.md mentions "Jito," which is exactly the right path. You would construct a transaction that includes both the buy instruction from the Magic Eden API and an additional instruction to pay a priority fee via Jito's block engine. The Magic Eden API won't handle the priority fee for you, but its instructions are compatible with being included in a transaction that does.
Wallet Holdings: Yes, the /wallets/{wallet_address}/tokens endpoint will give you the list of tokens a wallet holds.

In short, the Magic Eden API provides the crucial data (/listings) and transaction instructions (/instructions/buy) for your high-priority features. Your backend will be responsible for the logic, and for adding priority fees to the transaction to ensure speed.

What would be your next step? I can help you start scaffolding the Python code for the AUTOBUY logic.