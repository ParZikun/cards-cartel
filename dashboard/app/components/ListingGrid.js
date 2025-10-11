'use client'

import Card from './Card'

export default function ListingGrid({ listings, loading, error, solPriceUSD }) {

  if (loading) {
    return (
        <div className="text-center p-12">
            <p className="text-lg mt-4 text-gray-400">Connecting to live API...</p>
        </div>
    )
  }

  if (error) {
    return (
        <div className="card-glass p-4 rounded-lg border-red-500/50" role="alert">
             <div className="flex items-center">
                <div>
                    <strong className="font-bold text-red-300">API Connection Error!</strong>
                    <span className="block sm:inline text-red-400">{error}</span>
                </div>
            </div>
        </div>
    )
  }

  return (
    <div className="w-full max-w-7xl mx-auto">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-6">
        {listings.map((listing, index) => (
          <Card key={listing.listing_id} listing={listing} solPriceUSD={solPriceUSD} priority={index < 5} />
        ))}
      </div>
      
      <div className="mt-8 text-center">
        <p className="text-mono text-primary-text/60">
          Showing {listings.length} results
        </p>
      </div>
    </div>
  )
}
