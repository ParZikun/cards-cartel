import { Heart } from 'lucide-react'

export default function Footer() {
  return (
    <footer className="mt-auto border-t border-accent-gold/20 bg-primary-bg/80">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="text-center">
          <p className="text-mono text-sm text-primary-text/70 flex items-center justify-center space-x-2">
            <span>Copyright © 2025 | Developed with</span>
            <Heart className="w-4 h-4 text-status-alert fill-current" />
            <span>by ParZi</span>
          </p>
        </div>
      </div>
    </footer>
  )
}