import os
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from tdcs_dance_svc.models.base import get_db
from tdcs_dance_svc.models.appointment import Appointment
from tdcs_dance_svc.notification import notify_instructor

router = APIRouter()


class AppointmentBookingRequest(BaseModel):
    user_id: int
    start_time: datetime
    end_time: datetime
    timezone: str


class AppointmentBookingResponse(BaseModel):
    appointment_id: int
    start_time: datetime
    end_time: datetime


@router.post("/book", response_model=AppointmentBookingResponse)

def book_appointment(request: AppointmentBookingRequest, db: Session = Depends(get_db)):
    try:
        # Convert provided times to UTC using the provided timezone
        try:
            local_tz = ZoneInfo(request.timezone)
        except Exception as e:
            logging.error(e, exc_info=True)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid timezone provided")

        start_time_utc = request.start_time.astimezone(ZoneInfo("UTC"))
        end_time_utc = request.end_time.astimezone(ZoneInfo("UTC"))
        now_utc = datetime.utcnow().replace(tzinfo=ZoneInfo("UTC"))

        if start_time_utc <= now_utc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Appointment must be set in the future")
        if end_time_utc <= start_time_utc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="End time must be after start time")

        # Check for time slot conflicts
        conflict = db.query(Appointment).filter(
            Appointment.start_time < end_time_utc,
            Appointment.end_time > start_time_utc
        ).first()
        if conflict:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Time slot conflict with an existing appointment")

        # Create new appointment
        new_appointment = Appointment(
            user_id=request.user_id,
            start_time=start_time_utc,
            end_time=end_time_utc,
            timezone=request.timezone
        )
        db.add(new_appointment)
        db.commit()
        db.refresh(new_appointment)

        try:
            notify_instructor(new_appointment)
        except Exception as e:
            logging.error(e, exc_info=True)

        appointment_response = AppointmentBookingResponse(
            appointment_id=new_appointment.id,
            start_time=new_appointment.start_time,
            end_time=new_appointment.end_time
        )

        # Optional calendar synchronization
        sync_flag = os.getenv("SYNC_CALENDAR", "False").lower() in ("true", "1", "yes")
        if sync_flag:
            try:
                payload = {
                    "appointment_id": new_appointment.id,
                    "user_id": new_appointment.user_id,
                    "start_time": new_appointment.start_time.isoformat(),
                    "end_time": new_appointment.end_time.isoformat()
                }
                response = requests.post("https://api.calendar-service.com/update", json=payload, timeout=5)
                if response.status_code != 200:
                    logging.error(f"Calendar sync failed with status {response.status_code}: {response.text}")
            except Exception as e:
                logging.error(e, exc_info=True)

        return appointment_response
    except HTTPException:
        raise
    except Exception as e:
        logging.error(e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")
