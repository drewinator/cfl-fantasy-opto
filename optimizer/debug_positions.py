#!/usr/bin/env python3
from cfl_pydfs_optimizer_proper import CFLPydfsOptimizer
import json

optimizer = CFLPydfsOptimizer()

with open('../json_files/players.json', 'r') as f:
    players_data = json.load(f)

optimizer.load_players_from_json(players_data)

# Load teams to trigger the player loading into optimizer
with open('../json_files/sqauds.json', 'r') as f:
    teams_data = json.load(f)
optimizer.load_teams_from_json(teams_data)

# Check loaded_players first
print(f'Loaded players: {len(optimizer.loaded_players)}')
for p in optimizer.loaded_players[:5]:
    print(f'  {p.first_name} {p.last_name} - {p.positions[0]} - ${p.salary} - {p.fppg} pts')

all_players = list(optimizer.optimizer.player_pool.all_players)

print('Position breakdown:')
positions = {}
for p in all_players:
    pos = p.positions[0]
    positions[pos] = positions.get(pos, 0) + 1
    
for pos, count in positions.items():
    print(f'{pos}: {count}')
    
print('\nQB players:')
qbs = [p for p in all_players if 'QB' in p.positions]
for qb in qbs:
    print(f'  {qb.first_name} {qb.last_name} - ${qb.salary} - {qb.fppg} pts')
    
print('\nRB players:')
rbs = [p for p in all_players if 'RB' in p.positions]
for rb in rbs:
    print(f'  {rb.first_name} {rb.last_name} - ${rb.salary} - {rb.fppg} pts')

print('\nWR players:')
wrs = [p for p in all_players if 'WR' in p.positions]
for wr in wrs:
    print(f'  {wr.first_name} {wr.last_name} - ${wr.salary} - {wr.fppg} pts')