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
        """Load players from JSON data with bye week and current lineup filtering"""
        players_to_load = []
        
        # Find current gameweek and bye teams using PuLP's proven logic
        bye_teams = self._find_bye_teams(gameweeks_data)
        current_lineup_players = self._get_current_lineup_players(current_team_data)
        
        for p in players_json:
            # Skip unavailable players
            if p.get('status') == 'unavailable':
                continue
                
            player_id = str(p.get('id', ''))
            team_abbr = p.get('squad', {}).get('abbr', '')
            is_locked = p.get('isLocked', False)
            
            # Skip bye week players unless they're in current lineup
            if team_abbr in bye_teams and player_id not in current_lineup_players:
                continue
            
            # Skip locked players unless they're in current lineup
            if is_locked and player_id not in current_lineup_players:
                continue
                
            # Get normalized position
            position = self._normalize_position(p.get('position', ''))
            
            # Only add valid CFL positions
            if position in ['QB', 'RB', 'WR', 'TE']:
                salary = int(p.get('cost', 0))
                
                # Handle projected points conversion safely
                stats = p.get('stats', {})
                projected_scores = stats.get('projectedScores', 0.0)
                if isinstance(projected_scores, dict):
                    # Handle dict case - maybe it's nested
                    projected_points = float(projected_scores.get('value', projected_scores.get('score', 0.0)))
                else:
                    projected_points = float(projected_scores)
                
                # Get ownership percentage using PuLP's proven logic
                ownership_pct = 0.0
                if ownership_data and player_id in ownership_data:
                    ownership_pct = ownership_data[player_id].get('percents', 0.0)
                
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
                    # Store ownership data as custom attribute
                    player.ownership = ownership_pct
                    players_to_load.append(player)
        
        self.loaded_players = players_to_load
        logger.info(f"Loaded {len(players_to_load)} players for PyDFS optimizer")
    
    def load_teams_from_json(self, teams_json, ownership_data=None):
        """Load defense teams from JSON data"""
        defense_players = []
        
        for team in teams_json:
            if team.get('name') and team.get('cost', 0) > 0:
                salary = int(team.get('cost', 0))
                
                # Handle projected points conversion safely
                projected_scores = team.get('projectedScores', 0.0)
                if isinstance(projected_scores, dict):
                    # Handle dict case - maybe it's nested
                    projected_points = float(projected_scores.get('value', projected_scores.get('score', 0.0)))
                else:
                    projected_points = float(projected_scores)
                    
                team_id = f"DEF_{team.get('id', '')}"
                
                # Get ownership percentage for defense using PuLP's proven logic
                ownership_pct = 0.0
                if ownership_data and team_id in ownership_data:
                    ownership_pct = ownership_data[team_id].get('percents', 0.0)
                
                if salary > 0:
                    def_player = Player(
                        player_id=team_id,
                        first_name=team.get('abbreviation', ''),
                        last_name='Defense',
                        positions=['DEF'],
                        team=team.get('abbreviation', ''),
                        salary=salary,
                        fppg=projected_points,
                    )
                    # Store ownership data as custom attribute
                    def_player.ownership = ownership_pct
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
    
    def _find_bye_teams(self, gameweeks_data: List[Dict]) -> set:
        """Find teams that are on bye this week"""
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
                logger.warning("No active gameweek found")
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
            
            # All CFL teams (you might want to make this dynamic)
            all_teams = {'OTT', 'TOR', 'HAM', 'MTL', 'SSK', 'WPG', 'CGY', 'EDM', 'BC'}
            
            # Teams on bye = all teams - teams playing
            bye_teams = all_teams - teams_playing
            
        except Exception as e:
            logger.error(f"Error finding bye teams: {e}")
            
        return bye_teams
    
    def _get_current_lineup_players(self, current_team_data: Dict) -> set:
        """Get player IDs from current lineup"""
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
        gameweeks_data = data.get('gameweeks', {})
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
                'ownership': getattr(player, 'ownership', 0.0),
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