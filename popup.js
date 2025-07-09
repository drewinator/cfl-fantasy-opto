// CFL Fantasy Optimizer - Popup Script
// Handles user interactions and communication with content script and optimizer


// DOM elements
let optimizeButton;
let statusText;
let loader;
let playerDataInfo;
let resultsSection;
let errorSection;
let retryButton;
let clearButton;

// Initialize popup when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    
    // Get DOM elements
    optimizeButton = document.getElementById('optimizeButton');
    statusText = document.getElementById('statusText');
    loader = document.getElementById('loader');
    playerDataInfo = document.getElementById('playerDataInfo');
    resultsSection = document.getElementById('resultsSection');
    errorSection = document.getElementById('errorSection');
    retryButton = document.getElementById('retryButton');
    clearButton = document.getElementById('clearButton');
    
    // Add event listeners
    optimizeButton.addEventListener('click', handleOptimizeClick);
    retryButton.addEventListener('click', handleRetryClick);
    clearButton.addEventListener('click', handleClearClick);
    
    // Check if we're on the CFL fantasy page
    checkCurrentPage();
    
    // Try to restore saved lineup
    loadLineupFromStorage((lineupData) => {
        if (lineupData) {
            showResults(lineupData.lineup, true, lineupData.timestamp);
        }
    });
});

// Check if current page is CFL fantasy page
async function checkCurrentPage() {
    try {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        
        if (tab.url && tab.url.includes('gamezone.cfl.ca/fantasy')) {
            updateStatus('Ready to optimize');
            optimizeButton.disabled = false;
            
            // Request player data from content script to show info
            chrome.tabs.sendMessage(tab.id, { action: 'getPlayerData' }, (response) => {
                if (response && response.success) {
                    showPlayerDataInfo(response.data);
                }
            });
        } else {
            updateStatus('Please navigate to gamezone.cfl.ca/fantasy');
            optimizeButton.disabled = true;
        }
    } catch (error) {
        console.error('[CFL Optimizer] Error checking current page:', error);
        updateStatus('Error checking page');
        optimizeButton.disabled = true;
    }
}

// Handle optimize button click
async function handleOptimizeClick() {
    try {
        // Show loading state
        showLoading();
        
        // Get current tab
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        
        // Request player data from content script
        chrome.tabs.sendMessage(tab.id, { action: 'getPlayerData' }, async (response) => {
            if (chrome.runtime.lastError) {
                console.error('[CFL Optimizer] Error communicating with content script:', chrome.runtime.lastError);
                showError('Unable to connect to page. Please refresh and try again.');
                return;
            }
            
            if (!response || !response.success) {
                console.error('[CFL Optimizer] Failed to get player data:', response?.error || 'Unknown error');
                showError('Failed to get player data. Please ensure you are on the CFL fantasy page.');
                return;
            }
            
            showPlayerDataInfo(response.data);
            
            // Send data to optimizer backend
            await optimizeLineup(response.data);
        });
        
    } catch (error) {
        console.error('[CFL Optimizer] Error in optimize process:', error);
        showError('An unexpected error occurred. Please try again.');
    }
}

