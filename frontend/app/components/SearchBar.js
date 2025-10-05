'use client';

import { Search } from 'lucide-react';

export default function SearchBar() {
  return (
    <div className="w-full mb-6 glass-effect rounded-lg p-4">
      <div className="flex items-center gap-4">
        <Search className="w-6 h-6 text-gray-400 flex-shrink-0" />
        <input
          type="text"
          placeholder="Search by name, grading ID, pop..."
          className="w-full bg-transparent text-white placeholder-gray-500 font-retro text-lg focus:outline-none focus:ring-2 focus:ring-primary-gold/50 rounded px-2 py-1"
        />
      </div>
    </div>
  );
}