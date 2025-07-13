"""
CFL Fantasy Optimizer API Server
Flask server that provides optimization endpoints for the Chrome extension
"""

import json
import os
import logging
import requests
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from custom_cfl_optimizer import CustomCFLOptimizer
from cfl_pydfs_optimizer import CFLPydfsOptimizer
from projections import build_projection_map, build_team_projection_map


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for Chrome extension

# Global optimizer instances
pulp_optimizer = CustomCFLOptimizer()
pydfs_optimizer = CFLPydfsOptimizer()

def fetch_cfl_data():
    """
    Fetch live data from CFL Fantasy API endpoints
    Replicates the data fetching logic from content.js
    """
    logger.info("Fetching live CFL data...")
    
    cfl_api_endpoints = [
        'https://gamezone.cfl.ca/json/fantasy/players.json',
        'https://gamezone.cfl.ca/json/fantasy/playersSelection.json',
        'https://gamezone.cfl.ca/json/fantasy/squads.json',
        'https://gamezone.cfl.ca/json/fantasy/squadsSelection.json',
        'https://gamezone.cfl.ca/json/fantasy/gameweeks.json'
    ]
    
    all_players = []
    all_teams = []
    gameweeks_data = []
    current_team_data = {}
    ownership_data = {}
    team_ownership_data = {}
    
    for url in cfl_api_endpoints:
        try:
            logger.info(f"Fetching data from {url}")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Extract data based on endpoint type
            if 'players.json' in url:
                players = extract_players_from_cfl_api(data)
                if players:
                    all_players = players
                    logger.info(f"Loaded {len(players)} players")
                    
            elif 'playersSelection.json' in url:
                ownership_data = extract_ownership_from_players_selection(data)
                logger.info(f"Loaded ownership data for {len(ownership_data)} players")
                
            elif 'squads.json' in url:
                teams = extract_teams_from_cfl_squads_api(data)
                if teams:
                    all_teams = teams
                    logger.info(f"Loaded {len(teams)} teams")
                    
            elif 'squadsSelection.json' in url:
                team_ownership_data = extract_team_ownership_from_squads_selection(data)
                logger.info(f"Loaded team ownership data for {len(team_ownership_data)} teams")
                
            elif 'gameweeks.json' in url:
                gameweeks_data = data if isinstance(data, list) else []
                logger.info(f"Loaded {len(gameweeks_data)} gameweeks")
                
        except Exception as error:
            logger.warning(f"Failed to fetch {url}: {error}")
            continue
    
    # If we got players but no teams, create teams from player data
    if all_players and not all_teams:
        all_teams = create_teams_from_player_data(all_players)
        logger.info(f"Created {len(all_teams)} teams from player data")
    
    # Structure data for optimizer
    structured_data = {
        'players': all_players,
        'teams': all_teams,
        'gameweeks': gameweeks_data,
        'current_team': current_team_data,
        'player_ownership': ownership_data,
        'team_ownership': team_ownership_data,
        'source': 'CFL Fantasy API',
        'metadata': {
            'source': 'api_server',
            'timestamp': datetime.now().isoformat(),
            'player_count': len(all_players),
            'team_count': len(all_teams),
            'gameweek_count': len(gameweeks_data)
        }
    }
    
    logger.info(f"Successfully fetched CFL data: {len(all_players)} players, {len(all_teams)} teams")
    return structured_data

def extract_players_from_cfl_api(data):
    """Extract players from CFL players.json API - mirrors content.js logic"""
    players = []
    try:
        # Handle direct list format
        if isinstance(data, list):
            players_data = data
        else:
            # Handle object format with nested data
            players_data = data.get('players') or data.get('data') or data
        
        if isinstance(players_data, list):
            for player in players_data:
                if player and isinstance(player, dict) and player.get('firstName') and player.get('lastName'):
                    players.append(player)
        elif isinstance(players_data, dict):
            for player in players_data.values():
                if isinstance(player, dict) and player.get('firstName') and player.get('lastName'):
                    players.append(player)
                    
        logger.info(f"Extracted {len(players)} players from API data")
    except Exception as error:
        logger.error(f"Error extracting players from CFL API: {error}")
        logger.error(f"Data type: {type(data)}, Data sample: {str(data)[:200]}")
    
    return players

