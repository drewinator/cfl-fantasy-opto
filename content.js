// CFL Fantasy Optimizer - Content Script
// Injected into gamezone.cfl.ca/fantasy/* to scrape player data

console.log('[CFL Optimizer] Content script loaded');

// Global variables
let playerData = [];
let isDataLoaded = false;
let directApiFetchSuccessful = false;
let projectionsCache = null;
let projectionsCacheTime = null;
const PROJECTIONS_CACHE_DURATION = 60 * 60 * 1000; // 60 minutes in milliseconds

// Initialize content script
initialize();

function initialize() {
    // Wait for page to fully load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', startDataCollection);
    } else {
        startDataCollection();
    }
    
    // For React SPAs, also wait for the app to be ready
    waitForReactApp();
}

function waitForReactApp() {
    console.log('[CFL Optimizer] Waiting for React app to load...');
    
    // Check if React root exists and has content
    const checkReactReady = () => {
        const root = document.querySelector('#root');
        if (root && root.children.length > 0) {
            console.log('[CFL Optimizer] React app loaded successfully');
            return true;
        }
        return false;
    };
    
    // If already ready, return immediately
    if (checkReactReady()) {
        return;
    }
    
    // Set up observer to watch for React app loading
    const observer = new MutationObserver((mutations) => {
        if (checkReactReady()) {
            console.log('[CFL Optimizer] React app detected via MutationObserver');
            observer.disconnect();
        }
    });
    
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
    
    // Also set up a timeout fallback
    setTimeout(() => {
        observer.disconnect();
        console.log('[CFL Optimizer] React app wait timeout reached');
    }, 10000); // 10 second timeout
}

// Start collecting player data
function startDataCollection() {
    // Try direct API fetching
    tryDirectApiFetching();
}

// Try fetching CFL APIs directly
async function tryDirectApiFetching() {
    
    const cflApiEndpoints = [
        'https://gamezone.cfl.ca/json/fantasy/players.json',
        'https://gamezone.cfl.ca/json/fantasy/playersSelection.json',
        'https://gamezone.cfl.ca/json/fantasy/squads.json',
        'https://gamezone.cfl.ca/json/fantasy/squadsSelection.json',
        'https://gamezone.cfl.ca/json/fantasy/gameweeks.json',
        'https://gamezone.cfl.ca/fantasy/api/en/fantasy/ranking/gamebar',
        'https://gamezone.cfl.ca/fantasy/api/en/fantasy/team'
    ];
    
    let allPlayers = [];
    let allTeams = [];
    let gameweeksData = [];
    let currentTeamData = {};
    let ownershipData = {};
    let teamOwnershipData = {};
    
    for (const url of cflApiEndpoints) {
        try {
            const response = await fetch(url);
            const data = await response.json();
            
            // Extract data based on endpoint type
            if (url.includes('players.json')) {
                const players = extractPlayersFromCflPlayersApi(data);
                if (players.length > 0) {
                    allPlayers = players; // Use latest player data
                }
            } else if (url.includes('playersSelection.json')) {
                // This contains ownership data, not player data
                ownershipData = extractOwnershipFromPlayersSelection(data);
            } else if (url.includes('squads.json')) {
                const teams = extractTeamsFromCflSquadsApi(data);
                if (teams.length > 0) {
                    allTeams = teams;
                }
            } else if (url.includes('squadsSelection.json')) {
                // This contains team ownership data
                teamOwnershipData = extractTeamOwnershipFromSquadsSelection(data);
            } else if (url.includes('gameweeks.json')) {
                gameweeksData = Array.isArray(data) ? data : [];
            } else if (url.includes('team.json')) {
                currentTeamData = data;
            }
            
        } catch (error) {
            console.log(`[CFL Optimizer] API fetch failed for ${url}:`, error);
        }
    }
    
    // If we got data from any endpoint, update
    if (allPlayers.length > 0 || allTeams.length > 0) {
        // If we have players but no teams, create teams from player data
        if (allPlayers.length > 0 && allTeams.length === 0) {
            allTeams = createTeamsFromPlayerData(allPlayers);
        }
        
        console.log(`[CFL Optimizer] Data loaded: ${allPlayers.length} players, ${allTeams.length} teams`);
        directApiFetchSuccessful = true;
        
        // Fetch projections and merge with player data
        await fetchProjectionsAndMerge(allPlayers);
        
        updatePlayerData(allPlayers, allTeams, gameweeksData, currentTeamData, ownershipData, teamOwnershipData);
    }
}






