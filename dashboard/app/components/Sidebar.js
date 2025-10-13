'use client'

import { List, Zap, Siren, Info, Search, X, LayoutGrid, Wallet } from 'lucide-react';
import { useTransaction } from '../context/TransactionContext';

export default function Sidebar({ 
  filterValue, onFilterChange, 
  sortValue, onSortChange, 
  searchValue, onSearchChange, 
  onClose, 
  view, setView 
}) {
  const { priorityFee, setPriorityFee, slippage, setSlippage } = useTransaction();

  const filterOptions = [
    { value: 'all', label: 'Show All', icon: List },
    { value: 'autobuy', label: 'Autobuy', icon: Zap },
    { value: 'alert', label: 'Alert', icon: Siren },
    { value: 'info', label: 'Info', icon: Info },
  ];

  // Estimate the total fee in SOL for display purposes
  const microlamportsToSol = (microlamports) => {
    const ESTIMATED_COMPUTE_UNITS = 400000; // A rough estimate for a ME buy transaction
    const lamports = (ESTIMATED_COMPUTE_UNITS * microlamports) / 1000000;
    return lamports / 1_000_000_000; // 1 SOL = 1,000,000,000 lamports
  };

  return (
    <div className="w-full h-full bg-primary-bg/50 border-r border-accent-gold/20 p-4 space-y-8">
      <div className="flex justify-between items-center">
        <h2 className="text-pixel text-pixel-lg text-accent-gold">Menu</h2>
        <button onClick={onClose} className="text-primary-text/70 hover:text-accent-gold lg:hidden">
          <X className="w-6 h-6" />
        </button>
      </div>

      {/* View Navigation */}
      <div className="grid grid-cols-2 gap-2">
        <button
          onClick={() => setView('listings')}
          className={`flex items-center justify-center space-x-2 px-4 py-3 rounded-lg text-mono text-base transition-all duration-300 focus-gold ${view === 'listings' ? 'bg-accent-gold/20 text-accent-gold border-accent-gold/50' : 'bg-primary-bg/60 text-primary-text/70 border-accent-gold/30 hover:bg-primary-bg/80'}`}>
          <LayoutGrid className="w-4 h-4" />
          <span>Listings</span>
        </button>
        <button
          onClick={() => setView('holdings')}
          className={`flex items-center justify-center space-x-2 px-4 py-3 rounded-lg text-mono text-base transition-all duration-300 focus-gold ${view === 'holdings' ? 'bg-accent-gold/20 text-accent-gold border-accent-gold/50' : 'bg-primary-bg/60 text-primary-text/70 border-accent-gold/30 hover:bg-primary-bg/80'}`}>
          <Wallet className="w-4 h-4" />
          <span>Holdings</span>
        </button>
      </div>

      {view === 'listings' && (
        <div className="space-y-8 pt-8 border-t border-accent-gold/20">
          {/* Search Bar */}
          <div>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                <Search className="h-5 w-5 text-accent-gold/70" />
              </div>
              <input
                type="text"
                value={searchValue}
                onChange={(e) => onSearchChange(e.target.value)}
                className="w-full pl-12 pr-4 py-4 bg-primary-bg/60 border border-accent-gold/30 rounded-lg 
                         text-mono text-lg placeholder-primary-text/50 focus-gold
                         focus:border-accent-gold focus:bg-primary-bg/80 transition-all duration-300"
                placeholder="Search Listings..."
              />
            </div>
          </div>

          {/* Filter Buttons */}
          <div>
            <label className="block text-pixel text-pixel-xs text-accent-gold mb-2">
              Filter by:
            </label>
            <div className="grid grid-cols-2 gap-2">
              {filterOptions.map(({ value, label, icon: Icon }) => (
                <button
                  key={value}
                  onClick={() => onFilterChange(value)}
                  className={`flex items-center justify-center space-x-2 px-4 py-3 rounded-lg text-mono text-base transition-all duration-300 focus-gold ${filterValue === value ? 'bg-accent-gold/20 text-accent-gold border-accent-gold/50' : 'bg-primary-bg/60 text-primary-text/70 border-accent-gold/30 hover:bg-primary-bg/80'}`}>
                  <Icon className="w-4 h-4" />
                  <span>{label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Sort Dropdown */}
          <div>
            <label className="block text-pixel text-pixel-xs text-accent-gold mb-2">
              Sort by:
            </label>
            <select
              value={sortValue}
              onChange={(e) => onSortChange(e.target.value)}
              className="w-full px-4 py-3 bg-primary-bg/60 border border-accent-gold/30 rounded-lg
                       text-mono text-base text-primary-text focus-gold
                       focus:border-accent-gold focus:bg-primary-bg/80 transition-all duration-300"
            >
              <option value="listed-time">Listed Time</option>
              <option value="price-low">Price (Low to High)</option>
              <option value="price-high">Price (High to Low)</option>
              <option value="difference-percent">Difference %</option>
              <option value="popularity">Popularity</option>
            </select>
          </div>

          {/* Transaction Settings */}
          <div className="space-y-8 pt-8 border-t border-accent-gold/20">
            <h3 className="text-pixel text-pixel-md text-accent-gold">Transaction Settings</h3>
            
            {/* Priority Fee Slider */}
            <div>
              <label htmlFor="priority-fee" className="block text-pixel text-pixel-xs text-accent-gold mb-2">
                Priority Fee (SOL)
              </label>
              <div className="flex items-center space-x-4">
                <input
                  id="priority-fee"
                  type="range"
                  min="0"
                  max="1000000"
                  step="10000"
                  value={priorityFee}
                  onChange={(e) => setPriorityFee(Number(e.target.value))}
                  className="w-full h-2 bg-primary-bg/80 rounded-lg appearance-none cursor-pointer 
                           focus-gold range-thumb-gold"
                />
                <span className="text-mono text-sm text-primary-text w-24 text-right">
                  {(priorityFee / 1000000).toFixed(4)} SOL
                </span>
              </div>
            </div>

            {/* Slippage Input */}
            <div>
              <label htmlFor="slippage" className="block text-pixel text-pixel-xs text-accent-gold mb-2">
                Slippage
              </label>
              <div className="relative">
                <input
                  id="slippage"
                  type="number"
                  step="0.1"
                  value={slippage}
                  onChange={(e) => setSlippage(Number(e.target.value))}
                  className="w-full pl-4 pr-12 py-3 bg-primary-bg/60 border border-accent-gold/30 rounded-lg 
                           text-mono text-base placeholder-primary-text/50 focus-gold
                           focus:border-accent-gold focus:bg-primary-bg/80 transition-all duration-300"
                />
                <div className="absolute inset-y-0 right-0 pr-4 flex items-center pointer-events-none">
                  <span className="text-accent-gold/70">%</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}