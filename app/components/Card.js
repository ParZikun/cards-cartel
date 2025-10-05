'use client'

export default function Card({ index }) {
  return (
    <div className="group relative bg-primary-bg/40 backdrop-blur-sm border border-accent-gold/20 rounded-xl overflow-hidden hover:border-accent-gold/50 transition-all duration-300 glow-gold hover:scale-105 transform">
      {/* Card Image */}
      <div className="aspect-[3/4] relative overflow-hidden">
        <img
          src={`https://placehold.co/300x420/0c0a15/FFD700?text=Card+${index + 1}`}
          alt={`NFT Card ${index + 1}`}
          className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500"
        />
        
        {/* Overlay gradient */}
        <div className="absolute inset-0 bg-gradient-to-t from-primary-bg/80 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
        
        {/* Status indicator */}
        <div className="absolute top-3 right-3">
          <div className="w-3 h-3 bg-status-green rounded-full animate-pulse"></div>
        </div>
      </div>

      {/* Card Content */}
      <div className="p-4 space-y-2">
        <div className="flex items-center justify-between">
          <h3 className="font-pixel-secondary text-sm text-secondary-text truncate">
            Card #{index + 1}
          </h3>
          <span className="text-xs text-accent-gold font-pixel-secondary">
            LIVE
          </span>
        </div>
        
        <div className="flex items-center justify-between text-xs">
          <span className="text-secondary-text/60 font-pixel-secondary">
            Price: 0.5 ETH
          </span>
          <span className="text-status-green font-pixel-secondary">
            +12.5%
          </span>
        </div>
      </div>

      {/* Hover glow effect */}
      <div className="absolute inset-0 rounded-xl bg-gradient-to-r from-accent-gold/0 via-accent-gold/5 to-accent-gold/0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none"></div>
    </div>
  )
}