// CFL Fantasy Optimizer - Background Script / Optimizer Bridge
// Handles communication with the Python backend optimizer service

// Import configuration
importScripts('config.js');

console.log('[CFL Optimizer] Background script (optimizer bridge) loaded');

// Listen for messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    console.log('[CFL Optimizer] Message received in background script:', request);
    
    if (request.action === 'optimizeLineup') {
        console.log('[CFL Optimizer] Processing optimization request...');
        
        // Handle optimization request asynchronously
        handleOptimizationRequest(request.data)
            .then(result => {
                console.log('[CFL Optimizer] Optimization completed successfully');

                sendResponse({
                    success: true,
                    lineup: result
                });
            })
            .catch(error => {
                console.error('[CFL Optimizer] Optimization failed:', error);
                sendResponse({
                    success: false,
                    error: error.message || 'Optimization failed'
                });
            });
        
        // Return true to indicate we will send a response asynchronously
        return true;
    }
});

// Handle optimization request
async function handleOptimizationRequest(data) {
    console.log('[CFL Optimizer] Starting optimization process...');
    
    try {
        // Send request to optimizer backend
        const result = await sendOptimizationRequest(data);
        
        console.log('[CFL Optimizer] Optimization process completed successfully');
        return result.lineup;
        
    } catch (error) {
        console.error('[CFL Optimizer] Error in optimization process:', error);
        throw error;
    }
}

// Send optimization request to backend
async function sendOptimizationRequest(data) {
    console.log('[CFL Optimizer] Sending optimization request to backend...');
    
    try {
        // Get API URLs based on environment
        const apiUrls = await CFL_CONFIG.getApiUrls();
        console.log('[CFL Optimizer] Using environment:', CFL_CONFIG.getCurrentEnvironment());
        
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), CFL_CONFIG.REQUEST_CONFIG.TIMEOUT);
        
        // Build URL with parameters
        const params = {
            engine: data.engine || 'pulp',
            source: data.source || 'our'
        };
        
        const url = CFL_CONFIG.buildUrlWithParams(apiUrls.OPTIMIZE_URL, params);
        console.log(`[CFL Optimizer] Request URL: ${url}`);
        
        const response = await fetch(url, {
            method: 'POST',
            headers: CFL_CONFIG.REQUEST_CONFIG.HEADERS,
            body: JSON.stringify(data),
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`HTTP ${response.status}: ${errorText}`);
        }
        
        const responseData = await response.json();
        console.log('[CFL Optimizer] Received response from optimizer:', responseData);
        
        return responseData;
        
    } catch (error) {
        console.error('[CFL Optimizer] Error sending optimization request:', error);
        
        if (error.name === 'AbortError') {
            throw new Error('Request timed out. Please try again.');
        }
        
        if (error.message.includes('Failed to fetch')) {
            throw new Error('Unable to connect to optimizer service. Please check your internet connection.');
        }
        
        throw new Error('Optimization request failed: ' + error.message);
    }
}



// Handle extension installation
chrome.runtime.onInstalled.addListener((details) => {
    console.log('[CFL Optimizer] Extension installed/updated:', details.reason);
    
    if (details.reason === 'install') {
        console.log('[CFL Optimizer] First time installation');
        
        // Set up default configuration
        chrome.storage.sync.set({
            optimizerUrl: OPTIMIZER_API_URL,
            salaryCap: 100000,
            requestTimeout: REQUEST_TIMEOUT,
            enableLogging: true
        });
    }
});

// Handle extension startup
chrome.runtime.onStartup.addListener(() => {
    console.log('[CFL Optimizer] Extension startup');
});

// Utility function to log errors to storage for debugging
function logError(error, context) {
    console.error(`[CFL Optimizer] Error in ${context}:`, error);
    
    // Store error in local storage for debugging
    chrome.storage.local.get(['errorLog'], (result) => {
        const errorLog = result.errorLog || [];
        errorLog.push({
            timestamp: new Date().toISOString(),
            context: context,
            error: error.message,
            stack: error.stack
        });
        
        // Keep only last 50 errors
        if (errorLog.length > 50) {
            errorLog.splice(0, errorLog.length - 50);
        }
        
        chrome.storage.local.set({ errorLog: errorLog });
    });
}

// Export functions for testing (if needed)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        validatePlayerData,
        formatDataForOptimizer,
        formatOptimizerResponse
    };
}