// Update player data and notify popup
function updatePlayerData(newPlayers, newTeams = [], gameweeksData = [], currentTeamData = {}, ownershipData = {}, teamOwnershipData = {}) {
    
    // Structure data properly for the optimizer API
    playerData = {
        players: newPlayers,
        teams: newTeams,
        gameweeks: gameweeksData,
        current_team: currentTeamData,
        player_ownership: ownershipData,
        team_ownership: teamOwnershipData,
        source: 'CFL Fantasy Page',
        metadata: {
            source: 'content_script',
            timestamp: new Date().toISOString(),
            playerCount: newPlayers.length,
            teamCount: newTeams.length,
            gameweekCount: gameweeksData.length
        }
    };
    
    isDataLoaded = true;
    
    // Notify popup about data update
    chrome.runtime.sendMessage({
        action: 'playerDataUpdated',
        data: playerData
    }).catch(error => {
        console.log('[CFL Optimizer] Popup not available:', error);
    });
}



// Extract players from CFL players.json API
function extractPlayersFromCflPlayersApi(data) {
    const players = [];
    
    try {
        // CFL players.json likely has players array or object
        const playersData = data.players || data.data || data;
        
        if (Array.isArray(playersData)) {
            playersData.forEach(player => {
                // Pass raw player data directly to backend (don't normalize)
                if (player && typeof player === 'object' && player.firstName && player.lastName) {
                    players.push(player);
                }
            });
        } else if (typeof playersData === 'object') {
            // Handle object format where players might be nested
            Object.values(playersData).forEach(player => {
                if (typeof player === 'object' && player.firstName && player.lastName) {
                    // Pass raw player data directly to backend (don't normalize)
                    players.push(player);
                }
            });
        }
        
    } catch (error) {
        console.error('[CFL Optimizer] Error extracting from CFL players API:', error);
    }
    
    return players;
}

// Extract ownership data from CFL playersSelection.json API
function extractOwnershipFromPlayersSelection(data) {
    const ownershipData = {};
    
    try {
        // playersSelection.json format: {"player_id": {"number": count, "percents": percentage}}
        if (typeof data === 'object' && data !== null) {
            Object.keys(data).forEach(playerId => {
                const playerOwnership = data[playerId];
                if (playerOwnership && typeof playerOwnership === 'object') {
                    // Convert to the format expected by the backend
                    ownershipData[playerId] = {
                        percents: playerOwnership.percents || 0,
                        number: playerOwnership.number || 0
                    };
                }
            });
        }
        
        
    } catch (error) {
        console.error('[CFL Optimizer] Error extracting ownership data:', error);
    }
    
    return ownershipData;
}

// Extract team ownership data from CFL squadsSelection.json API
function extractTeamOwnershipFromSquadsSelection(data) {
    const teamOwnershipData = {};
    
    try {
        // squadsSelection.json should contain team ownership data
        // Format: {"team_id": {"number": count, "percents": percentage}}
        if (typeof data === 'object' && data !== null) {
            Object.keys(data).forEach(teamId => {
                const teamOwnership = data[teamId];
                if (teamOwnership && typeof teamOwnership === 'object') {
                    // Convert to the format expected by the backend
                    teamOwnershipData[teamId] = {
                        percents: teamOwnership.percents || 0,
                        number: teamOwnership.number || 0
                    };
                }
            });
        }
        
    } catch (error) {
        console.error('[CFL Optimizer] Error extracting team ownership data:', error);
    }
    
    return teamOwnershipData;
}


