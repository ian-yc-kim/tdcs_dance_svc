import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from fastapi import status


def get_future_time(minutes=10):
    return datetime.utcnow() + timedelta(minutes=minutes)


def test_notify_instructor_called(client, monkeypatch):
    # Flag to record whether notify_instructor was called
    called_flag = {"called": False}

    def fake_notify_instructor(appointment):
        called_flag["called"] = True

    # Patch notify_instructor in the appointment router instead of the notification module
    monkeypatch.setattr("tdcs_dance_svc.routers.appointment.notify_instructor", fake_notify_instructor)

    # Prepare a valid appointment booking payload
    future_start = get_future_time(20)
    future_end = future_start + timedelta(hours=1)
    payload = {
        "user_id": 1,
        "start_time": future_start.isoformat(),
        "end_time": future_end.isoformat(),
        "timezone": "UTC"
    }

    response = client.post("/appointments/book", json=payload)
    assert response.status_code == 200
    assert called_flag["called"] is True


def test_notify_instructor_exception_handling(client, monkeypatch, caplog):
    # Simulate notify_instructor throwing an exception
    def fake_notify_instructor(appointment):
        raise Exception("Notification Error")

    monkeypatch.setattr("tdcs_dance_svc.routers.appointment.notify_instructor", fake_notify_instructor)

    # Prepare a valid appointment booking payload
    future_start = get_future_time(30)
    future_end = future_start + timedelta(hours=1)
    payload = {
        "user_id": 2,
        "start_time": future_start.isoformat(),
        "end_time": future_end.isoformat(),
        "timezone": "UTC"
    }

    response = client.post("/appointments/book", json=payload)
    # Booking should still succeed despite notification failure
    assert response.status_code == 200
    # Check that the exception message was logged
    assert "Notification Error" in caplog.text
