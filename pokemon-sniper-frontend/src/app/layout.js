import "./globals.css";
import Header from "@/components/Header";
import Footer from "@/components/Footer";

export const metadata = {
  title: "Catrel Pro Sniper Bot",
  description: "Professional Pokémon card sniper bot for finding the best deals",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="bg-primary text-secondary font-gameboy min-h-screen">
        <div className="flex flex-col min-h-screen">
          <Header />
          <main className="flex-grow">
            {children}
          </main>
          <Footer />
        </div>
      </body>
    </html>
  );
}