// Send player data to optimizer backend
async function optimizeLineup(playerData) {
    try {
        // Get selected engine from dropdown
        const engineSelect = document.getElementById('engineSelect');
        const selectedEngine = engineSelect ? engineSelect.value : 'pulp';
        
        // Update status to show which engine is being used
        updateStatus(`Optimizing with ${selectedEngine.toUpperCase()} engine...`);
        
        // Format data for the optimizer API
        const apiRequest = {
            players: playerData.players || [],
            teams: playerData.teams || [],
            gameweeks: playerData.gameweeks || [],
            current_team: playerData.current_team || {},
            player_ownership: playerData.player_ownership || {},
            team_ownership: playerData.team_ownership || {},
            league_config: {
                salary_cap: 70000,
                roster_size: 7,
                positions: {
                    QB: 1,
                    WR: 2,
                    RB: 2,
                    FLEX: 1,
                    DEF: 1
                }
            },
            optimization_settings: {
                max_players_from_team: 3,
                use_captain: true,
                num_lineups: 1
            },
            engine: selectedEngine  // Add engine selection
        };
        
        // Send message to background script for optimization
        chrome.runtime.sendMessage({ 
            action: 'optimizeLineup', 
            data: apiRequest 
        }, (response) => {
            if (chrome.runtime.lastError) {
                console.error('[CFL Optimizer] Error communicating with background script:', chrome.runtime.lastError);
                showError('Unable to connect to the optimizer. Please check the console for more details.');
                return;
            }

            if (response.success) {
                saveLineupToStorage(response.lineup);
                showResults(response.lineup, false, null, selectedEngine);
            } else {
                console.error('[CFL Optimizer] Optimization failed:', response.error);
                showError(response.error || 'Optimization failed. Please try again.');
            }
        });
        
    } catch (error) {
        console.error('[CFL Optimizer] Error in optimization process:', error);
        
        if (error.message.includes('fetch')) {
            showError('Unable to connect to optimizer service. Please ensure the API server is running on localhost:3000.');
        } else {
            showError('Error optimizing lineup. Please try again.');
        }
    }
}

// Show loading state
function showLoading() {
    optimizeButton.disabled = true;
    statusText.textContent = 'Optimizing lineup...';
    loader.classList.remove('hidden');
    
    // Hide other sections
    playerDataInfo.classList.add('hidden');
    resultsSection.classList.add('hidden');
    errorSection.classList.add('hidden');
}

// Show player data info
function showPlayerDataInfo(playerData) {
    
    // Handle different data formats
    let playerCount = 0;
    let teamCount = 0;
    let dataSource = 'Unknown';
    
    if (playerData.players && playerData.teams) {
        // New format with separate players and teams
        playerCount = playerData.players.length;
        teamCount = playerData.teams.length;
        dataSource = playerData.source || playerData.metadata?.source || 'CFL API';
    } else if (Array.isArray(playerData)) {
        // Legacy format
        playerCount = playerData.length;
        dataSource = 'CFL Fantasy Page';
    }
    
    document.getElementById('playerCountValue').textContent = `${playerCount} players, ${teamCount} teams`;
    document.getElementById('dataSourceValue').textContent = dataSource;
    playerDataInfo.classList.remove('hidden');
}

