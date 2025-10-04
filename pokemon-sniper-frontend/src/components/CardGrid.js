'use client';

import { useState, useEffect } from 'react';
import Image from 'next/image';

export default function CardGrid({ searchQuery, sortBy, filterType }) {
  const [cards, setCards] = useState([]);
  const [loading, setLoading] = useState(true);

  // Mock data for demonstration - replace with actual API calls
  useEffect(() => {
    const mockCards = [
      {
        id: 1,
        name: 'Charizard',
        image: 'https://images.pokemontcg.io/base1/4_hires.png',
        price: 150.00,
        grade: 'PSA 9',
        rarity: 'gold',
        listingId: 'ME-001',
        timestamp: new Date().toISOString(),
      },
      {
        id: 2,
        name: 'Blastoise',
        image: 'https://images.pokemontcg.io/base1/2_hires.png',
        price: 89.99,
        grade: 'PSA 8',
        rarity: 'blue',
        listingId: 'ME-002',
        timestamp: new Date().toISOString(),
      },
      {
        id: 3,
        name: 'Venusaur',
        image: 'https://images.pokemontcg.io/base1/15_hires.png',
        price: 75.50,
        grade: 'PSA 7',
        rarity: 'red',
        listingId: 'ME-003',
        timestamp: new Date().toISOString(),
      },
      {
        id: 4,
        name: 'Pikachu',
        image: 'https://images.pokemontcg.io/base1/58_hires.png',
        price: 200.00,
        grade: 'PSA 10',
        rarity: 'gold',
        listingId: 'ME-004',
        timestamp: new Date().toISOString(),
      },
      {
        id: 5,
        name: 'Mewtwo',
        image: 'https://images.pokemontcg.io/base1/10_hires.png',
        price: 125.75,
        grade: 'PSA 9',
        rarity: 'blue',
        listingId: 'ME-005',
        timestamp: new Date().toISOString(),
      },
      {
        id: 6,
        name: 'Mew',
        image: 'https://images.pokemontcg.io/base1/101_hires.png',
        price: 300.00,
        grade: 'PSA 10',
        rarity: 'gold',
        listingId: 'ME-006',
        timestamp: new Date().toISOString(),
      },
    ];

    // Simulate API loading
    setTimeout(() => {
      setCards(mockCards);
      setLoading(false);
    }, 1000);
  }, []);

  // Filter and sort cards based on props
  const filteredCards = cards.filter(card => {
    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      const matchesSearch = 
        card.name.toLowerCase().includes(query) ||
        card.grade.toLowerCase().includes(query) ||
        card.listingId.toLowerCase().includes(query) ||
        card.price.toString().includes(query);
      
      if (!matchesSearch) return false;
    }

    // Type filter
    if (filterType !== 'all' && card.rarity !== filterType) {
      return false;
    }

    return true;
  });

  // Sort cards
  const sortedCards = [...filteredCards].sort((a, b) => {
    switch (sortBy) {
      case 'newest':
        return new Date(b.timestamp) - new Date(a.timestamp);
      case 'oldest':
        return new Date(a.timestamp) - new Date(b.timestamp);
      case 'price-low':
        return a.price - b.price;
      case 'price-high':
        return b.price - a.price;
      case 'rarity':
        const rarityOrder = { gold: 3, blue: 2, red: 1 };
        return (rarityOrder[b.rarity] || 0) - (rarityOrder[a.rarity] || 0);
      default:
        return 0;
    }
  });

  const getRarityColor = (rarity) => {
    switch (rarity) {
      case 'gold':
        return 'border-accent bg-accent/10';
      case 'blue':
        return 'border-pokemon-blue bg-pokemon-blue/10';
      case 'red':
        return 'border-pokemon-red bg-pokemon-red/10';
      default:
        return 'border-secondary/30 bg-secondary/10';
    }
  };

  const getRarityTextColor = (rarity) => {
    switch (rarity) {
      case 'gold':
        return 'text-accent';
      case 'blue':
        return 'text-pokemon-blue';
      case 'red':
        return 'text-pokemon-red';
      default:
        return 'text-secondary';
    }
  };

  if (loading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6">
        {[...Array(10)].map((_, index) => (
          <div
            key={index}
            className="bg-primary/30 border border-accent/20 rounded-lg p-4 animate-pulse"
          >
            <div className="aspect-[3/4] bg-secondary/20 rounded-lg mb-4"></div>
            <div className="h-4 bg-secondary/20 rounded mb-2"></div>
            <div className="h-3 bg-secondary/20 rounded w-2/3"></div>
          </div>
        ))}
      </div>
    );
  }

  if (sortedCards.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="text-6xl mb-4">🔍</div>
        <h3 className="text-xl font-pokemon text-secondary mb-2">No Cards Found</h3>
        <p className="text-secondary/70 font-gameboy">
          Try adjusting your search criteria or filters
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Results Count */}
      <div className="text-center">
        <p className="text-secondary/70 font-gameboy">
          Showing {sortedCards.length} card{sortedCards.length !== 1 ? 's' : ''}
        </p>
      </div>

      {/* Card Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6">
        {sortedCards.map((card) => (
          <div
            key={card.id}
            className={`group relative bg-primary/50 border-2 rounded-lg p-4 transition-all duration-300 hover:scale-105 hover:shadow-lg ${getRarityColor(card.rarity)}`}
          >
            {/* Card Image */}
            <div className="aspect-[3/4] relative mb-4 rounded-lg overflow-hidden bg-secondary/10">
              <Image
                src={card.image}
                alt={card.name}
                fill
                className="object-cover group-hover:scale-110 transition-transform duration-300"
                sizes="(max-width: 640px) 100vw, (max-width: 768px) 50vw, (max-width: 1024px) 33vw, (max-width: 1280px) 25vw, 20vw"
              />
              
              {/* Rarity Badge */}
              <div className={`absolute top-2 right-2 px-2 py-1 rounded-full text-xs font-gameboy font-bold ${getRarityColor(card.rarity)} ${getRarityTextColor(card.rarity)}`}>
                {card.rarity.toUpperCase()}
              </div>
            </div>

            {/* Card Info */}
            <div className="space-y-2">
              <h3 className="font-pokemon text-sm text-secondary group-hover:text-accent transition-colors">
                {card.name}
              </h3>
              
              <div className="space-y-1">
                <div className="flex justify-between items-center">
                  <span className="text-xs text-secondary/70 font-gameboy">Grade:</span>
                  <span className="text-xs font-gameboy text-accent">{card.grade}</span>
                </div>
                
                <div className="flex justify-between items-center">
                  <span className="text-xs text-secondary/70 font-gameboy">Price:</span>
                  <span className="text-sm font-gameboy text-accent font-bold">
                    ${card.price.toFixed(2)}
                  </span>
                </div>
                
                <div className="flex justify-between items-center">
                  <span className="text-xs text-secondary/70 font-gameboy">ID:</span>
                  <span className="text-xs font-gameboy text-secondary/80">{card.listingId}</span>
                </div>
              </div>

              {/* Hover Actions */}
              <div className="opacity-0 group-hover:opacity-100 transition-opacity duration-300 pt-2">
                <button className="w-full py-2 bg-accent/20 border border-accent/30 rounded-lg text-accent font-gameboy text-sm hover:bg-accent/30 transition-colors">
                  SNIPE NOW
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}