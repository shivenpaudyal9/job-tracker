"""
Simple API tests for Job Tracker backend
Run with: pytest test_api.py
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    """Test health endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_root():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_sync_health():
    """Test sync health endpoint"""
    response = client.get("/sync/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_sync_status():
    """Test sync status endpoint"""
    response = client.get("/sync/status")
    assert response.status_code == 200
    data = response.json()
    assert "is_connected" in data
    assert "is_running" in data


def test_connect_start():
    """Test device code flow start"""
    response = client.post("/sync/connect/start")
    assert response.status_code == 200
    data = response.json()
    assert "verification_uri" in data
    assert "user_code" in data
    assert "expires_in" in data
    assert data["verification_uri"] == "https://microsoft.com/devicelogin"


def test_list_applications():
    """Test listing applications"""
    response = client.get("/applications")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "data" in data
    assert isinstance(data["data"], list)


def test_list_applications_with_filters():
    """Test listing applications with filters"""
    response = client.get("/applications?search=Google&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert data["limit"] == 10


def test_get_stats():
    """Test dashboard stats"""
    response = client.get("/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_applications" in data
    assert "pending_actions" in data
    assert "pending_manual_review" in data
    assert "by_status" in data


def test_list_manual_reviews():
    """Test listing manual reviews"""
    response = client.get("/manual-reviews")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "data" in data


def test_get_nonexistent_application():
    """Test getting non-existent application returns 404"""
    response = client.get("/applications/99999")
    assert response.status_code == 404


def test_create_application():
    """Test creating a new application"""
    app_data = {
        "company_name": "Test Company",
        "job_title": "Test Engineer",
        "location": "Remote"
    }
    response = client.post("/applications", json=app_data)
    assert response.status_code == 201
    data = response.json()
    assert data["company_name"] == "Test Company"
    assert "id" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
