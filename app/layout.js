import './styles/globals.css'

export const metadata = {
  title: 'Cartel Pro Sniper Bot',
  description: 'Professional Sniper Bot Dashboard for NFT Trading',
  keywords: 'NFT, sniper bot, trading, dashboard, crypto',
  authors: [{ name: 'ParZi' }],
  viewport: 'width=device-width, initial-scale=1',
}

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="true" />
        <link 
          href="https://fonts.googleapis.com/css2?family=Press+Start+2P&family=VT323:wght@400&display=swap" 
          rel="stylesheet" 
        />
      </head>
      <body className="min-h-screen flex flex-col">
        {children}
      </body>
    </html>
  )
}