// Extract teams from CFL squads.json API
function extractTeamsFromCflSquadsApi(data) {
    const teams = [];
    
    try {
        // Handle different possible data structures
        let squadsData = data;
        
        // Check if data is wrapped in an object
        if (data.squads && Array.isArray(data.squads)) {
            squadsData = data.squads;
        } else if (data.data && Array.isArray(data.data)) {
            squadsData = data.data;
        } else if (Array.isArray(data)) {
            squadsData = data;
        }
        
        if (Array.isArray(squadsData)) {
            squadsData.forEach(squad => {
                const normalizedTeam = normalizeCflTeam(squad);
                if (normalizedTeam) {
                    teams.push(normalizedTeam);
                }
            });
        }
        
    } catch (error) {
        console.error('[CFL Optimizer] Error extracting teams from CFL squads API:', error);
    }
    
    return teams;
}

// Normalize CFL team data to our standard format
function normalizeCflTeam(rawTeam) {
    if (!rawTeam || typeof rawTeam !== 'object') return null;
    
    try {
        return {
            id: rawTeam.id || rawTeam.teamId || '',
            name: rawTeam.name || rawTeam.teamName || '',
            abbreviation: rawTeam.abbreviation || rawTeam.abbr || rawTeam.short || '',
            cost: parseInt(rawTeam.cost || rawTeam.price || rawTeam.salary || 0),
            projectedScores: parseFloat(rawTeam.projectedScores || rawTeam.points || rawTeam.projection || 0),
            // Additional fields that might be useful
            city: rawTeam.city || '',
            logoUrl: rawTeam.logoUrl || '',
            primaryColor: rawTeam.primaryColor || '',
            secondaryColor: rawTeam.secondaryColor || ''
        };
    } catch (error) {
        console.error('[CFL Optimizer] Error normalizing CFL team:', error);
        return null;
    }
}

// Normalize CFL player data to our standard format
function normalizeCflPlayer(rawPlayer) {
    if (!rawPlayer || typeof rawPlayer !== 'object') return null;
    
    try {
        // Combine first and last name
        const fullName = `${rawPlayer.firstName || ''} ${rawPlayer.lastName || ''}`.trim();
        
        // Extract team name from squad object
        const teamName = rawPlayer.squad ? (rawPlayer.squad.name || rawPlayer.squad.abbreviation || '') : '';
        
        return {
            id: rawPlayer.id || rawPlayer.feedId || '',
            name: fullName || rawPlayer.name || '',
            position: rawPlayer.position || '',
            team: teamName,
            salary: parseInt(rawPlayer.cost || 0),
            projectedPoints: parseFloat(rawPlayer.points || 0),
            gameInfo: '', // Not provided in this API
            status: rawPlayer.status || (rawPlayer.isLocked ? 'locked' : 'active'),
            // Additional CFL-specific fields
            firstName: rawPlayer.firstName || '',
            lastName: rawPlayer.lastName || '',
            feedId: rawPlayer.feedId || '',
            isLocked: rawPlayer.isLocked || false,
            videoURL: rawPlayer.videoURL || '',
            newsURL: rawPlayer.newsURL || '',
            newsTitle: rawPlayer.newsTitle || '',
            injuredText: rawPlayer.injuredText || '',
            stats: rawPlayer.stats || {}
        };
    } catch (error) {
        console.error('[CFL Optimizer] Error normalizing CFL player:', error);
        return null;
    }
}


// Create teams/defenses from player data when team API is not available
function createTeamsFromPlayerData(players) {
    const teams = [];
    const teamAbbreviations = new Set();
    
    // Extract unique teams from player data
    players.forEach(player => {
        if (player.team && player.team.trim()) {
            teamAbbreviations.add(player.team.trim());
        }
    });
    
    // Create defense teams for each unique team
    let teamId = 1;
    teamAbbreviations.forEach(abbr => {
        teams.push({
            id: teamId.toString(),
            name: `${abbr} Defense`,
            abbreviation: abbr,
            cost: 5000, // Default cost
            projectedScores: 8.0 // Default projection
        });
        teamId++;
    });
    
    return teams;
}

