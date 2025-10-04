'use client';

import { useState } from 'react';
import { Search, Filter, SortAsc } from 'lucide-react';
import CardGrid from '@/components/CardGrid';

export default function Home() {
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState('newest');
  const [filterType, setFilterType] = useState('all');

  const sortOptions = [
    { value: 'newest', label: 'Newest First' },
    { value: 'oldest', label: 'Oldest First' },
    { value: 'price-low', label: 'Price: Low to High' },
    { value: 'price-high', label: 'Price: High to Low' },
    { value: 'rarity', label: 'Rarity' },
  ];

  const filterOptions = [
    { value: 'all', label: 'All Cards', color: 'text-secondary' },
    { value: 'blue', label: 'Blue Cards', color: 'text-pokemon-blue' },
    { value: 'red', label: 'Red Cards', color: 'text-pokemon-red' },
    { value: 'gold', label: 'Gold Cards', color: 'text-accent' },
  ];

  return (
    <div className="min-h-screen bg-primary dark-gradient">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Hero Section */}
        <div className="text-center mb-12">
          <h1 className="text-4xl md:text-6xl font-pokemon text-accent gold-shimmer mb-4">
            POKÉMON CARD SNIPER
          </h1>
          <p className="text-lg text-secondary/80 font-gameboy max-w-2xl mx-auto">
            Find the best deals on Pokémon cards with our advanced sniper bot. 
            Real-time monitoring, instant alerts, and lightning-fast transactions.
          </p>
        </div>

        {/* Search Bar */}
        <div className="mb-8">
          <div className="relative max-w-4xl mx-auto">
            <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
              <Search className="h-5 w-5 text-secondary/50" />
            </div>
            <input
              type="text"
              placeholder="Search by name, grading ID, grade, or any card details..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-12 pr-4 py-4 bg-primary/50 border border-accent/30 rounded-lg text-secondary placeholder-secondary/50 font-gameboy focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent/50 transition-all"
            />
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-4 mb-8">
          {/* Sort Dropdown */}
          <div className="flex-1">
            <div className="relative">
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="w-full pl-4 pr-10 py-3 bg-primary/50 border border-accent/30 rounded-lg text-secondary font-gameboy focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent/50 transition-all appearance-none"
              >
                {sortOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                <SortAsc className="h-4 w-4 text-secondary/50" />
              </div>
            </div>
          </div>

          {/* Filter Dropdown */}
          <div className="flex-1">
            <div className="relative">
              <select
                value={filterType}
                onChange={(e) => setFilterType(e.target.value)}
                className="w-full pl-4 pr-10 py-3 bg-primary/50 border border-accent/30 rounded-lg text-secondary font-gameboy focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent/50 transition-all appearance-none"
              >
                {filterOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                <Filter className="h-4 w-4 text-secondary/50" />
              </div>
            </div>
          </div>
        </div>

        {/* Active Filters Display */}
        <div className="mb-6">
          <div className="flex flex-wrap gap-2">
            {searchQuery && (
              <span className="px-3 py-1 bg-accent/20 border border-accent/30 rounded-full text-accent font-gameboy text-sm">
                Search: "{searchQuery}"
              </span>
            )}
            <span className="px-3 py-1 bg-secondary/20 border border-secondary/30 rounded-full text-secondary font-gameboy text-sm">
              Sort: {sortOptions.find(opt => opt.value === sortBy)?.label}
            </span>
            <span className={`px-3 py-1 border rounded-full font-gameboy text-sm ${
              filterType === 'all' 
                ? 'bg-secondary/20 border-secondary/30 text-secondary'
                : filterType === 'gold'
                ? 'bg-accent/20 border-accent/30 text-accent'
                : filterType === 'blue'
                ? 'bg-pokemon-blue/20 border-pokemon-blue/30 text-pokemon-blue'
                : 'bg-pokemon-red/20 border-pokemon-red/30 text-pokemon-red'
            }`}>
              Filter: {filterOptions.find(opt => opt.value === filterType)?.label}
            </span>
          </div>
        </div>

        {/* Card Grid */}
        <CardGrid 
          searchQuery={searchQuery}
          sortBy={sortBy}
          filterType={filterType}
        />
      </div>
    </div>
  );
}
