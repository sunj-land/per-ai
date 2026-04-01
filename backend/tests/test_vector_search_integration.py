import unittest
import requests
import json
import time

BASE_URL = "http://localhost:8000/api/v1/vector"

class TestVectorSearchIntegration(unittest.TestCase):
    
    def test_search_basic(self):
        """Test basic search functionality with default limit"""
        response = requests.get(f"{BASE_URL}/search", params={"q": "AI"})
        self.assertEqual(response.status_code, 200, f"Failed: {response.text}")
        results = response.json()
        self.assertIsInstance(results, list)
        if len(results) > 0:
            item = results[0]
            self.assertIn("id", item)
            self.assertIn("score", item)
            self.assertIn("metadata", item)
            self.assertIn("content", item)
            
    def test_search_limit_control(self):
        """Test limit parameter works correctly"""
        # Test limit=1
        response = requests.get(f"{BASE_URL}/search", params={"q": "technology", "limit": 1})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.json()) <= 1)
        
        # Test limit=10
        response = requests.get(f"{BASE_URL}/search", params={"q": "technology", "limit": 10})
        self.assertEqual(response.status_code, 200)
        # Note: If there are fewer than 10 documents, it returns all of them. 
        # So we can only assert len <= 10.
        self.assertTrue(len(response.json()) <= 10)

    def test_search_validation_error(self):
        """Test validation for invalid limit parameters"""
        # Limit too low
        response = requests.get(f"{BASE_URL}/search", params={"q": "test", "limit": 0})
        self.assertEqual(response.status_code, 422)
        
        # Limit too high
        response = requests.get(f"{BASE_URL}/search", params={"q": "test", "limit": 100})
        self.assertEqual(response.status_code, 422)
        
        # Missing query
        response = requests.get(f"{BASE_URL}/search")
        self.assertEqual(response.status_code, 422)
        
    def test_search_performance(self):
        """Simple performance check (response time < 2s)"""
        start_time = time.time()
        requests.get(f"{BASE_URL}/search", params={"q": "performance test", "limit": 50})
        duration = time.time() - start_time
        print(f"Search duration (50 items): {duration:.4f}s")
        self.assertTrue(duration < 2.0, "Search took too long (>2s)")

if __name__ == "__main__":
    unittest.main()
