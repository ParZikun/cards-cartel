import Image from 'next/image';
import { WalletCards, TrendingDown, Tag, BarChart4, Copy, Zap, CheckCircle, XCircle, Loader } from 'lucide-react';
import { useState } from 'react';
import { useConnection } from '@solana/wallet-adapter-react';
import { useWallet } from '@solana/wallet-adapter-react';
import { useTransaction } from '../context/TransactionContext';
import { Transaction, VersionedTransaction } from '@solana/web3.js';

const getCategoryStyle = (category) => {
    const styles = {
        'AUTOBUY': { badge: 'bg-yellow-400/10 text-yellow-300 border-yellow-400/20', glow: 'rgba(250, 204, 21, 0.5)', border: 'rgba(250, 204, 21, 0.3)', hover: 'rgba(250, 204, 21, 0.4)' },
        'GOOD':    { badge: 'bg-red-500/10 text-red-400 border-red-500/20',       glow: 'rgba(239, 68, 68, 0.4)', border: 'rgba(239, 68, 68, 0.25)', hover: 'rgba(239, 68, 68, 0.35)' },
        'OK':      { badge: 'bg-sky-500/10 text-sky-300 border-sky-500/20',        glow: 'rgba(56, 189, 248, 0.4)', border: 'rgba(56, 189, 248, 0.25)', hover: 'rgba(56, 189, 248, 0.35)' },
    };
    const fallback = { glow: 'rgba(100, 116, 139, 0.4)', border: 'rgba(55, 65, 81, 1)', hover: 'rgba(100, 116, 139, 1)'};
    return styles[category] || fallback;
}

const timeAgo = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    const seconds = Math.floor((new Date() - date) / 1000);
    if (seconds < 60) return "Just now";
    const intervals = { year: 31536000, month: 2592000, day: 86400, hour: 3600, minute: 60 };
    if (seconds < intervals.hour) return Math.floor(seconds / intervals.minute) + " mins ago";
    if (seconds < intervals.day) return Math.floor(seconds / intervals.hour) + " hours ago";
    if (seconds < intervals.month) return Math.floor(seconds / intervals.day) + " days ago";
    if (seconds < intervals.year) return Math.floor(seconds / intervals.month) + " months ago";
    return Math.floor(seconds / intervals.year) + " years ago";
}

const getAltConfidenceColor = (confidence) => {
    if (confidence === null || confidence === undefined) return 'text-gray-400';
    if (confidence >= 75) return 'text-green-400';
    if (confidence >= 60) return 'text-orange-400';
    if (confidence < 35) return 'text-red-500';
    return 'text-gray-400';
}

const getDifferenceColor = (category) => {
    const colorMap = {
        'AUTOBUY': 'text-yellow-300 font-bold',
        'GOOD': 'text-red-400',
        'OK': 'text-sky-300',
    };
    return colorMap[category] || 'text-gray-400';
}

