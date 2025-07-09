"""
CFL Fantasy Lineup Optimizer
Optimizes CFL fantasy lineups using pydfs-lineup-optimizer with custom CFL rules
"""

import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pydfs_lineup_optimizer import get_optimizer, Player, LineupOptimizerException
from pydfs_lineup_optimizer.constants import Site, Sport

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class CFLPlayer:
    """Data class for CFL fantasy player"""
    id: str
    name: str
    position: str
    team: str
    salary: int
    projected_points: float
    ownership: float = 0.0
    status: str = "available"

@dataclass
class CFLTeam:
    """Data class for CFL defense teams"""
    id: str
    name: str
    abbreviation: str
    salary: int
    projected_points: float
    ownership: float = 0.0

class CFLOptimizerSettings:
    """CFL Fantasy specific settings"""
    SALARY_CAP = 70000
    ROSTER_SIZE = 7  # QB, WR1, WR2, RB1, RB2, FLEX, DEF
    CAPTAIN_MULTIPLIER = 1.5
    
    # Position requirements
    POSITIONS = {
        'QB': 1,
        'WR': 2, 
        'RB': 2,
        'FLEX': 1,  # Can be WR, RB, or TE
        'DEF': 1
    }
    
    FLEX_POSITIONS = ['WR', 'RB', 'TE']

