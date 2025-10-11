'use client'

import { Wallet, Menu } from 'lucide-react'
import Image from 'next/image'
import WalletButton from './WalletButton'

export default function Header({ apiStatus, lastUpdated, onMenuClick }) {
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
      <div className="flex items-center justify-between h-20 px-4 sm:px-6 lg:px-8">
        {/* Logo and Title */}
        <div className="flex items-center space-x-4">
          <button className="lg:hidden text-primary-text/80 hover:text-accent-gold" onClick={onMenuClick}>
            <Menu className="w-7 h-7" />
          </button>
          <div className="flex items-center justify-center w-12 h-12 rounded-lg bg-accent-gold/10 border border-accent-gold/30">
            <Image src="/logo.png" alt="CCP-S Logo" width={28} height={28} />
          </div>
          <div className="pokemon-title">
            <h1 className="pokemon-title-solid font-pokemon text-3xl text-accent-gold">
              CCP-S
            </h1>
            <h1 className="pokemon-title-outline font-pokemon-hollow text-3xl">
              CCP-S
            </h1>
          </div>
        </div>

        {/* Status and Wallet Button */}
        <div className="flex items-center space-x-4">
          <div className="hidden sm:flex items-center space-x-2">
            <div className="flex items-center gap-2">
              {statusIndicator()}
              <span className="text-base text-primary-text/70">{apiStatus === 'live' ? 'Live' : apiStatus === 'error' ? 'Error' : 'Loading...'}</span>
            </div>
            <div className="text-base text-primary-text/70">
              Last Update: {lastUpdated ? lastUpdated.toLocaleTimeString() : '...'}
            </div>
          </div>
          {/* <button className="btn-primary px-4 py-2 rounded-lg flex items-center space-x-2 focus-gold text-sm sm:text-base">
            <Wallet className="w-4 h-4" />
            <span className="hidden sm:inline">Connect Wallet</span>
            <span className="sm:hidden">Connect</span>
          </button> */}
          <WalletButton />
        </div>
      </div>
    </header>
  )
}