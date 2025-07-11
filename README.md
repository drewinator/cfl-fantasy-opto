# CFL Fantasy Optimizer

A comprehensive optimization tool for CFL Fantasy football that provides both **Chrome extension** and **mobile web interfaces**. Uses advanced linear programming algorithms to generate optimal lineups with captain logic and constraint handling.

## 🚀 Features

### 🎯 Chrome Extension
- **Inline optimization controls** directly on CFL fantasy page - no popup needed!
- **Real-time lineup display** with professional card-based design
- **Dual optimization engines**: PuLP (custom) and PyDFS (library)
- **Live data extraction** from CFL fantasy APIs
- **Captain optimization** with 2x point multipliers
- **Ownership percentages** for all players
- **Collapse/expand panels** for clean interface
- **Auto-injection** - controls appear automatically on CFL pages

### 📱 Mobile Web Interface
- **Live CFL data optimization** from any mobile device
- **Touch-optimized UI** with responsive design
- **Same optimization engines** as Chrome extension
- **Professional lineup display** with ownership data
- **No Chrome extension required** - works in any mobile browser
- **Server-side data fetching** - bypasses CORS limitations

### ⚡ Optimization Features
- **Advanced constraints**: Salary cap, position requirements, team limits
- **Captain logic**: Automatically tests all viable captain options
- **Multiple engines**: Choose between custom PuLP or PyDFS algorithms
- **Real-time data**: Always uses current CFL player data and projections
- **Custom projections (v0.1)**: Weighted-average model using recent game performance
- **Ownership analysis**: Includes player ownership percentages
- **Live API integration**: Fetches fresh data from CFL endpoints

## 📁 Project Structure

```
cfl_fantasy_opto/
├── README.md                    # This file
├── CLAUDE.md                   # Development guidelines
├── manifest.json               # Chrome extension manifest
├── popup.html                  # Extension popup interface
├── popup.js                    # Extension popup logic
├── content.js                  # Main content script (injected into CFL pages)
├── optimizerBridge.js         # Background service worker
├── styles.css                  # Extension UI styles
├── mobile.html                 # Mobile web interface
├── icon16.png, icon48.png, icon128.png  # Extension icons
├── json_files/                 # Sample CFL data for development
│   ├── players.json
│   ├── playersselection.json
│   ├── sqauds.json
│   └── ...
└── optimizer/                  # Python backend
    ├── api_server.py          # Flask API server
    ├── custom_cfl_optimizer.py # PuLP-based optimizer
    ├── cfl_pydfs_optimizer.py # PyDFS-based optimizer
    ├── requirements.txt       # Python dependencies
    └── test_*.py             # Test scripts
```

## 🛠 Installation & Setup

### Prerequisites
- Python 3.8+
- Chrome browser
- Internet connection for live CFL data

### 1. Clone Repository
```bash
git clone https://github.com/drewinator/cfl-fantasy-opto.git
cd cfl-fantasy-opto
```

### 2. Install Python Dependencies
```bash
cd optimizer
pip install -r requirements.txt
```

### 3. Install Chrome Extension

#### Development Mode:
1. Open Chrome and go to `chrome://extensions/`
2. Enable "Developer mode" (toggle in top right)
3. Click "Load unpacked" 
4. Select the project root directory (`cfl_fantasy_opto/`)
5. Extension should now appear in your browser

#### Production Mode:
Extension is production-ready and can be packaged for Chrome Web Store distribution.

## 🚀 Usage

### Starting the Backend Server
```bash
cd optimizer
python api_server.py
```
Server will start on `http://localhost:3000`

### Using the Chrome Extension

#### Method 1: Inline Controls (Recommended)
1. Navigate to `https://gamezone.cfl.ca/fantasy/team`
2. **Inline controls appear automatically** in top-right corner
3. Select optimization engine (PuLP or PyDFS)
4. Click "🚀 Optimize Lineup"
5. **Optimized lineup appears inline** on the page with professional card design

#### Method 2: Extension Popup
1. Click the extension icon in Chrome toolbar
2. Select optimization engine
3. Click "Optimize"
4. View results in popup and inline panel

### Using the Mobile Web Interface

#### Local Testing:
1. Ensure API server is running (`python api_server.py`)
2. Open `mobile.html` in any browser
3. Select optimization engine
4. Click "🚀 Optimize Lineup"
5. View optimized lineup with live CFL data

#### Mobile Device:
1. Deploy mobile.html to any web server
2. Access from mobile browser
3. Enjoy full optimization capabilities on-the-go

## 📊 Custom Projections (v0.1)

The optimizer now includes a **weighted-average projection model** that uses recent game performance to calculate more accurate player projections.

### Formula
```
projection = (0.5 × last_game_points) + (0.3 × avg_of_previous_2_games) + (0.2 × season_average)
```

