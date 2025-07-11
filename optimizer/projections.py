"""Weighted-average projections for CFL fantasy.

Formula:
    proj = (0.5 * last_game_pts) + (0.3 * average of previous 2 games) + (0.2 * season_avgPts)

If the player has < 2 games, fall back to site `projectedScores`.
Round to two decimals.

Public function:
    build_projection_map(players_json) -> dict[int, float]
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


def build_projection_map(players_json: List[Dict[str, Any]]) -> Dict[int, float]:
    """
    Build a projection map using weighted-average formula.
    
    Args:
        players_json: List of player dictionaries from CFL API
        
    Returns:
        Dictionary mapping player_id to weighted projection value
    """
    projection_map = {}
    
    for player in players_json:
        try:
            player_id = player.get('id') or player.get('feedId')
            if not player_id:
                continue
                
            # Extract gameweek points data
            stats = player.get('stats', {})
            points_data = stats.get('points', {})
            
            # Handle case where points is an empty array
            if isinstance(points_data, list):
                # Fall back to site projectedScores
                site_projection = stats.get('projectedScores', 0)
                projection_map[player_id] = round(float(site_projection), 2)
                continue
                
            gws_data = points_data.get('gws', {})
            
            if not gws_data or len(gws_data) < 2:
                # Fall back to site projectedScores for players with < 2 games
                site_projection = stats.get('projectedScores', 0)
                projection_map[player_id] = round(float(site_projection), 2)
                continue
            
            # Calculate weighted projection
            projection = calculate_weighted_projection(gws_data, stats)
            projection_map[player_id] = round(projection, 2)
            
        except Exception as e:
            logger.warning(f"Error processing player {player.get('id', 'unknown')}: {e}")
            # Fall back to site projection on error
            try:
                stats = player.get('stats', {})
                site_projection = stats.get('projectedScores', 0)
                if player_id:
                    projection_map[player_id] = round(float(site_projection), 2)
            except:
                pass
    
    logger.info(f"Generated projections for {len(projection_map)} players")
    return projection_map


def calculate_weighted_projection(gws_data: Dict[str, float], stats: Dict[str, Any]) -> float:
    """
    Calculate weighted projection using recent game performance.
    
    Formula: 0.5 * last_game + 0.3 * avg_previous_2 + 0.2 * season_avg
    
    Args:
        gws_data: Dictionary of gameweek -> points
        stats: Player stats containing season average
        
    Returns:
        Weighted projection value
    """
    # Convert gameweek keys to integers and sort to get chronological order
    gameweeks = [(int(week), points) for week, points in gws_data.items() if week.isdigit()]
    gameweeks.sort(key=lambda x: x[0])  # Sort by week number
    
    if len(gameweeks) < 2:
        # Should not happen due to caller check, but safety fallback
        season_avg = stats.get('avgPoints', 0)
        return float(season_avg)
    
    # Get points values in chronological order
    points_values = [points for _, points in gameweeks]
    
    # Last game points (most recent)
    last_game_pts = points_values[-1]
    
    # Average of previous 2 games (2nd and 3rd most recent)
    if len(points_values) >= 3:
        # Take the 2 games before the most recent
        prev_2_games = points_values[-3:-1]
    else:
        # Only have 2 games total, use the first game twice for the "previous 2"
        prev_2_games = [points_values[0], points_values[0]]
    
    avg_previous_2 = sum(prev_2_games) / len(prev_2_games)
    
    # Season average
    season_avg = stats.get('avgPoints', 0)
    
    # Apply weighted formula
    weighted_projection = (
        0.5 * last_game_pts +
        0.3 * avg_previous_2 +
        0.2 * season_avg
    )
    
    return weighted_projection


def get_player_gameweek_summary(player: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get a summary of player's gameweek performance for debugging.
    
    Args:
        player: Player dictionary
        
    Returns:
        Summary dictionary with gameweek info
    """
    stats = player.get('stats', {})
    points_data = stats.get('points', {})
    
    if isinstance(points_data, list):
        return {
            'player_id': player.get('id'),
            'name': f"{player.get('firstName', '')} {player.get('lastName', '')}".strip(),
            'gameweeks': 0,
            'points_data': 'empty_array',
            'site_projection': stats.get('projectedScores', 0)
        }
    
    gws_data = points_data.get('gws', {})
    
    return {
        'player_id': player.get('id'),
        'name': f"{player.get('firstName', '')} {player.get('lastName', '')}".strip(),
        'gameweeks': len(gws_data),
        'points_data': gws_data,
        'season_avg': stats.get('avgPoints', 0),
        'site_projection': stats.get('projectedScores', 0)
    }