def extract_ownership_from_players_selection(data):
    """Extract ownership data from CFL playersSelection.json API"""
    ownership_data = {}
    try:
        if isinstance(data, dict):
            for player_id, player_ownership in data.items():
                if player_ownership and isinstance(player_ownership, dict):
                    ownership_data[player_id] = {
                        'percents': player_ownership.get('percents', 0),
                        'number': player_ownership.get('number', 0)
                    }
    except Exception as error:
        logger.error(f"Error extracting ownership data: {error}")
    
    return ownership_data

def extract_teams_from_cfl_squads_api(data):
    """Extract teams from CFL squads.json API"""
    teams = []
    try:
        # Handle direct list format
        if isinstance(data, list):
            squads_data = data
        else:
            # Handle object format with nested data
            squads_data = data.get('squads') or data.get('data') or data
        
        if isinstance(squads_data, list):
            for squad in squads_data:
                normalized_team = normalize_cfl_team(squad)
                if normalized_team:
                    teams.append(normalized_team)
                    
        logger.info(f"Extracted {len(teams)} teams from API data")
    except Exception as error:
        logger.error(f"Error extracting teams from CFL squads API: {error}")
        logger.error(f"Data type: {type(data)}, Data sample: {str(data)[:200]}")
    
    return teams

def extract_team_ownership_from_squads_selection(data):
    """Extract team ownership data from CFL squadsSelection.json API"""
    team_ownership_data = {}
    try:
        if isinstance(data, dict):
            for team_id, team_ownership in data.items():
                if team_ownership and isinstance(team_ownership, dict):
                    team_ownership_data[team_id] = {
                        'percents': team_ownership.get('percents', 0),
                        'number': team_ownership.get('number', 0)
                    }
    except Exception as error:
        logger.error(f"Error extracting team ownership data: {error}")
    
    return team_ownership_data

def normalize_cfl_team(raw_team):
    """Normalize CFL team data to standard format"""
    if not raw_team or not isinstance(raw_team, dict):
        return None
    
    try:
        return {
            'id': raw_team.get('id') or raw_team.get('teamId', ''),
            'name': raw_team.get('name') or raw_team.get('teamName', ''),
            'abbreviation': raw_team.get('abbreviation') or raw_team.get('abbr') or raw_team.get('short', ''),
            'cost': int(raw_team.get('cost') or raw_team.get('price') or raw_team.get('salary') or 0),
            'projectedScores': float(raw_team.get('projectedScores') or raw_team.get('points') or raw_team.get('projection') or 0),
            'city': raw_team.get('city', ''),
            'logoUrl': raw_team.get('logoUrl', ''),
            'primaryColor': raw_team.get('primaryColor', ''),
            'secondaryColor': raw_team.get('secondaryColor', '')
        }
    except Exception as error:
        logger.error(f"Error normalizing CFL team: {error}")
        return None

def create_teams_from_player_data(players):
    """Create defense teams from player data when team API is not available"""
    teams = []
    team_abbreviations = set()
    
    # Extract unique teams from player data
    for player in players:
        squad = player.get('squad', {})
        team_name = squad.get('name') or squad.get('abbreviation', '')
        if team_name:
            team_abbreviations.add(team_name.strip())
    
    # Create defense teams for each unique team
    team_id = 1
    for abbr in team_abbreviations:
        teams.append({
            'id': str(team_id),
            'name': f"{abbr} Defense",
            'abbreviation': abbr,
            'cost': 5000,  # Default cost
            'projectedScores': 8.0  # Default projection
        })
        team_id += 1
    
    return teams

@app.route('/')
def index():
    """Serve the mobile web interface"""
    return send_from_directory(os.path.dirname(os.path.dirname(__file__)), 'mobile.html')

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'CFL Fantasy Optimizer API'
    })

