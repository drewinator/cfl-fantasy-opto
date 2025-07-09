"""
CFL Fantasy optimizer built on pydfs-lineup-optimizer
Simplified approach that works within PyDFS constraints
"""
import logging
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---- Simplified Optimizer ----
class CFLPydfsOptimizer:
    SALARY_CAP = 70000

    def __init__(self):
        # We'll implement a simple version that doesn't rely on PyDFS constraints
        # since PyDFS is designed for NFL and doesn't easily adapt to CFL rules
        self.players = []
        self.teams = []

    # ------------- Data Loading ------------------
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
    
    def _find_bye_teams(self, gameweeks_data: List[Dict]) -> set:
        """Find teams that are on bye this week (matching existing optimizer logic)"""
        bye_teams = set()
        
        if not gameweeks_data:
            return bye_teams
            
        try:
            # Find current gameweek (status: "active" or most recent incomplete)
            current_gameweek = None
            for gameweek in gameweeks_data:
                if gameweek.get('status') == 'active':
                    current_gameweek = gameweek
                    break
            
            # If no active gameweek, find the first incomplete one
            if not current_gameweek:
                for gameweek in gameweeks_data:
                    if gameweek.get('status') != 'complete':
                        current_gameweek = gameweek
                        break
            
            if not current_gameweek:
                return bye_teams
            
            # Get all teams that have matches this week
            teams_playing = set()
            matches = current_gameweek.get('matches', [])
            
            for match in matches:
                home_team = match.get('homeSquad', {}).get('abbr')
                away_team = match.get('awaySquad', {}).get('abbr')
                
                if home_team:
                    teams_playing.add(home_team)
                if away_team:
                    teams_playing.add(away_team)
            
            # All CFL teams
            all_teams = {'OTT', 'TOR', 'HAM', 'MTL', 'SSK', 'WPG', 'CGY', 'EDM', 'BC'}
            
            # Teams on bye = all teams - teams playing
            bye_teams = all_teams - teams_playing
            
        except Exception as e:
            logger.error(f"Error finding bye teams: {e}")
            
        return bye_teams
    
    def _get_current_lineup_players(self, current_team_data: Dict) -> set:
        """Get player IDs from current lineup (matching existing optimizer logic)"""
        current_players = set()
        
        if not current_team_data:
            return current_players
            
        try:
            team = current_team_data.get('success', {}).get('team', {})
            
            # Extract player IDs from current lineup
            position_fields = [
                'captain', 'quarterback', 'firstWideReceivers', 'secondWideReceivers',
                'firstRunningBacks', 'secondRunningBacks', 'flex', 'defenseSquad'
            ]
            
            for field in position_fields:
                player_id = team.get(field)
                if player_id:
                    current_players.add(str(player_id))
            
        except Exception as e:
            logger.error(f"Error getting current lineup players: {e}")
            
        return current_players

    # ------------- MVP brute-force ----------------
    def get_best_lineup(self):
        """Generate best lineup with captain logic using brute-force approach"""
        best_lineup = None
        best_points = -1
        best_captain_id = None
        
        # Get all non-DST players as captain candidates
        candidates = [p for p in self.optimizer.players if 'DST' not in p.positions]
        
        logger.info(f"Testing {len(candidates)} captain candidates")
        
        for i, captain in enumerate(candidates):
            # Temporarily double captain's points
            original_fppg = captain.fppg
            captain.fppg *= 2  # add MVP multiplier
            
            try:
                # Generate lineup with this captain
                lineup = next(self.optimizer.optimize(1))
                points = lineup.fantasy_points_projection
                
                if points > best_points:
                    best_points = points
                    best_lineup = lineup
                    best_captain_id = captain.id
                    
            except Exception as e:
                logger.warning(f"Failed to optimize with captain {captain.first_name} {captain.last_name}: {e}")
            finally:
                # Reset captain's points
                captain.fppg = original_fppg
        
        if best_lineup and best_captain_id:
            # Mark the captain in the lineup
            for player in best_lineup.lineup:
                if player.id == best_captain_id:
                    player.is_captain = True
                    break
            
            logger.info(f"Best lineup found with {best_points} points")
        
        return best_lineup, best_captain_id

    # API helper
    def optimize_from_request(self, data):
        """Main optimization method matching existing API interface"""
        # Load data
        players_data = data.get('players', [])
        teams_data = data.get('teams', [])
        ownership_data = data.get('player_ownership', {})
        team_ownership_data = data.get('team_ownership', {})
        gameweeks_data = data.get('gameweeks', [])
        current_team_data = data.get('current_team', {})
        
        if players_data:
            self.load_players_from_json(players_data, ownership_data, gameweeks_data, current_team_data)
        
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
        captain_bonus = 0
        
        for player in lineup.lineup:
            # Check if this player is the captain
            is_captain = getattr(player, 'is_captain', False)
            
            # Calculate actual projected points (captain gets 2x bonus)
            actual_points = player.fppg
            if is_captain:
                actual_points = player.fppg / 2  # Remove the temporary doubling
                captain_bonus = actual_points  # Captain gets 1x bonus (2x total)
            else:
                captain_bonus = 0
            
            player_info = {
                'id': player.id,
                'name': f'{player.first_name} {player.last_name}'.strip(),
                'team': player.team,
                'position': player.positions[0],
                'salary': player.salary,
                'projected_points': round(actual_points, 2),
                'ownership': 0.0,  # Could be enhanced to include ownership data
                'is_captain': is_captain
            }
            
            formatted_lineup.append(player_info)
            total_salary += player.salary
            projected_points += actual_points + captain_bonus
        
        return {
            'players': formatted_lineup,
            'total_salary': total_salary,
            'projected_points': round(projected_points, 2),
            'remaining_cap': self.SALARY_CAP - total_salary,
            'salary_cap': self.SALARY_CAP,
            'lineup_score': round(projected_points, 2),
            'is_valid': total_salary <= self.SALARY_CAP,
            'captain_id': best_captain_id if best_captain_id else '',
            'captain_bonus_points': captain_bonus
        }
    
    def get_player_stats(self):
        """Get player statistics matching existing API interface"""
        stats = {
            'total_players': len([p for p in self.optimizer.players if 'DST' not in p.positions]),
            'total_teams': len([p for p in self.optimizer.players if 'DST' in p.positions]),
            'positions': {},
            'salary_range': {},
            'projection_range': {}
        }
        
        # Position breakdown
        for player in self.optimizer.players:
            pos = player.positions[0] if player.positions else 'UNKNOWN'
            if pos not in stats['positions']:
                stats['positions'][pos] = 0
            stats['positions'][pos] += 1
        
        # Salary and projection ranges
        if self.optimizer.players:
            salaries = [p.salary for p in self.optimizer.players]
            projections = [p.fppg for p in self.optimizer.players]
            
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