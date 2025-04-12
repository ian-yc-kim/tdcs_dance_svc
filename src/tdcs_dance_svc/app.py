from fastapi import FastAPI
from tdcs_dance_svc.routers.appointment import router as appointment_router

app = FastAPI(debug=True)

# Include appointment booking router
app.include_router(appointment_router, prefix="/appointments")
