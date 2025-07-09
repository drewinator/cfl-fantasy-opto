"""
Custom CFL Fantasy Lineup Optimizer
Creates a custom optimizer for CFL fantasy rules without relying on predefined sports
"""

import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from itertools import combinations
import pulp

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
    is_captain: bool = False

@dataclass
class CFLTeam:
    """Data class for CFL defense teams"""
    id: str
    name: str
    abbreviation: str
    salary: int
    projected_points: float
    ownership: float = 0.0

@dataclass
class CFLLineup:
    """Data class for a CFL fantasy lineup"""
    players: List[CFLPlayer]
    total_salary: int
    projected_points: float
    remaining_cap: int
    salary_cap: int
    is_valid: bool
    captain_id: str = ""
    captain_bonus_points: float = 0.0

class CustomCFLOptimizer:
    """Custom CFL Fantasy Optimizer using linear programming"""
    
    def __init__(self):
        self.salary_cap = 70000
        self.players: List[CFLPlayer] = []
        self.teams: List[CFLTeam] = []
        
        # CFL lineup requirements
        self.position_requirements = {
            'QB': 1,
            'WR': 2,
            'RB': 2,
            'FLEX': 1,  # Can be WR, RB, or TE
            'DEF': 1
        }
        
        self.flex_positions = ['WR', 'RB', 'TE']
        
    def load_players_from_json(self, players_data: List[Dict], ownership_data: Dict = None, 
                             gameweeks_data: List[Dict] = None, current_team_data: Dict = None) -> None:
        """Load players from JSON data with bye week and current lineup filtering"""
        try:
            self.players = []
            
            # Find current gameweek and bye teams
            bye_teams = self._find_bye_teams(gameweeks_data)
            current_lineup_players = self._get_current_lineup_players(current_team_data)
            
            for player_data in players_data:
                # Skip unavailable players
                if player_data.get('status') == 'unavailable':
                    continue
                
                player_id = str(player_data.get('id', ''))
                team_abbr = player_data.get('squad', {}).get('abbr', '')
                is_locked = player_data.get('isLocked', False)
                
                # Skip bye week players unless they're in current lineup
                if team_abbr in bye_teams and player_id not in current_lineup_players:
                    continue
                
                # Skip locked players unless they're in current lineup
                if is_locked and player_id not in current_lineup_players:
                    continue
                    
                # Get ownership percentage if available
                ownership = 0.0
                if ownership_data and str(player_data.get('id')) in ownership_data:
                    ownership = ownership_data[str(player_data['id'])].get('percents', 0.0)
                
                # Create CFL player
                player = CFLPlayer(
                    id=player_id,
                    name=f"{player_data.get('firstName', '')} {player_data.get('lastName', '')}".strip(),
                    position=self._normalize_position(player_data.get('position', '')),
                    team=team_abbr,
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
    
    def generate_lineup(self, max_players_from_team: int = 3, use_captain: bool = True) -> CFLLineup:
        """Generate optimal lineup using linear programming with captain logic"""
        try:
            if use_captain:
                return self._generate_lineup_with_captain(max_players_from_team)
            else:
                return self._generate_lineup_without_captain(max_players_from_team)
                
        except Exception as e:
            logger.error(f"Failed to generate lineup: {e}")
            raise
    
    def _generate_lineup_with_captain(self, max_players_from_team: int = 3) -> CFLLineup:
        """Generate lineup with captain logic (brute force optimization)"""
        try:
            # Get all eligible captain candidates (non-DEF players)
            captain_candidates = [p for p in self.players if p.position != 'DEF']
            
            best_lineup = None
            best_total_points = 0
            best_captain = None
            
            # Test each potential captain
            for i, candidate in enumerate(captain_candidates):
                
                # Create temporary modified player pool with doubled captain points
                temp_players = []
                for player in self.players:
                    if player.id == candidate.id:
                        # Double the captain candidate's projected points
                        temp_player = CFLPlayer(
                            id=player.id,
                            name=player.name,
                            position=player.position,
                            team=player.team,
                            salary=player.salary,
                            projected_points=player.projected_points * 2,  # Double for captain
                            ownership=player.ownership,
                            status=player.status
                        )
                        temp_players.append(temp_player)
                    else:
                        temp_players.append(player)
                
                # Backup original players and temporarily use modified pool
                original_players = self.players
                self.players = temp_players
                
                try:
                    # Run full optimization with modified player pool
                    temp_lineup = self._generate_lineup_without_captain(max_players_from_team)
                    
                    if temp_lineup and temp_lineup.projected_points > best_total_points:
                        best_total_points = temp_lineup.projected_points
                        best_lineup = temp_lineup
                        best_captain = candidate
                        
                except Exception as e:
                    logger.warning(f"Failed to optimize with captain {candidate.name}: {e}")
                
                finally:
                    # Restore original players
                    self.players = original_players
            
            if best_lineup and best_captain:
                # Mark the best captain in the final lineup
                for player in best_lineup.players:
                    if player.id == best_captain.id:
                        player.is_captain = True
                        break
                
                # Calculate actual captain bonus (original projected points, not doubled)
                best_lineup.captain_id = best_captain.id
                best_lineup.captain_bonus_points = best_captain.projected_points
                
                # Recalculate total points with captain bonus
                base_points = sum(p.projected_points for p in best_lineup.players)
                best_lineup.projected_points = base_points + best_captain.projected_points
                
                return best_lineup
            else:
                logger.warning("No valid captain found, falling back to no-captain lineup")
                return self._generate_lineup_without_captain(max_players_from_team)

        except Exception as e:
            logger.error(f"Captain optimization failed: {e}")
            raise
    
    def _generate_lineup_without_captain(self, max_players_from_team: int = 3) -> CFLLineup:
        """Generate optimal lineup using linear programming (original logic)"""
        try:
            # Combine players and teams
            all_options = []
            
            # Add players
            for player in self.players:
                all_options.append({
                    'id': player.id,
                    'name': player.name,
                    'position': player.position,
                    'team': player.team,
                    'salary': player.salary,
                    'projected_points': player.projected_points,
                    'ownership': player.ownership,
                    'type': 'player'
                })
            
            # Add teams as DEF
            for team in self.teams:
                all_options.append({
                    'id': f"DEF_{team.id}",
                    'name': f"{team.abbreviation} Defense",
                    'position': 'DEF',
                    'team': team.abbreviation,
                    'salary': team.salary,
                    'projected_points': team.projected_points,
                    'ownership': team.ownership,
                    'type': 'team'
                })
            
            # Debug: Check if we have enough players for each position
            position_counts = {}
            for option in all_options:
                pos = option['position']
                position_counts[pos] = position_counts.get(pos, 0) + 1
            
            # Check flex positions
            flex_available = sum(position_counts.get(pos, 0) for pos in self.flex_positions)
            wr_available = position_counts.get('WR', 0)
            rb_available = position_counts.get('RB', 0)
            
            # Create the linear programming problem
            prob = pulp.LpProblem("CFL_Fantasy_Lineup", pulp.LpMaximize)
            
            # Decision variables: binary variable for each player/team
            player_vars = {}
            for i, option in enumerate(all_options):
                player_vars[i] = pulp.LpVariable(f"player_{i}", cat='Binary')
            
            # Objective function: maximize projected points
            prob += pulp.lpSum([
                player_vars[i] * option['projected_points'] 
                for i, option in enumerate(all_options)
            ])
            
            # Constraint 1: Salary cap
            prob += pulp.lpSum([
                player_vars[i] * option['salary'] 
                for i, option in enumerate(all_options)
            ]) <= self.salary_cap
            
            # Constraint 2: Fixed position requirements (QB and DEF)
            prob += pulp.lpSum([
                player_vars[i] 
                for i, option in enumerate(all_options) 
                if option['position'] == 'QB'
            ]) == 1
            
            prob += pulp.lpSum([
                player_vars[i] 
                for i, option in enumerate(all_options) 
                if option['position'] == 'DEF'
            ]) == 1
            
            # Constraint 3: Flexible position requirements
            # Total of 5 players from WR/RB/TE positions
            prob += pulp.lpSum([
                player_vars[i] 
                for i, option in enumerate(all_options) 
                if option['position'] in self.flex_positions
            ]) == 5
            
            # Constraint 4: Minimum position requirements within flex group
            # At least 2 WRs
            prob += pulp.lpSum([
                player_vars[i] 
                for i, option in enumerate(all_options) 
                if option['position'] == 'WR'
            ]) >= 2
            
            # At least 2 RBs
            prob += pulp.lpSum([
                player_vars[i] 
                for i, option in enumerate(all_options) 
                if option['position'] == 'RB'
            ]) >= 2
            
            # Constraint 5: Total roster size (1 QB + 1 DEF + 5 flex = 7 players)
            prob += pulp.lpSum([player_vars[i] for i in range(len(all_options))]) == 7
            
            # Constraint 4: Max players per team
            teams = set(option['team'] for option in all_options)
            for team in teams:
                prob += pulp.lpSum([
                    player_vars[i] 
                    for i, option in enumerate(all_options) 
                    if option['team'] == team
                ]) <= max_players_from_team
            
            # Solve the problem
            prob.solve(pulp.PULP_CBC_CMD(msg=0))
            
            # Check if solution is optimal
            if prob.status != pulp.LpStatusOptimal:
                raise Exception(f"No optimal solution found. Status: {pulp.LpStatus[prob.status]}")
            
            # Extract the selected players
            selected_players = []
            total_salary = 0
            projected_points = 0
            
            for i, option in enumerate(all_options):
                if player_vars[i].varValue == 1:
                    selected_players.append(CFLPlayer(
                        id=option['id'],
                        name=option['name'],
                        position=option['position'],
                        team=option['team'],
                        salary=option['salary'],
                        projected_points=option['projected_points'],
                        ownership=option['ownership']
                    ))
                    total_salary += option['salary']
                    projected_points += option['projected_points']
            
            # Create lineup result
            lineup = CFLLineup(
                players=selected_players,
                total_salary=total_salary,
                projected_points=round(projected_points, 2),
                remaining_cap=self.salary_cap - total_salary,
                salary_cap=self.salary_cap,
                is_valid=total_salary <= self.salary_cap and len(selected_players) == 7,
                captain_id="",  # No captain in base optimization
                captain_bonus_points=0.0
            )
            
            return lineup
            
        except Exception as e:
            logger.error(f"Failed to generate lineup: {e}")
            raise
    
    def generate_multiple_lineups(self, count: int = 5, max_players_from_team: int = 3, use_captain: bool = True) -> List[CFLLineup]:
        """Generate multiple diverse lineups"""
        lineups = []
        used_players = set()
        
        for i in range(count):
            try:
                # For diversity, exclude some previously used players
                if i > 0:
                    # Remove some high-ownership players for diversity
                    pass  # Could implement player exclusion logic here
                
                lineup = self.generate_lineup(max_players_from_team, use_captain)
                lineups.append(lineup)
                
                # Track used players
                for player in lineup.players:
                    used_players.add(player.id)
                    
            except Exception as e:
                logger.warning(f"Failed to generate lineup {i+1}: {e}")
                break
        
        return lineups
    
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
    
    def format_lineup_for_api(self, lineup: CFLLineup) -> Dict[str, Any]:
        """Format lineup for API response"""
        return {
            'players': [
                {
                    'id': player.id,
                    'name': player.name,
                    'position': player.position,
                    'team': player.team,
                    'salary': player.salary,
                    'projected_points': player.projected_points,
                    'ownership': player.ownership,
                    'is_captain': player.is_captain
                }
                for player in lineup.players
            ],
            'total_salary': lineup.total_salary,
            'projected_points': lineup.projected_points,
            'remaining_cap': lineup.remaining_cap,
            'salary_cap': lineup.salary_cap,
            'lineup_score': lineup.projected_points,
            'is_valid': lineup.is_valid,
            'captain_id': lineup.captain_id,
            'captain_bonus_points': lineup.captain_bonus_points
        }


def main():
    """Test the custom optimizer"""
    optimizer = CustomCFLOptimizer()
    
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
        },
        {
            'id': 2,
            'firstName': 'Test',
            'lastName': 'RB1',
            'position': 'running_back',
            'squad': {'abbr': 'MTL'},
            'cost': 7500,
            'stats': {'projectedScores': 12.3},
            'status': 'available'
        },
        {
            'id': 3,
            'firstName': 'Test',
            'lastName': 'RB2',
            'position': 'running_back',
            'squad': {'abbr': 'CGY'},
            'cost': 6500,
            'stats': {'projectedScores': 10.1},
            'status': 'available'
        },
        {
            'id': 4,
            'firstName': 'Test',
            'lastName': 'WR1',
            'position': 'wide_receiver',
            'squad': {'abbr': 'WPG'},
            'cost': 8500,
            'stats': {'projectedScores': 14.2},
            'status': 'available'
        },
        {
            'id': 5,
            'firstName': 'Test',
            'lastName': 'WR2',
            'position': 'wide_receiver',
            'squad': {'abbr': 'SSK'},
            'cost': 7200,
            'stats': {'projectedScores': 11.8},
            'status': 'available'
        },
        {
            'id': 6,
            'firstName': 'Test',
            'lastName': 'WR3',
            'position': 'wide_receiver',
            'squad': {'abbr': 'BC'},
            'cost': 6800,
            'stats': {'projectedScores': 9.7},
            'status': 'available'
        },
        {
            'id': 7,
            'firstName': 'Test',
            'lastName': 'RB3',
            'position': 'running_back',
            'squad': {'abbr': 'EDM'},
            'cost': 6000,
            'stats': {'projectedScores': 8.5},
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
        
        lineup = optimizer.generate_lineup()
        print("Generated lineup:", optimizer.format_lineup_for_api(lineup))
        
    except Exception as e:
        print(f"Test failed: {e}")


if __name__ == "__main__":
    main()