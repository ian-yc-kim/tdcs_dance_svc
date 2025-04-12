import os
import logging
import requests
from typing import Any


def notify_instructor(appointment: Any) -> None:
    """Send a notification to the instructor about a new appointment.

    If the environment variable INSTRUCTOR_NOTIFICATION_URL is set, a POST request will be sent.
    Otherwise, the notification message is logged using logging.info.
    """
    message = f"New appointment booked: ID {appointment.id} starting at {appointment.start_time}"
    notification_url = os.getenv("INSTRUCTOR_NOTIFICATION_URL")

    if not notification_url:
        logging.info(message)
        return

    payload = {
        "appointment_id": appointment.id,
        "start_time": appointment.start_time.isoformat(),
        "end_time": appointment.end_time.isoformat(),
        "user_id": appointment.user_id
    }

    headers = {}
    api_key = os.getenv("INSTRUCTOR_NOTIFICATION_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        response = requests.post(notification_url, json=payload, headers=headers, timeout=5)
        if response.status_code != 200:
            logging.error(f"Notification failed with status {response.status_code}: {response.text}")
    except Exception as e:
        logging.error(e, exc_info=True)
