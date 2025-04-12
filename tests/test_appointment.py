import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from fastapi import status


def get_future_time(minutes=10):
    return datetime.utcnow() + timedelta(minutes=minutes)


def test_valid_booking(client, db_session):
    # Arrange
    future_start = get_future_time(20)
    future_end = future_start + timedelta(hours=1)
    payload = {
        "user_id": 1,
        "start_time": future_start.isoformat(),
        "end_time": future_end.isoformat(),
        "timezone": "UTC"
    }
    
    # Act
    response = client.post("/appointments/book", json=payload)
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "appointment_id" in data
    assert data["start_time"] == payload["start_time"]
    assert data["end_time"] == payload["end_time"]


def test_conflict_booking(client, db_session):
    future_start = get_future_time(30)
    future_end = future_start + timedelta(hours=1)
    payload = {
        "user_id": 1,
        "start_time": future_start.isoformat(),
        "end_time": future_end.isoformat(),
        "timezone": "UTC"
    }
    
    # First booking should succeed
    response1 = client.post("/appointments/book", json=payload)
    assert response1.status_code == 200
    
    # Overlapping booking should yield conflict error
    overlapping_payload = {
        "user_id": 2,
        "start_time": (future_start + timedelta(minutes=30)).isoformat(),
        "end_time": (future_end + timedelta(minutes=30)).isoformat(),
        "timezone": "UTC"
    }
    response2 = client.post("/appointments/book", json=overlapping_payload)
    assert response2.status_code == status.HTTP_409_CONFLICT


def test_invalid_booking(client):
    # Missing required field (user_id)
    payload = {
        "start_time": get_future_time(20).isoformat(),
        "end_time": (get_future_time(80)).isoformat(),
        "timezone": "UTC"
    }
    response = client.post("/appointments/book", json=payload)
    # Expecting validation error from FastAPI
    assert response.status_code == 422


def test_calendar_sync_success(monkeypatch, client):
    # Enable calendar sync
    os.environ["SYNC_CALENDAR"] = "True"

    # Monkey patch requests.post to simulate a successful sync
    def fake_post(url, json, timeout):
        class FakeResponse:
            status_code = 200
            text = "OK"
        return FakeResponse()
    
    monkeypatch.setattr("tdcs_dance_svc.routers.appointment.requests.post", fake_post)

    future_start = get_future_time(40)
    future_end = future_start + timedelta(hours=1)
    payload = {
        "user_id": 3,
        "start_time": future_start.isoformat(),
        "end_time": future_end.isoformat(),
        "timezone": "UTC"
    }
    response = client.post("/appointments/book", json=payload)
    assert response.status_code == 200
    
    # Clean up
    del os.environ["SYNC_CALENDAR"]


def test_calendar_sync_failure(monkeypatch, client):
    # Enable calendar sync
    os.environ["SYNC_CALENDAR"] = "True"
    
    # Monkey patch requests.post to simulate a failure in calendar sync
    def fake_post(url, json, timeout):
        class FakeResponse:
            status_code = 500
            text = "Internal Error"
        return FakeResponse()
    
    monkeypatch.setattr("tdcs_dance_svc.routers.appointment.requests.post", fake_post)

    future_start = get_future_time(50)
    future_end = future_start + timedelta(hours=1)
    payload = {
        "user_id": 4,
        "start_time": future_start.isoformat(),
        "end_time": future_end.isoformat(),
        "timezone": "UTC"
    }
    response = client.post("/appointments/book", json=payload)
    # Even if calendar sync fails, booking should succeed
    assert response.status_code == 200
    
    # Clean up
    del os.environ["SYNC_CALENDAR"]
