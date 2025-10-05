import { IBM_Plex_Mono, Press_Start_2P, VT323 } from 'next/font/google'
import './styles/globals.css'

const ibmPlexMono = IBM_Plex_Mono({
  weight: ['400', '700'],
  subsets: ['latin'],
  variable: '--font-ibm-plex-mono',
  display: 'swap',
})

const pressStart2P = Press_Start_2P({
  weight: ['400'],
  subsets: ['latin'],
  variable: '--font-press-start-2p',
  display: 'swap',
})

const vt323 = VT323({
  weight: ['400'],
  subsets: ['latin'],
  variable: '--font-vt323',
  display: 'swap',
})

export const metadata = {
  title: 'Cartel Pro Sniper Bot',
  description: 'Professional Pokémon card sniping dashboard',
}

export default function RootLayout({ children }) {
  return (
    <html lang="en" className={`${ibmPlexMono.variable} ${pressStart2P.variable} ${vt323.variable}`}>
      <body className="min-h-screen bg-primary-bg text-primary-text">
        {children}
      </body>
    </html>
  )
}