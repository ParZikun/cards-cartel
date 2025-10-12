'use client'

import HoldingCard from './HoldingCard';
import { useWallet } from '@solana/wallet-adapter-react';

export default function HoldingsGrid({ holdings, loading, error, solPriceUSD }) {
  const { connected } = useWallet();

  if (!connected) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center">
        <h2 className="text-2xl font-bold text-accent-gold mb-4">Please connect your wallet</h2>
        <p className="text-primary-text/70">Connect your wallet to view your token holdings.</p>
      </div>
    );
  }

  if (loading) {
    return <div className="text-center">Loading holdings...</div>;
  }

  if (error) {
    return <div className="text-center text-red-400">Error: {error}</div>;
  }

  if (!holdings || holdings.length === 0) {
    return <div className="text-center">No holdings found for this wallet.</div>;
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
      {holdings.map((holding, index) => (
        <HoldingCard key={index} holding={holding} solPriceUSD={solPriceUSD} />
      ))}
    </div>
  );
}

