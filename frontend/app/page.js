import Header from './components/Header';
import Footer from './components/Footer';
import SearchBar from './components/SearchBar';
import FilterControls from './components/FilterControls';
import ListingGrid from './components/ListingGrid';

export default function Home() {
  return (
    <>
      {/* Animated Hexagon Background */}
      <div className="hex-bg" />
      
      {/* Header */}
      <Header />

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        <SearchBar />
        <FilterControls />
        <ListingGrid />
      </main>

      {/* Footer */}
      <Footer />
    </>
  );
}