@app.route('/optimize', methods=['POST'])
def optimize_lineup():
    """Main optimization endpoint"""
    try:
        # Get request data
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Get engine parameter (default to pulp)
        engine = request.args.get('engine', 'pulp')
        
        # Get projection source parameter (default to our projections)
        source = request.args.get('source', 'our')
        
        logger.info(f"Received optimization request with engine: {engine}, source: {source}, data keys: {list(data.keys())}")
        
        # Select optimizer based on engine parameter
        if engine == 'pydfs':
            optimizer = pydfs_optimizer
        else:
            optimizer = pulp_optimizer
        
        # Extract players and configuration
        players_data = data.get('players', [])
        teams_data = data.get('teams', [])
        config = data.get('league_config', {})
        settings = data.get('optimization_settings', {})
        
        # Apply custom projections if source is 'our'
        if source == 'our':
            try:
                # Apply player projections
                if players_data:
                    player_projection_map = build_projection_map(players_data)
                    # Update player projectedScores with our projections
                    for player in players_data:
                        player_id = player.get('id') or player.get('feedId')
                        if player_id and player_id in player_projection_map:
                            # Update the projectedScores in stats
                            if 'stats' not in player:
                                player['stats'] = {}
                            player['stats']['projectedScores'] = player_projection_map[player_id]
                    
                    logger.info(f"Applied custom projections to {len(player_projection_map)} players")
                
                # Apply team projections
                if teams_data:
                    team_projection_map = build_team_projection_map(teams_data)
                    # Update team projectedScores with our projections
                    for team in teams_data:
                        team_id = team.get('id')
                        if team_id and team_id in team_projection_map:
                            # For teams, projectedScores is at root level
                            team['projectedScores'] = team_projection_map[team_id]
                    
                    logger.info(f"Applied custom projections to {len(team_projection_map)} teams")
                        
            except Exception as e:
                logger.warning(f"Failed to apply custom projections, falling back to site projections: {e}")
        
        if not players_data and not teams_data:
            return jsonify({
                'success': False,
                'error': 'No player or team data provided'
            }), 400
        
        # Handle different optimizer interfaces
        if engine == 'pydfs':
            # PyDFS optimizer uses optimize_from_request method
            formatted_lineup = optimizer.optimize_from_request(data)
            result = {
                'success': True,
                'lineup': formatted_lineup,
                'player_stats': optimizer.get_player_stats(),
                'optimization_time': datetime.now().isoformat(),
                'engine': 'pydfs'
            }
        else:
            # PuLP optimizer uses existing interface
            # Load data into optimizer
            if players_data:
                ownership_data = data.get('player_ownership', {})
                gameweeks_data = data.get('gameweeks', [])
                current_team_data = data.get('current_team', {})
                
                # Debug logging
                logger.info(f"Gameweeks data received: {len(gameweeks_data)} items")
                logger.info(f"Current team data received: {bool(current_team_data)}")
                if len(gameweeks_data) > 0:
                    logger.info(f"First gameweek: {gameweeks_data[0].get('name', 'Unknown')}")
                
                optimizer.load_players_from_json(players_data, ownership_data, gameweeks_data, current_team_data)
            
            if teams_data:
                team_ownership_data = data.get('team_ownership', {})
                optimizer.load_teams_from_json(teams_data, team_ownership_data, current_team_data)
            
            # Get optimization parameters
            max_players_from_team = settings.get('max_players_from_team', 3)
            use_captain = settings.get('use_captain', True)
            num_lineups = settings.get('num_lineups', 1)
            
            # Generate lineup(s)
            if num_lineups > 1:
                lineups = optimizer.generate_multiple_lineups(
                    count=num_lineups,
                    max_players_from_team=max_players_from_team,
                    use_captain=use_captain
                )
                # Format lineups for API response
                formatted_lineups = [optimizer.format_lineup_for_api(lineup) for lineup in lineups]
                result = {
                    'success': True,
                    'lineups': formatted_lineups,
                    'player_stats': optimizer.get_player_stats(),
                    'optimization_time': datetime.now().isoformat(),
                    'engine': 'pulp'
                }
            else:
                lineup = optimizer.generate_lineup(
                    max_players_from_team=max_players_from_team,
                    use_captain=use_captain
                )
                # Format lineup for API response
                formatted_lineup = optimizer.format_lineup_for_api(lineup)
                result = {
                    'success': True,
                    'lineup': formatted_lineup,
                    'player_stats': optimizer.get_player_stats(),
                    'optimization_time': datetime.now().isoformat(),
                    'engine': 'pulp'
                }
        
        logger.info("Optimization completed successfully")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Optimization failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/optimize/multiple', methods=['POST'])
