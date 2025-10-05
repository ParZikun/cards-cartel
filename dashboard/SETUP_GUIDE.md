# Sniper Bot Dashboard Setup Guide

## Quick Start (Automated Setup)

The fastest way to get started is using the automated setup script:

```bash
cd dashboard
chmod +x setup.sh
./setup.sh
```

This script will:
- ✅ Check Node.js version compatibility
- 📦 Install all dependencies
- 🔨 Verify the build works correctly
- 🎉 Provide next steps

## Manual Setup (Node.js)

Since this is a Node.js/Next.js project, we use `npm` for dependency management instead of Python virtual environments.

### Prerequisites
- Node.js (version 18.17 or later)
- npm (comes with Node.js) or yarn

### Manual Setup Steps

1. **Check Node.js version:**
   ```bash
   node --version  # Should be 18.17+
   npm --version
   ```

2. **Navigate to the dashboard directory:**
   ```bash
   cd dashboard
   ```

3. **Install dependencies:**
   ```bash
   npm install
   ```

4. **Run the development server:**
   ```bash
   npm run dev
   ```
   Open [http://localhost:3000](http://localhost:3000) in your browser.

5. **Build for production:**
   ```bash
   npm run build
   npm start
   ```

### Project Dependencies

The `package.json` file contains all dependencies with locked versions:

- **Next.js 14+**: React framework with App Router
- **React 18**: UI library
- **Tailwind CSS**: Utility-first CSS framework
- **Lucide React**: Icon library
- **PostCSS & Autoprefixer**: CSS processing

### Development Workflow

1. **Development mode**: `npm run dev` - Hot reload enabled
2. **Linting**: `npm run lint` - Check code quality
3. **Building**: `npm run build` - Create production build
4. **Production**: `npm start` - Run production server

### Deployment to Vercel

1. Install Vercel CLI: `npm i -g vercel`
2. Login: `vercel login`
3. Deploy: `vercel --prod`

Or connect your GitHub repository to Vercel for automatic deployments.

### Environment Isolation

Node.js projects use `package.json` and `package-lock.json` to lock dependency versions. This ensures:
- Consistent builds across environments
- No version conflicts
- Isolated project dependencies

The `node_modules` directory contains all project dependencies and should not be committed to version control.