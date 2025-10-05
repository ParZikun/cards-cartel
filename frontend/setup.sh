#!/bin/bash

# Cartel Pro Sniper Bot Dashboard - Setup Script
# This script automates the setup process for the Next.js dashboard

echo "╔════════════════════════════════════════════════════════════╗"
echo "║   Cartel Pro Sniper Bot Dashboard - Setup Script         ║"
echo "║   Setting up Next.js with isolated dependencies...       ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check if Node.js is installed
echo "🔍 Checking Node.js installation..."
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed!"
    echo "📥 Please install Node.js from: https://nodejs.org/"
    exit 1
fi

NODE_VERSION=$(node -v)
echo "✅ Node.js is installed: $NODE_VERSION"

# Check if npm is installed
echo "🔍 Checking npm installation..."
if ! command -v npm &> /dev/null; then
    echo "❌ npm is not installed!"
    exit 1
fi

NPM_VERSION=$(npm -v)
echo "✅ npm is installed: v$NPM_VERSION"
echo ""

# Navigate to frontend directory
echo "📂 Navigating to frontend directory..."
cd "$(dirname "$0")" || exit
echo "✅ Current directory: $(pwd)"
echo ""

# Install dependencies
echo "📦 Installing dependencies (this may take a few minutes)..."
echo "   Note: Dependencies will be installed in ./node_modules"
echo "   This ensures complete isolation from other projects!"
echo ""
npm install

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Dependencies installed successfully!"
    echo ""
    echo "📊 Installed packages:"
    npm list --depth=0
else
    echo ""
    echo "❌ Failed to install dependencies!"
    exit 1
fi

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║   🎉 Setup Complete!                                      ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "🚀 To start the development server, run:"
echo "   npm run dev"
echo ""
echo "🌐 The app will be available at:"
echo "   http://localhost:3000"
echo ""
echo "📚 For more information, see README.md"
echo ""