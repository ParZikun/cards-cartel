# Sniper Bot Dashboard Setup Instructions

## Virtual Environment Setup

### Option 1: Using Node.js Virtual Environment (Recommended)

1. **Install Node.js** (if not already installed):
   ```bash
   # Check if Node.js is installed
   node --version
   npm --version
   ```

2. **Create a virtual environment using npm**:
   ```bash
   # Create a new directory for the project
   mkdir sniper-bot-dashboard
   cd sniper-bot-dashboard
   
   # Initialize npm project
   npm init -y
   
   # Install dependencies with exact versions
   npm install next@14.2.5 react@18.3.1 react-dom@18.3.1 lucide-react@0.400.0
   npm install --save-dev eslint@8.57.0 eslint-config-next@14.2.5 tailwindcss@3.4.7 autoprefixer@10.4.19 postcss@8.4.39
   ```

### Option 2: Using Python Virtual Environment (Alternative)

1. **Create Python virtual environment**:
   ```bash
   # Create virtual environment
   python3 -m venv sniper-bot-env
   
   # Activate virtual environment
   source sniper-bot-env/bin/activate  # On Linux/Mac
   # OR
   sniper-bot-env\Scripts\activate     # On Windows
   
   # Install Node.js dependencies using pip (if you have nodeenv)
   pip install nodeenv
   nodeenv -p
   ```

### Option 3: Using Docker (Isolated Environment)

1. **Create Dockerfile**:
   ```dockerfile
   FROM node:18-alpine
   WORKDIR /app
   COPY package*.json ./
   RUN npm ci --only=production
   COPY . .
   EXPOSE 3000
   CMD ["npm", "run", "dev"]
   ```

2. **Build and run**:
   ```bash
   docker build -t sniper-bot-dashboard .
   docker run -p 3000:3000 sniper-bot-dashboard
   ```

## Project Setup

1. **Copy all project files** to your chosen directory
2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Run the development server**:
   ```bash
   npm run dev
   ```

4. **Open your browser** and navigate to `http://localhost:3000`

## File Structure

```
sniper-bot-dashboard/
├── app/
│   ├── components/
│   │   ├── Header.js
│   │   ├── Footer.js
│   │   ├── SearchBar.js
│   │   ├── FilterControls.js
│   │   ├── Card.js
│   │   └── ListingGrid.js
│   ├── styles/
│   │   └── globals.css
│   ├── layout.js
│   └── page.js
├── public/
├── package.json
├── next.config.js
├── tailwind.config.js
├── postcss.config.js
└── requirements.txt
```

## Dependencies Locked Versions

All dependencies are locked to specific versions to ensure consistency:

- **Next.js**: 14.2.5
- **React**: 18.3.1
- **React DOM**: 18.3.1
- **Lucide React**: 0.400.0
- **Tailwind CSS**: 3.4.7
- **ESLint**: 8.57.0

## Development Commands

```bash
# Start development server
npm run dev

# Build for production
npm run build

# Start production server
npm start

# Run linting
npm run lint
```

## Features Implemented

✅ Dark, futuristic Pokémon-inspired theme
✅ Responsive design (mobile-first)
✅ Glassmorphism effects
✅ Animated background with gradients
✅ Pixel fonts (Press Start 2P, VT323)
✅ Component-based architecture
✅ Search functionality (UI only)
✅ Filter and sort controls
✅ Card grid with hover effects
✅ Professional header and footer
✅ Gold accent color scheme
✅ Status indicators and animations

## Next Steps

1. Add API integration for real NFT data
2. Implement wallet connection functionality
3. Add real-time updates
4. Implement actual filtering and sorting logic
5. Add more detailed card information
6. Implement user authentication
7. Add settings and preferences