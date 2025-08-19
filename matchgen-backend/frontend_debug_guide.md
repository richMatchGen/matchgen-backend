# Frontend Debugging Guide - Constant API Calls

## Problem
The `/api/users/my-club/` and `/api/content/matches/` endpoints are being called constantly when on the `/gen/posts` page.

## Common Causes & Solutions

### 1. React useEffect with Missing Dependencies

**Problem:**
```javascript
useEffect(() => {
  fetchMyClub();
  fetchMatches();
}, []); // Empty dependency array but functions are not memoized
```

**Solution:**
```javascript
const fetchMyClub = useCallback(async () => {
  // fetch logic
}, []);

const fetchMatches = useCallback(async () => {
  // fetch logic
}, []);

useEffect(() => {
  fetchMyClub();
  fetchMatches();
}, [fetchMyClub, fetchMatches]);
```

### 2. State Updates Causing Re-renders

**Problem:**
```javascript
const [data, setData] = useState(null);

useEffect(() => {
  fetchData().then(setData);
}, []); // This might re-run if component re-mounts
```

**Solution:**
```javascript
const [data, setData] = useState(null);
const [isLoading, setIsLoading] = useState(false);

useEffect(() => {
  if (!data && !isLoading) {
    setIsLoading(true);
    fetchData()
      .then(setData)
      .finally(() => setIsLoading(false));
  }
}, [data, isLoading]);
```

### 3. Polling/Interval Issues

**Problem:**
```javascript
useEffect(() => {
  const interval = setInterval(() => {
    fetchMyClub();
    fetchMatches();
  }, 1000);
  
  return () => clearInterval(interval);
}, []);
```

**Solution:**
```javascript
useEffect(() => {
  // Only poll if needed
  if (needsPolling) {
    const interval = setInterval(() => {
      fetchMyClub();
      fetchMatches();
    }, 5000); // Increase interval
    
    return () => clearInterval(interval);
  }
}, [needsPolling]);
```

### 4. Component Re-mounting

**Problem:**
```javascript
// Parent component re-renders causing child to re-mount
<GenPosts key={someChangingValue} />
```

**Solution:**
```javascript
// Use React.memo or stable keys
const GenPosts = React.memo(() => {
  // component logic
});

// Or stable key
<GenPosts key="gen-posts" />
```

### 5. Context/State Management Issues

**Problem:**
```javascript
const { user, setUser } = useContext(UserContext);

useEffect(() => {
  if (user) {
    fetchMyClub();
  }
}, [user]); // user object might be recreated on every render
```

**Solution:**
```javascript
const { user } = useContext(UserContext);

useEffect(() => {
  if (user?.id) { // Use specific property
    fetchMyClub();
  }
}, [user?.id]); // Only depend on specific property
```

## Debugging Steps

### 1. Check Browser Network Tab
- Open DevTools → Network tab
- Filter by "Fetch/XHR"
- Look for repeated calls to the same endpoints
- Check the timing between calls

### 2. Add Console Logs
```javascript
useEffect(() => {
  console.log('useEffect triggered', new Date().toISOString());
  fetchMyClub();
}, [dependencies]);
```

### 3. Check Component Re-renders
```javascript
console.log('Component rendered', new Date().toISOString());
```

### 4. Use React DevTools Profiler
- Install React DevTools
- Use Profiler to see what's causing re-renders

## Quick Fixes to Try

### 1. Add Request Deduplication
```javascript
const fetchMyClub = useCallback(async () => {
  if (isLoading) return; // Prevent concurrent requests
  
  setIsLoading(true);
  try {
    const response = await api.get('/api/users/my-club/');
    setClubData(response.data);
  } finally {
    setIsLoading(false);
  }
}, [isLoading]);
```

### 2. Use AbortController
```javascript
useEffect(() => {
  const abortController = new AbortController();
  
  fetchMyClub(abortController.signal);
  
  return () => abortController.abort();
}, []);
```

### 3. Implement Caching
```javascript
const [cache, setCache] = useState({});

const fetchWithCache = useCallback(async (url, cacheKey) => {
  if (cache[cacheKey] && Date.now() - cache[cacheKey].timestamp < 30000) {
    return cache[cacheKey].data;
  }
  
  const response = await api.get(url);
  setCache(prev => ({
    ...prev,
    [cacheKey]: {
      data: response.data,
      timestamp: Date.now()
    }
  }));
  
  return response.data;
}, [cache]);
```

## Backend Monitoring

The backend now logs:
- When `/api/users/my-club/` is called
- When `/api/content/matches/` is called
- Request headers and timing
- User information

Check the Railway logs to see the frequency and pattern of calls.

## Expected Behavior

- **Initial load**: 1 call to each endpoint
- **User interaction**: Calls only when needed
- **No polling**: Unless explicitly implemented
- **Reasonable intervals**: If polling, use 5+ seconds

## Next Steps

1. Check the browser console for any errors
2. Look at the Network tab timing
3. Add the debugging logs to your frontend
4. Check if any polling mechanisms are active
5. Review useEffect dependencies