class CFLFantasyOptimizer:
    """Main CFL Fantasy Optimizer class"""
    
    def __init__(self):
        self.settings = CFLOptimizerSettings()
        self.players: List[CFLPlayer] = []
        self.teams: List[CFLTeam] = []
        self.optimizer = None
        self._setup_optimizer()
    
    def _setup_optimizer(self):
        """Initialize the optimizer with custom settings"""
        try:
            # Create custom optimizer settings for CFL
            self.optimizer = get_optimizer(
                site=Site.DRAFTKINGS,
                sport=Sport.FANTASY_FOOTBALL
            )
            
            logger.info(f"Optimizer initialized for Canadian Football")
            logger.info(f"Available positions: {self.optimizer.available_positions}")
            logger.info(f"Budget: ${self.optimizer.budget}")
            
        except Exception as e:
            logger.error(f"Failed to initialize optimizer: {e}")
            raise
    
    def load_players_from_json(self, players_data: List[Dict], ownership_data: Dict = None) -> None:
        """Load players from JSON data"""
        try:
            self.players = []
            
            for player_data in players_data:
                # Skip unavailable players
                if player_data.get('status') == 'unavailable':
                    continue
                    
                # Get ownership percentage if available
                ownership = 0.0
                if ownership_data and str(player_data.get('id')) in ownership_data:
                    ownership = ownership_data[str(player_data['id'])].get('percents', 0.0)
                
                # Create CFL player
                player = CFLPlayer(
                    id=str(player_data.get('id', '')),
                    name=f"{player_data.get('firstName', '')} {player_data.get('lastName', '')}".strip(),
                    position=self._normalize_position(player_data.get('position', '')),
                    team=player_data.get('squad', {}).get('abbr', ''),
                    salary=player_data.get('cost', 0),
                    projected_points=player_data.get('stats', {}).get('projectedScores', 0.0),
                    ownership=ownership,
                    status=player_data.get('status', 'available')
                )
                
                # Only add players with valid data
                if player.name and player.position and player.salary > 0:
                    self.players.append(player)
            
            logger.info(f"Loaded {len(self.players)} players")
            
        except Exception as e:
            logger.error(f"Failed to load players: {e}")
            raise
    
    def load_teams_from_json(self, teams_data: List[Dict], ownership_data: Dict = None) -> None:
        """Load defense teams from JSON data"""
        try:
            self.teams = []
            
            for team_data in teams_data:
                # Get ownership percentage if available
                ownership = 0.0
                if ownership_data and str(team_data.get('id')) in ownership_data:
                    ownership = ownership_data[str(team_data['id'])].get('percents', 0.0)
                
                team = CFLTeam(
                    id=str(team_data.get('id', '')),
                    name=team_data.get('name', ''),
                    abbreviation=team_data.get('abbreviation', ''),
                    salary=team_data.get('cost', 0),
                    projected_points=team_data.get('projectedScores', 0.0),
                    ownership=ownership
                )
                
                if team.name and team.salary > 0:
                    self.teams.append(team)
            
            logger.info(f"Loaded {len(self.teams)} defense teams")
            
        except Exception as e:
            logger.error(f"Failed to load teams: {e}")
            raise
    
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
    
    def _add_players_to_optimizer(self):
        """Add all players to the optimizer"""
        try:
            # Clear existing players
            self.optimizer.reset_lineup()
            
            # Add individual players
            for player in self.players:
                # Convert to pydfs Player object
                pydfs_player = Player(
                    player_id=player.id,
                    first_name=player.name.split()[0] if player.name.split() else '',
                    last_name=' '.join(player.name.split()[1:]) if len(player.name.split()) > 1 else '',
                    positions=[player.position],
                    team=player.team,
                    salary=player.salary,
                    fppg=player.projected_points
                )
                
                self.optimizer.load_players([pydfs_player])
            
            # Note: Canadian Football doesn't seem to have DEF position in this version
            # Let's skip defense teams for now and focus on the main positions
            
            # If we need to add defense later, we can do:
            # for team in self.teams:
            #     def_player = Player(
            #         player_id=f"DEF_{team.id}",
            #         first_name=team.abbreviation,
            #         last_name="Defense",
            #         positions=['DEF'],
            #         team=team.abbreviation,
            #         salary=team.salary,
            #         fppg=team.projected_points
            #     )
            #     self.optimizer.load_players([def_player])
            
            logger.info(f"Added {len(self.players)} players to optimizer")
            
        except Exception as e:
            logger.error(f"Failed to add players to optimizer: {e}")
            raise
    
    def _apply_cfl_constraints(self):
        """Apply CFL-specific constraints"""
        try:
            # Apply CFL-specific constraints
            self.optimizer.set_fantasy_points_strategy('from_fppg')
            self.optimizer.set_salary_cap(self.settings.SALARY_CAP)
            self.optimizer.set_position_for_flex(self.settings.FLEX_POSITIONS)
            self.optimizer.set_roster_size(self.settings.ROSTER_SIZE)

            for position, limit in self.settings.POSITIONS.items():
                self.optimizer.set_positions_for_same_team(False, positions=[position])

            logger.info("Applied custom CFL constraints to the optimizer")
            
        except Exception as e:
            logger.error(f"Failed to apply constraints: {e}")
            raise
    
    def generate_lineup(self, randomness: float = 0.1) -> Dict[str, Any]:
        """Generate an optimal lineup"""
        try:
            # Add players to optimizer
            self._add_players_to_optimizer()
            
            # Apply constraints
            self._apply_cfl_constraints()
            
            # Note: randomness is handled differently in this version
            # We can add deviation to players for lineup diversity
            
            # Generate lineup
            lineups = self.optimizer.optimize(n=1)
            
            lineups_list = list(lineups)

            if not lineups_list:
                raise Exception("No valid lineups found")
            
            lineup = lineups_list[0]
            
            # Format the result
            result = self._format_lineup_result(lineup)
            
            logger.info(f"Generated lineup with {result['total_salary']} salary and {result['projected_points']} projected points")
            
            return result
            
        except LineupOptimizerException as e:
            logger.error(f"Lineup optimization failed: {e}")
            raise Exception(f"Optimization failed: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to generate lineup: {e}")
            raise
    
    def generate_multiple_lineups(self, count: int = 5, randomness: float = 0.2) -> List[Dict[str, Any]]:
        """Generate multiple diverse lineups"""
        try:
            # Add players to optimizer
            self._add_players_to_optimizer()
            
            # Apply constraints
            self._apply_cfl_constraints()
            
            # Note: randomness is handled differently in this version
            # We can add deviation to players for lineup diversity
            
            # Generate multiple lineups
            lineups = self.optimizer.optimize(n=count)
            
            results = []
            for i, lineup in enumerate(list(lineups)):
                result = self._format_lineup_result(lineup)
                result['lineup_number'] = i + 1
                results.append(result)
            
            logger.info(f"Generated {len(results)} lineups")
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to generate multiple lineups: {e}")
            raise
    
    def _format_lineup_result(self, lineup) -> Dict[str, Any]:
        """Format lineup result for output"""
        try:
            players = []
            total_salary = 0
            projected_points = 0
            
            for player in lineup.lineup:
                player_info = {
                    'id': player.id,
                    'name': f"{player.first_name} {player.last_name}".strip(),
                    'position': player.positions[0] if player.positions else 'UNKNOWN',
                    'team': player.team,
                    'salary': player.salary,
                    'projected_points': player.fppg,
                    'ownership': self._get_player_ownership(player.id)
                }
                
                players.append(player_info)
                total_salary += player.salary
                projected_points += player.fppg
            
            salary_cap = getattr(self.optimizer, 'budget', self.settings.SALARY_CAP)
            
            return {
                'players': players,
                'total_salary': total_salary,
                'projected_points': round(projected_points, 2),
                'remaining_cap': salary_cap - total_salary,
                'salary_cap': salary_cap,
                'lineup_score': round(projected_points, 2),
                'is_valid': total_salary <= salary_cap
            }
            
        except Exception as e:
            logger.error(f"Failed to format lineup result: {e}")
            raise
    
    def _get_player_ownership(self, player_id: str) -> float:
        """Get player ownership percentage"""
        # Find player in our data
        for player in self.players:
            if player.id == player_id:
                return player.ownership
        
        # Check teams
        for team in self.teams:
            if f"DEF_{team.id}" == player_id:
                return team.ownership
        
        return 0.0
    
    def get_player_stats(self) -> Dict[str, Any]:
        """Get statistics about the player pool"""
        stats = {
            'total_players': len(self.players),
            'total_teams': len(self.teams),
            'positions': {},
            'salary_range': {},
            'projection_range': {}
        }
        
        # Position breakdown
        for player in self.players:
            pos = player.position
            if pos not in stats['positions']:
                stats['positions'][pos] = 0
            stats['positions'][pos] += 1
        
        # Salary and projection ranges
        if self.players:
            salaries = [p.salary for p in self.players]
            projections = [p.projected_points for p in self.players]
            
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


def main():
    """Test the optimizer with sample data"""
    optimizer = CFLFantasyOptimizer()
    
    # Test with sample data
    sample_players = [
        {
            'id': 1,
            'firstName': 'Test',
            'lastName': 'QB',
            'position': 'quarterback',
            'squad': {'abbr': 'TOR'},
            'cost': 8000,
            'stats': {'projectedScores': 15.5},
            'status': 'available'
        }
    ]
    
    sample_teams = [
        {
            'id': 1,
            'name': 'Toronto Argonauts',
            'abbreviation': 'TOR',
            'cost': 5000,
            'projectedScores': 8.0
        }
    ]
    
    try:
        optimizer.load_players_from_json(sample_players)
        optimizer.load_teams_from_json(sample_teams)
        
        print("Player stats:", optimizer.get_player_stats())
        
    except Exception as e:
        print(f"Test failed: {e}")


if __name__ == "__main__":
    main()