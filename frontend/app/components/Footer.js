'use client';

import { Heart } from 'lucide-react';

export default function Footer() {
  return (
    <footer className="mt-16 py-8 border-t border-white/10">
      <div className="container mx-auto px-4">
        <p className="text-center text-gray-400 font-retro text-lg flex items-center justify-center gap-2">
          <span>Copyright © 2025 | Developed with</span>
          <Heart className="w-5 h-5 text-red-500 fill-red-500" />
          <span>by ParZi</span>
        </p>
      </div>
    </footer>
  );
}