### How It Works
- **Last Game (50%)**: Most recent performance carries the highest weight
- **Previous 2 Games (30%)**: Short-term trend analysis
- **Season Average (20%)**: Baseline performance level
- **Fallback**: Players with less than 2 games use site projections

### Usage

#### Chrome Extension
Use the **"Proj: Our / Site"** toggle in the popup to switch between:
- **Our**: Custom weighted-average projections
- **Site**: Original CFL site projections

#### API Integration
Add `source` parameter to optimization requests:
```bash
# Use custom projections (default)
POST /optimize?source=our

# Use site projections  
POST /optimize?source=site
```

#### Caching
- Projections are cached for 60 minutes in Chrome storage
- Fresh calculations on each API server restart
- Automatic fallback to site projections on errors

### Data Requirements
Custom projections require gameweek history data (`stats.points.gws`) from CFL APIs. The system automatically falls back to site projections for players with insufficient historical data.

## 🔧 API Endpoints

### Core Endpoints
- `POST /optimize` - Optimize lineup with provided data
- `POST /optimize-mobile` - **Mobile optimization with live CFL data fetching**
- `POST /optimize-multiple` - Generate multiple diverse lineups
- `POST /test-data` - Test optimization with local JSON data
- `GET /projections` - Get weighted-average projections for all players
- `GET /health` - Health check

### Request Format
```json
{
  "engine": "pulp",
  "optimization_settings": {
    "max_players_from_team": 3,
    "use_captain": true,
    "num_lineups": 1
  }
}
```

### Response Format
```json
{
  "success": true,
  "lineup": {
    "players": [...],
    "total_salary": 69500,
    "projected_points": 127.3,
    "remaining_cap": 500
  },
  "engine": "pulp",
  "data_source": "live_cfl_api"
}
```

## ⚙️ Configuration

### CFL Fantasy Rules
- **Roster Size**: 7 players (1 QB, 2 WR, 2 RB, 1 FLEX, 1 DEF)
- **Salary Cap**: $70,000
- **Team Limit**: Maximum 3 players from same team
- **Captain Logic**: 2x point multiplier for one player

### Engine Options
- **PuLP (Custom)**: Custom linear programming implementation with advanced captain logic
- **PyDFS (Library)**: Industry-standard DFS optimization library

## 🔍 How It Works

### Data Flow
1. **Chrome Extension**: Extracts live data from CFL fantasy page
2. **Mobile Interface**: Server fetches live data directly from CFL APIs
3. **Optimization**: Advanced algorithms find optimal lineup combinations
4. **Captain Testing**: Brute force tests all viable captain options
5. **Results**: Professional display with ownership and projections

### Live Data Sources
- `https://gamezone.cfl.ca/json/fantasy/players.json`
- `https://gamezone.cfl.ca/json/fantasy/playersSelection.json`
- `https://gamezone.cfl.ca/json/fantasy/squads.json`
- `https://gamezone.cfl.ca/json/fantasy/squadsSelection.json`
- `https://gamezone.cfl.ca/json/fantasy/gameweeks.json`

### Optimization Algorithm
1. **Linear Programming**: Uses constraints to find mathematically optimal solution
2. **Captain Logic**: Tests each eligible player as captain (2x points)
3. **Constraint Handling**: Ensures salary cap, positions, and team limits
4. **Ownership Integration**: Displays real ownership percentages

## 📱 Mobile Deployment Guide

### Quick Deploy Options

#### Option 1: Simple HTTP Server
```bash
# Serve mobile.html locally
python -m http.server 8000
# Access at http://localhost:8000/mobile.html
```

#### Option 2: Heroku (Recommended)
```bash
# Install Heroku CLI
# Create Procfile:
echo "web: gunicorn --chdir optimizer --bind 0.0.0.0:\$PORT api_server:app" > Procfile

# Deploy
heroku create your-cfl-optimizer
git push heroku main
```

#### Option 3: Netlify (Static + API)
1. Deploy mobile.html to Netlify
2. Deploy API server to Heroku/Railway
3. Update `API_BASE_URL` in mobile.html

#### Option 4: Railway
```bash
# Install Railway CLI
npm install -g @railway/cli

# Deploy
railway login
railway init
railway up
```

## 🚀 Production Deployment

### Environment Setup
```bash
export PORT=3000
export DEBUG=false
export FLASK_ENV=production
```

### Production Server
```bash
# Install production WSGI server
pip install gunicorn

# Run production server
gunicorn --bind 0.0.0.0:3000 optimizer.api_server:app
```

