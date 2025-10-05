'use client'

import { Zap, Wallet } from 'lucide-react'

export default function Header({ apiStatus, lastUpdated }) {
  const statusIndicator = () => {
    switch (apiStatus) {
      case 'live':
        return <span className="w-3 h-3 rounded-full bg-green-400 animate-pulse"></span>;
      case 'error':
        return <span className="w-3 h-3 rounded-full bg-red-500"></span>;
      default:
        return <span className="w-3 h-3 rounded-full bg-yellow-500 animate-pulse"></span>;
    }
  }

  return (
    <header className="sticky top-0 z-50 glass border-b border-accent-gold/20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-20">
          {/* Logo and Title */}
          <div className="flex items-center space-x-4">
            <div className="flex items-center justify-center w-12 h-12 rounded-lg bg-accent-gold/10 border border-accent-gold/30">
              <Zap className="w-7 h-7 text-accent-gold" />
            </div>
            <h1 className="text-pixel text-pixel-base sm:text-pixel-lg text-accent-gold">
              Cartel Pro Sniper Bot
            </h1>
          </div>

          {/* Status and Wallet Button */}
          <div className="flex items-center space-x-4">
            <div className="hidden sm:flex items-center space-x-2">
              <div className="flex items-center gap-2">
                {statusIndicator()}
                <span className="text-sm text-primary-text/70">{apiStatus === 'live' ? 'Live' : apiStatus === 'error' ? 'Error' : 'Loading...'}</span>
              </div>
              <div className="text-sm text-primary-text/70">
                Last Update: {lastUpdated ? lastUpdated.toLocaleTimeString() : '...'}
              </div>
            </div>
            <button className="btn-primary px-4 py-2 rounded-lg text-pixel text-pixel-xs sm:text-pixel-sm flex items-center space-x-2 focus-gold">
              <Wallet className="w-4 h-4" />
              <span class="hidden sm:inline">Connect Wallet</span>
              <span class="sm:hidden">Connect</span>
            </button>
          </div>
        </div>
      </div>
    </header>
  )
}