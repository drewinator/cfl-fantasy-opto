# CFL Fantasy Optimizer

A Chrome extension and Python backend system that optimizes Canadian Football League (CFL) fantasy lineups using advanced linear programming algorithms with captain logic.

## 🚀 Features

- **Smart Optimization**: Uses linear programming to find optimal lineups within salary cap constraints
- **Captain Logic**: Automatically tests all eligible players as captains with 2x point multipliers
- **Real-time Data**: Fetches live player data, salaries, and projections from CFL's fantasy platform
- **Ownership Integration**: Incorporates player ownership percentages for strategic diversity
- **Chrome Extension**: Seamless integration with gamezone.cfl.ca/fantasy pages
- **Multiple Lineups**: Generate diverse lineup options for tournaments
- **Production Ready**: Clean, optimized codebase with comprehensive error handling

## 📋 CFL Fantasy Rules

The optimizer implements official CFL fantasy constraints:
- **Roster Size**: 7 players total
- **Positions**: 1 QB + 2 WR + 2 RB + 1 FLEX (WR/RB/TE) + 1 DEF
- **Salary Cap**: $70,000
- **Captain Bonus**: One player gets 2x points multiplier
- **Team Limits**: Maximum 3 players from same team

## 🛠️ Installation

### Prerequisites
- Python 3.7+
- Google Chrome browser
- Git

### 1. Clone Repository
```bash
git clone https://github.com/drewinator/cfl-fantasy-opto.git
cd cfl-fantasy-opto
```

### 2. Setup Python Backend
```bash
cd optimizer
pip install -r requirements.txt
```

### 3. Test the Optimizer
```bash
python test_custom_optimizer.py
```

### 4. Start API Server
```bash
python api_server.py
```
Server will start on `http://localhost:3000`

### 5. Load Chrome Extension
1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode" (top right toggle)
3. Click "Load unpacked"
4. Select the project root directory (`cfl-fantasy-opto`)
5. Extension should appear in your toolbar

## 📱 Usage

### Using the Chrome Extension
1. Navigate to [CFL Fantasy](https://gamezone.cfl.ca/fantasy/)
2. Click the CFL Optimizer extension icon
3. Click "Optimize Lineup" button
4. View optimized lineup with captain selection
5. Lineup automatically saves for 24 hours

### API Usage
The backend provides REST endpoints for direct integration:

#### Generate Optimal Lineup
```bash
POST http://localhost:3000/optimize
Content-Type: application/json

{
  "players": [...],
  "teams": [...],
  "player_ownership": {...},
  "team_ownership": {...},
  "optimization_settings": {
    "max_players_from_team": 3,
    "use_captain": true,
    "num_lineups": 1
  }
}
```

#### Generate Multiple Lineups
```bash
POST http://localhost:3000/optimize-multiple
```

#### Health Check
```bash
GET http://localhost:3000/test
```

## 🏗️ Architecture

### Chrome Extension
- **popup.js**: Main UI logic and optimization controls
- **content.js**: Data extraction from CFL fantasy pages
- **optimizerBridge.js**: Background service worker for API communication
- **manifest.json**: Extension configuration and permissions

### Python Backend
- **custom_cfl_optimizer.py**: Primary optimizer using PuLP linear programming
- **cfl_optimizer.py**: Alternative optimizer using pydfs-lineup-optimizer
- **api_server.py**: Flask REST API server with CORS support

### Data Processing
- **Direct API Fetching**: Retrieves data from CFL's JSON endpoints
- **Real-time Sync**: Automatically updates player data and ownership percentages
- **Bye Week Handling**: Excludes players on bye weeks unless in current lineup
- **Lock Status**: Respects player lock status from CFL platform

## 🧮 Optimization Algorithm

### Captain Selection Process
1. **Candidate Identification**: All non-defense players eligible for captain
2. **Brute Force Testing**: Tests each candidate with 2x point multiplier
3. **Linear Programming**: Runs full optimization for each captain scenario
4. **Best Selection**: Chooses combination with highest total projected points

### Constraints
- Salary cap: ≤ $70,000
- Position requirements: Exact counts for each position
- Team diversity: ≤ 3 players from same team
- Flex optimization: Automatically fills FLEX with optimal WR/RB/TE

### Performance
- **Speed**: Typically optimizes in under 10 seconds
- **Accuracy**: Finds mathematically optimal solutions within constraints
- **Scalability**: Handles 350+ player pools efficiently

## 📊 Expected Results

### Typical Improvements
- **Base Lineup**: ~107 projected points
- **With Captain**: ~129 projected points
- **Point Gain**: +22 points average improvement
- **Salary Efficiency**: Maximizes points per dollar spent

## 🔧 Development

### Project Structure
```
cfl-fantasy-opto/
├── manifest.json          # Chrome extension manifest
├── popup.html/js          # Extension UI
├── content.js             # Data extraction
├── optimizerBridge.js     # API communication
├── styles.css             # UI styling
├── optimizer/             # Python backend
│   ├── api_server.py      # Flask API
│   ├── custom_cfl_optimizer.py  # Main optimizer
│   ├── cfl_optimizer.py   # Alternative optimizer
│   └── requirements.txt   # Python dependencies
├── json_files/            # Sample data
└── README.md              # This file
```

### Running Tests
```bash
# Test custom optimizer
python optimizer/test_custom_optimizer.py

# Test basic functionality
python optimizer/test_optimizer.py
```

### Debug Mode
Enable Chrome DevTools for extension debugging:
1. Right-click extension icon → "Inspect popup"
2. Check console for detailed logs
3. Network tab shows API communication

## 🚀 Production Features

### Code Quality
- **Clean Codebase**: ~400+ lines of development code removed
- **Error Handling**: Comprehensive exception handling and user feedback
- **Logging**: Essential error logging without debug noise
- **Performance**: Optimized for production use

### Security
- **CORS Enabled**: Secure cross-origin requests
- **Input Validation**: Validates all API inputs
- **No Secrets**: No API keys or sensitive data stored

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- CFL Fantasy platform for providing the data APIs
- PuLP library for linear programming optimization
- pydfs-lineup-optimizer for alternative optimization methods

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/drewinator/cfl-fantasy-opto/issues)
- **Discussions**: [GitHub Discussions](https://github.com/drewinator/cfl-fantasy-opto/discussions)

---

**Made with ⚡ by [drewinator](https://github.com/drewinator)**