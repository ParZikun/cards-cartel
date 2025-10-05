'use client'

import { useState } from 'react'

export default function FilterControls() {
  const [filterValue, setFilterValue] = useState('all')
  const [sortValue, setSortValue] = useState('listed-time')

  return (
    <div className="w-full max-w-4xl mx-auto mb-8">
      <div className="flex flex-col sm:flex-row gap-4 sm:gap-6">
        {/* Filter Dropdown */}
        <div className="flex-1">
          <label className="block text-sm font-pixel-secondary text-accent-gold mb-2">
            Filter by:
          </label>
          <select
            value={filterValue}
            onChange={(e) => setFilterValue(e.target.value)}
            className="w-full px-4 py-3 bg-primary-bg/60 backdrop-blur-sm border border-accent-gold/30 rounded-lg text-secondary-text font-pixel-secondary text-base focus:outline-none focus:ring-2 focus:ring-accent-gold/50 focus:border-accent-gold/50 transition-all duration-300 glow-gold appearance-none cursor-pointer"
          >
            <option value="all" className="bg-primary-bg text-secondary-text">Show All</option>
            <option value="autobuy" className="bg-primary-bg text-secondary-text">Autobuy (Gold)</option>
            <option value="alert" className="bg-primary-bg text-secondary-text">Alert (Red)</option>
            <option value="info" className="bg-primary-bg text-secondary-text">Info (Blue)</option>
          </select>
        </div>

        {/* Sort Dropdown */}
        <div className="flex-1">
          <label className="block text-sm font-pixel-secondary text-accent-gold mb-2">
            Sort by:
          </label>
          <select
            value={sortValue}
            onChange={(e) => setSortValue(e.target.value)}
            className="w-full px-4 py-3 bg-primary-bg/60 backdrop-blur-sm border border-accent-gold/30 rounded-lg text-secondary-text font-pixel-secondary text-base focus:outline-none focus:ring-2 focus:ring-accent-gold/50 focus:border-accent-gold/50 transition-all duration-300 glow-gold appearance-none cursor-pointer"
          >
            <option value="listed-time" className="bg-primary-bg text-secondary-text">Listed Time</option>
            <option value="price" className="bg-primary-bg text-secondary-text">Price</option>
            <option value="difference" className="bg-primary-bg text-secondary-text">Difference %</option>
            <option value="rarity" className="bg-primary-bg text-secondary-text">Rarity</option>
          </select>
        </div>
      </div>
    </div>
  )
}