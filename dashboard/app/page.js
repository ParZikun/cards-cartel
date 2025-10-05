'use client'

import { useState, useEffect, useMemo } from 'react'
import Header from './components/Header'
import Footer from './components/Footer'
import SearchBar from './components/SearchBar'
import FilterControls from './components/FilterControls'
import ListingGrid from './components/ListingGrid'

import { getSolPriceUsd } from './lib/priceService'

export default function Home() {
  const [listings, setListings] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [filter, setFilter] = useState('all')
  const [sort, setSort] = useState('listed-time')
  const [solPriceUSD, setSolPriceUSD] = useState(null)
  const [lastUpdated, setLastUpdated] = useState(null)
  const [apiStatus, setApiStatus] = useState('loading')

  useEffect(() => {
    const fetchData = async () => {
      try {
        setApiStatus('loading');
        const price = await getSolPriceUsd();
        if (price > 0) {
          setSolPriceUSD(price);
        }

        const response = await fetch(process.env.API_URL, {
          headers: {
            'X-API-Key': process.env.API_KEY
          }
        });
        if (!response.ok) {
          throw new Error(`API returned status ${response.status}`)
        }
        const data = await response.json();
        setListings(data)
        setApiStatus('live')
        setLastUpdated(new Date())
      } catch (e) {
        setError(e.message)
        setApiStatus('error')
      } finally {
        setLoading(false)
      }
    }

    fetchData(); // Initial fetch

    const priceInterval = setInterval(async () => {
      const price = await getSolPriceUsd();
      if (price > 0) {
        setSolPriceUSD(price);
      }
    }, 60000); // Refresh price every minute

    const listingsInterval = setInterval(async () => {
      try {
        const response = await fetch(process.env.API_URL, {
          headers: {
            'X-API-Key': process.env.API_KEY
          }
        });
        if (response.ok) {
          const data = await response.json();
          setListings(data);
          setApiStatus('live');
          setLastUpdated(new Date());
        }
      } catch (e) {
        // Silently fail on interval updates or handle as needed
        console.warn("Failed to refresh listings in background", e);
      }
    }, 5000); // Refresh listings every 5 seconds

    return () => {
      clearInterval(priceInterval);
      clearInterval(listingsInterval);
    }; // Cleanup on unmount
  }, [])

  const filteredAndSortedListings = useMemo(() => {
    return listings
      .map(listing => {
        const listingPriceUSD = listing.price_amount ? listing.price_amount * solPriceUSD : null;
        const diffPercent = (listingPriceUSD && listing.alt_value > 0) ? (((listingPriceUSD - listing.alt_value) / listing.alt_value) * 100) : null;
        return { ...listing, diffPercent };
      })
      .filter(listing => {
        // Search filter
        const searchLower = searchQuery.toLowerCase();
        const nameMatch = listing.name?.toLowerCase().includes(searchLower);
        const gradingIdMatch = listing.grading_id?.toString().toLowerCase().includes(searchLower);
        const popMatch = listing.supply?.toString().toLowerCase().includes(searchLower);
        const searchMatch = nameMatch || gradingIdMatch || popMatch;

        // Category filter
        const categoryMap = {
          autobuy: 'AUTOBUY',
          alert: 'GOOD',
          info: 'OK'
        };
        const categoryMatch = filter === 'all' || listing.cartel_category === categoryMap[filter];

        return searchMatch && categoryMatch;
      })
      .sort((a, b) => {
        switch (sort) {
          case 'price-low':
            return (a.price_amount || 0) - (b.price_amount || 0);
          case 'price-high':
            return (b.price_amount || 0) - (a.price_amount || 0);
          case 'difference-percent':
            return (a.diffPercent || 0) - (b.diffPercent || 0);
          case 'popularity':
            return (a.supply || 0) - (b.supply || 0);
          case 'listed-time':
          default:
            return new Date(b.listed_at) - new Date(a.listed_at);
        }
      });
  }, [listings, searchQuery, filter, sort, solPriceUSD]);

  return (
    <div className="min-h-screen flex flex-col">
      <Header apiStatus={apiStatus} lastUpdated={lastUpdated} />
      
      <main className="flex-1 px-4 sm:px-6 lg:px-8 py-8">
        <div className="max-w-7xl mx-auto space-y-8">
          {/* Hero Section */}
          <div className="text-center mb-12">
            <h2 className="text-pixel text-pixel-base sm:text-pixel-lg text-primary-text mb-4">
              Mission Control
            </h2>
            <p className="text-mono text-lg text-primary-text/70 max-w-2xl mx-auto">
              Target, Snipe, Collect.
            </p>
          </div>

          {/* Search and Filter Controls */}
          <SearchBar value={searchQuery} onChange={setSearchQuery} />
          <FilterControls 
            filterValue={filter} 
            onFilterChange={setFilter} 
            sortValue={sort} 
            onSortChange={setSort} 
          />
          
          {/* Results Grid */}
          <ListingGrid listings={filteredAndSortedListings} loading={loading} error={error} solPriceUSD={solPriceUSD} />
        </div>
      </main>
      
      <Footer />
    </div>
  )
}