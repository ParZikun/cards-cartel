'use client'

import { useState } from 'react'

export default function FilterControls() {
  const [filter, setFilter] = useState('all')
  const [sort, setSort] = useState('listed-time')

  return (
    <div className="w-full max-w-4xl mx-auto mb-8">
      <div className="flex flex-col sm:flex-row gap-4 sm:gap-8">
        {/* Filter Dropdown */}
        <div className="flex-1">
          <label className="block text-pixel text-pixel-xs text-accent-gold mb-2">
            Filter by:
          </label>
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="w-full px-4 py-3 bg-primary-bg/60 border border-accent-gold/30 rounded-lg
                     text-mono text-base text-primary-text focus-gold
                     focus:border-accent-gold focus:bg-primary-bg/80 transition-all duration-300"
          >
            <option value="all">Show All</option>
            <option value="autobuy">Autobuy (Gold)</option>
            <option value="alert">Alert (Red)</option>
            <option value="info">Info (Blue)</option>
          </select>
        </div>

        {/* Sort Dropdown */}
        <div className="flex-1">
          <label className="block text-pixel text-pixel-xs text-accent-gold mb-2">
            Sort by:
          </label>
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value)}
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
    </div>
  )
}