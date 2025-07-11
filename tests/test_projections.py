"""
Unit tests for projections module
Tests the weighted-average projection calculation logic
"""

import json
import os
import sys
import unittest

# Add the optimizer directory to the path to import projections
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
optimizer_dir = os.path.join(parent_dir, 'optimizer')
sys.path.insert(0, optimizer_dir)

import projections as p


class TestProjections(unittest.TestCase):
    
    def setUp(self):
        """Set up test data"""
        # Sample player data with gameweek history
        self.sample_players = [
            {
                "id": 1,
                "firstName": "Test",
                "lastName": "Player1",
                "stats": {
                    "avgPoints": 10.0,
                    "projectedScores": 8.5,
                    "points": {
                        "gws": {
                            "1": 15.0,
                            "2": 12.0,
                            "3": 8.0
                        }
                    }
                }
            },
            {
                "id": 2,
                "firstName": "Test",
                "lastName": "Player2",
                "stats": {
                    "avgPoints": 5.0,
                    "projectedScores": 6.0,
                    "points": {
                        "gws": {
                            "1": 8.0,
                            "2": 4.0
                        }
                    }
                }
            },
            {
                "id": 3,
                "firstName": "Test",
                "lastName": "Player3",
                "stats": {
                    "avgPoints": 7.5,
                    "projectedScores": 7.0,
                    "points": []  # No gameweek data - should fall back to site projection
                }
            },
            {
                "id": 4,
                "firstName": "Test",
                "lastName": "Player4",
                "stats": {
                    "avgPoints": 12.0,
                    "projectedScores": 11.0,
                    "points": {
                        "gws": {
                            "1": 5.0  # Only 1 game - should fall back to site projection
                        }
                    }
                }
            }
        ]
    
    def test_build_projection_map_basic(self):
        """Test basic projection map generation"""
        projection_map = p.build_projection_map(self.sample_players)
        
        # Should return a dictionary
        self.assertIsInstance(projection_map, dict)
        
        # Should have projections for all players
        self.assertEqual(len(projection_map), 4)
        
        # All values should be floats rounded to 2 decimals
        for player_id, projection in projection_map.items():
            self.assertIsInstance(projection, float)
            self.assertEqual(projection, round(projection, 2))
    
    def test_weighted_calculation_player1(self):
        """Test weighted calculation for player with 3+ games"""
        projection_map = p.build_projection_map(self.sample_players)
        player1_projection = projection_map[1]
        
        # Player 1: last_game=8.0, avg_prev_2=(15.0+12.0)/2=13.5, season_avg=10.0
        # Expected: 0.5*8.0 + 0.3*13.5 + 0.2*10.0 = 4.0 + 4.05 + 2.0 = 10.05
        expected = 0.5 * 8.0 + 0.3 * 13.5 + 0.2 * 10.0
        self.assertEqual(player1_projection, round(expected, 2))
    
    def test_weighted_calculation_player2(self):
        """Test weighted calculation for player with exactly 2 games"""
        projection_map = p.build_projection_map(self.sample_players)
        player2_projection = projection_map[2]
        
        # Player 2: last_game=4.0, avg_prev_2=(8.0+8.0)/2=8.0 (first game used twice), season_avg=5.0
        # Expected: 0.5*4.0 + 0.3*8.0 + 0.2*5.0 = 2.0 + 2.4 + 1.0 = 5.4
        expected = 0.5 * 4.0 + 0.3 * 8.0 + 0.2 * 5.0
        self.assertEqual(player2_projection, round(expected, 2))
    
    def test_fallback_to_site_projections(self):
        """Test fallback to site projections for players with insufficient data"""
        projection_map = p.build_projection_map(self.sample_players)
        
        # Player 3 (no gameweek data) should use site projection
        self.assertEqual(projection_map[3], 7.0)
        
        # Player 4 (only 1 game) should use site projection
        self.assertEqual(projection_map[4], 11.0)
    
    def test_calculate_weighted_projection_direct(self):
        """Test the weighted calculation function directly"""
        # Test data: gws with 3 games
        gws_data = {"1": 10.0, "2": 15.0, "3": 5.0}
        stats = {"avgPoints": 12.0}
        
        result = p.calculate_weighted_projection(gws_data, stats)
        
        # last_game=5.0, avg_prev_2=(10.0+15.0)/2=12.5, season_avg=12.0
        # Expected: 0.5*5.0 + 0.3*12.5 + 0.2*12.0 = 2.5 + 3.75 + 2.4 = 8.65
        expected = 0.5 * 5.0 + 0.3 * 12.5 + 0.2 * 12.0
        self.assertAlmostEqual(result, expected, places=2)
    
    def test_gameweek_ordering(self):
        """Test that gameweeks are properly ordered chronologically"""
        # Test with non-sequential gameweek numbers
        gws_data = {"3": 20.0, "1": 10.0, "2": 15.0}
        stats = {"avgPoints": 12.0}
        
        result = p.calculate_weighted_projection(gws_data, stats)
        
        # Should be ordered as 1, 2, 3, so last_game=20.0, avg_prev_2=(10.0+15.0)/2=12.5
        expected = 0.5 * 20.0 + 0.3 * 12.5 + 0.2 * 12.0
        self.assertAlmostEqual(result, expected, places=2)
    
    def test_real_data_integration(self):
        """Test with real data if available"""
        try:
            # Try to load real players.json data
            current_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(current_dir)
            players_file = os.path.join(parent_dir, 'json_files', 'players.json')
            
            if os.path.exists(players_file):
                with open(players_file, 'r') as f:
                    real_players = json.load(f)
                
                # Should not crash with real data
                projection_map = p.build_projection_map(real_players)
                self.assertIsInstance(projection_map, dict)
                self.assertGreater(len(projection_map), 0)
                
                # All projections should be reasonable values (0-100 points)
                for projection in projection_map.values():
                    self.assertGreaterEqual(projection, 0)
                    self.assertLessEqual(projection, 100)
                    
        except FileNotFoundError:
            # Skip this test if real data is not available
            self.skipTest("Real players.json data not available")
    
    def test_get_player_gameweek_summary(self):
        """Test the debugging helper function"""
        player = self.sample_players[0]
        summary = p.get_player_gameweek_summary(player)
        
        self.assertEqual(summary['player_id'], 1)
        self.assertEqual(summary['name'], 'Test Player1')
        self.assertEqual(summary['gameweeks'], 3)
        self.assertEqual(summary['season_avg'], 10.0)
        self.assertEqual(summary['site_projection'], 8.5)


