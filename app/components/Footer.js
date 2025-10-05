import { Heart } from 'lucide-react'

export default function Footer() {
  return (
    <footer className="mt-auto glass border-t border-accent-gold/20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="flex items-center justify-center space-x-2 text-secondary-text/80 font-pixel-secondary text-sm">
          <span>Copyright © 2025 | Developed with</span>
          <Heart className="w-4 h-4 text-status-red fill-current" />
          <span>by ParZi</span>
        </div>
      </div>
    </footer>
  )
}