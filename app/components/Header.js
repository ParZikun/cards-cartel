'use client'

import { Zap } from 'lucide-react'

export default function Header() {
  return (
    <header className="sticky top-0 z-50 glass border-b border-accent-gold/20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Left side - Logo and Title */}
          <div className="flex items-center space-x-3">
            <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-gradient-to-br from-accent-gold to-yellow-600 glow-gold">
              <Zap className="w-6 h-6 text-primary-bg" />
            </div>
            <h1 className="font-pixel-primary text-lg sm:text-xl text-accent-gold pixel-text">
              Cartel Pro Sniper Bot
            </h1>
          </div>

          {/* Right side - Connect Wallet Button */}
          <button className="px-6 py-2.5 bg-gradient-to-r from-accent-gold to-yellow-600 text-primary-bg font-pixel-secondary text-sm font-bold rounded-lg hover:from-yellow-500 hover:to-accent-gold transition-all duration-300 glow-gold hover:scale-105 transform">
            Connect Wallet
          </button>
        </div>
      </div>
    </header>
  )
}