// Fetch projections from API with caching
async function fetchProjectionsAndMerge(players) {
    try {
        // Check if we have cached projections that are still fresh
        const now = Date.now();
        if (projectionsCache && projectionsCacheTime && (now - projectionsCacheTime) < PROJECTIONS_CACHE_DURATION) {
            console.log('[CFL Optimizer] Using cached projections');
            mergeProjectionsIntoPlayers(players, projectionsCache);
            return;
        }
        
        // Check chrome storage for cached projections
        const cachedData = await getCachedProjections();
        if (cachedData && cachedData.projections && (now - cachedData.timestamp) < PROJECTIONS_CACHE_DURATION) {
            console.log('[CFL Optimizer] Using stored cached projections');
            projectionsCache = cachedData.projections;
            projectionsCacheTime = cachedData.timestamp;
            mergeProjectionsIntoPlayers(players, projectionsCache);
            return;
        }
        
        // Fetch fresh projections from API
        console.log('[CFL Optimizer] Fetching fresh projections from API');
        const apiUrls = await window.CFL_CONFIG.getApiUrls();
        console.log('[CFL Optimizer] Using environment for projections:', window.CFL_CONFIG.getCurrentEnvironment());
        
        const response = await fetch(apiUrls.PROJECTIONS_URL);
        
        if (response.ok) {
            const data = await response.json();
            if (data.success && data.projections) {
                projectionsCache = data.projections;
                projectionsCacheTime = now;
                
                // Store in chrome storage
                await setCachedProjections(data.projections, now);
                
                // Merge into players
                mergeProjectionsIntoPlayers(players, projectionsCache);
                console.log(`[CFL Optimizer] Fetched and cached projections for ${Object.keys(projectionsCache).length} players`);
            }
        } else {
            console.warn('[CFL Optimizer] Failed to fetch projections, using site projections');
        }
        
    } catch (error) {
        console.warn('[CFL Optimizer] Error fetching projections:', error);
    }
}

// Merge projections into player objects
function mergeProjectionsIntoPlayers(players, projections) {
    for (const player of players) {
        const playerId = player.id || player.feedId;
        if (playerId && projections[playerId] !== undefined) {
            player.projectedPoints = projections[playerId];
            // Also update stats.projectedScores for consistency
            if (!player.stats) player.stats = {};
            player.stats.projectedScores = projections[playerId];
        }
    }
}

// Get cached projections from chrome storage
async function getCachedProjections() {
    return new Promise((resolve) => {
        chrome.storage.local.get(['projections_cache'], (result) => {
            resolve(result.projections_cache || null);
        });
    });
}

// Set cached projections in chrome storage
async function setCachedProjections(projections, timestamp) {
    return new Promise((resolve) => {
        chrome.storage.local.set({
            'projections_cache': {
                projections: projections,
                timestamp: timestamp
            }
        }, () => {
            resolve();
        });
    });
}

// Utility to sum projections
function totalPoints(arr){
    return arr.reduce((s,p)=>s+(Number(p.projected_points)||Number(p.projection)||0),0).toFixed(1);
}

