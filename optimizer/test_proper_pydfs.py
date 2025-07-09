#!/usr/bin/env python3
"""
Test the proper PyDFS CFL implementation
"""
from cfl_pydfs_optimizer_proper import CFLPydfsOptimizer
import json

def test_proper_pydfs():
    # Test the proper implementation
    optimizer = CFLPydfsOptimizer()

    # Load real data
    with open('../json_files/players.json', 'r') as f:
        players_data = json.load(f)

    with open('../json_files/sqauds.json', 'r') as f:
        teams_data = json.load(f)

    print('Testing proper PyDFS CFL implementation...')
    print(f'Loaded {len(players_data)} players and {len(teams_data)} teams')

    # Test data loading
    optimizer.load_players_from_json(players_data)
    optimizer.load_teams_from_json(teams_data)

    # Test optimization
    try:
        result = optimizer.optimize_from_request({
            'players': players_data,
            'teams': teams_data
        })
        print('SUCCESS!')
        print(f'Total salary: ${result["total_salary"]:,}')
        print(f'Projected points: {result["projected_points"]}')
        print(f'Captain: {result["captain_id"]}')
        print(f'Captain bonus: {result["captain_bonus_points"]}')
        print(f'Valid lineup: {result["is_valid"]}')
        print(f'Players: {len(result["players"])}')
        
        print('\nLineup:')
        for i, player in enumerate(result["players"], 1):
            captain_mark = " (C)" if player['is_captain'] else ""
            print(f'{i}. {player["name"]} ({player["position"]}) - ${player["salary"]:,} - {player["projected_points"]} pts{captain_mark}')
            
        return True
    except Exception as e:
        print(f'ERROR: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_proper_pydfs()
    exit(0 if success else 1)