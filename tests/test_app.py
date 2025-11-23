"""
Tests for the Mergington High School API

Tests cover:
- Root endpoint redirection
- Getting activities list
- Signing up for activities
- Error handling for invalid inputs
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add src directory to path so we can import the app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI application"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities data before each test to ensure test isolation"""
    # Store original state
    original_activities = {
        name: {
            "description": details["description"],
            "schedule": details["schedule"],
            "max_participants": details["max_participants"],
            "participants": details["participants"].copy()
        }
        for name, details in activities.items()
    }
    
    yield
    
    # Restore original state after test
    activities.clear()
    activities.update(original_activities)


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_static_html(self, client):
        """Test that root endpoint redirects to static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for getting the activities list"""
    
    def test_get_activities_returns_200(self, client):
        """Test that GET /activities returns 200 OK"""
        response = client.get("/activities")
        assert response.status_code == 200
    
    def test_get_activities_returns_dict(self, client):
        """Test that activities endpoint returns a dictionary"""
        response = client.get("/activities")
        data = response.json()
        assert isinstance(data, dict)
    
    def test_get_activities_has_correct_structure(self, client):
        """Test that each activity has the required fields"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_details in data.items():
            assert "description" in activity_details
            assert "schedule" in activity_details
            assert "max_participants" in activity_details
            assert "participants" in activity_details
            assert isinstance(activity_details["participants"], list)
    
    def test_get_activities_includes_expected_activities(self, client):
        """Test that response includes some expected activities"""
        response = client.get("/activities")
        data = response.json()
        
        expected_activities = ["Chess Club", "Programming Class", "Soccer Team"]
        for activity in expected_activities:
            assert activity in data


class TestSignupForActivity:
    """Tests for signing up for activities"""
    
    def test_signup_for_valid_activity(self, client):
        """Test successful signup for an existing activity"""
        response = client.post(
            "/activities/Chess%20Club/signup?email=test@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "test@mergington.edu" in data["message"]
        assert "Chess Club" in data["message"]
    
    def test_signup_adds_participant_to_activity(self, client):
        """Test that signup actually adds the participant to the activity"""
        email = "newstudent@mergington.edu"
        activity_name = "Programming Class"
        
        # Get initial participant count
        initial_response = client.get("/activities")
        initial_participants = initial_response.json()[activity_name]["participants"]
        initial_count = len(initial_participants)
        
        # Sign up
        client.post(f"/activities/{activity_name}/signup?email={email}")
        
        # Check participant was added
        updated_response = client.get("/activities")
        updated_participants = updated_response.json()[activity_name]["participants"]
        
        assert len(updated_participants) == initial_count + 1
        assert email in updated_participants
    
    def test_signup_for_nonexistent_activity(self, client):
        """Test that signing up for a non-existent activity returns 404"""
        response = client.post(
            "/activities/Nonexistent%20Activity/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
    
    def test_duplicate_signup_returns_400(self, client):
        """Test that signing up twice for the same activity returns 400"""
        email = "duplicate@mergington.edu"
        activity_name = "Drama Club"
        
        # First signup should succeed
        response1 = client.post(f"/activities/{activity_name}/signup?email={email}")
        assert response1.status_code == 200
        
        # Second signup should fail
        response2 = client.post(f"/activities/{activity_name}/signup?email={email}")
        assert response2.status_code == 400
        data = response2.json()
        assert "detail" in data
        assert "already signed up" in data["detail"].lower()
    
    def test_signup_with_special_characters_in_activity_name(self, client):
        """Test that activity names with spaces are properly handled"""
        response = client.post(
            "/activities/Track%20and%20Field/signup?email=athlete@mergington.edu"
        )
        assert response.status_code == 200
    
    def test_signup_with_special_characters_in_email(self, client):
        """Test that emails with special characters are properly handled"""
        response = client.post(
            "/activities/Science%20Club/signup?email=test%2Buser@mergington.edu"
        )
        assert response.status_code == 200


class TestActivityCapacity:
    """Tests related to activity participant limits"""
    
    def test_activities_have_max_participants(self, client):
        """Test that all activities have a max_participants field"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_details in data.items():
            assert "max_participants" in activity_details
            assert isinstance(activity_details["max_participants"], int)
            assert activity_details["max_participants"] > 0


class TestDataIntegrity:
    """Tests for data integrity and validation"""
    
    def test_participant_emails_are_strings(self, client):
        """Test that all participant emails are strings"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_details in data.items():
            for participant in activity_details["participants"]:
                assert isinstance(participant, str)
    
    def test_multiple_signups_for_different_activities(self, client):
        """Test that a student can sign up for multiple different activities"""
        email = "multisport@mergington.edu"
        
        response1 = client.post(f"/activities/Soccer%20Team/signup?email={email}")
        assert response1.status_code == 200
        
        response2 = client.post(f"/activities/Chess%20Club/signup?email={email}")
        assert response2.status_code == 200
        
        # Verify the student is in both activities
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        
        assert email in activities_data["Soccer Team"]["participants"]
        assert email in activities_data["Chess Club"]["participants"]