// Inject optimizer lineup panel into page
function injectOptimizerPanel(list){
    console.log('[CFL Optimizer] Injecting optimizer panel');
    
    // Check for injection target
    const targetFound = document.querySelector('#team') || document.querySelector('[class*="team"]');
    if (!targetFound) {
        console.warn('[CFL Optimizer] No suitable injection target found');
    }
    
    const old=document.querySelector('#cfl-optimizer-panel');
    if(old) {
        console.log('[CFL Optimizer] Removing existing panel');
        old.remove();
    }

    const panel=document.createElement('div');
    panel.id='cfl-optimizer-panel';
    panel.innerHTML=`
    <style>
      #cfl-optimizer-panel {
        position: relative;
        width: 100%;
        background: #1a1a1a;
        border-radius: 8px;
        margin: 16px 0 0 0;
        padding: 0;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        overflow: hidden;
        box-sizing: border-box;
      }
      
      #cfl-optimizer-panel * {
        box-sizing: border-box;
      }
      
      .cfl-opt-header {
        background: #c5242b;
        color: white;
        padding: 14px 18px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-weight: 600;
        font-size: 18px;
      }
      
      .cfl-opt-header .toggle {
        cursor: pointer;
        font-size: 16px;
        padding: 4px 8px;
        border-radius: 4px;
        background: rgba(255,255,255,0.2);
        transition: background 0.2s;
      }
      
      .cfl-opt-header .toggle:hover {
        background: rgba(255,255,255,0.3);
      }
      
      .cfl-opt-content {
        padding: 0;
        margin: 0;
        border-bottom-left-radius: 8px;
        border-bottom-right-radius: 8px;
        overflow: hidden;
      }
      
      .cfl-player-card {
        display: flex;
        align-items: center;
        padding: 10px 18px;
        border-bottom: 1px solid #333;
        background: #2a2a2a;
        transition: background 0.2s;
      }
      
      .cfl-player-card:hover {
        background: #333;
      }
      
      .cfl-player-card:last-child {
        border-bottom: none;
        margin-bottom: 0;
      }
      
      .player-position {
        background: #c5242b;
        color: white;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 12px;
        min-width: 35px;
        text-align: center;
        margin-right: 12px;
      }
      
      .player-info {
        flex: 1;
        color: white;
      }
      
      .player-name {
        font-weight: 600;
        font-size: 14px;
        margin-bottom: 2px;
      }
      
      .player-details {
        font-size: 12px;
        color: #bbb;
        display: flex;
        gap: 12px;
      }
      
      .ownership-badge {
        background: #4a5568;
        color: #e2e8f0;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: 500;
      }
      
      .captain-badge {
        background: #ffd700;
        color: #000;
        padding: 2px 6px;
        border-radius: 12px;
        font-size: 10px;
        font-weight: 700;
        margin-left: 8px;
      }
      
      .add-btn {
        background: #c5242b;
        border: none;
        color: white;
        padding: 8px 12px;
        border-radius: 6px;
        cursor: pointer;
        font-weight: 600;
        font-size: 12px;
        transition: background 0.2s;
        margin-left: 12px;
      }
      
      .add-btn:hover {
        background: #a01e24;
      }
    </style>
    
    <div class="cfl-opt-header">
      <span>⭐ Optimized Lineup</span>
      <div style="display: flex; align-items: center; gap: 16px;">
        <span>${totalPoints(list)} pts</span>
        <span class="toggle">▲</span>
      </div>
    </div>
    
    <div class="cfl-opt-content">`;

    list.forEach(p=>{
        const card = document.createElement('div');
        card.className = 'cfl-player-card';
        const captainBadge = p.is_captain ? '<span class="captain-badge">CPT</span>' : '';
        const points = p.projected_points || p.projection || 0;
        
        // Get ownership data - try multiple sources
        let ownership = 0;
        if (p.ownership !== undefined && p.ownership !== null) {
            ownership = p.ownership;
        } else if (p.id && playerData.player_ownership && playerData.player_ownership[p.id]) {
            ownership = playerData.player_ownership[p.id].percents || 0;
        } else if (p.feedId && playerData.player_ownership && playerData.player_ownership[p.feedId]) {
            ownership = playerData.player_ownership[p.feedId].percents || 0;
        }
        
        const ownershipText = ownership > 0 ? `${ownership.toFixed(1)}%` : 'N/A';
        
        card.innerHTML = `
            <div class="player-position">${p.position}</div>
            <div class="player-info">
                <div class="player-name">
                    ${p.name}${captainBadge}
                </div>
                <div class="player-details">
                    <span>$${(p.salary/1000).toFixed(1)}k</span>
                    <span>${points} pts</span>
                    <span class="ownership-badge">${ownershipText}</span>
                </div>
            </div>
            <button class="add-btn">➕</button>
        `;
        
        // Add the card to the content area
        const content = panel.querySelector('.cfl-opt-content');
        content.appendChild(card);
    });

    panel.querySelector('.toggle').onclick=()=>{
        const content = panel.querySelector('.cfl-opt-content');
        const cards = [...panel.querySelectorAll('.cfl-player-card')];
        const collapsed = content.style.display === 'none';
        
        content.style.display = collapsed ? 'block' : 'none';
        panel.querySelector('.toggle').textContent = collapsed ? '▲' : '▼';
    };

    // Try to find the best injection point (target roster area specifically)
    const possibleSelectors = [
        // Specific roster area selectors
        '.tutorial-pick-team-step', // Found in debug output with team classes
        '[class*="tutorial-pick-team"]',
        '[class*="team"][class*="step"]',
        '.sc-jnOGJG', // Styled component class from debug output
        '[class*="pre-game"]',
        
        // General team/roster selectors
        '#team',
        '.team-section', 
        '.roster-section',
        '.team-container',
        '.fantasy-team',
        '[data-section="team"]',
        'div[class*="team"]',
        
        // Material-UI containers
        '.MuiContainer-root',
        '.MuiBox-root',
        
        // Fallbacks
        '.main-content',
        'main',
        '.container',
        'div[class*="container"]',
        'div[class*="layout"]',
        'div[class*="grid"]',
        '#root' // Last resort
    ];
    
    let targetElement = null;
    let selectedSelector = null;
    
    for (const selector of possibleSelectors) {
        const element = document.querySelector(selector);
        if (element) {
            targetElement = element;
            selectedSelector = selector;
            console.log(`[CFL Optimizer] Found element with selector: ${selector}`);
            break;
        }
    }
    
    if (!targetElement) {
        console.warn('[CFL Optimizer] Could not find suitable injection point, falling back to body');
        targetElement = document.body;
        selectedSelector = 'body';
    }
    
    try {
        if (selectedSelector === '#root') {
            // For React root, try to find a better injection point first
            const betterTargets = [
                '.tutorial-pick-team-step',
                '[class*="tutorial-pick-team"]',
                '.sc-jnOGJG',
                'div[class*="team"]'
            ];
            
            let foundBetter = false;
            for (const selector of betterTargets) {
                const betterTarget = document.querySelector(selector);
                if (betterTarget) {
                    targetElement = betterTarget;
                    selectedSelector = selector;
                    foundBetter = true;
                    console.log(`[CFL Optimizer] Found better injection point: ${selector}`);
                    break;
                }
            }
            
            if (!foundBetter) {
                // Fallback to fixed positioning only if no better option
                panel.style.position = 'fixed';
                panel.style.top = '0';
                panel.style.left = '0';
                panel.style.right = '0';
                panel.style.zIndex = '99999';
                panel.style.boxShadow = '0 2px 8px rgba(0,0,0,0.3)';
                document.body.appendChild(panel);
                console.log('[CFL Optimizer] Panel injected as fixed header (fallback)');
                return;
            }
        }
        
        // Inline injection strategy for roster area
        if (targetElement.parentNode) {
            targetElement.parentNode.insertBefore(panel, targetElement);
            // Add margin to push content down naturally
            targetElement.style.marginTop = (panel.offsetHeight + 16) + 'px';
            console.log(`[CFL Optimizer] Panel injected inline before ${selectedSelector}`);
        } else {
            // Fallback to prepending to the target element
            targetElement.prepend(panel);
            console.log(`[CFL Optimizer] Panel prepended to ${selectedSelector}`);
        }
        
        // Add success notification
        console.log('[CFL Optimizer] Panel successfully injected and displayed');
        
    } catch (error) {
        console.error('[CFL Optimizer] Error injecting panel:', error);
        // Fallback: append to body as fixed element
        panel.style.position = 'fixed';
        panel.style.top = '0';
        panel.style.left = '0';
        panel.style.right = '0';
        panel.style.zIndex = '99999';
        document.body.appendChild(panel);
        console.log('[CFL Optimizer] Panel injected as fallback fixed element');
    }
}

