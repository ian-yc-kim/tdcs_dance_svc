import os
import json
import logging
import requests
from fastapi import status
from fastapi.testclient import TestClient

import pytest

# We'll use monkeypatch to simulate external calls

# Test /login endpoint

def test_login_redirect(client, monkeypatch):
    # Set environment variables for Google OAuth configuration
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test_client_id")
    monkeypatch.setenv("GOOGLE_REDIRECT_URI", "http://testserver/auth/google/callback")

    # Use follow_redirects=False to capture the initial redirection response
    response = client.get("/auth/google/login", follow_redirects=False)
    # Check for redirection status code (307 Temporary Redirect or 302 Found)
    assert response.status_code in (307, 302)
    # Verify that the oauth_state cookie is set
    cookies = response.cookies
    assert "oauth_state" in cookies
    # Verify that the location header contains the Google OAuth URL
    location = response.headers.get("location")
    assert location is not None
    assert "https://accounts.google.com/o/oauth2/v2/auth" in location


# Test /callback success scenario

def test_callback_success(client, monkeypatch):
    # First, simulate setting the oauth_state cookie via /login
    state_token = "test_state_token"
    # Prepare fake token exchange response
    def fake_post(url, data, timeout):
        class FakeResponse:
            status_code = 200
            def json(self):
                return {"access_token": "fake_access_token"}
        return FakeResponse()
    monkeypatch.setattr(requests, "post", fake_post)

    # Prepare fake user info response
    def fake_get(url, headers, timeout):
        class FakeResponse:
            status_code = 200
            def json(self):
                return {"id": "123", "email": "user@example.com", "name": "Test User"}
        return FakeResponse()
    monkeypatch.setattr(requests, "get", fake_get)

    # Set environment variables for Google OAuth configuration
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test_client_id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test_client_secret")
    monkeypatch.setenv("GOOGLE_REDIRECT_URI", "http://testserver/auth/google/callback")

    # Simulate a callback request with matching state and code
    callback_url = "/auth/google/callback?state=test_state_token&code=test_code"
    # Set the oauth_state cookie in the request
    response = client.get(callback_url, cookies={"oauth_state": state_token})
    assert response.status_code == 200
    data = response.json()
    assert data.get("message") == "Authentication successful"
    assert "user" in data
    user = data.get("user")
    assert user.get("email") == "user@example.com"


# Test /callback with invalid state

def test_callback_invalid_state(client):
    # State in cookie does not match query parameter
    callback_url = "/auth/google/callback?state=invalid_state&code=test_code"
    response = client.get(callback_url, cookies={"oauth_state": "different_state"})
    assert response.status_code == 400
    data = response.json()
    assert "Invalid state parameter" in data.get("detail")


# Test /callback with missing code parameter

def test_callback_missing_code(client):
    callback_url = "/auth/google/callback?state=test_state_token"
    response = client.get(callback_url, cookies={"oauth_state": "test_state_token"})
    assert response.status_code == 400
    data = response.json()
    assert "Missing code parameter" in data.get("detail")


# Test token exchange failure

def test_token_exchange_failure(client, monkeypatch):
    # Simulate token exchange failure by making fake_post return non-200 status
    def fake_post_failure(url, data, timeout):
        class FakeResponse:
            status_code = 400
            text = "Bad Request"
            def json(self):
                return {}
        return FakeResponse()
    monkeypatch.setattr(requests, "post", fake_post_failure)

    # Set environment variables for Google OAuth configuration
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test_client_id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test_client_secret")
    monkeypatch.setenv("GOOGLE_REDIRECT_URI", "http://testserver/auth/google/callback")

    callback_url = "/auth/google/callback?state=test_state_token&code=test_code"
    response = client.get(callback_url, cookies={"oauth_state": "test_state_token"})
    assert response.status_code == 400
    data = response.json()
    assert "Failed to exchange token" in data.get("detail")
