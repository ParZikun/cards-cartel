import Card from './Card'

export default function ListingGrid() {
  // Generate 12 placeholder cards
  const cards = Array.from({ length: 12 }, (_, index) => index + 1)

  return (
    <div className="w-full max-w-7xl mx-auto">
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4 sm:gap-6">
        {cards.map((cardNumber) => (
          <Card key={cardNumber} index={cardNumber} />
        ))}
      </div>
      
      {/* Loading state placeholder */}
      <div className="mt-8 text-center">
        <p className="text-mono text-primary-text/60">
          Showing {cards.length} results
        </p>
      </div>
    </div>
  )
}