if __name__ == '__main__':
    # Create a small sample file for testing if it doesn't exist
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    sample_file = os.path.join(parent_dir, 'json_files', 'players_sample.json')
    
    if not os.path.exists(sample_file):
        sample_data = [
            {
                "id": 1,
                "firstName": "Sample",
                "lastName": "Player1",
                "stats": {
                    "avgPoints": 10.0,
                    "projectedScores": 8.5,
                    "points": {
                        "gws": {"1": 15.0, "2": 12.0, "3": 8.0}
                    }
                }
            },
            {
                "id": 2,
                "firstName": "Sample",
                "lastName": "Player2",
                "stats": {
                    "avgPoints": 5.0,
                    "projectedScores": 6.0,
                    "points": {
                        "gws": {"1": 8.0, "2": 4.0}
                    }
                }
            },
            {
                "id": 3,
                "firstName": "Sample",
                "lastName": "Player3",
                "stats": {
                    "avgPoints": 7.5,
                    "projectedScores": 7.0,
                    "points": []
                }
            }
        ]
        
        os.makedirs(os.path.dirname(sample_file), exist_ok=True)
        with open(sample_file, 'w') as f:
            json.dump(sample_data, f, indent=2)
        
        print(f"Created sample file: {sample_file}")
    
    unittest.main()