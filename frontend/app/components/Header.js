'use client';

import { Crosshair } from 'lucide-react';

export default function Header() {
  return (
    <header className="sticky top-0 z-50 glass-effect backdrop-blur-lg border-b border-white/10 mb-8">
      <div className="container mx-auto px-4 py-4">
        <div className="flex flex-col md:flex-row justify-between items-center gap-4">
          {/* Left Side - Logo and Title */}
          <div className="flex items-center gap-4">
            <Crosshair className="w-8 h-8 text-primary-gold" />
            <h1 className="font-pixel text-base md:text-lg text-white leading-relaxed">
              Cartel Pro Sniper Bot
            </h1>
          </div>

          {/* Right Side - Connect Wallet Button */}
          <button className="px-6 py-3 bg-transparent border-2 border-primary-gold text-primary-gold font-retro text-lg font-bold rounded-lg transition-all duration-300 hover:bg-primary-gold hover:text-primary-bg hover:shadow-lg hover:shadow-primary-gold/50">
            Connect Wallet
          </button>
        </div>
      </div>
    </header>
  );
}