// Show optimization results
function showResults(lineup, isRestored = false, timestamp = null, engine = null) {
    
    if (!lineup || !lineup.players) {
        showError('Invalid lineup data received');
        return;
    }
    
    // Hide loading
    loader.classList.add('hidden');
    optimizeButton.disabled = false;
    
    // Update status based on whether this is a restored lineup
    if (isRestored && timestamp) {
        const timeAgo = formatTimeAgo(timestamp);
        statusText.textContent = `Saved lineup (${timeAgo})`;
        showSavedIndicator();
    } else {
        const engineText = engine ? ` (${engine.toUpperCase()} engine)` : '';
        statusText.textContent = `Optimization complete!${engineText}`;
    }
    
    // Clear all slots first
    const allSlots = document.querySelectorAll('.position-slot');
    allSlots.forEach(slot => {
        slot.querySelector('.player-name').textContent = '-';
        slot.querySelector('.player-salary').textContent = '$0';
        slot.querySelector('.player-initials').textContent = '-';
        if (slot.querySelector('.player-points')) {
            slot.querySelector('.player-points').textContent = '0 pts';
        }
        if (slot.querySelector('.player-ownership')) {
            slot.querySelector('.player-ownership').textContent = '-';
        }
        slot.classList.remove('captain-slot');
    });
    
    // Map positions to slot names for CFL format
    const positionSlots = {
        'QB': ['QB'],
        'WR': ['WR1', 'WR2'],
        'RB': ['RB1', 'RB2'], 
        'FLEX': ['FLEX'],
        'DEF': ['DEF']
    };
    
    const usedSlots = {};
    
    // Populate lineup slots
    lineup.players.forEach(player => {
        const position = player.position;
        const availableSlots = positionSlots[position] || [];
        
        // Find first unused slot for this position
        let targetSlot = null;
        for (const slotName of availableSlots) {
            if (!usedSlots[slotName]) {
                targetSlot = slotName;
                usedSlots[slotName] = true;
                break;
            }
        }
        
        // If no direct position slot available, try FLEX
        if (!targetSlot && (position === 'WR' || position === 'RB' || position === 'TE')) {
            if (!usedSlots['FLEX']) {
                targetSlot = 'FLEX';
                usedSlots['FLEX'] = true;
            }
        }
        
        if (targetSlot) {
            const slot = document.querySelector(`.position-slot[data-position="${targetSlot}"]`);
            if (slot) {
                const playerName = player.name || 'Unknown';
                const teamAbbr = player.team ? ` (${player.team})` : '';
                const captainMarker = player.is_captain ? ' ⭐' : '';
                
                // Update player name
                slot.querySelector('.player-name').textContent = playerName + teamAbbr + captainMarker;
                
                // Update player photo/initials
                updatePlayerPhoto(slot, player);
                
                // Update salary
                slot.querySelector('.player-salary').textContent = `$${(player.salary || 0).toLocaleString()}`;
                
                // Update points
                if (slot.querySelector('.player-points')) {
                    const basePoints = player.projected_points || 0;
                    const pointsText = player.is_captain ? 
                        `${basePoints} pts (2x = ${basePoints * 2})` : 
                        `${basePoints} pts`;
                    slot.querySelector('.player-points').textContent = pointsText;
                }
                
                // Update ownership
                if (slot.querySelector('.player-ownership')) {
                    const ownershipText = formatOwnership(player.ownership || 0);
                    slot.querySelector('.player-ownership').textContent = ownershipText;
                }
                
                // Add captain styling
                if (player.is_captain) {
                    slot.classList.add('captain-slot');
                } else {
                    slot.classList.remove('captain-slot');
                }
            }
        }
    });
    
    // Update summary
    document.getElementById('totalSalary').textContent = `$${(lineup.total_salary || 0).toLocaleString()}`;
    document.getElementById('projectedPoints').textContent = lineup.projected_points || 0;
    document.getElementById('remainingCap').textContent = `$${(lineup.remaining_cap || 0).toLocaleString()}`;
    
    // Show captain bonus if available
    if (lineup.captain_bonus_points && lineup.captain_bonus_points > 0) {
        const captainInfo = document.getElementById('captainBonusInfo');
        if (captainInfo) {
            captainInfo.textContent = `Captain Bonus: +${lineup.captain_bonus_points} pts`;
            captainInfo.classList.remove('hidden');
        }
    }
    
    // Show results section
    resultsSection.classList.remove('hidden');
    errorSection.classList.add('hidden');
}

// Show error message
function showError(message) {
    
    // Hide loading
    loader.classList.add('hidden');
    optimizeButton.disabled = false;
    statusText.textContent = 'Error occurred';
    
    // Show error section
    document.getElementById('errorMessage').textContent = message;
    errorSection.classList.remove('hidden');
    resultsSection.classList.add('hidden');
}

// Handle retry button click
function handleRetryClick() {
    // Hide error section
    errorSection.classList.add('hidden');
    
    // Reset status
    updateStatus('Ready to optimize');
    
    // Re-enable optimize button
    optimizeButton.disabled = false;
}

function handleClearClick() {
    clearLineupFromStorage();
    
    // Hide results and clear button
    resultsSection.classList.add('hidden');
    clearButton.classList.add('hidden');
    
    // Reset status
    statusText.textContent = 'Ready to optimize';
}

// Update status text
function updateStatus(message) {
    statusText.textContent = message;
}

// Listen for messages from content script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'playerDataUpdated') {
        showPlayerDataInfo(request.data);
    }
    
    sendResponse({ success: true });
});

// Local storage functions for lineup persistence
function saveLineupToStorage(lineup) {
    try {
        const lineupData = {
            lineup: lineup,
            timestamp: Date.now(),
            date: new Date().toISOString(),
            version: '1.0'
        };
        
        chrome.storage.local.set({ 'cfl_optimizer_lineup': lineupData }, () => {
            if (chrome.runtime.lastError) {
                console.error('[CFL Optimizer] Error saving lineup:', chrome.runtime.lastError);
            } else {
                showSavedIndicator();
            }
        });
    } catch (error) {
        console.error('[CFL Optimizer] Error saving lineup to storage:', error);
    }
}

