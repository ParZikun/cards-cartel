'use client'

import { Search } from 'lucide-react'
import { useState } from 'react'

export default function SearchBar() {
  const [searchQuery, setSearchQuery] = useState('')

  return (
    <div className="w-full max-w-4xl mx-auto mb-8">
      <div className="relative">
        <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
          <Search className="h-5 w-5 text-accent-gold/60" />
        </div>
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search by name, grading ID, pop..."
          className="w-full pl-12 pr-4 py-4 bg-primary-bg/60 backdrop-blur-sm border border-accent-gold/30 rounded-xl text-secondary-text placeholder-secondary-text/60 font-pixel-secondary text-lg focus:outline-none focus:ring-2 focus:ring-accent-gold/50 focus:border-accent-gold/50 transition-all duration-300 glow-gold"
        />
        <div className="absolute inset-y-0 right-0 pr-4 flex items-center">
          <div className="w-2 h-2 bg-status-green rounded-full animate-pulse"></div>
        </div>
      </div>
    </div>
  )
}