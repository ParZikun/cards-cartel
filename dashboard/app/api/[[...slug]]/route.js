import { NextResponse } from 'next/server';

export async function GET(request, { params }) {
  const slug = params.slug ? params.slug.join('/') : '';
  const { search } = new URL(request.url); // Use search to get the full query string with '?'
  
  // Fallback to localhost:5000 if API_URL is not set.
  const apiUrl = `${process.env.API_URL || 'http://localhost:5000'}/api/${slug}${search}`;

  try {
    const apiResponse = await fetch(apiUrl, {
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': process.env.API_KEY,
      },
    });

    if (!apiResponse.ok) {
      const errorText = await apiResponse.text();
      console.error(`API Error (${apiResponse.status}) from ${apiUrl}: ${errorText}`);
      return new NextResponse(errorText, { status: apiResponse.status, statusText: apiResponse.statusText });
    }

    const data = await apiResponse.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error(`Error forwarding request to ${apiUrl}:`, error);
    return new NextResponse('Error forwarding request to backend API.', { status: 502 }); // 502 Bad Gateway is more appropriate
  }
}