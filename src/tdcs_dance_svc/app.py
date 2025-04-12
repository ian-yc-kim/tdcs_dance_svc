from fastapi import FastAPI
from tdcs_dance_svc.routers.appointment import router as appointment_router
from tdcs_dance_svc.routers import google_auth

app = FastAPI(debug=True)

# Include appointment booking router
app.include_router(appointment_router, prefix="/appointments")

# Include Google OAuth router
app.include_router(google_auth.router, prefix="/auth/google")
