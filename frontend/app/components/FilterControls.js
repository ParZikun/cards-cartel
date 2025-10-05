'use client';

export default function FilterControls() {
  return (
    <div className="w-full mb-8 glass-effect rounded-lg p-4">
      <div className="flex flex-col lg:flex-row items-start lg:items-center gap-4 lg:gap-6">
        {/* Filter Dropdown */}
        <div className="flex items-center gap-3 w-full lg:w-auto">
          <label htmlFor="filter-by" className="text-gray-300 font-retro text-lg whitespace-nowrap">
            Filter by:
          </label>
          <select
            id="filter-by"
            className="custom-select bg-gray-900/50 border border-gray-700 text-white font-retro text-base rounded-md focus:ring-2 focus:ring-primary-gold focus:border-primary-gold block w-full lg:w-48 p-2"
          >
            <option value="all">Show All</option>
            <option value="autobuy">Autobuy (Gold)</option>
            <option value="alert">Alert (Red)</option>
            <option value="info">Info (Blue)</option>
          </select>
        </div>

        {/* Divider */}
        <div className="hidden lg:block h-8 w-px bg-gray-700"></div>

        {/* Sort Dropdown */}
        <div className="flex items-center gap-3 w-full lg:w-auto">
          <label htmlFor="sort-by" className="text-gray-300 font-retro text-lg whitespace-nowrap">
            Sort by:
          </label>
          <select
            id="sort-by"
            className="custom-select bg-gray-900/50 border border-gray-700 text-white font-retro text-base rounded-md focus:ring-2 focus:ring-primary-gold focus:border-primary-gold block w-full lg:w-48 p-2"
          >
            <option value="listed-time">Listed Time</option>
            <option value="price">Price</option>
            <option value="difference">Difference %</option>
          </select>
        </div>
      </div>
    </div>
  );
}