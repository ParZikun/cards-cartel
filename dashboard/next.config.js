/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'placehold.co',
      },
      {
        protocol: 'https',
        hostname: 'arweave.net',
      },
      {
        protocol: 'https',
        hostname: '*.arweave.net',
      },
      {
        protocol: 'https',
        hostname: 'cdn.prod.website-files.com',
      },
      {
        protocol: 'https',
        hostname: 'www.marketbeat.com',
      },
      {
        protocol: 'https',
        hostname: 'magiceden-launchpad.mypinata.cloud',
      },
      {
        protocol: 'https',
        hostname: '*.mypinata.cloud',
      },
      {
        protocol: 'https',
        hostname: 'ipfs.io',
      },
      {
        protocol: 'https',
        hostname: 'bafybeif3ef6migxwcxj6lvpyzhilpp3qz64pqzytnmscq2v6bbwck64zku.ipfs.nftstorage.link',
      },
      {
        protocol: 'https',
        hostname: '*.ipfs.nftstorage.link',
      },
    ],
  },
  env: {
    API_URL: process.env.API_URL,
    API_KEY: process.env.API_KEY,
  },
}

module.exports = nextConfig
