"""
Test the custom CFL optimizer with real JSON data
"""

import json
import os
from custom_cfl_optimizer import CustomCFLOptimizer

def test_with_real_data():
    """Test the custom optimizer with real CFL data"""
    print("=== Custom CFL Optimizer Test with Real Data ===\n")
    
    try:
        # Load real data
        base_path = os.path.dirname(os.path.dirname(__file__))
        json_path = os.path.join(base_path, 'json_files')
        
        print("1. Loading real CFL data...")
        
        # Load players
        players_file = os.path.join(json_path, 'players.json')
        with open(players_file, 'r') as f:
            players_data = json.load(f)
        
        # Load teams
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
        
        print(f"   Loaded {len(players_data)} players and {len(teams_data)} teams")
        
        # Initialize optimizer
        print("\n2. Initializing custom optimizer...")
        optimizer = CustomCFLOptimizer()
        
        # Load data
        print("\n3. Loading data into optimizer...")
        optimizer.load_players_from_json(players_data, player_ownership)
        optimizer.load_teams_from_json(teams_data, team_ownership)
        
        # Get stats
        print("\n4. Player pool statistics:")
        stats = optimizer.get_player_stats()
        for key, value in stats.items():
            print(f"   {key}: {value}")
        
        # Generate lineup
        print("\n5. Generating optimal lineup...")
        lineup = optimizer.generate_lineup()
        formatted_lineup = optimizer.format_lineup_for_api(lineup)
        
        print(f"\n=== OPTIMAL LINEUP ===")
        print(f"Total Salary: ${formatted_lineup['total_salary']:,} / ${formatted_lineup['salary_cap']:,}")
        print(f"Remaining Cap: ${formatted_lineup['remaining_cap']:,}")
        print(f"Projected Points: {formatted_lineup['projected_points']}")
        print(f"Captain Bonus: +{formatted_lineup['captain_bonus_points']:.1f} pts")
        print(f"Valid: {formatted_lineup['is_valid']}")
        print("\nPlayers:")
        
        for i, player in enumerate(formatted_lineup['players'], 1):
            ownership_str = f" ({player['ownership']:.1f}%)" if player['ownership'] > 0 else ""
            captain_str = " ⭐ CAPTAIN" if player['is_captain'] else ""
            print(f"  {i}. {player['name']} ({player['position']}) - ${player['salary']:,} - {player['projected_points']} pts{ownership_str}{captain_str}")
        
        # Generate multiple lineups
        print("\n6. Generating multiple lineups...")
        lineups = optimizer.generate_multiple_lineups(count=3)
        
        print(f"\n=== MULTIPLE LINEUPS ({len(lineups)}) ===")
        for i, lineup in enumerate(lineups, 1):
            formatted = optimizer.format_lineup_for_api(lineup)
            print(f"\nLineup {i}:")
            print(f"  Salary: ${formatted['total_salary']:,} | Points: {formatted['projected_points']}")
            print(f"  Players: {', '.join([p['name'] for p in formatted['players']])}")
        
        print("\n✅ TEST COMPLETED SUCCESSFULLY!")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_with_real_data()
    exit(0 if success else 1)