'use client'

import { Search } from 'lucide-react'

export default function SearchBar({ value, onChange }) {

  return (
    <div className="w-full max-w-4xl mx-auto mb-8">
      <div className="relative">
        <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
          <Search className="h-5 w-5 text-accent-gold/70" />
        </div>
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-full pl-12 pr-4 py-4 bg-primary-bg/60 border border-accent-gold/30 rounded-lg 
                   text-mono text-lg placeholder-primary-text/50 focus-gold
                   focus:border-accent-gold focus:bg-primary-bg/80 transition-all duration-300"
          placeholder="Search by name, grading ID, pop..."
        />
      </div>
    </div>
  )
}