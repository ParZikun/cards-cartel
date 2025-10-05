import Card from './Card'

export default function ListingGrid() {
  // Generate 12 placeholder cards
  const cards = Array.from({ length: 12 }, (_, index) => index)

  return (
    <div className="w-full max-w-7xl mx-auto">
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-6">
        {cards.map((index) => (
          <Card key={index} index={index} />
        ))}
      </div>
      
      {/* Loading indicator */}
      <div className="mt-12 flex justify-center">
        <div className="flex items-center space-x-2 text-secondary-text/60 font-pixel-secondary text-sm">
          <div className="w-2 h-2 bg-accent-gold rounded-full animate-pulse"></div>
          <div className="w-2 h-2 bg-accent-gold rounded-full animate-pulse" style={{ animationDelay: '0.2s' }}></div>
          <div className="w-2 h-2 bg-accent-gold rounded-full animate-pulse" style={{ animationDelay: '0.4s' }}></div>
          <span className="ml-3">Loading more listings...</span>
        </div>
      </div>
    </div>
  )
}