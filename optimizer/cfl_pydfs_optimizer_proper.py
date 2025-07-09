"""
CFL Fantasy optimizer using proper PyDFS custom sport implementation
"""
import logging
from typing import List, Dict, Any, Optional

from pydfs_lineup_optimizer.settings import BaseSettings, LineupPosition
from pydfs_lineup_optimizer.lineup_optimizer import LineupOptimizer
from pydfs_lineup_optimizer.constants import Site, Sport
from pydfs_lineup_optimizer import Player

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CFLCustomSettings(BaseSettings):
    """Custom settings for CFL Fantasy optimization"""
    site = 'CFL_FANTASY'
    sport = 'CFL'
    budget = 70000  # CFL salary cap
    max_from_one_team = 3  # Maximum players from same team
    min_teams = 2  # Minimum teams represented
    
    # CFL lineup positions: 1 QB, 2 RB, 2 WR, 1 FLEX (WR/RB/TE), 1 DEF
    positions = [
        LineupPosition('QB', ('QB',)),           # 1 quarterback
        LineupPosition('RB1', ('RB',)),          # 1st running back
        LineupPosition('RB2', ('RB',)),          # 2nd running back
        LineupPosition('WR1', ('WR',)),          # 1st wide receiver
        LineupPosition('WR2', ('WR',)),          # 2nd wide receiver
        LineupPosition('FLEX', ('WR', 'RB', 'TE')), # Flex position
        LineupPosition('DEF', ('DEF',))          # Defense
    ]

class CFLPydfsOptimizer:
    """CFL Fantasy optimizer using PyDFS with custom CFL sport"""
    
    def __init__(self):
        self.settings = CFLCustomSettings
        self.optimizer = LineupOptimizer(self.settings)
        self.loaded_players = []
        
    def load_players_from_json(self, players_json, ownership_data=None, gameweeks_data=None, current_team_data=None):
        """Load players from JSON data"""
        players_to_load = []
        
        for p in players_json:
            # Skip unavailable players
            if p.get('status') == 'unavailable':
                continue
                
            player_id = str(p.get('id', ''))
            team_abbr = p.get('squad', {}).get('abbr', '')
            is_locked = p.get('isLocked', False)
            
            # Skip locked players for now (commented out for testing)
            # if is_locked:
            #     continue
                
            # Get normalized position
            position = self._normalize_position(p.get('position', ''))
            
            # Only add valid CFL positions
            if position in ['QB', 'RB', 'WR', 'TE']:
                salary = int(p.get('cost', 0))
                projected_points = float(p.get('stats', {}).get('projectedScores', 0.0))
                
                # Only add players with valid data
                if salary > 0 and projected_points > 0:
                    player = Player(
                        player_id=player_id,
                        first_name=p.get('firstName', ''),
                        last_name=p.get('lastName', ''),
                        positions=[position],
                        team=team_abbr,
                        salary=salary,
                        fppg=projected_points,
                    )
                    players_to_load.append(player)
        
        self.loaded_players = players_to_load
        logger.info(f"Loaded {len(players_to_load)} players for PyDFS optimizer")
    
    def load_teams_from_json(self, teams_json, ownership_data=None):
        """Load defense teams from JSON data"""
        defense_players = []
        
        for team in teams_json:
            if team.get('name') and team.get('cost', 0) > 0:
                salary = int(team.get('cost', 0))
                projected_points = float(team.get('projectedScores', 0.0))
                
                if salary > 0:
                    def_player = Player(
                        player_id=f"DEF_{team.get('id', '')}",
                        first_name=team.get('abbreviation', ''),
                        last_name='Defense',
                        positions=['DEF'],
                        team=team.get('abbreviation', ''),
                        salary=salary,
                        fppg=projected_points,
                    )
                    defense_players.append(def_player)
        
        # Combine with loaded players
        all_players = self.loaded_players + defense_players
        
        # Load all players into the optimizer
        self.optimizer.load_players(all_players)
        
        logger.info(f"Loaded {len(defense_players)} defense teams. Total players: {len(all_players)}")
    
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
        """Generate best lineup with captain logic using PyDFS optimization"""
        best_lineup = None
        best_points = -1
        best_captain_id = None
        
        # Get all non-DEF players as captain candidates
        all_players = list(self.optimizer.player_pool.all_players)
        candidates = [p for p in all_players if 'DEF' not in p.positions]
        
        logger.info(f"Testing {len(candidates)} captain candidates using PyDFS")
        
        for i, captain in enumerate(candidates):
            # Temporarily double captain's points
            original_fppg = captain.fppg
            captain.fppg *= 2  # add MVP multiplier
            
            try:
                # Generate lineup with this captain using PyDFS
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
            
            logger.info(f"Best lineup found with {best_points} points using PyDFS engine")
        
        return best_lineup, best_captain_id

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
        
        for player in lineup.lineup:
            is_captain = getattr(player, 'is_captain', False)
            
            # Calculate actual projected points (captain gets 2x bonus)
            actual_points = player.fppg
            if is_captain:
                actual_points = player.fppg / 2  # Remove the temporary doubling
                captain_bonus_points = actual_points  # Captain gets 1x bonus (2x total)
            
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
            projected_points += actual_points
        
        # Add captain bonus to total
        projected_points += captain_bonus_points
        
        return {
            'players': formatted_lineup,
            'total_salary': total_salary,
            'projected_points': round(projected_points, 2),
            'remaining_cap': CFLCustomSettings.budget - total_salary,
            'salary_cap': CFLCustomSettings.budget,
            'lineup_score': round(projected_points, 2),
            'is_valid': total_salary <= CFLCustomSettings.budget and len(formatted_lineup) == 7,
            'captain_id': best_captain_id if best_captain_id else '',
            'captain_bonus_points': round(captain_bonus_points, 2)
        }
    
    def get_player_stats(self):
        """Get player statistics matching existing API interface"""
        all_players = list(self.optimizer.player_pool.all_players)
        
        stats = {
            'total_players': len([p for p in all_players if 'DEF' not in p.positions]),
            'total_teams': len([p for p in all_players if 'DEF' in p.positions]),
            'positions': {},
            'salary_range': {},
            'projection_range': {}
        }
        
        # Position breakdown
        for player in all_players:
            pos = player.positions[0] if player.positions else 'UNKNOWN'
            if pos not in stats['positions']:
                stats['positions'][pos] = 0
            stats['positions'][pos] += 1
        
        # Salary and projection ranges
        if all_players:
            salaries = [p.salary for p in all_players]
            projections = [p.fppg for p in all_players]
            
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