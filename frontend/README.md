# Cartel Pro Sniper Bot Dashboard

A professional, futuristic Pokémon-inspired dashboard built with Next.js 14, Tailwind CSS, and Lucide React icons.

## 🎨 Design Features

- **Dark Futuristic Theme**: Near-black background (#0c0a15) with purple and blue gradients
- **Animated Hexagon Background**: Subtle, slowly panning hexagon pattern overlay
- **Glassmorphism Effects**: Backdrop blur effects on cards and UI elements
- **Gold Accent Color**: Rich gold (#FFD700) for highlights and interactive elements
- **Retro Fonts**: 
  - 'Press Start 2P' for headings (Pokémon GBA/GBC style)
  - 'VT323' for body text (readable pixel font)
- **Responsive Grid**: 2 columns on mobile, 3 on tablet, 4-5 on desktop

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

- **Node.js** version 18.0.0 or higher
- **npm** version 9.0.0 or higher

Check your versions:
```bash
node --version
npm --version
```

If you need to install or update Node.js, visit [nodejs.org](https://nodejs.org/)

## 🚀 Setup Instructions

### Understanding Dependency Isolation in Node.js

**Note about "Virtual Environments":**
Unlike Python which uses virtual environments (venv), Node.js handles dependency isolation automatically through the `node_modules` directory. Each project gets its own `node_modules` folder where all dependencies are installed locally. This means:

- ✅ Dependencies are automatically isolated per project
- ✅ No need to activate/deactivate environments
- ✅ `package.json` and `package-lock.json` lock dependency versions
- ✅ Different projects can use different versions of the same package

### Installation Steps

1. **Navigate to the frontend directory:**
   ```bash
   cd /workspace/frontend
   ```

2. **Install all dependencies:**
   ```bash
   npm install
   ```
   
   This command will:
   - Read `package.json` to see what packages are needed
   - Download all required packages into the `node_modules` directory
   - Create/update `package-lock.json` to lock exact versions
   - Install dependencies locally (isolated from other projects)

3. **Verify installation:**
   ```bash
   npm list --depth=0
   ```

## 🏃 Running the Application

### Development Mode (with hot reload)
```bash
npm run dev
```

The application will start at [http://localhost:3000](http://localhost:3000)

Features in development mode:
- ⚡ Fast Refresh (instant updates on save)
- 🐛 Detailed error messages
- 🔍 Source maps for debugging

### Production Build
```bash
# Build the application
npm run build

# Start the production server
npm start
```

### Linting (Code Quality Check)
```bash
npm run lint
```

## 📁 Project Structure

```
frontend/
├── app/
│   ├── components/
│   │   ├── Header.js          # Top navigation with logo and wallet button
│   │   ├── Footer.js          # Bottom footer with copyright
│   │   ├── SearchBar.js       # Full-width search input
│   │   ├── FilterControls.js  # Filter and sort dropdowns
│   │   ├── ListingGrid.js     # Responsive grid container
│   │   └── Card.js            # Individual card component
│   ├── styles/
│   │   └── globals.css        # Global styles and animations
│   ├── layout.js              # Root layout with fonts
│   └── page.js                # Main homepage
├── public/                    # Static assets (fonts, images)
├── package.json               # Dependencies and scripts
├── package-lock.json          # Locked dependency versions
├── tailwind.config.js         # Tailwind CSS configuration
├── postcss.config.mjs         # PostCSS configuration
├── next.config.js             # Next.js configuration
└── .eslintrc.json             # ESLint configuration
```

## 🎯 Key Components

### Header Component
- Sticky positioning with glassmorphism effect
- Logo (Crosshair icon) and title in 'Press Start 2P' font
- "Connect Wallet" button with gold hover effect (placeholder, no functionality)

### SearchBar Component
- Full-width glass effect container
- Search icon from Lucide React
- Gold focus ring on input
- Placeholder: "Search by name, grading ID, pop..."

### FilterControls Component
- Two dropdown menus with custom styling
- Filter by: Show All, Autobuy (Gold), Alert (Red), Info (Blue)
- Sort by: Listed Time, Price, Difference %

### ListingGrid Component
- Responsive CSS Grid layout
- 2 columns (mobile) → 3 (tablet) → 4-5 (desktop)
- Populated with 12 placeholder cards

### Card Component
- Fixed aspect ratio (3:4)
- Dark semi-transparent background
- Placeholder image from placehold.co
- Gold border glow on hover

## 🎨 Color Palette

| Color | Hex Code | Usage |
|-------|----------|-------|
| Primary Background | `#0c0a15` | Main background |
| Primary Gold | `#FFD700` | Accents, borders, buttons |
| Alert Red | `#EF4444` | Alert status |
| Info Blue | `#3B82F6` | Info status |
| Success Green | `#22C55E` | Success states |
| Light Gray | `#E2E8F0` | Secondary text |

## 📦 Dependencies

### Production Dependencies
- **next** (^14.2.16) - React framework with App Router
- **react** (^18.3.1) - UI library
- **react-dom** (^18.3.1) - React DOM rendering
- **lucide-react** (^0.447.0) - Icon library

### Development Dependencies
- **tailwindcss** (^3.4.15) - Utility-first CSS framework
- **autoprefixer** (^10.4.20) - PostCSS plugin for vendor prefixes
- **postcss** (^8.4.49) - CSS transformation tool
- **eslint** (^8.57.1) - Code linting
- **eslint-config-next** (^14.2.16) - ESLint config for Next.js

## 🌐 Deployment on Vercel

This project is optimized for deployment on [Vercel](https://vercel.com).

### Quick Deploy

1. **Install Vercel CLI:**
   ```bash
   npm install -g vercel
   ```

2. **Deploy:**
   ```bash
   vercel
   ```

### Or Deploy via GitHub

1. Push your code to GitHub
2. Import your repository on [vercel.com](https://vercel.com)
3. Vercel will automatically detect Next.js and configure the build
4. Click "Deploy"

## 🔧 Customization

### Changing Colors
Edit `tailwind.config.js`:
```javascript
colors: {
  primary: {
    bg: '#0c0a15',      // Change background color
    gold: '#FFD700',    // Change accent color
  },
  // ... add more custom colors
}
```

### Changing Fonts
Edit `globals.css` and update the Google Fonts import URL:
```css
@import url('https://fonts.googleapis.com/css2?family=Your+Font&display=swap');
```

### Modifying Grid Layout
Edit `ListingGrid.js`:
```javascript
// Change: grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5
className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 ..."
```

## 📝 Development Notes

- **No TypeScript**: This project uses JavaScript only (as requested)
- **No State Management**: Currently no Redux/Zustand (static UI foundation)
- **No API Integration**: Placeholder components only
- **No Wallet Connection**: Button is a visual placeholder

## 🐛 Troubleshooting

### Port Already in Use
```bash
# Kill process on port 3000
npx kill-port 3000

# Or use a different port
npm run dev -- -p 3001
```

### Dependencies Not Installing
```bash
# Clear npm cache
npm cache clean --force

# Delete node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

### Build Errors
```bash
# Clear Next.js cache
rm -rf .next

# Rebuild
npm run build
```

## 📄 License

Copyright © 2025 | Developed with ❤️ by ParZi

## 🤝 Contributing

This is a foundation project. Future enhancements can include:
- Real API integration
- Wallet connection functionality
- Real-time data updates
- Advanced filtering and sorting
- User authentication
- Responsive mobile optimizations

---

**Happy Coding! 🚀**