### Docker Deployment
Create `Dockerfile`:
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY optimizer/requirements.txt .
RUN pip install -r requirements.txt
COPY optimizer/ ./optimizer/
COPY mobile.html .
EXPOSE 3000
CMD ["gunicorn", "--bind", "0.0.0.0:3000", "optimizer.api_server:app"]
```

Deploy:
```bash
docker build -t cfl-optimizer .
docker run -p 3000:3000 cfl-optimizer
```

## 📋 Startup Instructions (Self-Sufficient)

### For Personal Server Deployment

#### 1. Server Requirements
- Ubuntu 20.04+ / CentOS 8+ / Any Linux distro
- Python 3.8+
- 1GB RAM minimum
- Port 3000 open for HTTP traffic

#### 2. Installation Script
```bash
#!/bin/bash
# save as deploy.sh and run: chmod +x deploy.sh && ./deploy.sh

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and pip
sudo apt install python3 python3-pip git nginx -y

# Clone repository
git clone https://github.com/drewinator/cfl-fantasy-opto.git
cd cfl-fantasy-opto

# Install dependencies
cd optimizer
pip3 install -r requirements.txt
pip3 install gunicorn

# Test the server
python3 api_server.py &
PID=$!
sleep 5
curl http://localhost:3000/health
kill $PID

echo "✅ Installation complete!"
```

#### 3. Production Startup
```bash
# Start production server
cd cfl-fantasy-opto/optimizer
gunicorn --bind 0.0.0.0:3000 --workers 4 --timeout 120 api_server:app

# Or run in background
nohup gunicorn --bind 0.0.0.0:3000 --workers 4 api_server:app > server.log 2>&1 &
```

#### 4. Systemd Service (Auto-start)
Create `/etc/systemd/system/cfl-optimizer.service`:
```ini
[Unit]
Description=CFL Fantasy Optimizer
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/cfl-fantasy-opto/optimizer
ExecStart=/usr/local/bin/gunicorn --bind 0.0.0.0:3000 --workers 4 api_server:app
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable cfl-optimizer
sudo systemctl start cfl-optimizer
sudo systemctl status cfl-optimizer
```

#### 5. Nginx Reverse Proxy (Optional)
Create `/etc/nginx/sites-available/cfl-optimizer`:
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /mobile.html {
        root /home/ubuntu/cfl-fantasy-opto;
        try_files $uri $uri/ =404;
    }
}
```

Enable:
```bash
sudo ln -s /etc/nginx/sites-available/cfl-optimizer /etc/nginx/sites-enabled/
sudo systemctl restart nginx
```

## 🔒 Security & Maintenance

### Security Checklist
- [ ] Firewall configured (allow ports 22, 80, 443)
- [ ] Regular system updates
- [ ] Rate limiting configured if public
- [ ] HTTPS enabled for production
- [ ] Logs monitored for errors

### Monitoring
```bash
# Check server status
systemctl status cfl-optimizer

# View logs
journalctl -u cfl-optimizer -f

# Monitor API health
curl http://localhost:3000/health
```

### Updates
```bash
# Update code
cd cfl-fantasy-opto
git pull origin main

# Restart service
sudo systemctl restart cfl-optimizer
```

## 🐛 Troubleshooting

### Common Issues

#### "No player data found"
- Ensure you're on `gamezone.cfl.ca/fantasy/*` page
- Refresh the page and wait for data to load
- Check console for error messages

#### "Unable to connect to optimizer service"
- Verify API server is running: `systemctl status cfl-optimizer`
- Check port 3000 is open: `netstat -tlnp | grep 3000`
- Test API health: `curl http://localhost:3000/health`

#### Mobile interface not working
- Confirm API server is accessible
- Check browser console for CORS errors
- Verify mobile.html is served over HTTP/HTTPS

#### Server won't start
- Check Python version: `python3 --version`
- Verify dependencies: `pip3 list | grep -E 'flask|requests|pulp'`
- Check port availability: `lsof -i :3000`

### Debug Commands
```bash
# Test API server directly
cd optimizer
python3 api_server.py

# Test optimization with sample data
python3 test_custom_optimizer.py

# Check server logs
tail -f server.log

# Monitor system resources
htop
```

## 📈 Performance

### Typical Performance
- **Data Fetching**: 1-2 seconds for live CFL data
- **Optimization**: 2-5 seconds for single lineup
- **Captain Testing**: 5-10 seconds (tests ~140 players)
- **Total Process**: 8-15 seconds end-to-end

### Optimization Stats
- **Player Pool**: 350+ active CFL players
- **Team Count**: 9 CFL teams
- **Constraints**: 7+ simultaneous constraints
- **Captain Options**: ~140 eligible players tested

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- CFL for providing fantasy data APIs
- PuLP library for linear programming capabilities
- PyDFS Lineup Optimizer for DFS algorithms
- Chrome Extension APIs for seamless integration

## 📞 Support

For issues, questions, or feature requests:
1. Check the [Issues](https://github.com/drewinator/cfl-fantasy-opto/issues) page
2. Review the troubleshooting section above
3. Create a new issue with detailed description

---

**Built with ⚡ for CFL Fantasy enthusiasts by [drewinator](https://github.com/drewinator)**