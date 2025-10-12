import { NextResponse } from 'next/server';

export async function POST(request) {
  const { buyer, tokenMint, price, priorityFee } = await request.json();

  if (!buyer || !tokenMint || !price) {
    return NextResponse.json({ error: 'Missing required parameters: buyer, tokenMint, price' }, { status: 400 });
  }

  const apiKey = process.env.MAGIC_EDEN_API_KEY;

  const params = new URLSearchParams({
    buyer,
    tokenMint,
    price: price.toString(),
  });

  if (priorityFee) {
    params.append('priorityFee', priorityFee.toString());
  }

  try {
    const response = await fetch(`https://api-mainnet.magiceden.dev/v2/instructions/buy?${params.toString()}`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
      },
    });

    if (!response.ok) {
      const errorData = await response.json();
      console.error('Magic Eden API Error:', errorData);
      return NextResponse.json({ error: 'Failed to get buy instructions from Magic Eden', details: errorData }, { status: response.status });
    }

    const data = await response.json();
    return NextResponse.json(data);

  } catch (error) {
    console.error('Error fetching from Magic Eden API:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
