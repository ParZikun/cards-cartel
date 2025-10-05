import Header from './components/Header'
import Footer from './components/Footer'
import SearchBar from './components/SearchBar'
import FilterControls from './components/FilterControls'
import ListingGrid from './components/ListingGrid'

export default function Home() {
  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      
      <main className="flex-1 px-4 sm:px-6 lg:px-8 py-8">
        <div className="max-w-7xl mx-auto">
          {/* Page Title */}
          <div className="text-center mb-12">
            <h2 className="font-pixel-primary text-2xl sm:text-3xl lg:text-4xl text-accent-gold mb-4 pixel-text">
              SNIPER BOT DASHBOARD
            </h2>
            <p className="font-pixel-secondary text-lg text-secondary-text/80 max-w-2xl mx-auto">
              Monitor and snipe the best NFT deals in real-time with our advanced trading bot
            </p>
          </div>

          {/* Search and Filter Section */}
          <div className="mb-12">
            <SearchBar />
            <FilterControls />
          </div>

          {/* Listings Grid */}
          <ListingGrid />
        </div>
      </main>

      <Footer />
    </div>
  )
}