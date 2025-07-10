// CFL Fantasy Optimizer - Content Script
// Injected into gamezone.cfl.ca/fantasy/* to scrape player data

console.log('[CFL Optimizer] Content script loaded');

// Global variables
let playerData = [];
let isDataLoaded = false;
let directApiFetchSuccessful = false;

// Initialize content script
initialize();

function initialize() {
    // Wait for page to fully load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', startDataCollection);
    } else {
        startDataCollection();
    }
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

// Utility to sum projections
function totalPoints(arr){
    return arr.reduce((s,p)=>s+(+p.projection||0),0).toFixed(1);
}

// Inject optimizer lineup panel into page
function injectOptimizerPanel(list){
    const old=document.querySelector('#cfl-optimizer-panel');
    if(old) old.remove();

    const panel=document.createElement('div');
    panel.id='cfl-optimizer-panel';
    panel.innerHTML=`
    <style>
      #cfl-optimizer-panel{position:relative;width:100%;background:#111;color:#fff;padding:12px 16px;font-family:Arial,Helvetica,sans-serif;box-shadow:0 2px 6px rgba(0,0,0,.35);z-index:9999;}
      #cfl-optimizer-panel h3{margin:0 0 8px;font-size:18px;display:flex;justify-content:space-between;align-items:center;}
      #cfl-optimizer-panel .toggle{cursor:pointer;font-size:14px;margin-left:8px;}
      .cfl-opt-row{display:flex;align-items:center;gap:8px;font-size:14px;margin-bottom:4px;}
      .cfl-opt-row .add-btn{margin-left:auto;cursor:pointer;background:#c5242b;border:none;border-radius:3px;color:#fff;font-size:12px;padding:2px 6px;}
    </style>
    <h3><span>⭐\u00A0Optimized\u00A0Lineup</span><span>${totalPoints(list)}\u00A0pts</span><span class="toggle">▲</span></h3>`;

    list.forEach(p=>{
        const row=document.createElement('div');
        row.className='cfl-opt-row';
        const cap=p.isCaptain?' <strong>[CPT]</strong>':'';
        row.innerHTML=`<strong>${p.position}</strong><span>${p.name}</span><span>$${(p.salary/1000).toFixed(1)}k</span><span>${p.projection}</span>${cap}<button class="add-btn">➕</button>`;
        panel.appendChild(row);
    });

    panel.querySelector('.toggle').onclick=()=>{
        const rows=[...panel.querySelectorAll('.cfl-opt-row')];
        const collapsed=rows[0].style.display==='none';
        rows.forEach(r=>r.style.display=collapsed?'flex':'none');
        panel.querySelector('.toggle').textContent=collapsed?'▲':'▼';
    };

    const rosterCol=document.querySelector('#team');
    if(!rosterCol) return console.warn('Roster column not found!');
    rosterCol.parentNode.insertBefore(panel, rosterCol);
    rosterCol.style.marginTop=panel.offsetHeight+'px';
}

// Listen for messages from popup/background
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if(request.action==='getPlayerData'){
        if(isDataLoaded && playerData?.players?.length>0){
            sendResponse({success:true,data:playerData});
        }else{
            sendResponse({success:false,error:'No player data found. Please make sure you are on the CFL fantasy page and refresh the page.'});
        }
    }else if(request.action==='lineupGenerated' && request.success){
        injectOptimizerPanel(request.lineup);
    }
    return true;
});
