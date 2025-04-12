import os
import secrets
import logging
import requests
from urllib.parse import urlencode

from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import RedirectResponse

router = APIRouter()

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
SCOPE = "openid email profile"


@router.get("/login")

def login() -> RedirectResponse:
    try:
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
        if not client_id or not redirect_uri:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail="Missing Google OAuth configuration")
        state = secrets.token_urlsafe(16)
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": SCOPE,
            "state": state
        }
        url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
        logging.info("Initiating Google OAuth flow")
        # Create RedirectResponse and set secure HTTP-only cookie on it
        resp = RedirectResponse(url=url)
        resp.set_cookie(key="oauth_state", value=state, httponly=True, secure=True)
        return resp
    except Exception as e:
        logging.error(e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Internal server error")


@router.get("/callback")

def callback(request: Request) -> dict:
    try:
        query_params = request.query_params
        state_query = query_params.get("state")
        code = query_params.get("code")

        if not state_query:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Missing state parameter")
        if not code:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Missing code parameter")

        state_cookie = request.cookies.get("oauth_state")
        if not state_cookie or state_cookie != state_query:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Invalid state parameter")

        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
        if not client_id or not client_secret or not redirect_uri:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail="Missing Google OAuth configuration")

        token_data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code"
        }

        token_response = None
        # Attempt token exchange with at most one retry for transient failures
        for attempt in range(2):
            try:
                token_response = requests.post(GOOGLE_TOKEN_URL, data=token_data, timeout=5)
                if token_response.status_code == 200:
                    break
            except Exception as e:
                logging.error(e, exc_info=True)
                if attempt == 1:
                    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                        detail="Token exchange failed")
        if not token_response or token_response.status_code != 200:
            logging.error(f"Token exchange failed: {token_response.text if token_response else 'no response'}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Failed to exchange token")

        token_json = token_response.json()
        access_token = token_json.get("access_token")
        if not access_token:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="No access token received")

        # Use the access token to fetch user profile information
        headers = {"Authorization": f"Bearer {access_token}"}
        userinfo_response = requests.get(GOOGLE_USERINFO_URL, headers=headers, timeout=5)
        if userinfo_response.status_code != 200:
            logging.error(f"Failed to fetch user info: {userinfo_response.text}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Failed to fetch user info")

        user_info = userinfo_response.json()
        logging.info("Google OAuth callback successful, user authenticated")

        # Map the Google user information to the internal user system and establish a session
        # (Simulation: In production, integrate with your user management system here.)
        return {"message": "Authentication successful", "user": user_info}

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logging.error(e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Internal server error")
