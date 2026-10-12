"""Client for communicating with MyWhoosh services."""

import logging
import os
import tempfile
import uuid
from typing import Any, Dict, List, Optional
try:
    import requests
    RequestException = requests.RequestException
except ImportError:
    requests = None  # type: ignore

    class RequestException(Exception):  # type: ignore
        pass

logger = logging.getLogger(__name__)


class MyWhooshClient:
    """Handles authentication and activity downloading from MyWhoosh."""

    LOGIN_URL = "https://services.mywhoosh.com/http-service/api/login"
    ACTIVITIES_URL = "https://service14.mywhoosh.com/v2/rider/profile/activities"
    DOWNLOAD_URL = "https://service14.mywhoosh.com/v2/rider/profile/download-activity-file"

    def __init__(self, email: str, password: str, device_id: Optional[str] = None):
        self.email = email
        self.password = password
        self.device_id = device_id or str(uuid.uuid4())
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.whoosh_id: Optional[str] = None

    def login(self) -> bool:
        """Authenticate with MyWhoosh and obtain access tokens."""
        logger.info("Logging into MyWhoosh as %s...", self.email)
        payload = {
            "Username": self.email,
            "Password": self.password,
            "Platform": "Android",
            "Action": 1001,
            "CorrelationId": str(uuid.uuid4()),
            "DeviceId": self.device_id,
            "Authorization": "",
        }

        try:
            response = requests.post(self.LOGIN_URL, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()

            if not data.get("Success"):
                msg = data.get("Message", "Unknown login failure")
                logger.error("MyWhoosh login failed: %s", msg)
                raise RuntimeError(f"MyWhoosh authentication failed: {msg}")

            self.access_token = data.get("AccessToken")
            self.refresh_token = data.get("RefreshToken")
            self.whoosh_id = data.get("WhooshId")

            logger.info("Successfully authenticated with MyWhoosh (WhooshId: %s)", self.whoosh_id)
            return True

        except RequestException as exc:
            logger.exception("Network error during MyWhoosh authentication: %s", exc)
            raise RuntimeError(f"Network error during MyWhoosh login: {exc}") from exc

    def ensure_authenticated(self) -> None:
        """Ensure an active access token is present."""
        if not self.access_token or not self.whoosh_id:
            self.login()

    def get_activities(self, limit: int = 10, page: int = 1) -> List[Dict[str, Any]]:
        """Fetch list of user activities from MyWhoosh.

        Returns:
            List of standardized activity dictionaries.
        """
        self.ensure_authenticated()

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Myswoosh2Garmin/1.0",
        }

        payloads = [
            {"page": page, "limit": limit, "sortDate": "DESC"},
            {"page": page, "limit": limit, "sortDate": "ASC"},
        ]

        last_error = None
        for attempt, payload in enumerate(payloads, 1):
            try:
                logger.debug("Requesting activities attempt %d with payload %s", attempt, payload)
                response = requests.post(self.ACTIVITIES_URL, headers=headers, json=payload, timeout=30)

                if response.status_code == 401:
                    logger.warning("MyWhoosh token expired. Re-authenticating...")
                    self.login()
                    headers["Authorization"] = f"Bearer {self.access_token}"
                    continue

                if response.status_code == 200:
                    data = response.json()
                    raw_items = self._extract_activity_items(data)
                    logger.info("Found %d activities on MyWhoosh", len(raw_items))
                    normalized = [self._normalize_activity(item) for item in raw_items]
                    try:
                        from datetime import datetime, timezone
                        from src.garmin_client import parse_activity_datetime
                        normalized.sort(
                            key=lambda a: parse_activity_datetime(a.get("date")) or datetime.min.replace(tzinfo=timezone.utc),
                            reverse=True,
                        )
                    except Exception as sort_exc:
                        logger.debug("Activity sort by date failed: %s", sort_exc)

                    if limit and limit > 0:
                        normalized = normalized[:limit]
                    return normalized

                last_error = f"HTTP {response.status_code}: {response.text}"
                logger.warning("Activities fetch attempt failed: %s", last_error)

            except RequestException as exc:
                last_error = str(exc)
                logger.warning("Network error fetching activities: %s", exc)

        raise RuntimeError(f"Failed to fetch MyWhoosh activities: {last_error}")

    def _extract_activity_items(self, data: Any) -> List[Dict[str, Any]]:
        """Extract activities array from response JSON supporting multiple schema versions."""
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            if "data" in data:
                inner = data["data"]
                if isinstance(inner, dict):
                    return inner.get("results") or inner.get("activities") or []
                if isinstance(inner, list):
                    return inner
            for key in ("activities", "results", "rides", "rideHistory"):
                if key in data and isinstance(data[key], list):
                    return data[key]
        return []

    def _normalize_activity(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Convert varying API activity properties into consistent dictionary fields."""
        activity_id = str(item.get("id") or item.get("_id") or item.get("activityId") or "")
        file_id = str(item.get("activityFileId") or item.get("fileId") or "")
        name = item.get("name") or item.get("title") or "MyWhoosh Ride"
        date_val = (
            item.get("date")
            or item.get("startTime")
            or item.get("createdAt")
            or item.get("timestamp")
        )

        return {
            "id": activity_id,
            "activity_file_id": file_id,
            "name": name,
            "date": str(date_val) if date_val else None,
            "distance_m": item.get("distance") or item.get("totalDistanceMeters"),
            "duration_s": item.get("duration") or item.get("movingTime") or item.get("elapsedTime"),
            "calories": item.get("calories") or item.get("totalCaloriesBurn"),
            "elevation_gain_m": item.get("elevation") or item.get("totalElevation"),
            "raw": item,
        }

    def download_activity_fit(self, activity: Dict[str, Any], output_dir: Optional[str] = None) -> str:
        """Request pre-signed S3 URL and download the raw activity .fit file.

        Args:
            activity: Normalized activity dictionary.
            output_dir: Optional directory to store the downloaded file.

        Returns:
            Absolute file path to the downloaded .fit file.
        """
        self.ensure_authenticated()

        activity_id = activity["id"]
        file_id = activity["activity_file_id"]

        if not file_id:
            raise ValueError(f"Activity {activity_id} has no valid activity_file_id")

        logger.info("Requesting S3 download URL for activity %s (fileId: %s)...", activity_id, file_id)

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "User-Agent": "Myswoosh2Garmin/1.0",
        }
        payload = {
            "key": self.whoosh_id,
            "fileId": file_id,
        }

        try:
            resp = requests.post(self.DOWNLOAD_URL, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            if data.get("error"):
                raise RuntimeError(f"MyWhoosh API returned error: {data.get('message')}")

            download_url = data.get("data")
            if not isinstance(download_url, str) or not download_url.startswith("http"):
                raise RuntimeError(f"Invalid download URL in MyWhoosh response: {data}")

        except RequestException as exc:
            raise RuntimeError(f"Failed to obtain S3 download URL: {exc}") from exc

        # Download binary content
        logger.info("Downloading .fit binary from S3...")
        try:
            s3_resp = requests.get(download_url, timeout=90)
            s3_resp.raise_for_status()
            content = s3_resp.content

            target_dir = output_dir or tempfile.gettempdir()
            os.makedirs(target_dir, exist_ok=True)
            out_path = os.path.join(target_dir, f"mywhoosh_{activity_id}.fit")

            with open(out_path, "wb") as f:
                f.write(content)

            # Validate FIT header magic bytes
            with open(out_path, "rb") as f:
                header = f.read(14)
                if len(header) >= 12 and header[8:12] == b".FIT":
                    logger.info("Downloaded valid FIT file (%d bytes) to %s", len(content), out_path)
                else:
                    logger.warning(
                        "File downloaded (%d bytes) but missing standard .FIT header magic bytes.",
                        len(content),
                    )

            return out_path

        except RequestException as exc:
            raise RuntimeError(f"Failed downloading FIT file from S3: {exc}") from exc
