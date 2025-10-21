# Cloudflare Worker Deployment Guide

This guide explains how to deploy the FA Fulltime proxy worker to Cloudflare Workers.

## Prerequisites

1. **Cloudflare Account**: Sign up at [cloudflare.com](https://cloudflare.com)
2. **Wrangler CLI**: Install the Cloudflare Workers CLI
   ```bash
   npm install -g wrangler
   ```

## Deployment Steps

### 1. Login to Cloudflare

```bash
wrangler login
```

### 2. Initialize Worker Project

```bash
mkdir fulltime-proxy
cd fulltime-proxy
wrangler init
```

### 3. Replace the Generated Code

Replace the contents of `src/index.js` with the code from `workers/fulltime-proxy.js`:

```bash
cp ../workers/fulltime-proxy.js src/index.js
```

### 4. Configure wrangler.toml

Create or update `wrangler.toml`:

```toml
name = "fulltime-proxy"
main = "src/index.js"
compatibility_date = "2024-01-01"

[env.production]
name = "fulltime-proxy-prod"
```

### 5. Deploy the Worker

```bash
# Deploy to production
wrangler deploy

# Or deploy to preview first
wrangler deploy --env preview
```

### 6. Update Django Settings

After deployment, update the `PROXY_BASE` in your Django views:

```python
# In matchgen-backend/content/views.py
PROXY_BASE = "https://fulltime-proxy.your-subdomain.workers.dev"
```

## Testing the Worker

### 1. Test Basic Functionality

```bash
curl "https://your-worker.workers.dev?url=https://fulltime.thefa.com/displayTeam.html?id=562720767"
```

### 2. Test CORS Headers

```bash
curl -H "Origin: https://app.matchgen.app" \
     "https://your-worker.workers.dev?url=https://fulltime.thefa.com/displayTeam.html?id=562720767"
```

### 3. Test Caching

Make the same request twice and check for `X-Cache: HIT` header on the second request.

## Configuration Options

### Allowed Origins

Update the `ALLOWED_ORIGINS` array in the worker code to include your domains:

```javascript
const ALLOWED_ORIGINS = [
    "https://app.matchgen.app", 
    "http://localhost:3000",
    "https://matchgen.app",
    "https://your-custom-domain.com"
];
```

### Cache Duration

Modify the `MAX_AGE` constant to change cache duration:

```javascript
const MAX_AGE = 10800; // 3 hours in seconds
```

### Timeout Settings

Adjust the timeout for upstream requests:

```javascript
const TIMEOUT_MS = 30000; // 30 seconds
```

## Monitoring and Debugging

### 1. View Logs

```bash
wrangler tail
```

### 2. Monitor Analytics

Visit the Cloudflare Workers dashboard to see:
- Request volume
- Error rates
- Cache hit ratios
- Response times

### 3. Debug Issues

Common issues and solutions:

**Issue**: Worker returns 500 errors
**Solution**: Check the worker logs with `wrangler tail`

**Issue**: CORS errors in browser
**Solution**: Verify your domain is in `ALLOWED_ORIGINS`

**Issue**: Timeout errors
**Solution**: Increase `TIMEOUT_MS` or check FA website availability

**Issue**: Cache not working
**Solution**: Check that `Cache-Control` headers are being set correctly

## Production Considerations

### 1. Rate Limiting

Consider adding rate limiting to prevent abuse:

```javascript
// Add to worker code
const RATE_LIMIT = 100; // requests per hour per IP
```

### 2. Error Handling

The worker includes comprehensive error handling for:
- Invalid URLs
- Network timeouts
- Upstream errors
- CORS violations

### 3. Security

The worker:
- Validates target URLs (only allows fulltime.thefa.com)
- Sets appropriate CORS headers
- Includes timeout protection
- Uses proper User-Agent headers

## Troubleshooting

### Common Issues

1. **Worker not responding**: Check if it's deployed correctly
2. **CORS errors**: Verify allowed origins
3. **Timeout errors**: FA website may be slow or down
4. **Cache issues**: Clear cache or wait for expiration

### Support

For issues with the worker:
1. Check Cloudflare Workers documentation
2. Review worker logs with `wrangler tail`
3. Test with curl to isolate issues
4. Verify FA website accessibility

## Cost Considerations

Cloudflare Workers pricing:
- **Free tier**: 100,000 requests/day
- **Paid tier**: $5/month for 10M requests
- **Additional**: $0.50 per 1M requests

For most applications, the free tier should be sufficient.