// Listen for messages from popup/background
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    console.log('[CFL Optimizer] Message received:', request);
    
    if(request.action==='getPlayerData'){
        console.log('[CFL Optimizer] Player data request received');
        if(isDataLoaded && playerData?.players?.length>0){
            console.log('[CFL Optimizer] Sending player data:', playerData.players.length, 'players');
            sendResponse({success:true,data:playerData});
        }else{
            console.log('[CFL Optimizer] No player data available');
            sendResponse({success:false,error:'No player data found. Please make sure you are on the CFL fantasy page and refresh the page.'});
        }
    }else if(request.action==='lineupGenerated' && request.success){
        console.log('[CFL Optimizer] Lineup generated message received');
        if (request.lineup && Array.isArray(request.lineup) && request.lineup.length > 0) {
            console.log('[CFL Optimizer] Valid lineup data, injecting panel');
            injectOptimizerPanel(request.lineup);
        } else {
            console.warn('[CFL Optimizer] Invalid lineup data received:', request.lineup);
        }
    }
    return true;
});

// Inject optimize controls directly on the page
function injectOptimizeControls() {
    
    // Check if controls already exist
    if (document.querySelector('#cfl-optimizer-controls')) {
        console.log('[CFL Optimizer] Controls already exist');
        return;
    }
    
    const controls = document.createElement('div');
    controls.id = 'cfl-optimizer-controls';
    controls.innerHTML = `
        <style>
            #cfl-optimizer-controls {
                position: fixed;
                top: 120px;
                right: 20px;
                background: #1a1a1a;
                border: 2px solid #c5242b;
                border-radius: 8px;
                padding: 16px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                z-index: 10000;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                min-width: 280px;
            }
            
            .cfl-controls-header {
                color: #c5242b;
                font-weight: 600;
                font-size: 16px;
                margin-bottom: 12px;
                display: flex;
                align-items: center;
                gap: 8px;
            }
            
            .cfl-engine-selector {
                margin-bottom: 12px;
            }
            
            .cfl-engine-selector label {
                display: block;
                color: #fff;
                font-size: 12px;
                margin-bottom: 4px;
                font-weight: 500;
            }
            
            .cfl-engine-selector select {
                width: 100%;
                padding: 8px 12px;
                border: 1px solid #444;
                border-radius: 4px;
                background: #2a2a2a;
                color: #fff;
                font-size: 14px;
            }
            
            .cfl-optimize-btn {
                width: 100%;
                background: #c5242b;
                color: white;
                border: none;
                padding: 12px 16px;
                border-radius: 6px;
                font-weight: 600;
                font-size: 14px;
                cursor: pointer;
                transition: all 0.2s;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 8px;
            }
            
            .cfl-optimize-btn:hover:not(:disabled) {
                background: #a01e24;
                transform: translateY(-1px);
            }
            
            .cfl-optimize-btn:disabled {
                background: #666;
                cursor: not-allowed;
                transform: none;
            }
            
            .cfl-status {
                margin-top: 8px;
                font-size: 12px;
                text-align: center;
                min-height: 16px;
            }
            
            .cfl-status.loading { color: #ffd700; }
            .cfl-status.success { color: #4caf50; }
            .cfl-status.error { color: #f44336; }
            
            .spinner {
                width: 14px;
                height: 14px;
                border: 2px solid transparent;
                border-top: 2px solid currentColor;
                border-radius: 50%;
                animation: spin 1s linear infinite;
            }
            
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        </style>
        
        <div class="cfl-controls-header">
            ⚡ CFL Optimizer
        </div>
        
        <div class="cfl-engine-selector">
            <label for="cfl-engine-select">Optimization Engine:</label>
            <select id="cfl-engine-select">
                <option value="pulp">PuLP (Custom)</option>
                <option value="pydfs">PyDFS (Library)</option>
            </select>
        </div>
        
        <button class="cfl-optimize-btn" id="cfl-optimize-btn">
            <span>🚀 Optimize Lineup</span>
        </button>
        
        <div class="cfl-status" id="cfl-status"></div>
    `;
    
    // Inject into page
    document.body.appendChild(controls);
    
    // Add event listeners
    setupControlEventListeners();
    
    console.log('[CFL Optimizer] Controls injected successfully');
}