export default function Card({ listing, solPriceUSD, priority }) {
    const { connection } = useConnection();
    const { publicKey, signTransaction, sendTransaction } = useWallet();
    const { priorityFee } = useTransaction(); // Assuming slippage is handled elsewhere or not needed for this step
    
    const [snipeState, setSnipeState] = useState('idle'); // idle, loading, success, error

    const listingPriceUSD = listing.price_amount ? listing.price_amount * solPriceUSD : null;
    const diffPercent = (listingPriceUSD && listing.alt_value > 0) ? (((listingPriceUSD - listing.alt_value) / listing.alt_value) * 100) : null;
    const categoryStyle = getCategoryStyle(listing.cartel_category);
    const altConfidenceColor = getAltConfidenceColor(listing.alt_value_confidence);
    const differenceColor = getDifferenceColor(listing.cartel_category);

    const copyToClipboard = (text) => {
        navigator.clipboard.writeText(text);
        // You can add a toast notification here
    };

    const handleSnipe = async () => {
        if (!publicKey) {
            alert('Please connect your wallet first!');
            return;
        }
        setSnipeState('loading');

        try {
            // 1. Get transaction instructions from our API
            const response = await fetch('/api/magiceden/buy', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    buyer: publicKey.toBase58(),
                    tokenMint: listing.token_mint,
                    price: listing.price_amount,
                    priorityFee: priorityFee,
                }),
            });

            if (!response.ok) {
                throw new Error('Failed to get transaction instructions');
            }

            const data = await response.json();
            
            // The API sends back a field `tx` which is a base64 encoded transaction
            const txData = data.tx;

            // 2. Deserialize the transaction
            const txBuffer = Buffer.from(txData, 'base64');
            
            let transaction;
            try {
                // First try to deserialize as a VersionedTransaction
                transaction = VersionedTransaction.deserialize(txBuffer);
                console.log("Deserialized as VersionedTransaction");
            } catch (e) {
                try {
                    // If that fails, try to deserialize as a legacy Transaction
                    transaction = Transaction.from(txBuffer);
                    console.log("Deserialized as Legacy Transaction");
                } catch (e2) {
                    console.error("Failed to deserialize transaction:", e2);
                    throw new Error("Could not deserialize the transaction from Magic Eden.");
                }
            }

            // 3. Sign the transaction with the user's wallet
            if (!signTransaction) {
                 throw new Error('Wallet does not support signing transactions.');
            }
            const signedTx = await signTransaction(transaction);

            // 4. Send the transaction
            const signature = await connection.sendRawTransaction(signedTx.serialize());

            // 5. Confirm the transaction
            await connection.confirmTransaction(signature, 'processed');

            setSnipeState('success');
            setTimeout(() => setSnipeState('idle'), 3000); // Reset after 3s

        } catch (error) {
            console.error("Snipe failed:", error);
            setSnipeState('error');
            setTimeout(() => setSnipeState('idle'), 3000); // Reset after 3s
        }
    };

    const getButtonContent = () => {
        switch (snipeState) {
            case 'loading':
                return <><Loader className="w-4 h-4 animate-spin" /><span>Processing...</span></>;
            case 'success':
                return <><CheckCircle className="w-4 h-4" /><span>Success!</span></>;
            case 'error':
                return <><XCircle className="w-4 h-4" /><span>Failed</span></>;
            default:
                return <><Zap className="w-4 h-4" /><span>{listing.listed ? 'Snipe Now' : 'Sold'}</span></>;
        }
    };

    const getButtonClass = () => {
        switch (snipeState) {
            case 'loading':
                return 'bg-gray-500';
            case 'success':
                return 'bg-green-500 hover:bg-green-600';
            case 'error':
                return 'bg-red-500 hover:bg-red-600';
            default:
                return 'bg-yellow-500 hover:bg-yellow-600';
        }
    };

    return (
        <div className="card-glass card-glow rounded-xl shadow-lg flex flex-col transition-all duration-300" style={{'--glow-color': categoryStyle.glow, '--border-color': categoryStyle.border, '--border-color-hover': categoryStyle.hover}}>
            <div className="relative">
                <Image src={listing.img_url || 'https://placehold.co/300x420/0c0a15/2d3748?text=N/A'} alt={listing.name} width={300} height={420} className="h-72 w-full object-contain rounded-t-xl pt-4 bg-black/20" priority={priority} placeholder="blur" blurDataURL="data:image/gif;base64,R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw==" />
            </div>
            
            <div className="p-4 flex flex-col flex-grow">
                <h3 className="font-bold text-white text-base leading-tight truncate mb-1" title={listing.name}>{listing.name}</h3>
                
                <div className="flex justify-between items-center text-xs text-gray-400 mb-3">
                    <span>{listing.grade || 'N/A'}</span>
                    <span className="font-mono">Pop: {listing.supply !== null ? listing.supply : 'N/A'}</span>
                </div>
                
                <div className="text-xs text-gray-500 space-y-1 mb-3">
                    <p>Grading ID: <span className="font-mono text-gray-300">{listing.grading_id || 'N/A'}</span></p>
                    <p>Insured: <span className="font-mono text-gray-300">{listing.insured_value != null ? listing.insured_value.toFixed(2) : 'N/A'}</span></p>
                </div>

                <div className="grid grid-cols-2 gap-2 my-2">
                    <div className="bg-black/20 p-2 rounded-md border border-gray-700/50 text-center">
                        <p className="text-xs text-gray-400 flex items-center justify-center gap-1"><WalletCards className="w-3 h-3" />Price (SOL)</p>
                        <p className="font-mono text-white text-lg">{listing.price_amount ? listing.price_amount.toFixed(4) : 'N/A'}</p>
                        <p className="font-mono text-xs text-gray-500">{listingPriceUSD ? `~${listingPriceUSD.toFixed(2)}` : ''}</p>
                    </div>
                    <div className="bg-black/20 p-2 rounded-md border border-gray-700/50 text-center">
                        <p className="text-xs text-gray-400 flex items-center justify-center gap-1"><TrendingDown className="w-3 h-3" />Difference</p>
                        <p className={`font-mono text-lg font-semibold ${differenceColor}`}>{diffPercent !== null ? `${diffPercent.toFixed(2)}%` : 'N/A'}</p>
                        <p className="font-mono text-xs text-gray-500">&nbsp;</p>
                    </div>
                    <div className="bg-black/20 p-2 rounded-md border border-gray-700/50 text-center">
                        <p className="text-xs text-gray-400 flex items-center justify-center gap-1"><Tag className="w-3 h-3" />ALT Value</p>
                        <p className={`font-mono text-lg ${altConfidenceColor}`}>{listing.alt_value !== null ? `${listing.alt_value.toFixed(2)}` : 'N/A'}</p>
                        <p className="font-mono text-xs text-gray-500">{(listing.alt_value_lower_bound !== null && listing.alt_value_upper_bound !== null) ? `${listing.alt_value_lower_bound.toFixed(2)} - ${listing.alt_value_upper_bound.toFixed(2)}` : 'N/A'}</p>
                    </div>
                    <div className="bg-black/20 p-2 rounded-md border border-gray-700/50 text-center">
                        <p className="text-xs text-gray-400 flex items-center justify-center gap-1"><BarChart4 className="w-3 h-3" />Cartel AVG</p>
                        <p className="font-mono text-lg text-white">{listing.avg_price !== null ? `${listing.avg_price.toFixed(2)}` : 'N/A'}</p>
                         <p className="font-mono text-xs text-gray-500">&nbsp;</p>
                    </div>
                </div>
                
                <div className="flex-grow"></div>
                
                <div className="mt-4 pt-4 border-t border-gray-700/50 space-y-2">
                     <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                             <a href={listing.alt_asset_id ? `https://app.alt.xyz/research/${listing.alt_asset_id}` : '#'} target="_blank" title="View on ALT.xyz" className="text-gray-500 hover:opacity-80 transition-opacity"><Image src="https://cdn.prod.website-files.com/62829b28e6300b34ff739f02/629661dd02bdba04fb424173_ALT-white-logo.png" width={20} height={20} style={{ width: 'auto', height: 'auto' }} className="object-contain" alt="ALT logo" /></a>
                             <a href={`https://collectorcrypt.com/assets/solana/${listing.token_mint}`} target="_blank" title="View on Collector Crypt" className="text-gray-500 hover:opacity-80 transition-opacity"><Image src="https://www.marketbeat.com/logos/cryptocurrencies/collector-crypt-CARDS.png?v=2025-09-12" width={20} height={20} className="object-contain bg-white rounded-full p-0.5" alt="CC logo" /></a>
                             <button onClick={() => copyToClipboard(listing.token_mint)} className="text-gray-500 hover:text-sky-400 transition-colors"><Copy className="w-4 h-4" /></button>
                        </div>
                        <p className="text-xs text-gray-500">{timeAgo(listing.listed_at)}</p>
                    </div>
                    <div className="flex gap-2 mt-2">
                        <button 
                            className={`buy-now-btn flex-1 flex items-center justify-center gap-2 text-black text-sm font-bold py-2 px-3 rounded-md transition-all duration-200 disabled:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed ${getButtonClass()}`}
                            disabled={true} // !listing.listed || snipeState === 'loading' || snipeState === 'success'}
                            onClick={handleSnipe}
                        >
                            {getButtonContent()}
                        </button>
                        <a href={`https://magiceden.io/item-details/${listing.token_mint}`} target="_blank" className="flex-1 flex items-center justify-center gap-2 text-center bg-sky-500/20 hover:bg-sky-500/40 text-sky-300 text-sm font-bold py-2 px-3 rounded-md transition-colors duration-200">
                            <Image src="https://cdn.prod.website-files.com/614c99cf4f23700c8aa3752a/637db1043720a3ea88e4ea96_public.png" width={20} height={20} className="object-contain" alt="Magic Eden Logo" />
                            <span>View on ME</span>
                        </a>
                    </div>
                </div>
            </div>
        </div>
    )
}