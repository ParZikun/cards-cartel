'use client';

export default function Card({ index }) {
  return (
    <div className="glass-effect card-glow rounded-xl overflow-hidden aspect-[3/4] flex items-center justify-center border border-white/10 hover:border-primary-gold/50 transition-all duration-300">
      <img
        src={`https://placehold.co/300x420/0c0a15/2d3748?text=Card+${index + 1}`}
        alt={`Card ${index + 1}`}
        className="w-full h-full object-cover"
      />
    </div>
  );
}