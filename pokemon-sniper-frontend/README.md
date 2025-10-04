# Catrel Pro Sniper Bot - Frontend

A professional Next.js frontend for the Pokémon card sniper bot application. Built with a dark theme, Pokémon-style fonts, and modern UI components.

## Features

- 🎨 **Dark Theme**: Black primary, white secondary, gold accent colors with radial gradients
- 🔤 **Pokémon Fonts**: Pixelated fonts for titles, readable fonts for body content
- 🔍 **Advanced Search**: Search by name, grading ID, grade, or any card details
- 🎯 **Smart Filters**: Filter by card type (All, Blue, Red, Gold)
- 📊 **Sorting Options**: Sort by newest, oldest, price, or rarity
- 💳 **Wallet Connect**: Integrated wallet connection for instant transactions
- 📱 **Responsive Design**: Works perfectly on desktop, tablet, and mobile
- ⚡ **Real-time Updates**: Live card data with instant filtering

## Tech Stack

- **Framework**: Next.js 15.5.4 with App Router
- **Styling**: Tailwind CSS with custom theme
- **Fonts**: Press Start 2P (Pokémon-style), Orbitron (GameBoy-style)
- **Icons**: Lucide React
- **Wallet**: RainbowKit + Wagmi + Viem
- **Animations**: Framer Motion
- **Language**: JavaScript (no TypeScript)

## Getting Started

### Prerequisites

- Node.js 18+ 
- npm or yarn

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd pokemon-sniper-frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

4. Open [http://localhost:3000](http://localhost:3000) in your browser.

## Project Structure

```
src/
├── app/
│   ├── globals.css          # Global styles and theme
│   ├── layout.js           # Root layout with header/footer
│   └── page.js             # Main dashboard page
├── components/
│   ├── Header.js           # Navigation header with wallet connect
│   ├── Footer.js           # Footer with copyright
│   └── CardGrid.js         # Card grid with filtering/sorting
└── ...
```

## Customization

### Colors
The theme uses a custom color palette defined in `tailwind.config.js`:
- **Primary**: Black (#000000)
- **Secondary**: White (#ffffff) 
- **Accent**: Gold (#FFD700)
- **Pokémon Colors**: Red, Blue, Orange, Green

### Fonts
- **Pokémon Style**: Press Start 2P (for titles and headers)
- **GameBoy Style**: Orbitron (for body text and UI elements)

### Animations
- **Gold Shimmer**: Moving gradient animation for gold elements
- **Float**: Subtle floating animation for interactive elements
- **Hover Effects**: Scale and color transitions

## Deployment

### Vercel (Recommended)

1. Push your code to GitHub
2. Connect your repository to Vercel
3. Deploy with zero configuration

### Manual Deployment

```bash
npm run build
npm start
```

## API Integration

The frontend is designed to work with the backend API. Update the API endpoints in the components to connect to your deployed backend:

- Card data fetching
- Wallet transaction processing
- Real-time updates via WebSocket

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

Developed with ❤️ by ParZi

---

**Note**: This is the frontend component of the Catrel Pro Sniper Bot system. Make sure your backend API is running and properly configured for full functionality.