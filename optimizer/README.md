# CFL Fantasy Optimizer Backend

This directory contains the Python backend for the CFL Fantasy Optimizer Chrome extension. It uses `pydfs-lineup-optimizer` to generate optimal lineups based on CFL fantasy rules.

## Features

- **CFL-Specific Rules**: Configured for CFL fantasy format (QB, 2×WR, 2×RB, FLEX, DEF)
- **Salary Cap**: $70,000 salary cap constraint
- **Captain Logic**: Ready for 1.5x captain multiplier (future enhancement)
- **Ownership Data**: Incorporates player ownership percentages for diversity
- **Multiple Lineups**: Generate diverse lineup options
- **REST API**: Flask server for Chrome extension integration

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Test the Optimizer**:
   ```bash
   python test_optimizer.py
   ```

3. **Start the API Server**:
   ```bash
   python3 optimizer/api_server.py
   ```

The server will start on `http://localhost:3000` by default.

## API Endpoints

### `POST /optimize`
Generate an optimal lineup.

**Request**:
```json
{
  "players": [...],
  "teams": [...],
  "player_ownership": {...},
  "team_ownership": {...},
  "optimization_settings": {
    "randomness": 0.1,
    "num_lineups": 1
  }
}
```

**Response**:
```json
{
  "success": true,
  "lineup": {
    "players": [...],
    "total_salary": 69500,
    "projected_points": 142.5,
    "remaining_cap": 500,
    "is_valid": true
  },
  "player_stats": {...}
}
```

### `POST /optimize/multiple`
Generate multiple diverse lineups.

### `POST /test-data`
Test optimization using local JSON files.

### `GET /health`
Health check endpoint.

## CFL Fantasy Rules

The optimizer is configured for the following CFL fantasy format:

- **Roster Size**: 7 players
- **Positions**: 
  - QB: 1
  - WR: 2  
  - RB: 2
  - FLEX: 1 (can be WR, RB, or TE)
  - DEF: 1 (team defense)
- **Salary Cap**: $70,000
- **Captain**: Future feature for 1.5x multiplier

## Data Format

### Players
```json
{
  "id": 123,
  "firstName": "Player",
  "lastName": "Name", 
  "position": "quarterback",
  "squad": {"abbr": "TOR"},
  "cost": 8000,
  "stats": {"projectedScores": 15.5},
  "status": "available"
}
```

### Teams (Defense)
```json
{
  "id": 1,
  "name": "Toronto Argonauts",
  "abbreviation": "TOR",
  "cost": 5000,
  "projectedScores": 8.0
}
```

## Testing

Run the test suite:
```bash
python test_optimizer.py
```

This will:
1. Load real CFL data from JSON files
2. Test lineup generation
3. Validate API request/response formats
4. Generate sample lineups

## Environment Variables

- `PORT`: Server port (default: 3000)
- `DEBUG`: Enable debug mode (default: true)

## Dependencies

- `pydfs-lineup-optimizer`: Core optimization engine
- `flask`: Web server
- `flask-cors`: Cross-origin requests for Chrome extension
- `pandas`, `numpy`: Data processing

## Development

The optimizer is designed to work with the Chrome extension but can be used standalone. The test script demonstrates how to use it with real CFL data.

For Chrome extension integration, the server must be running on `localhost:3000` (or update the extension's `OPTIMIZER_API_URL`).