'use client'

import { List, Zap, Siren, Info, Search, X } from 'lucide-react'

export default function Sidebar({ filterValue, onFilterChange, sortValue, onSortChange, searchValue, onSearchChange, onClose }) {
  const filterOptions = [
    { value: 'all', label: 'Show All', icon: List },
    { value: 'autobuy', label: 'Autobuy', icon: Zap },
    { value: 'alert', label: 'Alert', icon: Siren },
    { value: 'info', label: 'Info', icon: Info },
  ];

  return (
    <div className="w-full h-full bg-primary-bg/50 border-r border-accent-gold/20 p-4 space-y-8">
      <div className="flex justify-between items-center lg:hidden">
        <h2 className="text-pixel text-pixel-lg text-accent-gold">Filters</h2>
        <button onClick={onClose} className="text-primary-text/70 hover:text-accent-gold">
          <X className="w-6 h-6" />
        </button>
      </div>

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
            placeholder="Search..."
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
    </div>
  )
}