// Setup event listeners for the controls
function setupControlEventListeners() {
    const optimizeBtn = document.getElementById('cfl-optimize-btn');
    const statusDiv = document.getElementById('cfl-status');
    
    optimizeBtn.addEventListener('click', async () => {
        console.log('[CFL Optimizer] Optimize button clicked');
        
        // Get selected engine
        const engineSelect = document.getElementById('cfl-engine-select');
        const selectedEngine = engineSelect.value;
        
        // Update UI to loading state
        optimizeBtn.disabled = true;
        optimizeBtn.innerHTML = '<div class="spinner"></div><span>Optimizing...</span>';
        statusDiv.textContent = 'Gathering player data...';
        statusDiv.className = 'cfl-status loading';
        
        try {
            // Start optimization process
            await performDirectOptimization(selectedEngine);
            
            // Success state
            optimizeBtn.disabled = false;
            optimizeBtn.innerHTML = '<span>✅ Optimization Complete</span>';
            statusDiv.textContent = 'Lineup optimized and displayed!';
            statusDiv.className = 'cfl-status success';
            
            // Reset button after 3 seconds
            setTimeout(() => {
                optimizeBtn.innerHTML = '<span>🚀 Optimize Lineup</span>';
                statusDiv.textContent = '';
                statusDiv.className = 'cfl-status';
            }, 3000);
            
        } catch (error) {
            console.error('[CFL Optimizer] Optimization failed:', error);
            
            // Error state
            optimizeBtn.disabled = false;
            optimizeBtn.innerHTML = '<span>❌ Optimization Failed</span>';
            statusDiv.textContent = error.message || 'Optimization failed';
            statusDiv.className = 'cfl-status error';
            
            // Reset button after 5 seconds
            setTimeout(() => {
                optimizeBtn.innerHTML = '<span>🚀 Optimize Lineup</span>';
                statusDiv.textContent = '';
                statusDiv.className = 'cfl-status';
            }, 5000);
        }
    });
}