def optimize_multiple_lineups():
    """Generate multiple diverse lineups"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Extract data
        players_data = data.get('players', [])
        teams_data = data.get('teams', [])
        settings = data.get('optimization_settings', {})
        
        # Load data
        if players_data:
            ownership_data = data.get('player_ownership', {})
            optimizer.load_players_from_json(players_data, ownership_data)
        
        if teams_data:
            team_ownership_data = data.get('team_ownership', {})
            optimizer.load_teams_from_json(teams_data, team_ownership_data, {})
        
        # Get parameters
        count = settings.get('num_lineups', 5)
        max_players_from_team = settings.get('max_players_from_team', 3)
        use_captain = settings.get('use_captain', True)
        
        # Generate lineups
        lineups = optimizer.generate_multiple_lineups(
            count=count,
            max_players_from_team=max_players_from_team,
            use_captain=use_captain
        )
        
        # Format lineups for API response
        formatted_lineups = [optimizer.format_lineup_for_api(lineup) for lineup in lineups]
        
        result = {
            'success': True,
            'lineups': formatted_lineups,
            'count': len(lineups),
            'player_stats': optimizer.get_player_stats(),
            'optimization_time': datetime.now().isoformat()
        }
        
        logger.info(f"Generated {len(lineups)} multiple lineups")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Multiple lineup optimization failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/test-data', methods=['POST'])
def test_with_local_data():
    """Test endpoint using local JSON files"""
    try:
        # Get engine parameter (default to pulp)
        engine = request.args.get('engine', 'pulp')
        
        # Select optimizer based on engine parameter
        if engine == 'pydfs':
            optimizer = pydfs_optimizer
        else:
            optimizer = pulp_optimizer
        
        # Load local JSON files
        base_path = os.path.dirname(os.path.dirname(__file__))
        json_path = os.path.join(base_path, 'json_files')
        
        # Load players
        players_file = os.path.join(json_path, 'players.json')
        with open(players_file, 'r') as f:
            players_data = json.load(f)
        
        # Load teams (squads)
        teams_file = os.path.join(json_path, 'sqauds.json')
        with open(teams_file, 'r') as f:
            teams_data = json.load(f)
        
        # Load ownership data
        player_ownership_file = os.path.join(json_path, 'playersselection.json')
        with open(player_ownership_file, 'r') as f:
            player_ownership = json.load(f)
        
        team_ownership_file = os.path.join(json_path, 'sqaudsselection.json')
        with open(team_ownership_file, 'r') as f:
            team_ownership = json.load(f)
        
        # Handle different optimizer interfaces
        if engine == 'pydfs':
            # PyDFS optimizer uses optimize_from_request method
            test_data = {
                'players': players_data,
                'teams': teams_data,
                'player_ownership': player_ownership,
                'team_ownership': team_ownership
            }
            formatted_lineup = optimizer.optimize_from_request(test_data)
            result = {
                'success': True,
                'lineup': formatted_lineup,
                'player_stats': optimizer.get_player_stats(),
                'data_source': 'local_json_files',
                'optimization_time': datetime.now().isoformat(),
                'engine': 'pydfs'
            }
        else:
            # PuLP optimizer uses existing interface
            # Load data into optimizer
            optimizer.load_players_from_json(players_data, player_ownership)
            optimizer.load_teams_from_json(teams_data, team_ownership, {})
            
            # Generate lineup with captain logic
            lineup = optimizer.generate_lineup(max_players_from_team=3, use_captain=True)
            
            # Format lineup for API response
            formatted_lineup = optimizer.format_lineup_for_api(lineup)
            
            result = {
                'success': True,
                'lineup': formatted_lineup,
                'player_stats': optimizer.get_player_stats(),
                'data_source': 'local_json_files',
                'optimization_time': datetime.now().isoformat(),
                'engine': 'pulp'
            }
        
        logger.info(f"Test optimization with local data completed using {engine} engine")
        return jsonify(result)
        
    except FileNotFoundError as e:
        logger.error(f"Local data file not found: {e}")
        return jsonify({
            'success': False,
            'error': f'Local data file not found: {str(e)}'
        }), 404
    except Exception as e:
        logger.error(f"Test optimization failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/projections', methods=['GET'])
def get_projections():
    """Get weighted-average projections for all players"""
    try:
        # Try to get data from local JSON files first
        base_path = os.path.dirname(os.path.dirname(__file__))
        json_path = os.path.join(base_path, 'json_files')
        players_file = os.path.join(json_path, 'players.json')
        
        with open(players_file, 'r') as f:
            players_data = json.load(f)
        
        # Also load teams for defense projections
        teams_file = os.path.join(json_path, 'sqauds.json')
        teams_data = []
        try:
            with open(teams_file, 'r') as f:
                teams_data = json.load(f)
        except FileNotFoundError:
            logger.warning("Teams file not found, skipping team projections")
        
        # Build projection maps
        player_projections = build_projection_map(players_data)
        team_projections = build_team_projection_map(teams_data) if teams_data else {}
        
        # Combine projections
        all_projections = {**player_projections, **team_projections}
        
        return jsonify({
            'success': True,
            'projections': all_projections,
            'player_projections': player_projections,
            'team_projections': team_projections,
            'player_count': len(player_projections),
            'team_count': len(team_projections),
            'total_count': len(all_projections),
            'timestamp': datetime.now().isoformat(),
            'source': 'weighted_average_model'
        })
        
    except FileNotFoundError:
        # Try fetching live data if local files not available
        try:
            cfl_data = fetch_cfl_data()
            if cfl_data.get('players'):
                player_projections = build_projection_map(cfl_data['players'])
                team_projections = build_team_projection_map(cfl_data.get('teams', [])) if cfl_data.get('teams') else {}
                
                # Combine projections
                all_projections = {**player_projections, **team_projections}
                
                return jsonify({
                    'success': True,
                    'projections': all_projections,
                    'player_projections': player_projections,
                    'team_projections': team_projections,
                    'player_count': len(player_projections),
                    'team_count': len(team_projections),
                    'total_count': len(all_projections),
                    'timestamp': datetime.now().isoformat(),
                    'source': 'weighted_average_model_live'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'No player data available'
                }), 404
        except Exception as live_error:
            logger.error(f"Failed to fetch live data for projections: {live_error}")
            return jsonify({
                'success': False,
                'error': 'Unable to fetch player data for projections'
            }), 500
            
    except Exception as e:
        logger.error(f"Failed to generate projections: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/projection-comparison', methods=['GET'])
def get_projection_comparison():
    """Get side-by-side comparison of site vs our projections"""
    try:
        # Try to get data from local JSON files first
        base_path = os.path.dirname(os.path.dirname(__file__))
        json_path = os.path.join(base_path, 'json_files')
        players_file = os.path.join(json_path, 'players.json')
        
        with open(players_file, 'r') as f:
            players_data = json.load(f)
        
        # Also load teams for defense projections
        teams_file = os.path.join(json_path, 'sqauds.json')
        teams_data = []
        try:
            with open(teams_file, 'r') as f:
                teams_data = json.load(f)
        except FileNotFoundError:
            logger.warning("Teams file not found for comparison")
        
        # Build our projection maps
        player_projections = build_projection_map(players_data)
        team_projections = build_team_projection_map(teams_data) if teams_data else {}
        
        # Build comparison data
        comparison_data = []
        
        # Add player comparisons
        for player in players_data:
            player_id = player.get('id') or player.get('feedId')
            if not player_id:
                continue
                
            stats = player.get('stats', {})
            site_projection = stats.get('projectedScores', 0)
            our_projection = player_projections.get(player_id, site_projection)
            
            name = f"{player.get('firstName', '')} {player.get('lastName', '')}".strip()
            team = player.get('squad', {}).get('abbreviation', '')
            position = player.get('position', '')
            
            difference = our_projection - site_projection
            percent_change = ((difference / site_projection) * 100) if site_projection > 0 else 0
            
            comparison_data.append({
                'id': player_id,
                'name': name,
                'team': team,
                'position': position,
                'type': 'player',
                'site_projection': round(site_projection, 2),
                'our_projection': round(our_projection, 2),
                'difference': round(difference, 2),
                'percent_change': round(percent_change, 1)
            })
        
        # Add team comparisons
        for team in teams_data:
            team_id = team.get('id')
            if not team_id:
                continue
                
            site_projection = team.get('projectedScores', 0)
            our_projection = team_projections.get(team_id, site_projection)
            
            name = team.get('name', '')
            abbreviation = team.get('abbreviation', '')
            
            difference = our_projection - site_projection
            percent_change = ((difference / site_projection) * 100) if site_projection > 0 else 0
            
            comparison_data.append({
                'id': team_id,
                'name': name,
                'team': abbreviation,
                'position': 'DEF',
                'type': 'team',
                'site_projection': round(site_projection, 2),
                'our_projection': round(our_projection, 2),
                'difference': round(difference, 2),
                'percent_change': round(percent_change, 1)
            })
        
        # Sort by largest differences first
        comparison_data.sort(key=lambda x: abs(x['difference']), reverse=True)
        
        return jsonify({
            'success': True,
            'comparisons': comparison_data,
            'summary': {
                'total_players': len([c for c in comparison_data if c['type'] == 'player']),
                'total_teams': len([c for c in comparison_data if c['type'] == 'team']),
                'avg_difference': round(sum(c['difference'] for c in comparison_data) / len(comparison_data), 2) if comparison_data else 0,
                'largest_increase': max(comparison_data, key=lambda x: x['difference'])['name'] if comparison_data else None,
                'largest_decrease': min(comparison_data, key=lambda x: x['difference'])['name'] if comparison_data else None
            },
            'timestamp': datetime.now().isoformat()
        })
        
    except FileNotFoundError:
        return jsonify({
            'success': False,
            'error': 'Player data files not found'
        }), 404
    except Exception as e:
        logger.error(f"Failed to generate projection comparison: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/player-stats', methods=['GET'])
def get_player_stats():
    """Get current player pool statistics"""
    try:
        # Get engine parameter (default to pulp)
        engine = request.args.get('engine', 'pulp')
        
        # Select optimizer based on engine parameter
        if engine == 'pydfs':
            optimizer = pydfs_optimizer
        else:
            optimizer = pulp_optimizer
            
        stats = optimizer.get_player_stats()
        return jsonify({
            'success': True,
            'stats': stats,
            'engine': engine
        })
    except Exception as e:
        logger.error(f"Failed to get player stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/load-data', methods=['POST'])
def load_data():
    """Load player and team data without optimization"""
    try:
        data = request.get_json()
        
        players_data = data.get('players', [])
        teams_data = data.get('teams', [])
        
        if players_data:
            ownership_data = data.get('player_ownership', {})
            optimizer.load_players_from_json(players_data, ownership_data)
        
        if teams_data:
            team_ownership_data = data.get('team_ownership', {})
            optimizer.load_teams_from_json(teams_data, team_ownership_data, {})
        
        stats = optimizer.get_player_stats()
        
        return jsonify({
            'success': True,
            'message': 'Data loaded successfully',
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"Failed to load data: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500

@app.route('/optimize-mobile', methods=['POST'])
def optimize_mobile():
    """
    Mobile optimization endpoint that fetches live CFL data and optimizes
    Designed for mobile browsers that can't directly access CFL APIs due to CORS
    """
    try:
        # Get request data
        request_data = request.get_json() or {}
        engine = request_data.get('engine', 'pulp')
        source = request_data.get('source', 'our')
        settings = request_data.get('optimization_settings', {})
        
        logger.info(f"Mobile optimization request with engine: {engine}, source: {source}")
        
        # Fetch live CFL data
        try:
            cfl_data = fetch_cfl_data()
        except Exception as error:
            logger.error(f"Failed to fetch CFL data: {error}")
            return jsonify({
                'success': False,
                'error': f'Unable to fetch live CFL data: {str(error)}'
            }), 500
        
        if not cfl_data.get('players'):
            return jsonify({
                'success': False,
                'error': 'No player data available from CFL APIs'
            }), 500
        
        # Select optimizer based on engine
        if engine == 'pydfs':
            optimizer = pydfs_optimizer
        else:
            optimizer = pulp_optimizer
        
        # Prepare data for optimization
        optimization_data = {
            'players': cfl_data['players'],
            'teams': cfl_data['teams'],
            'gameweeks': cfl_data['gameweeks'],
            'current_team': cfl_data['current_team'],
            'player_ownership': cfl_data['player_ownership'],
            'team_ownership': cfl_data['team_ownership'],
            'league_config': {
                'salary_cap': 70000,
                'roster_size': 7,
                'positions': {
                    'QB': 1,
                    'WR': 2,
                    'RB': 2,
                    'FLEX': 1,
                    'DEF': 1
                }
            },
            'optimization_settings': {
                'max_players_from_team': settings.get('max_players_from_team', 3),
                'use_captain': settings.get('use_captain', True),
                'num_lineups': settings.get('num_lineups', 1)
            },
            'engine': engine,
            'source': source
        }
        
        # Apply custom projections if source is 'our'
        if source == 'our':
            try:
                # Apply player projections
                if cfl_data['players']:
                    player_projection_map = build_projection_map(cfl_data['players'])
                    # Update player projectedScores with our projections
                    for player in cfl_data['players']:
                        player_id = player.get('id') or player.get('feedId')
                        if player_id and player_id in player_projection_map:
                            # Update the projectedScores in stats
                            if 'stats' not in player:
                                player['stats'] = {}
                            player['stats']['projectedScores'] = player_projection_map[player_id]
                    
                    logger.info(f"Applied custom projections to {len(player_projection_map)} players (mobile)")
                
                # Apply team projections
                if cfl_data['teams']:
                    team_projection_map = build_team_projection_map(cfl_data['teams'])
                    # Update team projectedScores with our projections
                    for team in cfl_data['teams']:
                        team_id = team.get('id')
                        if team_id and team_id in team_projection_map:
                            # For teams, projectedScores is at root level
                            team['projectedScores'] = team_projection_map[team_id]
                    
                    logger.info(f"Applied custom projections to {len(team_projection_map)} teams (mobile)")
                        
            except Exception as e:
                logger.warning(f"Failed to apply custom projections in mobile endpoint, falling back to site projections: {e}")
        
        # Run optimization based on engine
        if engine == 'pydfs':
            # PyDFS optimizer
            formatted_lineup = optimizer.optimize_from_request(optimization_data)
            result = {
                'success': True,
                'lineup': formatted_lineup,
                'player_stats': optimizer.get_player_stats(),
                'optimization_time': datetime.now().isoformat(),
                'engine': 'pydfs',
                'data_source': 'live_cfl_api'
            }
        else:
            # PuLP optimizer
            # Load data into optimizer
            if cfl_data['players']:
                optimizer.load_players_from_json(
                    cfl_data['players'], 
                    cfl_data['player_ownership'], 
                    cfl_data['gameweeks'], 
                    cfl_data['current_team']
                )
            
            if cfl_data['teams']:
                optimizer.load_teams_from_json(
                    cfl_data['teams'], 
                    cfl_data['team_ownership'],
                    cfl_data['current_team']
                )
            
            # Generate lineup
            max_players_from_team = settings.get('max_players_from_team', 3)
            use_captain = settings.get('use_captain', True)
            
            lineup = optimizer.generate_lineup(
                max_players_from_team=max_players_from_team,
                use_captain=use_captain
            )
            
            if not lineup:
                return jsonify({
                    'success': False,
                    'error': 'No optimal lineup found'
                }), 400
            
            # Format lineup for API response
            formatted_lineup = optimizer.format_lineup_for_api(lineup)
            
            result = {
                'success': True,
                'lineup': formatted_lineup,
                'player_stats': optimizer.get_player_stats(),
                'optimization_time': datetime.now().isoformat(),
                'engine': 'pulp',
                'data_source': 'live_cfl_api'
            }
        
        logger.info(f"Mobile optimization completed successfully with {engine} engine")
        return jsonify(result)
        
    except Exception as error:
        logger.error(f"Mobile optimization error: {error}")
        return jsonify({
            'success': False,
            'error': str(error)
        }), 500

@app.route('/mobile-players', methods=['GET'])
def get_mobile_players():
    """
    Mobile player browser endpoint that returns all players and teams 
    with comprehensive data including projections and ownership
    """
    try:
        logger.info("Mobile players request received")
        
        # Fetch live CFL data
        try:
            cfl_data = fetch_cfl_data()
        except Exception as error:
            logger.error(f"Failed to fetch CFL data: {error}")
            return jsonify({
                'success': False,
                'error': f'Unable to fetch live CFL data: {str(error)}'
            }), 500
        
        if not cfl_data.get('players'):
            return jsonify({
                'success': False,
                'error': 'No player data available from CFL APIs'
            }), 500
        
        # Build projection maps for both players and teams
        player_projection_map = build_projection_map(cfl_data['players'])
        team_projection_map = build_team_projection_map(cfl_data.get('teams', []))
        
        # Process players data
        processed_players = []
        for player in cfl_data['players']:
            player_id = player.get('id') or player.get('feedId')
            if not player_id:
                continue
                
            # Get ownership data
            ownership_data = cfl_data.get('player_ownership', {}).get(str(player_id), {})
            ownership_percent = ownership_data.get('percents', 0)
            
            # Get projections
            stats = player.get('stats', {})
            site_projection = stats.get('projectedScores', 0)
            our_projection = player_projection_map.get(player_id, site_projection)
            
            # Map position names
            position_map = {
                'quarterback': 'QB',
                'wide_receiver': 'WR', 
                'running_back': 'RB',
                'tight_end': 'TE',
                'kicker': 'K',
                'defence': 'DEF'
            }
            
            position = position_map.get(player.get('position', ''), player.get('position', ''))
            
            processed_player = {
                'id': player_id,
                'name': f"{player.get('firstName', '')} {player.get('lastName', '')}".strip(),
                'firstName': player.get('firstName', ''),
                'lastName': player.get('lastName', ''),
                'position': position,
                'team': player.get('squad', {}).get('abbr', ''),
                'teamName': player.get('squad', {}).get('name', ''),
                'salary': player.get('cost', 0),
                'points': player.get('points', 0),
                'status': player.get('status', 'unavailable'),
                'isLocked': player.get('isLocked', False),
                'site_projection': round(float(site_projection), 2),
                'our_projection': round(float(our_projection), 2),
                'projection_difference': round(float(our_projection) - float(site_projection), 2),
                'avg_points': stats.get('avgPoints', 0),
                'ownership': round(float(ownership_percent), 2),
                'salary_change': stats.get('weekSalaryChange', 0),
                'video_available': bool(player.get('videoURL')),
                'news_available': bool(player.get('newsTitle', {}).get('en', '')),
                'injured': bool(player.get('injuredText', {}).get('en', ''))
            }
            
            processed_players.append(processed_player)
        
        # Process teams data
        processed_teams = []
        for team in cfl_data.get('teams', []):
            team_id = team.get('id')
            if not team_id:
                continue
                
            # Get ownership data
            team_ownership_data = cfl_data.get('team_ownership', {}).get(str(team_id), {})
            ownership_percent = team_ownership_data.get('percents', 0)
            
            # Get projections - teams store projectedScores at root level
            site_projection = team.get('projectedScores', 0)
            our_projection = team_projection_map.get(team_id, site_projection)
            
            processed_team = {
                'id': team_id,
                'name': team.get('name', ''),
                'abbreviation': team.get('abbreviation', ''),
                'position': 'DEF',
                'team': team.get('abbreviation', ''),
                'teamName': team.get('name', ''),
                'salary': team.get('cost', 0),
                'status': 'available',  # Teams are generally always available
                'site_projection': round(float(site_projection), 2),
                'our_projection': round(float(our_projection), 2),
                'projection_difference': round(float(our_projection) - float(site_projection), 2),
                'ownership': round(float(ownership_percent), 2),
                'video_available': bool(team.get('videoURL', {}).get('en', '')),
                'news_available': bool(team.get('newsTitle', {}).get('en', ''))
            }
            
            processed_teams.append(processed_team)
        
        # Sort players by position then by name
        position_order = {'QB': 1, 'WR': 2, 'RB': 3, 'TE': 4, 'K': 5, 'DEF': 6}
        processed_players.sort(key=lambda x: (position_order.get(x['position'], 99), x['name']))
        processed_teams.sort(key=lambda x: x['name'])
        
        # Combine statistics
        total_available_players = len([p for p in processed_players if p['status'] == 'available'])
        total_unavailable_players = len([p for p in processed_players if p['status'] == 'unavailable'])
        
        result = {
            'success': True,
            'players': processed_players,
            'teams': processed_teams,
            'summary': {
                'total_players': len(processed_players),
                'total_teams': len(processed_teams),
                'available_players': total_available_players,
                'unavailable_players': total_unavailable_players,
                'total_items': len(processed_players) + len(processed_teams)
            },
            'positions': ['QB', 'WR', 'RB', 'TE', 'K', 'DEF'],
            'teams_list': list(set([p['team'] for p in processed_players if p['team']])),
            'timestamp': datetime.now().isoformat(),
            'data_source': 'live_cfl_api'
        }
        
        logger.info(f"Mobile players endpoint completed: {len(processed_players)} players, {len(processed_teams)} teams")
        return jsonify(result)
        
    except Exception as error:
        logger.error(f"Mobile players endpoint error: {error}")
        return jsonify({
            'success': False,
            'error': str(error)
        }), 500

def main():
    """Run the Flask development server"""
    port = int(os.environ.get('PORT', 3000))
    debug = os.environ.get('DEBUG', 'true').lower() == 'true'
    
    logger.info(f"Starting CFL Fantasy Optimizer API server on port {port}")
    logger.info(f"Debug mode: {debug}")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))  # Render sets $PORT
    logger.info(f"Starting CFL Fantasy Optimizer API server on port {port}")
    app.run(host="0.0.0.0", port=port)