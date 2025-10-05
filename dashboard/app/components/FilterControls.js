'use client'

import { List, Zap, Siren, Info } from 'lucide-react'

export default function FilterControls({ filterValue, onFilterChange, sortValue, onSortChange }) {
  const filterOptions = [
    { value: 'all', label: 'Show All', icon: List },
    { value: 'autobuy', label: 'Autobuy', icon: Zap },
    { value: 'alert', label: 'Alert', icon: Siren },
    { value: 'info', label: 'Info', icon: Info },
  ];

  return (
    <div class="w-full max-w-4xl mx-auto mb-8">
      <div class="flex flex-col sm:flex-row gap-4 sm:gap-8">
        {/* Filter Buttons */}
        <div class="flex-1">
          <label class="block text-pixel text-pixel-xs text-accent-gold mb-2">
            Filter by:
          </label>
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {filterOptions.map(({ value, label, icon: Icon }) => (
              <button
                key={value}
                onClick={() => onFilterChange(value)}
                className={`flex items-center justify-center space-x-2 px-4 py-3 rounded-lg text-mono text-base transition-all duration-300 focus-gold ${filterValue === value ? 'bg-accent-gold/20 text-accent-gold border-accent-gold/50' : 'bg-primary-bg/60 text-primary-text/70 border-accent-gold/30 hover:bg-primary-bg/80'}`}>
                <Icon class="w-4 h-4" />
                <span>{label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Sort Dropdown */}
        <div class="flex-1 sm:max-w-xs">
          <label class="block text-pixel text-pixel-xs text-accent-gold mb-2">
            Sort by:
          </label>
          <select
            value={sortValue}
            onChange={(e) => onSortChange(e.target.value)}
            class="w-full px-4 py-3 bg-primary-bg/60 border border-accent-gold/30 rounded-lg
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
    </div>
  )
}