'use client';

import { useState } from 'react';
import { Wallet, Menu, X } from 'lucide-react';

export default function Header() {
  const [isWalletConnected, setIsWalletConnected] = useState(false);
  const [walletAddress, setWalletAddress] = useState('');
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const connectWallet = async () => {
    try {
      // Simulate wallet connection
      const mockAddress = '0x' + Math.random().toString(16).substr(2, 40);
      setWalletAddress(mockAddress);
      setIsWalletConnected(true);
    } catch (error) {
      console.error('Failed to connect wallet:', error);
    }
  };

  const disconnectWallet = () => {
    setIsWalletConnected(false);
    setWalletAddress('');
  };

  const formatAddress = (address) => {
    if (!address) return '';
    return `${address.slice(0, 6)}...${address.slice(-4)}`;
  };

  return (
    <header className="bg-primary border-b border-accent/20 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo and Brand */}
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-gradient-to-br from-accent to-accent/70 rounded-lg flex items-center justify-center">
              <span className="text-primary font-pokemon text-lg">⚡</span>
            </div>
            <div>
              <h1 className="text-xl font-pokemon text-accent gold-shimmer">
                CATREL PRO
              </h1>
              <p className="text-xs text-secondary/70 font-gameboy">
                SNIPER BOT
              </p>
            </div>
          </div>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center space-x-6">
            <nav className="flex space-x-4">
              <a href="#" className="text-secondary hover:text-accent transition-colors font-gameboy">
                Dashboard
              </a>
              <a href="#" className="text-secondary hover:text-accent transition-colors font-gameboy">
                Analytics
              </a>
              <a href="#" className="text-secondary hover:text-accent transition-colors font-gameboy">
                Settings
              </a>
            </nav>
            
            {/* Wallet Connect */}
            <div className="flex items-center space-x-2">
              {isWalletConnected ? (
                <div className="flex items-center space-x-2">
                  <div className="px-3 py-1 bg-accent/10 border border-accent/30 rounded-lg">
                    <span className="text-accent font-gameboy text-sm">
                      {formatAddress(walletAddress)}
                    </span>
                  </div>
                  <button
                    onClick={disconnectWallet}
                    className="px-3 py-1 bg-red-500/20 border border-red-500/30 rounded-lg hover:bg-red-500/30 transition-colors"
                  >
                    <span className="text-red-400 font-gameboy text-sm">Disconnect</span>
                  </button>
                </div>
              ) : (
                <button
                  onClick={connectWallet}
                  className="flex items-center space-x-2 px-4 py-2 bg-accent/10 border border-accent/30 rounded-lg hover:bg-accent/20 transition-colors group"
                >
                  <Wallet className="w-4 h-4 text-accent group-hover:scale-110 transition-transform" />
                  <span className="text-accent font-gameboy text-sm">Connect Wallet</span>
                </button>
              )}
            </div>
          </div>

          {/* Mobile menu button */}
          <div className="md:hidden">
            <button
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="text-secondary hover:text-accent transition-colors"
            >
              {isMobileMenuOpen ? (
                <X className="w-6 h-6" />
              ) : (
                <Menu className="w-6 h-6" />
              )}
            </button>
          </div>
        </div>

        {/* Mobile Navigation */}
        {isMobileMenuOpen && (
          <div className="md:hidden border-t border-accent/20 py-4">
            <nav className="flex flex-col space-y-4">
              <a href="#" className="text-secondary hover:text-accent transition-colors font-gameboy">
                Dashboard
              </a>
              <a href="#" className="text-secondary hover:text-accent transition-colors font-gameboy">
                Analytics
              </a>
              <a href="#" className="text-secondary hover:text-accent transition-colors font-gameboy">
                Settings
              </a>
              
              {/* Mobile Wallet Connect */}
              <div className="pt-4 border-t border-accent/20">
                {isWalletConnected ? (
                  <div className="flex flex-col space-y-2">
                    <div className="px-3 py-2 bg-accent/10 border border-accent/30 rounded-lg">
                      <span className="text-accent font-gameboy text-sm">
                        {formatAddress(walletAddress)}
                      </span>
                    </div>
                    <button
                      onClick={disconnectWallet}
                      className="px-3 py-2 bg-red-500/20 border border-red-500/30 rounded-lg hover:bg-red-500/30 transition-colors"
                    >
                      <span className="text-red-400 font-gameboy text-sm">Disconnect</span>
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={connectWallet}
                    className="flex items-center space-x-2 px-4 py-2 bg-accent/10 border border-accent/30 rounded-lg hover:bg-accent/20 transition-colors w-full"
                  >
                    <Wallet className="w-4 h-4 text-accent" />
                    <span className="text-accent font-gameboy text-sm">Connect Wallet</span>
                  </button>
                )}
              </div>
            </nav>
          </div>
        )}
      </div>
    </header>
  );
}