/**
 * Cloudflare Worker for FA Fulltime proxy with caching
 * 
 * This worker:
 * - Proxies requests to FA Fulltime website
 * - Caches responses for 3 hours to reduce load
 * - Adds CORS headers for your domain
 * - Handles timeouts and errors gracefully
 * 
 * Deploy this to Cloudflare Workers and update PROXY_BASE in your Django settings
 */

const ALLOWED_ORIGINS = [
    "https://app.matchgen.app", 
    "http://localhost:3000",
    "https://matchgen.app"
];

const MAX_AGE = 10800; // 3 hours in seconds
const TIMEOUT_MS = 30000; // 30 seconds

export default {
    async fetch(request, env, ctx) {
        // Handle CORS preflight
        if (request.method === 'OPTIONS') {
            return handleCors(request);
        }

        // Only allow GET requests
        if (request.method !== 'GET') {
            return new Response('Method not allowed', { status: 405 });
        }

        const url = new URL(request.url);
        const target = url.searchParams.get('url');
        
        // Validate target URL
        if (!target || !/^https:\/\/fulltime\.thefa\.com\/.+/.test(target)) {
            return new Response('Invalid target URL. Must be a fulltime.thefa.com URL.', { 
                status: 400,
                headers: getCorsHeaders(request)
            });
        }

        try {
            // Check cache first
            const cache = caches.default;
            const cacheKey = new Request(target, { method: 'GET' });
            let response = await cache.match(cacheKey);

            if (!response) {
                // Fetch from upstream with timeout
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_MS);

                try {
                    const upstreamResponse = await fetch(target, {
                        headers: {
                            'User-Agent': 'MatchGenBot/1.0 (support@matchgen.app)',
                            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                            'Accept-Language': 'en-US,en;q=0.5',
                            'Accept-Encoding': 'gzip, deflate',
                            'Connection': 'keep-alive',
                            'Upgrade-Insecure-Requests': '1',
                        },
                        signal: controller.signal
                    });

                    clearTimeout(timeoutId);

                    if (!upstreamResponse.ok) {
                        return new Response(
                            `Upstream error: ${upstreamResponse.status} ${upstreamResponse.statusText}`, 
                            { 
                                status: upstreamResponse.status,
                                headers: getCorsHeaders(request)
                            }
                        );
                    }

                    // Clone response for caching
                    const responseText = await upstreamResponse.text();
                    response = new Response(responseText, {
                        status: upstreamResponse.status,
                        statusText: upstreamResponse.statusText,
                        headers: {
                            ...Object.fromEntries(upstreamResponse.headers),
                            'Cache-Control': `public, max-age=${MAX_AGE}`,
                            'X-Cache': 'MISS'
                        }
                    });

                    // Cache the response
                    await cache.put(cacheKey, response.clone());
                    
                } catch (error) {
                    clearTimeout(timeoutId);
                    
                    if (error.name === 'AbortError') {
                        return new Response('Request timeout', { 
                            status: 408,
                            headers: getCorsHeaders(request)
                        });
                    }
                    
                    throw error;
                }
            } else {
                // Add cache hit header
                response = new Response(await response.text(), {
                    status: response.status,
                    statusText: response.statusText,
                    headers: {
                        ...Object.fromEntries(response.headers),
                        'X-Cache': 'HIT'
                    }
                });
            }

            // Add CORS headers to response
            const corsHeaders = getCorsHeaders(request);
            const finalResponse = new Response(await response.text(), {
                status: response.status,
                statusText: response.statusText,
                headers: {
                    ...Object.fromEntries(response.headers),
                    ...corsHeaders
                }
            });

            return finalResponse;

        } catch (error) {
            console.error('Proxy error:', error);
            return new Response(
                `Proxy error: ${error.message}`, 
                { 
                    status: 500,
                    headers: getCorsHeaders(request)
                }
            );
        }
    }
};

function handleCors(request) {
    return new Response(null, {
        status: 204,
        headers: getCorsHeaders(request)
    });
}

function getCorsHeaders(request) {
    const origin = request.headers.get('Origin') || '';
    const isAllowed = ALLOWED_ORIGINS.includes(origin);
    
    return {
        'Access-Control-Allow-Origin': isAllowed ? origin : ALLOWED_ORIGINS[0],
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        'Access-Control-Max-Age': '86400', // 24 hours
        'Vary': 'Origin'
    };
}

