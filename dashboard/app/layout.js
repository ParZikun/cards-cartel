import { IBM_Plex_Mono, Press_Start_2P, VT323 } from 'next/font/google'
import './styles/globals.css'
import "@solana/wallet-adapter-react-ui/styles.css";
import { SolanaProvider } from "./components/SolanaProvider";
import { TransactionProvider } from './context/TransactionContext';
import localFont from 'next/font/local';

const pokemonHollow = localFont({ 
  src: '../public/pokemon-hollow.ttf',
  variable: '--font-pokemon-hollow'
});

const pokemonSolid = localFont({ 
  src: '../public/pokemon-solid.ttf',
  variable: '--font-pokemon-solid'
});

export default function RootLayout({ children }) {
  return (
    <html lang="en" className={`${pokemonHollow.variable} ${pokemonSolid.variable}`}>
      <body>
        <SolanaProvider>
          <TransactionProvider>
            {children}
          </TransactionProvider>
        </SolanaProvider>
      </body>
    </html>
  );
}
