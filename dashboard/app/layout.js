import './styles/globals.css'

export const metadata = {
  title: 'Cartel Pro Sniper Bot',
  description: 'Professional Pokémon card sniping dashboard',
}

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-primary-bg text-primary-text">
        {children}
      </body>
    </html>
  )
}