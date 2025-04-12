import os
import logging
import datetime
import requests
import pytest

from tdcs_dance_svc.notification import notify_instructor


class FakeAppointment:
    def __init__(self, id, start_time, end_time, user_id):
        self.id = id
        self.start_time = start_time
        self.end_time = end_time
        self.user_id = user_id


def test_notify_without_url(monkeypatch, caplog):
    # Ensure INSTRUCTOR_NOTIFICATION_URL is not set
    monkeypatch.delenv("INSTRUCTOR_NOTIFICATION_URL", raising=False)
    # Set logging level to INFO to capture the log message
    caplog.set_level(logging.INFO)
    appointment = FakeAppointment(
        1,
        datetime.datetime(2023, 10, 1, 10, 0),
        datetime.datetime(2023, 10, 1, 11, 0),
        100
    )
    notify_instructor(appointment)
    # Verify that a log message with the notification text was emitted
    assert "New appointment booked: ID 1 starting at" in caplog.text


def test_notify_with_success(monkeypatch):
    # Set the notification URL
    test_url = "http://fake-notification.test/notify"
    monkeypatch.setenv("INSTRUCTOR_NOTIFICATION_URL", test_url)
    
    # Define a fake post function that simulates a successful response
    class FakeResponse:
        status_code = 200
        text = "OK"

    def fake_post(url, json, headers, timeout):
        return FakeResponse()

    monkeypatch.setattr(requests, "post", fake_post)
    
    appointment = FakeAppointment(
        2,
        datetime.datetime(2023, 10, 2, 12, 0),
        datetime.datetime(2023, 10, 2, 13, 0),
        200
    )
    # The function should complete without raising an exception
    notify_instructor(appointment)


def test_notify_with_failure(monkeypatch, caplog):
    # Set the notification URL
    test_url = "http://fake-notification.test/notify"
    monkeypatch.setenv("INSTRUCTOR_NOTIFICATION_URL", test_url)
    
    # Simulate a response with a non-200 status code
    class FakeResponse:
        status_code = 500
        text = "Internal Server Error"

    def fake_post(url, json, headers, timeout):
        return FakeResponse()

    monkeypatch.setattr(requests, "post", fake_post)
    
    appointment = FakeAppointment(
        3,
        datetime.datetime(2023, 10, 3, 14, 0),
        datetime.datetime(2023, 10, 3, 15, 0),
        300
    )
    notify_instructor(appointment)
    # Check that an error message was logged
    assert "Notification failed with status 500" in caplog.text


def test_notify_with_exception(monkeypatch, caplog):
    # Set the notification URL
    test_url = "http://fake-notification.test/notify"
    monkeypatch.setenv("INSTRUCTOR_NOTIFICATION_URL", test_url)
    
    # Simulate an exception during the POST request
    def fake_post(url, json, headers, timeout):
        raise Exception("Test exception")

    monkeypatch.setattr(requests, "post", fake_post)
    
    appointment = FakeAppointment(
        4,
        datetime.datetime(2023, 10, 4, 16, 0),
        datetime.datetime(2023, 10, 4, 17, 0),
        400
    )
    notify_instructor(appointment)
    # Verify that the exception message was logged
    assert "Test exception" in caplog.text
