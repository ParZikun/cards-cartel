# Sniper Bot Dashboard

A professional, dark-themed Pokemon card sniping dashboard built with Next.js 14, Tailwind CSS, and modern React components.

## Features

- 🌙 Dark, futuristic Pokemon-inspired theme
- ⚡ Built with Next.js 14 App Router
- 🎨 Tailwind CSS with custom color palette
- 🔍 Real-time search and filtering
- 📱 Fully responsive design
- ✨ Glassmorphism effects and animations
- 🎯 Optimized for Vercel deployment

## Tech Stack

- **Framework**: Next.js 14+ (App Router)
- **Language**: JavaScript
- **Styling**: Tailwind CSS
- **Icons**: Lucide React
- **Fonts**: Press Start 2P, VT323

## Getting Started

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Run the development server:**
   ```bash
   npm run dev
   ```

3. **Open your browser:**
   Navigate to [http://localhost:3000](http://localhost:3000)

## Project Structure

```
dashboard/
├── app/
│   ├── components/          # Reusable React components
│   │   ├── Header.js       # Navigation header with glassmorphism
│   │   ├── Footer.js       # Simple footer with copyright
│   │   ├── SearchBar.js    # Search input with icon
│   │   ├── FilterControls.js # Sort and filter dropdowns
│   │   ├── Card.js         # Individual card component
│   │   └── ListingGrid.js  # Responsive grid layout
│   ├── styles/
│   │   └── globals.css     # Global styles and animations
│   ├── layout.js           # Root layout component
│   └── page.js             # Main dashboard page
├── public/                 # Static assets
├── tailwind.config.js      # Tailwind configuration
├── next.config.js          # Next.js configuration
└── package.json            # Dependencies and scripts
```

## Color Palette

- **Primary Background**: `#0c0a15` (Near-black)
- **Text**: `#E2E8F0` (Light gray)
- **Accent Gold**: `#FFD700` (Highlights and interactions)
- **Status Colors**:
  - Alert (Red): `#EF4444`
  - Info (Blue): `#3B82F6`
  - Success (Green): `#22C55E`

## Typography

- **Headings/Logo**: Press Start 2P (Pixel font)
- **Body Text**: VT323 (Monospace pixel font)

## Deployment

This project is optimized for Vercel deployment:

```bash
npm run build
```

Or deploy directly to Vercel:
```bash
vercel --prod
```

## Development

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint

## License

Private project - All rights reserved.