// Perform optimization directly from content script
async function performDirectOptimization(selectedEngine) {
    console.log('[CFL Optimizer] Starting direct optimization with engine:', selectedEngine);
    
    // Check if player data is available
    if (!isDataLoaded || !playerData?.players?.length) {
        throw new Error('Player data not available. Please refresh the page.');
    }
    
    // Format data for the optimizer API (same as popup.js)
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
        engine: selectedEngine
    };
    
    console.log('[CFL Optimizer] Sending optimization request to background script...');
    
    // Send optimization request to background script
    return new Promise((resolve, reject) => {
        chrome.runtime.sendMessage({
            action: 'optimizeLineup',
            data: apiRequest
        }, (response) => {
            if (chrome.runtime.lastError) {
                console.error('[CFL Optimizer] Error communicating with background script:', chrome.runtime.lastError);
                reject(new Error('Unable to connect to optimizer service'));
                return;
            }
            
            if (response.success) {
                console.log('[CFL Optimizer] Optimization successful, injecting panel...');
                
                // Extract lineup data
                const lineup = response.lineup.players || response.lineup;
                
                // Inject the optimized lineup panel
                injectOptimizerPanel(lineup);
                
                resolve(response);
            } else {
                console.error('[CFL Optimizer] Optimization failed:', response.error);
                reject(new Error(response.error || 'Optimization failed'));
            }
        });
    });
}

// Inject optimize controls when page is ready
setTimeout(() => {
    injectOptimizeControls();
}, 2000); // Give React app time to load

console.log('[CFL Optimizer] Content script ready');
