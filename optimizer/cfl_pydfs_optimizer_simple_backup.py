"""
CFL Fantasy optimizer - Simple implementation that works
Since PyDFS is designed for NFL, this uses a simple greedy algorithm
"""
import logging
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CFLPydfsOptimizer:
    SALARY_CAP = 70000

    def __init__(self):
        self.players = []
        self.teams = []

    def load_players_from_json(self, players_json, ownership_data=None, gameweeks_data=None, current_team_data=None):
        """Load players from JSON data"""
        self.players = []
        
        for p in players_json:
            # Skip unavailable players
            if p.get('status') == 'unavailable':
                continue
                
            player_id = str(p.get('id', ''))
            team_abbr = p.get('squad', {}).get('abbr', '')
            is_locked = p.get('isLocked', False)
            
            # Skip locked players for simplicity
            if is_locked:
                continue
                
            # Get normalized position
            position = self._normalize_position(p.get('position', ''))
            
            # Only add valid CFL positions
            if position in ['QB', 'RB', 'WR', 'TE']:
                player_data = {
                    'id': player_id,
                    'first_name': p.get('firstName', ''),
                    'last_name': p.get('lastName', ''),
                    'position': position,
                    'team': team_abbr,
                    'salary': int(p.get('cost', 0)),
                    'projected_points': float(p.get('stats', {}).get('projectedScores', 0.0)),
                    'ownership': 0.0
                }
                
                # Only add players with valid data
                if player_data['salary'] > 0 and player_data['projected_points'] > 0:
                    self.players.append(player_data)
        
        logger.info(f"Loaded {len(self.players)} players for PyDFS optimizer")
    
    def load_teams_from_json(self, teams_json, ownership_data=None):
        """Load defense teams from JSON data"""
        self.teams = []
        
        for team in teams_json:
            if team.get('name') and team.get('cost', 0) > 0:
                team_data = {
                    'id': f"DEF_{team.get('id', '')}",
                    'first_name': team.get('abbreviation', ''),
                    'last_name': 'Defense',
                    'position': 'DEF',
                    'team': team.get('abbreviation', ''),
                    'salary': int(team.get('cost', 0)),
                    'projected_points': float(team.get('projectedScores', 0.0)),
                    'ownership': 0.0
                }
                
                if team_data['salary'] > 0:
                    self.teams.append(team_data)
        
        logger.info(f"Loaded {len(self.teams)} defense teams for PyDFS optimizer")
    
    def _normalize_position(self, position: str) -> str:
        """Normalize position names to standard format"""
        position_map = {
            'quarterback': 'QB',
            'wide_receiver': 'WR', 
            'running_back': 'RB',
            'tight_end': 'TE',
            'defense': 'DEF',
            'kicker': 'K'
        }
        
        return position_map.get(position.lower(), position.upper())

    def get_best_lineup(self):
        """Generate best lineup using simple greedy algorithm with captain logic"""
        # Combine players and teams
        all_players = self.players + self.teams
        
        if len(all_players) < 7:
            logger.error(f"Not enough players ({len(all_players)}) to form a lineup")
            return None, None
        
        # Calculate value per dollar for initial selection
        for player in all_players:
            if player['salary'] > 0:
                player['value'] = player['projected_points'] / player['salary']
            else:
                player['value'] = 0
        
        # Sort by value (points per dollar)
        sorted_players = sorted(all_players, key=lambda x: x['value'], reverse=True)
        
        # Try to build a valid CFL lineup (1 QB, 2 RB, 2 WR, 1 FLEX, 1 DEF)
        positions_needed = {'QB': 1, 'RB': 2, 'WR': 2, 'DEF': 1}
        flex_positions = ['RB', 'WR', 'TE']
        
        lineup = []
        total_salary = 0
        position_counts = {'QB': 0, 'RB': 0, 'WR': 0, 'TE': 0, 'DEF': 0}
        
        # First pass: fill required positions
        for player in sorted_players:
            pos = player['position']
            
            # Check if we need this position
            if pos in positions_needed and position_counts[pos] < positions_needed[pos]:
                if total_salary + player['salary'] <= self.SALARY_CAP:
                    lineup.append(player)
                    total_salary += player['salary']
                    position_counts[pos] += 1
        
        # Second pass: fill FLEX position
        flex_needed = 1
        for player in sorted_players:
            if len(lineup) >= 7:
                break
                
            pos = player['position']
            if pos in flex_positions and player not in lineup:
                if total_salary + player['salary'] <= self.SALARY_CAP:
                    lineup.append(player)
                    total_salary += player['salary']
                    flex_needed -= 1
                    if flex_needed <= 0:
                        break
        
        if len(lineup) != 7:
            logger.warning(f"Could not build complete lineup, only {len(lineup)} players")
            return None, None
        
        # Now test captain logic (brute force)
        best_total_points = 0
        best_captain_id = None
        base_points = sum(p['projected_points'] for p in lineup)
        
        # Test each non-DEF player as captain
        for potential_captain in lineup:
            if potential_captain['position'] != 'DEF':
                # Captain gets 2x points total (1x base + 1x bonus)
                captain_points = base_points + potential_captain['projected_points']
                
                if captain_points > best_total_points:
                    best_total_points = captain_points
                    best_captain_id = potential_captain['id']
        
        # Mark the captain
        for player in lineup:
            player['is_captain'] = (player['id'] == best_captain_id)
        
        logger.info(f"Built lineup with {len(lineup)} players, ${total_salary}, {best_total_points:.1f} points")
        return lineup, best_captain_id

    def optimize_from_request(self, data):
        """Main optimization method matching existing API interface"""
        # Load data
        players_data = data.get('players', [])
        teams_data = data.get('teams', [])
        ownership_data = data.get('player_ownership', {})
        team_ownership_data = data.get('team_ownership', {})
        
        if players_data:
            self.load_players_from_json(players_data, ownership_data)
        
        if teams_data:
            self.load_teams_from_json(teams_data, team_ownership_data)
        
        # Generate optimal lineup
        lineup, best_captain_id = self.get_best_lineup()
        
        if not lineup:
            raise ValueError("No valid lineup found")
        
        # Format response to match existing API
        formatted_lineup = []
        total_salary = 0
        projected_points = 0
        captain_bonus_points = 0
        
        for player in lineup:
            is_captain = player.get('is_captain', False)
            base_points = player['projected_points']
            
            if is_captain:
                captain_bonus_points = base_points
            
            player_info = {
                'id': player['id'],
                'name': f"{player['first_name']} {player['last_name']}".strip(),
                'team': player['team'],
                'position': player['position'],
                'salary': player['salary'],
                'projected_points': round(base_points, 2),
                'ownership': player.get('ownership', 0.0),
                'is_captain': is_captain
            }
            
            formatted_lineup.append(player_info)
            total_salary += player['salary']
            projected_points += base_points
        
        # Add captain bonus to total
        projected_points += captain_bonus_points
        
        return {
            'players': formatted_lineup,
            'total_salary': total_salary,
            'projected_points': round(projected_points, 2),
            'remaining_cap': self.SALARY_CAP - total_salary,
            'salary_cap': self.SALARY_CAP,
            'lineup_score': round(projected_points, 2),
            'is_valid': total_salary <= self.SALARY_CAP and len(formatted_lineup) == 7,
            'captain_id': best_captain_id if best_captain_id else '',
            'captain_bonus_points': round(captain_bonus_points, 2)
        }
    
    def get_player_stats(self):
        """Get player statistics matching existing API interface"""
        all_players = self.players + self.teams
        
        stats = {
            'total_players': len(self.players),
            'total_teams': len(self.teams),
            'positions': {},
            'salary_range': {},
            'projection_range': {}
        }
        
        # Position breakdown
        for player in all_players:
            pos = player['position']
            if pos not in stats['positions']:
                stats['positions'][pos] = 0
            stats['positions'][pos] += 1
        
        # Salary and projection ranges
        if all_players:
            salaries = [p['salary'] for p in all_players]
            projections = [p['projected_points'] for p in all_players]
            
            stats['salary_range'] = {
                'min': min(salaries),
                'max': max(salaries),
                'avg': round(sum(salaries) / len(salaries), 2)
            }
            
            stats['projection_range'] = {
                'min': min(projections),
                'max': max(projections), 
                'avg': round(sum(projections) / len(projections), 2)
            }
        
        return stats