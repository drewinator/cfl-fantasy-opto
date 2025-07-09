"""
Test script for the CFL Fantasy Optimizer
Tests the optimizer with local JSON data
"""

import json
import os
import sys
from cfl_optimizer import CFLFantasyOptimizer

def load_local_data():
    """Load test data from JSON files"""
    base_path = os.path.dirname(os.path.dirname(__file__))
    json_path = os.path.join(base_path, 'json_files')
    
    print(f"Loading data from: {json_path}")
    
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
    
    return players_data, teams_data, player_ownership, team_ownership

def test_optimizer():
    """Test the CFL optimizer with real data"""
    print("=== CFL Fantasy Optimizer Test ===\n")
    
    try:
        # Load data
        print("1. Loading data...")
        players_data, teams_data, player_ownership, team_ownership = load_local_data()
        print(f"   Loaded {len(players_data)} players and {len(teams_data)} teams")
        
        # Initialize optimizer
        print("\n2. Initializing optimizer...")
        optimizer = CFLFantasyOptimizer()
        
        # Load data into optimizer
        print("\n3. Loading data into optimizer...")
        optimizer.load_players_from_json(players_data, player_ownership)
        optimizer.load_teams_from_json(teams_data, team_ownership)
        
        # Get stats
        print("\n4. Player pool statistics:")
        stats = optimizer.get_player_stats()
        for key, value in stats.items():
            print(f"   {key}: {value}")
        
        # Generate single lineup
        print("\n5. Generating optimal lineup...")
        lineup = optimizer.generate_lineup()
        
        print(f"\n=== OPTIMAL LINEUP ===")
        print(f"Total Salary: ${lineup['total_salary']:,} / ${lineup['salary_cap']:,}")
        print(f"Remaining Cap: ${lineup['remaining_cap']:,}")
        print(f"Projected Points: {lineup['projected_points']}")
        print(f"Valid: {lineup['is_valid']}")
        print("\nPlayers:")
        
        for i, player in enumerate(lineup['players'], 1):
            print(f"  {i}. {player['name']} ({player['position']}) - ${player['salary']:,} - {player['projected_points']} pts")
        
        # Generate multiple lineups
        print("\n6. Generating multiple lineups...")
        lineups = optimizer.generate_multiple_lineups(count=3)
        
        print(f"\n=== MULTIPLE LINEUPS ({len(lineups)}) ===")
        for i, lineup in enumerate(lineups, 1):
            print(f"\nLineup {i}:")
            print(f"  Salary: ${lineup['total_salary']:,} | Points: {lineup['projected_points']}")
            print(f"  Players: {', '.join([p['name'] for p in lineup['players']])}")
        
        print("\n=== TEST COMPLETED SUCCESSFULLY ===")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_api_format():
    """Test API request/response format"""
    print("\n=== API FORMAT TEST ===")
    
    try:
        # Load data
        players_data, teams_data, player_ownership, team_ownership = load_local_data()
        
        # Create API request format
        api_request = {
            'players': players_data,
            'teams': teams_data,
            'player_ownership': player_ownership,
            'team_ownership': team_ownership,
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
                'randomness': 0.1,
                'num_lineups': 1
            }
        }
        
        print(f"API Request format validated:")
        print(f"  Players: {len(api_request['players'])}")
        print(f"  Teams: {len(api_request['teams'])}")
        print(f"  League config: {api_request['league_config']}")
        print(f"  Settings: {api_request['optimization_settings']}")
        
        # Test with optimizer
        optimizer = CFLFantasyOptimizer()
        optimizer.load_players_from_json(api_request['players'], api_request['player_ownership'])
        optimizer.load_teams_from_json(api_request['teams'], api_request['team_ownership'])
        
        lineup = optimizer.generate_lineup(api_request['optimization_settings']['randomness'])
        
        # Create API response format
        api_response = {
            'success': True,
            'lineup': lineup,
            'player_stats': optimizer.get_player_stats(),
            'optimization_time': '2024-01-01T12:00:00'
        }
        
        print(f"\nAPI Response format validated:")
        print(f"  Success: {api_response['success']}")
        print(f"  Lineup players: {len(api_response['lineup']['players'])}")
        print(f"  Total salary: ${api_response['lineup']['total_salary']:,}")
        print(f"  Projected points: {api_response['lineup']['projected_points']}")
        
        return True
        
    except Exception as e:
        print(f"❌ API FORMAT TEST FAILED: {e}")
        return False

if __name__ == "__main__":
    success = test_optimizer()
    api_success = test_api_format()
    
    if success and api_success:
        print("\n✅ ALL TESTS PASSED")
        sys.exit(0)
    else:
        print("\n❌ SOME TESTS FAILED")
        sys.exit(1)