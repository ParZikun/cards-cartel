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
        <div className="max-w-7xl mx-auto space-y-8">
          {/* Hero Section */}
          <div className="text-center mb-12">
            <h2 className="text-pixel text-pixel-base sm:text-pixel-lg text-primary-text mb-4">
              Pokemon Card Sniper Dashboard
            </h2>
            <p className="text-mono text-lg text-primary-text/70 max-w-2xl mx-auto">
              Real-time monitoring and automated sniping for the best Pokemon card deals across multiple platforms
            </p>
          </div>

          {/* Search and Filter Controls */}
          <SearchBar />
          <FilterControls />
          
          {/* Results Grid */}
          <ListingGrid />
        </div>
      </main>
      
      <Footer />
    </div>
  )
}