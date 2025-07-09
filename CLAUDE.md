# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a CFL (Canadian Football League) Fantasy Optimizer project consisting of a Chrome extension frontend and Python backend. The system optimizes CFL fantasy lineups using linear programming with custom constraints and captain logic.

## Architecture

### Chrome Extension Structure
- **popup.html/js**: Main UI with lineup display grid and optimization controls
- **content.js**: Content script for data extraction from `gamezone.cfl.ca/fantasy/*`
- **optimizerBridge.js**: Background service worker handling API communication
- **manifest.json**: Manifest V3 extension configuration
- **styles.css**: UI styling and theme colors

### Python Backend Structure  
- **custom_cfl_optimizer.py**: Primary optimizer using PuLP linear programming with captain logic
- **cfl_optimizer.py**: Alternative optimizer using pydfs-lineup-optimizer library
- **api_server.py**: Flask REST API server with CORS support
- **test_custom_optimizer.py**: Comprehensive testing with real JSON data
- **test_optimizer.py**: Basic testing functionality

### Data Files
- **json_files/players.json**: 356+ CFL players with positions, salaries, projections
- **json_files/sqauds.json**: 9 CFL defense teams
- **json_files/playersselection.json**: Player ownership percentages
- **json_files/sqaudsselection.json**: Team ownership percentages

## CFL Fantasy Rules

The optimizer implements specific CFL fantasy constraints:
- **Roster Size**: 7 players total
- **Positions**: 1 QB + 2 WR + 2 RB + 1 FLEX (WR/RB/TE) + 1 DEF
- **Salary Cap**: $70,000
- **Captain Logic**: One player gets 2x points multiplier
- **Team Limits**: Maximum 3 players from same team

## Common Commands

### Backend Development
```bash
# Start API server (runs on localhost:3000)
python api_server.py

# Test custom optimizer with real data
python test_custom_optimizer.py

# Test basic optimizer functionality  
python test_optimizer.py

# Install dependencies
pip install -r requirements.txt
```

### Chrome Extension Development
- Load extension: Chrome → Extensions → Developer mode → Load unpacked
- Debug: Chrome DevTools → Sources → Extension scripts
- Production-ready: All development files removed, clean codebase

## Key Technical Details

### Optimizer Implementation
The custom optimizer (`custom_cfl_optimizer.py`) uses:
- **Linear Programming**: PuLP library for constraint optimization
- **Captain Logic**: Brute force testing of all potential captains for 2x multiplier
- **Flex Constraints**: Exactly 5 WR/RB/TE players with minimums of 2 WR and 2 RB
- **Position Mapping**: Maps CFL positions (quarterback → QB, wide_receiver → WR, etc.)

### API Endpoints
- `POST /optimize`: Generate single optimal lineup
- `POST /optimize-multiple`: Generate multiple diverse lineups  
- `GET /test`: Health check with local JSON data
- `GET /stats`: Player pool statistics

### Data Extraction Methods
1. **Direct API Fetching**: Fetch data directly from CFL's JSON endpoints
2. **Local JSON**: Use provided JSON files for offline development and testing

### Extension Communication Flow
CFL Site → Content Script → Background Script → Python API → Optimizer → Response → Popup UI

## Development Notes

### Testing Strategy
- **Real Data Testing**: Uses actual CFL player and team data (356 players, 9 teams)
- **Expected Results**: Optimizer typically improves lineups by 20+ points with captain logic
- **Validation**: Checks salary cap compliance, position requirements, and team limits

### Extension Permissions
- **Host Permissions**: `gamezone.cfl.ca/fantasy/*`
- **Background**: Service worker for API communication
- **Content Scripts**: Automatic injection on CFL fantasy pages

### Data Structures
Players contain: id, name, position, team, salary, projected_points, ownership, status
Teams contain: id, name, abbreviation, salary, projected_points, ownership

### Captain Selection Logic
The optimizer tests all eligible players (non-DEF positions) as potential captains by:
1. Temporarily doubling their projected points
2. Running optimization with modified player pool
3. Selecting the combination that produces highest total points
4. Typical improvement: 107.2 → 129.5 points (+22.3 point boost)

### Performance Considerations
- Captain optimization is O(n) where n = number of eligible players (~140)
- Each captain test runs full linear programming optimization
- Total optimization time typically under 10 seconds for real datasets

## Production Readiness

### Code Cleanup Completed
This codebase has been cleaned and optimized for production use:
- **Removed ~400+ lines** of unused development code
- **Eliminated DOM scraping functions** and network interception fallbacks
- **Streamlined logging** from 100+ debug statements to essential error handling
- **Removed development files**: test-mock-server.js, content-local.js, prd.md, etc.
- **Clean manifest**: No references to deleted files
- **Core functionality preserved**: All optimization and API features intact

### Current Production Structure
- **Chrome Extension**: 4 core files (popup, content script, background, manifest)
- **Python Backend**: 2 optimizers + API server + tests
- **Data Files**: Real CFL JSON data (players, teams, ownership, gameweeks)
- **Documentation**: Clean README and CLAUDE.md files