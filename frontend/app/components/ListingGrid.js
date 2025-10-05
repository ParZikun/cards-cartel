'use client';

import Card from './Card';

export default function ListingGrid() {
  // Create 12 placeholder cards
  const cardCount = 12;
  const cards = Array.from({ length: cardCount }, (_, i) => i);

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4 md:gap-6">
      {cards.map((index) => (
        <Card key={index} index={index} />
      ))}
    </div>
  );
}