# Quick Start Guide ⚡

Get up and running in 3 minutes!

## 🚀 Ultra Quick Setup

```bash
# 1. Navigate to project
cd /workspace/frontend

# 2. Install dependencies (automatic isolation!)
npm install

# 3. Start dev server
npm run dev

# 4. Open browser
# Go to: http://localhost:3000
```

That's it! No virtual environment needed. 🎉

## 📋 Quick Commands Reference

```bash
# Development
npm run dev          # Start dev server with hot reload

# Production
npm run build        # Build for production
npm start            # Run production server

# Maintenance
npm run lint         # Check code quality
npm install          # Install/update dependencies
npm outdated         # Check for package updates
```

## 🎨 Project Structure Quick View

```
frontend/
├── app/
│   ├── components/       # All React components
│   │   ├── Header.js
│   │   ├── Footer.js
│   │   ├── SearchBar.js
│   │   ├── FilterControls.js
│   │   ├── ListingGrid.js
│   │   └── Card.js
│   ├── styles/
│   │   └── globals.css   # Global styles + animations
│   ├── layout.js         # Root layout
│   └── page.js           # Homepage
├── public/               # Static files
├── package.json          # Dependencies list
└── package-lock.json     # Locked versions
```

## 🛠️ Customization Quick Tips

### Change Colors
Edit `tailwind.config.js`:
```javascript
colors: {
  primary: {
    gold: '#YOUR_COLOR',  // Change accent color
  }
}
```

### Change Fonts
Edit `app/styles/globals.css` - update the Google Fonts URL

### Change Grid Layout
Edit `app/components/ListingGrid.js`:
```javascript
className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4"
//                     ↑             ↑             ↑
//                  mobile        tablet        desktop
```

## ❓ Need Help?

- **Detailed Setup**: See `SETUP_GUIDE.md`
- **Full Documentation**: See `README.md`
- **Troubleshooting**: See README.md troubleshooting section

## 🎯 Key Features Built

✅ Responsive dark theme with gold accents  
✅ Animated hexagon background  
✅ Glassmorphism effects  
✅ Sticky header with wallet button  
✅ Search bar with gold focus ring  
✅ Filter and sort controls  
✅ Responsive card grid (2-3-4-5 columns)  
✅ Hover effects on cards  
✅ Retro Pokémon-style fonts  
✅ Clean component architecture  

## 📝 Next Steps (Future Development)

- Add API integration for real data
- Implement wallet connection
- Add state management (Redux/Zustand)
- Create detailed card design
- Add animations and transitions
- Implement filtering/sorting logic

---

**Happy Coding! 🚀**