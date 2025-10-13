'use client'

let cachedSolPrice = 0.0;
let lastFetchTime = 0;
const CACHE_DURATION_SECONDS = 300; // 5 minutes

async function fetchSolToUsdcPrice() {
  const url = "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd";
  try {
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return data.solana.usd;
  } catch (error) {
    console.error("Could not fetch SOL price from CoinGecko:", error);
    return null;
  }
}

export async function getSolPriceUsd() {
  const currentTime = Date.now() / 1000; // in seconds

  if (cachedSolPrice === 0.0 || (currentTime - lastFetchTime) > CACHE_DURATION_SECONDS) {
    console.log("Price cache is stale or empty. Fetching new SOL price...");
    const newPrice = await fetchSolToUsdcPrice();
    if (newPrice !== null) {
      cachedSolPrice = newPrice;
      lastFetchTime = currentTime;
      console.log(`New SOL price cached: ${cachedSolPrice.toFixed(2)}`);
    } else {
      console.warn("WARN: Failed to fetch new price. Using previous cached value (if available).");
    }
  }

  return cachedSolPrice;
}
