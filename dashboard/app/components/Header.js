'use client'

import { Zap, Wallet } from 'lucide-react'

export default function Header() {
  return (
    <header className="sticky top-0 z-50 glass border-b border-accent-gold/20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo and Title */}
          <div className="flex items-center space-x-4">
            <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-accent-gold/10 border border-accent-gold/30">
              <Zap className="w-6 h-6 text-accent-gold" />
            </div>
            <h1 className="text-pixel text-pixel-sm sm:text-pixel-base text-accent-gold">
              Cartel Pro Sniper Bot
            </h1>
          </div>

          {/* Connect Wallet Button */}
          <button className="btn-primary px-4 py-2 rounded-lg text-pixel text-pixel-xs sm:text-pixel-sm flex items-center space-x-2 focus-gold">
            <Wallet className="w-4 h-4" />
            <span className="hidden sm:inline">Connect Wallet</span>
            <span className="sm:hidden">Connect</span>
          </button>
        </div>
      </div>
    </header>
  )
}