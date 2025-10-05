# 🎯 Cartel Pro Sniper Bot Dashboard

A professional, dark-themed NFT sniper bot dashboard built with Next.js 14, featuring a futuristic Pokémon-inspired design with glassmorphism effects and responsive layout.

## ✨ Features

- **Dark Futuristic Theme**: Near-black background with gold accents and animated gradients
- **Pokémon-Inspired Design**: Pixel fonts and retro gaming aesthetics
- **Glassmorphism Effects**: Modern glass-like UI elements with backdrop blur
- **Responsive Design**: Mobile-first approach with adaptive grid layouts
- **Component Architecture**: Clean, reusable React components
- **Animated Background**: Subtle hexagon patterns and floating gradients
- **Interactive Elements**: Hover effects, glow animations, and smooth transitions

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ 
- npm or yarn

### Installation

1. **Clone or download the project files**

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Run the development server**:
   ```bash
   npm run dev
   ```

4. **Open [http://localhost:3000](http://localhost:3000)** in your browser

## 🎨 Design System

### Color Palette
- **Primary Background**: `#0c0a15` (Near-black)
- **Secondary Text**: `#E2E8F0` (Light gray)
- **Accent Gold**: `#FFD700` (Rich gold)
- **Status Colors**:
  - Red: `#EF4444` (Alerts/Good deals)
  - Blue: `#3B82F6` (Info deals)
  - Green: `#22C55E` (Success states)

### Typography
- **Primary Font**: Press Start 2P (Pixel font for headings)
- **Secondary Font**: VT323 (Pixel font for body text)

## 🏗️ Project Structure

```
app/
├── components/
│   ├── Header.js          # Sticky header with glassmorphism
│   ├── Footer.js          # Simple footer with copyright
│   ├── SearchBar.js       # Search input with icon
│   ├── FilterControls.js  # Filter and sort dropdowns
│   ├── Card.js           # Individual NFT card component
│   └── ListingGrid.js    # Responsive grid layout
├── styles/
│   └── globals.css       # Global styles and animations
├── layout.js            # Root layout with fonts
└── page.js             # Main dashboard page
```

## 🛠️ Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: JavaScript (ES6+)
- **Styling**: Tailwind CSS
- **Icons**: Lucide React
- **Fonts**: Google Fonts (Press Start 2P, VT323)

## 📱 Responsive Breakpoints

- **Mobile**: 2 columns (grid-cols-2)
- **Small**: 3 columns (sm:grid-cols-3)
- **Medium**: 4 columns (md:grid-cols-4)
- **Large**: 5 columns (lg:grid-cols-5)

## 🎯 Components Overview

### Header
- Sticky positioning with glassmorphism effect
- Logo with lightning bolt icon
- "Connect Wallet" button with hover effects

### SearchBar
- Full-width search input
- Search icon and live indicator
- Gold focus ring and glow effects

### FilterControls
- Filter dropdown (Show All, Autobuy, Alert, Info)
- Sort dropdown (Listed Time, Price, Difference %, Rarity)
- Responsive layout

### Card
- 3:4 aspect ratio placeholder images
- Hover effects with scale and glow
- Status indicators and price information
- Gradient overlays

### ListingGrid
- Responsive CSS Grid layout
- Loading indicator with animated dots
- 12 placeholder cards

## 🎨 Custom CSS Classes

- `.glass` - Glassmorphism effect
- `.glass-strong` - Stronger glassmorphism
- `.glow-gold` - Gold glow effect
- `.pixel-text` - Pixel font rendering optimization

## 🚀 Deployment

This project is optimized for Vercel deployment:

1. Push to GitHub
2. Connect to Vercel
3. Deploy automatically

## 🔮 Future Enhancements

- [ ] Real-time NFT data integration
- [ ] Wallet connection functionality
- [ ] Advanced filtering and sorting
- [ ] User authentication
- [ ] Settings and preferences
- [ ] Real-time notifications
- [ ] Dark/light theme toggle

## 📄 License

Copyright © 2025 | Developed with ❤️ by ParZi

---

**Note**: This is a UI foundation project. No actual trading functionality is implemented.