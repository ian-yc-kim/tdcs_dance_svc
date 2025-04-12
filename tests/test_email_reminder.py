import logging
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pytest

from tdcs_dance_svc import email_reminder


class DummyAppointment:
    def __init__(self, id=None, start_time=None):
        self.id = id
        self.start_time = start_time


# Test case for a valid appointment that should schedule the email reminder

def test_schedule_email_reminder_valid(monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    
    # Prepare a dummy appointment with valid id and timezone-aware start_time
    future_time = datetime.now(ZoneInfo("UTC")) + timedelta(hours=1)
    appointment = DummyAppointment(id=123, start_time=future_time)

    # Create a flag to check if schedule_email was called
    call_info = {"called": False}

    def fake_schedule_email(content, scheduled_time):
        call_info["called"] = True
        # Assert that scheduled_time is 30 minutes before the appointment start time
        expected_time = appointment.start_time - timedelta(minutes=30)
        assert scheduled_time == expected_time
        return True

    monkeypatch.setattr(email_reminder, "schedule_email", fake_schedule_email)

    email_reminder.schedule_email_reminder(appointment)
    assert call_info["called"] == True
    assert any("Email reminder scheduled successfully" in record.message for record in caplog.records)


# Test case for invalid appointment missing required fields

def test_schedule_email_reminder_invalid(monkeypatch, caplog):
    caplog.set_level(logging.ERROR)
    
    # Appointment missing start_time
    appointment = DummyAppointment(id=456, start_time=None)
    email_reminder.schedule_email_reminder(appointment)
    assert any("missing required fields" in record.message.lower() for record in caplog.records) or \
           any("must be a timezone-aware" in record.message for record in caplog.records)

    # Appointment missing id
    future_time = datetime.now(ZoneInfo("UTC")) + timedelta(hours=1)
    appointment = DummyAppointment(id=None, start_time=future_time)
    email_reminder.schedule_email_reminder(appointment)
    assert any("missing required fields" in record.message.lower() for record in caplog.records)


# Test case for email scheduling failure triggering retry mechanism

def test_schedule_email_reminder_failure(monkeypatch, caplog):
    caplog.set_level(logging.ERROR)
    
    future_time = datetime.now(ZoneInfo("UTC")) + timedelta(hours=1)
    appointment = DummyAppointment(id=789, start_time=future_time)
    
    # Create a counter to track the number of attempts
    attempts = {"count": 0}

    def failing_schedule_email(content, scheduled_time):
        attempts["count"] += 1
        raise Exception("Simulated scheduling failure")

    monkeypatch.setattr(email_reminder, "schedule_email", failing_schedule_email)

    # To speed up the test, monkeypatch time.sleep to avoid real sleeping
    monkeypatch.setattr(time, "sleep", lambda x: None)

    email_reminder.schedule_email_reminder(appointment)
    # Total attempts should be 3 (initial attempt + 2 retries)
    assert attempts["count"] == 3
    assert any("Max retries reached" in record.message for record in caplog.records)
