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
    console.log(`📍 Stack trace:`, new Error().stack);
    
    // Log if it's one of the problematic endpoints
    if (url.includes('/api/users/my-club/') || url.includes('/api/content/matches/')) {
      console.warn(`⚠️  CONSTANT API CALL DETECTED: ${url}`);
      console.warn(`📊 Total calls to this endpoint: ${Array.from(apiCalls.values()).filter(call => call.url === url).length}`);
    }
  }
  
  return originalFetch.apply(this, args);
};

// 2. Monitor useEffect calls
const originalUseEffect = React.useEffect;
React.useEffect = function(effect, deps) {
  console.log(`🔧 useEffect called with deps:`, deps);
  console.log(`📍 useEffect stack:`, new Error().stack);
  return originalUseEffect.call(this, effect, deps);
};

// 3. Monitor setInterval calls
const originalSetInterval = window.setInterval;
window.setInterval = function(callback, delay, ...args) {
  console.warn(`⏰ setInterval called with delay: ${delay}ms`);
  console.warn(`📍 setInterval stack:`, new Error().stack);
  return originalSetInterval.call(this, callback, delay, ...args);
};

// 4. Monitor setTimeout calls
const originalSetTimeout = window.setTimeout;
window.setTimeout = function(callback, delay, ...args) {
  if (delay < 5000) { // Only log short timeouts
    console.log(`⏱️  setTimeout called with delay: ${delay}ms`);
    console.log(`📍 setTimeout stack:`, new Error().stack);
  }
  return originalSetTimeout.call(this, callback, delay, ...args);
};

// 5. API call summary function
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

// 6. Clear API call history
window.clearApiCallHistory = function() {
  apiCalls.clear();
  console.log('🗑️  API call history cleared');
};

// 7. Monitor component renders
const originalRender = React.Component.prototype.render;
React.Component.prototype.render = function() {
  console.log(`🎨 Component rendered: ${this.constructor.name}`);
  return originalRender.call(this);
};

// 8. Auto-log every 10 seconds
setInterval(() => {
  const summary = window.debugApiCalls();
  const myClubCalls = summary['/api/users/my-club/'] || 0;
  const matchesCalls = summary['/api/content/matches/'] || 0;
  
  if (myClubCalls > 5 || matchesCalls > 5) {
    console.error(`🚨 HIGH API CALL RATE DETECTED!`);
    console.error(`MyClub: ${myClubCalls} calls, Matches: ${matchesCalls} calls`);
  }
}, 10000);

console.log('🔍 Frontend debugging script loaded!');
console.log('Use debugApiCalls() to see API call summary');
console.log('Use clearApiCallHistory() to clear history');
