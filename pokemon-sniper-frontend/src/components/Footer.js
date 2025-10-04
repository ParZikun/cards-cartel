export default function Footer() {
  return (
    <footer className="bg-primary border-t border-accent/20 mt-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="flex flex-col md:flex-row justify-between items-center space-y-4 md:space-y-0">
          <div className="text-center md:text-left">
            <p className="text-secondary/70 font-gameboy text-sm">
              © 2024 Catrel Pro Sniper Bot. All rights reserved.
            </p>
          </div>
          
          <div className="text-center md:text-right">
            <p className="text-secondary/70 font-gameboy text-sm">
              Developed with <span className="text-red-500">♥</span> by{' '}
              <span className="text-accent font-pokemon">ParZi</span>
            </p>
          </div>
        </div>
        
        <div className="mt-4 pt-4 border-t border-accent/10">
          <div className="flex flex-wrap justify-center md:justify-between items-center space-y-2 md:space-y-0">
            <div className="flex space-x-6">
              <a href="#" className="text-secondary/70 hover:text-accent transition-colors font-gameboy text-sm">
                Privacy Policy
              </a>
              <a href="#" className="text-secondary/70 hover:text-accent transition-colors font-gameboy text-sm">
                Terms of Service
              </a>
              <a href="#" className="text-secondary/70 hover:text-accent transition-colors font-gameboy text-sm">
                Support
              </a>
            </div>
            
            <div className="flex items-center space-x-2">
              <span className="text-secondary/50 font-gameboy text-xs">
                Powered by Next.js & Tailwind CSS
              </span>
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
}