// CFL Fantasy Optimizer - Configuration
// Shared configuration for environment detection and API URLs

console.log('[CFL Config] Loading configuration...');

// API Configuration
const API_CONFIG = {
    // Production URLs (Render deployment)
    PRODUCTION: {
        BASE_URL: 'https://cfl-fantasy-opto.onrender.com',
        OPTIMIZE_URL: 'https://cfl-fantasy-opto.onrender.com/optimize',
        PROJECTIONS_URL: 'https://cfl-fantasy-opto.onrender.com/projections'
    },
    
    // Development URLs (local server)
    DEVELOPMENT: {
        BASE_URL: 'http://localhost:3000',
        OPTIMIZE_URL: 'http://localhost:3000/optimize',
        PROJECTIONS_URL: 'http://localhost:3000/projections'
    }
};

// Request configuration
const REQUEST_CONFIG = {
    TIMEOUT: 30000, // 30 seconds
    DEV_CHECK_TIMEOUT: 3000, // 3 seconds for dev server check
    HEADERS: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'User-Agent': 'CFL Fantasy Optimizer Extension v1.0.0'
    }
};

// Environment detection state
let environmentDetected = false;
let currentEnvironment = 'PRODUCTION'; // Default to production
let apiUrls = API_CONFIG.PRODUCTION;

/**
 * Detect if we're in development mode by checking if localhost:3000 is accessible
 * @returns {Promise<boolean>} True if development mode detected
 */
async function detectDevelopmentMode() {
    try {
        console.log('[CFL Config] Checking for local development server...');
        
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), REQUEST_CONFIG.DEV_CHECK_TIMEOUT);
        
        const response = await fetch(`${API_CONFIG.DEVELOPMENT.BASE_URL}/health`, {
            method: 'GET',
            signal: controller.signal,
            headers: {
                'Accept': 'application/json'
            }
        });
        
        clearTimeout(timeoutId);
        
        if (response.ok) {
            console.log('[CFL Config] ✅ Local development server detected');
            return true;
        } else {
            console.log('[CFL Config] Local server responded but not healthy');
            return false;
        }
        
    } catch (error) {
        console.log('[CFL Config] Local development server not available:', error.message);
        return false;
    }
}

/**
 * Initialize environment detection and set API URLs
 * @returns {Promise<object>} API configuration object
 */
async function initializeEnvironment() {
    if (environmentDetected) {
        console.log(`[CFL Config] Environment already detected: ${currentEnvironment}`);
        return apiUrls;
    }
    
    console.log('[CFL Config] Initializing environment detection...');
    
    const isDevelopment = await detectDevelopmentMode();
    
    if (isDevelopment) {
        currentEnvironment = 'DEVELOPMENT';
        apiUrls = API_CONFIG.DEVELOPMENT;
        console.log('[CFL Config] 🔧 Using DEVELOPMENT environment');
    } else {
        currentEnvironment = 'PRODUCTION';
        apiUrls = API_CONFIG.PRODUCTION;
        console.log('[CFL Config] 🚀 Using PRODUCTION environment');
    }
    
    environmentDetected = true;
    return apiUrls;
}

/**
 * Get current API URLs (initialize if needed)
 * @returns {Promise<object>} API configuration object
 */
async function getApiUrls() {
    if (!environmentDetected) {
        return await initializeEnvironment();
    }
    return apiUrls;
}

/**
 * Get current environment name
 * @returns {string} Current environment name
 */
function getCurrentEnvironment() {
    return currentEnvironment;
}

/**
 * Build URL with query parameters
 * @param {string} baseUrl - Base API URL
 * @param {object} params - Query parameters object
 * @returns {string} Complete URL with parameters
 */
function buildUrlWithParams(baseUrl, params = {}) {
    const url = new URL(baseUrl);
    
    // Add query parameters
    Object.keys(params).forEach(key => {
        if (params[key] !== undefined && params[key] !== null) {
            url.searchParams.append(key, params[key]);
        }
    });
    
    return url.toString();
}

/**
 * Force re-detection of environment (useful for testing)
 */
function resetEnvironmentDetection() {
    console.log('[CFL Config] Resetting environment detection...');
    environmentDetected = false;
    currentEnvironment = 'PRODUCTION';
    apiUrls = API_CONFIG.PRODUCTION;
}

// Export configuration functions
// Make available globally for both window context and service workers
const CFL_CONFIG = {
    initializeEnvironment,
    getApiUrls,
    getCurrentEnvironment,
    buildUrlWithParams,
    resetEnvironmentDetection,
    REQUEST_CONFIG
};

// Make available in window context (for content scripts and popup)
if (typeof window !== 'undefined') {
    window.CFL_CONFIG = CFL_CONFIG;
}

// Make available in global context (for service workers)
if (typeof self !== 'undefined') {
    self.CFL_CONFIG = CFL_CONFIG;
}

// Also support module exports for testing
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        initializeEnvironment,
        getApiUrls,
        getCurrentEnvironment,
        buildUrlWithParams,
        resetEnvironmentDetection,
        REQUEST_CONFIG,
        API_CONFIG
    };
}

console.log('[CFL Config] Configuration loaded successfully');