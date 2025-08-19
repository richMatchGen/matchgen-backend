// Frontend Debugging Script for Constant API Calls
// Add this to your frontend to identify the issue

// 1. Intercept all fetch requests to track API calls
const originalFetch = window.fetch;
const apiCalls = new Map();

window.fetch = function(...args) {
  const url = args[0];
  const timestamp = new Date().toISOString();
  
  // Track API calls to our endpoints
  if (typeof url === 'string' && url.includes('/api/')) {
    const key = `${url}_${timestamp}`;
    apiCalls.set(key, {
      url,
      timestamp,
      stack: new Error().stack
    });
    
    console.log(`🔍 API Call: ${url} at ${timestamp}`);
    
    // Log if it's one of the problematic endpoints
    if (url.includes('/api/users/my-club/') || url.includes('/api/content/matches/')) {
      console.warn(`⚠️  CONSTANT API CALL DETECTED: ${url}`);
      console.warn(`📊 Total calls to this endpoint: ${Array.from(apiCalls.values()).filter(call => call.url === url).length}`);
      
      // Show stack trace for debugging
      const stack = new Error().stack;
      console.warn(`📍 Stack trace:`, stack);
      
      // Check if it's coming from GenPosts
      if (stack.includes('GenPosts')) {
        console.error(`🚨 GENPOSTS COMPONENT DETECTED AS SOURCE!`);
        console.error(`This is likely the cause of the constant API calls.`);
      }
    }
  }
  
  return originalFetch.apply(this, args);
};

// 2. Monitor useEffect calls specifically in GenPosts
const originalUseEffect = React.useEffect;
React.useEffect = function(effect, deps) {
  const stack = new Error().stack;
  if (stack.includes('GenPosts')) {
    console.warn(`🔧 GenPosts useEffect called with deps:`, deps);
    console.warn(`📍 GenPosts useEffect stack:`, stack);
  }
  return originalUseEffect.call(this, effect, deps);
};

// 3. Monitor setInterval calls
const originalSetInterval = window.setInterval;
window.setInterval = function(callback, delay, ...args) {
  const stack = new Error().stack;
  if (stack.includes('GenPosts')) {
    console.error(`⏰ GenPosts setInterval called with delay: ${delay}ms`);
    console.error(`📍 GenPosts setInterval stack:`, stack);
  }
  return originalSetInterval.call(this, callback, delay, ...args);
};

// 4. Monitor setTimeout calls
const originalSetTimeout = window.setTimeout;
window.setTimeout = function(callback, delay, ...args) {
  const stack = new Error().stack;
  if (stack.includes('GenPosts') && delay < 5000) {
    console.warn(`⏱️  GenPosts setTimeout called with delay: ${delay}ms`);
    console.warn(`📍 GenPosts setTimeout stack:`, stack);
  }
  return originalSetTimeout.call(this, callback, delay, ...args);
};

// 5. Monitor error handling that might trigger re-fetches
const originalConsoleError = console.error;
console.error = function(...args) {
  const message = args.join(' ');
  if (message.includes('User might not have a club yet') || 
      message.includes('429') || 
      message.includes('Too Many Requests')) {
    console.warn(`🚨 ERROR HANDLING DETECTED:`, message);
    console.warn(`📍 Error stack:`, new Error().stack);
  }
  return originalConsoleError.apply(this, args);
};

// 6. API call summary function
window.debugApiCalls = function() {
  console.log('📊 API Call Summary:');
  const summary = {};
  
  apiCalls.forEach((call, key) => {
    if (!summary[call.url]) {
      summary[call.url] = 0;
    }
    summary[call.url]++;
  });
  
  Object.entries(summary).forEach(([url, count]) => {
    console.log(`${url}: ${count} calls`);
  });
  
  return summary;
};

// 7. Clear API call history
window.clearApiCallHistory = function() {
  apiCalls.clear();
  console.log('🗑️  API call history cleared');
};

// 8. Auto-log every 5 seconds with GenPosts focus
setInterval(() => {
  const summary = window.debugApiCalls();
  const myClubCalls = summary['/api/users/my-club/'] || 0;
  const matchesCalls = summary['/api/content/matches/'] || 0;
  
  if (myClubCalls > 3 || matchesCalls > 3) {
    console.error(`🚨 HIGH API CALL RATE FROM GENPOSTS!`);
    console.error(`MyClub: ${myClubCalls} calls, Matches: ${matchesCalls} calls`);
    console.error(`🔧 Check GenPosts component for: useEffect, setInterval, or error handling loops`);
  }
}, 5000);

console.log('🔍 Enhanced GenPosts debugging script loaded!');
console.log('Use debugApiCalls() to see API call summary');
console.log('Use clearApiCallHistory() to clear history');
console.log('🚨 Focus on GenPosts component - this is likely the source!');
