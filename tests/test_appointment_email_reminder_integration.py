import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from fastapi import status


def get_future_time(minutes=10):
    # Return a timezone-aware datetime in UTC
    return datetime.now(ZoneInfo("UTC")) + timedelta(minutes=minutes)


def test_email_reminder_failure(monkeypatch, client, caplog):
    caplog.set_level(logging.ERROR)
    
    # Monkey-patch schedule_email_reminder in the appointment router to simulate a failure
    def fake_schedule_email(appointment):
        raise Exception("Simulated email scheduling failure")
    monkeypatch.setattr("tdcs_dance_svc.routers.appointment.schedule_email_reminder", fake_schedule_email)
    
    future_start = get_future_time(20)
    future_end = future_start + timedelta(hours=1)
    payload = {
        "user_id": 10,
        "start_time": future_start.isoformat(),
        "end_time": future_end.isoformat(),
        "timezone": "UTC"
    }
    response = client.post("/appointments/book", json=payload)
    
    # Booking should still return successfully
    assert response.status_code == 200
    
    # Check that the error from scheduling is logged
    assert any("Simulated email scheduling failure" in record.message for record in caplog.records)
