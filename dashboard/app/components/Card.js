import Image from 'next/image'

export default function Card({ index = 1 }) {
  return (
    <div className="card-glow rounded-lg overflow-hidden bg-primary-bg/40 aspect-[3/4] group">
      <div className="relative w-full h-full">
        <Image
          src={`https://placehold.co/300x420.png`}
          alt={`Placeholder card ${index}`}
          fill
          className="object-cover transition-transform duration-300 group-hover:scale-105"
          sizes="(max-width: 768px) 50vw, (max-width: 1024px) 33vw, 25vw"
        />
        
        {/* Overlay gradient for better text readability */}
        <div className="absolute inset-0 bg-gradient-to-t from-primary-bg/80 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
        
        {/* Card number indicator */}
        <div className="absolute top-2 right-2 bg-accent-gold/20 backdrop-blur-sm rounded px-2 py-1">
          <span className="text-pixel text-pixel-xs text-accent-gold">#{index}</span>
        </div>
      </div>
    </div>
  )
}