function loadLineupFromStorage(callback) {
    try {
        chrome.storage.local.get(['cfl_optimizer_lineup'], (result) => {
            if (chrome.runtime.lastError) {
                console.error('[CFL Optimizer] Error loading lineup:', chrome.runtime.lastError);
                callback(null);
                return;
            }
            
            const lineupData = result.cfl_optimizer_lineup;
            if (lineupData) {
                // Check if lineup is less than 24 hours old
                const now = Date.now();
                const ageHours = (now - lineupData.timestamp) / (1000 * 60 * 60);
                
                if (ageHours < 24) {
                    callback(lineupData);
                } else {
                    clearLineupFromStorage();
                    callback(null);
                }
            } else {
                callback(null);
            }
        });
    } catch (error) {
        console.error('[CFL Optimizer] Error loading lineup from storage:', error);
        callback(null);
    }
}

function clearLineupFromStorage() {
    try {
        chrome.storage.local.remove(['cfl_optimizer_lineup'], () => {
            if (chrome.runtime.lastError) {
                console.error('[CFL Optimizer] Error clearing lineup:', chrome.runtime.lastError);
            } else {
                hideSavedIndicator();
            }
        });
    } catch (error) {
        console.error('[CFL Optimizer] Error clearing lineup from storage:', error);
    }
}

function showSavedIndicator() {
    // Add visual indicator that lineup is saved
    const indicator = document.getElementById('savedIndicator');
    if (indicator) {
        indicator.textContent = '💾 Lineup saved';
        indicator.classList.remove('hidden');
    }
    
    // Show clear button
    if (clearButton) {
        clearButton.classList.remove('hidden');
    }
}

function hideSavedIndicator() {
    const indicator = document.getElementById('savedIndicator');
    if (indicator) {
        indicator.classList.add('hidden');
    }
    
    // Hide clear button
    if (clearButton) {
        clearButton.classList.add('hidden');
    }
}

function formatTimeAgo(timestamp) {
    const now = Date.now();
    const diff = now - timestamp;
    const minutes = Math.floor(diff / (1000 * 60));
    const hours = Math.floor(minutes / 60);
    
    if (hours > 0) {
        return `${hours} hour${hours > 1 ? 's' : ''} ago`;
    } else if (minutes > 0) {
        return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
    } else {
        return 'just now';
    }
}

function updatePlayerPhoto(slot, player) {
    const photoElement = slot.querySelector('.player-photo');
    const initialsElement = slot.querySelector('.player-initials');
    
    if (!photoElement || !initialsElement) return;
    
    // Try to get player initials
    const name = player.name || '';
    const nameParts = name.split(' ');
    let initials = '';
    
    if (nameParts.length >= 2) {
        initials = nameParts[0].charAt(0) + nameParts[nameParts.length - 1].charAt(0);
    } else if (nameParts.length === 1) {
        initials = nameParts[0].charAt(0);
    } else {
        initials = '?';
    }
    
    // Set team colors based on team abbreviation
    const teamColors = {
        'OTT': '#c8102e', 'TOR': '#00205b', 'HAM': '#ffb81c', 'MTL': '#c8102e',
        'SSK': '#006747', 'WPG': '#041e42', 'CGY': '#c8102e', 'EDM': '#00471b', 'BC': '#f47920'
    };
    
    const teamColor = teamColors[player.team] || '#666';
    photoElement.style.backgroundColor = teamColor + '20'; // Light version
    photoElement.style.borderColor = teamColor;
    photoElement.style.color = teamColor;
    
    initialsElement.textContent = initials.toUpperCase();
    
    // TODO: In the future, we could try to load actual player photos
    // const photoUrl = `https://cfl.ca/players/${player.id}/photo.jpg`;
    // But for now, we'll use initials with team colors
}

function formatOwnership(ownershipPercent) {
    if (!ownershipPercent || ownershipPercent === 0) {
        return '-';
    }
    
    return `${ownershipPercent.toFixed(1)}%`;
}