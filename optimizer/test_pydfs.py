#!/usr/bin/env python3
"""
Test script for PyDFS CFL optimizer
"""
import json
import os
from cfl_pydfs_optimizer import CFLPydfsOptimizer

def test_pydfs_optimizer():
    """Test PyDFS optimizer with real data"""
    print("=== PyDFS CFL Optimizer Test ===\n")
    
    # Get the base directory
    base_dir = os.path.dirname(os.path.dirname(__file__))
    json_dir = os.path.join(base_dir, 'json_files')
    
    try:
        # Load real data
        print("1. Loading real CFL data...")
        
        # Load players
        with open(os.path.join(json_dir, 'players.json'), 'r') as f:
            players_data = json.load(f)
        
        # Load teams
        with open(os.path.join(json_dir, 'sqauds.json'), 'r') as f:
            teams_data = json.load(f)
        
        # Load ownership data
        with open(os.path.join(json_dir, 'playersselection.json'), 'r') as f:
            player_ownership = json.load(f)
        
        with open(os.path.join(json_dir, 'sqaudsselection.json'), 'r') as f:
            team_ownership = json.load(f)
        
        print(f"   Loaded {len(players_data)} players and {len(teams_data)} teams")
        
        # Initialize optimizer
        print("\n2. Initializing PyDFS optimizer...")
        optimizer = CFLPydfsOptimizer()
        
        # Test data structure
        test_data = {
            'players': players_data,
            'teams': teams_data,
            'player_ownership': player_ownership,
            'team_ownership': team_ownership
        }
        
        print("\n3. Loading data into optimizer...")
        optimizer.load_players_from_json(players_data, player_ownership)
        optimizer.load_teams_from_json(teams_data, team_ownership)
        
        print("\n4. Player pool statistics:")
        stats = optimizer.get_player_stats()
        for key, value in stats.items():
            print(f"   {key}: {value}")
        
        print("\n5. Testing optimization...")
        result = optimizer.optimize_from_request(test_data)
        
        print(f"\n✅ SUCCESS! Generated lineup:")
        print(f"   Total salary: ${result['total_salary']:,}")
        print(f"   Projected points: {result['projected_points']}")
        print(f"   Remaining cap: ${result['remaining_cap']:,}")
        print(f"   Captain: {result['captain_id']}")
        print(f"   Captain bonus: {result['captain_bonus_points']}")
        
        print(f"\n   Lineup players:")
        for i, player in enumerate(result['players'], 1):
            captain_mark = " (C)" if player['is_captain'] else ""
            print(f"   {i}. {player['name']} ({player['position']}) - ${player['salary']:,} - {player['projected_points']} pts{captain_mark}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_pydfs_optimizer()
    exit(0 if success else 1)