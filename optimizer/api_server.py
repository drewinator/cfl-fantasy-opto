"""
CFL Fantasy Optimizer API Server
Flask server that provides optimization endpoints for the Chrome extension
"""

import json
import os
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from custom_cfl_optimizer import CustomCFLOptimizer
from cfl_pydfs_optimizer import CFLPydfsOptimizer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for Chrome extension

# Global optimizer instances
pulp_optimizer = CustomCFLOptimizer()
pydfs_optimizer = CFLPydfsOptimizer()

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
        
        logger.info(f"Received optimization request with engine: {engine}, data keys: {list(data.keys())}")
        
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
                optimizer.load_teams_from_json(teams_data, team_ownership_data)
            
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
            optimizer.load_teams_from_json(teams_data, team_ownership_data)
        
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
            optimizer.load_teams_from_json(teams_data, team_ownership)
            
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
            optimizer.load_teams_from_json(teams_data, team_ownership_data)
        
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
    main()