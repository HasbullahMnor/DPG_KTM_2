import os
import sys
import time
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

import requests
from google.transit import gtfs_realtime_pb2
from google.protobuf.json_format import MessageToDict
import pytz


# -------- Config --------
MYT_TZ = pytz.timezone("Asia/Kuala_Lumpur")
GTFSR_URL = "https://api.data.gov.my/gtfs-realtime/vehicle-position/ktmb"
DASHBOARD_TITLE = "KTM Train Status Live Update"
CONTENT_MARKER = "<!-- DASHBOARD:KTM -->"

# Taskade API - using correct endpoints from Colab learnings
TASKADE_BASE_URL = "https://www.taskade.com/api/v1"
TASKADE_API_TOKEN = os.getenv("TASKADE_API_TOKEN", "")
TASKADE_PROJECT_ID = os.getenv("TASKADE_PROJECT_ID", "")
TASKADE_TASK_ID = os.getenv("TASKADE_TASK_ID", "")

HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "20"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RETRY_BACKOFF = float(os.getenv("RETRY_BACKOFF", "1.5"))

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("ktm_taskade")


# -------- Utilities --------
def now_myt() -> datetime:
    return datetime.now(MYT_TZ)


def ts_fmt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S %Z")


def kmh(speed_mps: Optional[float]) -> Optional[float]:
    if speed_mps is None:
        return None
    return round(speed_mps * 3.6, 1)


def http_request(
    method: str,
    url: str,
    headers: Dict[str, str],
    json_body: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
) -> requests.Response:
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=json_body,
                params=params,
                timeout=HTTP_TIMEOUT,
            )
            if resp.status_code >= 500:
                raise requests.HTTPError(f"Server error {resp.status_code}: {resp.text[:500]}")
            return resp
        except Exception as e:
            last_err = e
            sleep_s = RETRY_BACKOFF ** (attempt - 1)
            logger.warning(
                f"{method} {url} failed on attempt {attempt}/{MAX_RETRIES}: {e}. Backing off {sleep_s:.1f}s"
            )
            time.sleep(sleep_s)
    assert last_err is not None
    raise last_err


# -------- GTFS-R ingestion --------
def fetch_gtfs_realtime_feed(url: str) -> gtfs_realtime_pb2.FeedMessage:
    logger.info(f"Fetching GTFS-R feed: {url}")
    resp = requests.get(url, timeout=HTTP_TIMEOUT)
    resp.raise_for_status()
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(resp.content)
    return feed


def parse_feed(feed: gtfs_realtime_pb2.FeedMessage) -> Tuple[Optional[int], List[Dict[str, Any]]]:
    feed_ts = None
    if feed.header and feed.header.timestamp:
        feed_ts = int(feed.header.timestamp)

    vehicles: List[Dict[str, Any]] = []
    for entity in feed.entity:
        if not entity.HasField("vehicle"):
            continue
        
        vehicle = entity.vehicle
        # Direct access like in Colab version
        train_id = vehicle.vehicle.id if vehicle.vehicle.id else "Unknown"
        route_id = vehicle.trip.route_id if vehicle.trip.route_id else "Unknown"
        
        if vehicle.position:
            lat = round(vehicle.position.latitude, 6)
            lon = round(vehicle.position.longitude, 6)
            speed_kmh = round(vehicle.position.speed * 3.6, 2) if vehicle.position.speed is not None else 0.0
        else:
            lat = lon = speed_kmh = "Unknown"

        vehicles.append(
            {
                "vehicle_id": train_id,
                "route_id": route_id,
                "lat": lat,
                "lon": lon,
                "speed_kmh": speed_kmh,
            }
        )
    return feed_ts, vehicles


# -------- Markdown formatting --------
def format_markdown(feed_ts: Optional[int], vehicles: List[Dict[str, Any]]) -> str:
    last_updated = ts_fmt(now_myt())
    if feed_ts is not None:
        try:
            dt = datetime.fromtimestamp(feed_ts, tz=pytz.UTC).astimezone(MYT_TZ)
            last_updated = ts_fmt(dt)
        except Exception:
            pass

    total = len(vehicles)

    # Enhanced formatting with emojis like Colab version
    task_content = f"🚌 **KTM Train Status Live Update**\n\n"
    task_content += f"*Last updated: {last_updated}*\n\n"

    if total == 0:
        task_content += "No active trains detected at the moment."
    else:
        task_content += f"Found **{total}** active trains.\n\n"
        
        # Show ALL trains (no limit) as requested
        for v in vehicles:
            train_id = v.get('vehicle_id', 'Unknown')
            route_id = v.get('route_id', 'Unknown')
            lat = v.get('lat', 'Unknown')
            lon = v.get('lon', 'Unknown')
            speed_kmh = v.get('speed_kmh', 'Unknown')
            
            task_content += (
                f"  - **Train ID:** {train_id} | **Route:** {route_id}\n"
                f"    - **Location:** `{lat}, {lon}`\n"
                f"    - **Speed:** {speed_kmh} km/h\n"
            )

    return task_content


# -------- Taskade Client --------
class TaskadeClient:
    def __init__(self, base_url: str, api_token: str):
        if not base_url:
            raise ValueError("TASKADE_BASE_URL is required")
        if not api_token:
            raise ValueError("TASKADE_API_TOKEN is required")
        self.base = base_url.rstrip("/")
        self.token = api_token

    @property
    def headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def create_task(self, project_id: str, content_md: str, title: str = None) -> Dict[str, Any]:
        # Using correct Taskade API structure from Colab learnings
        url = f"{self.base}/projects/{project_id}/tasks"
        payload = {
            "tasks": [{
                "taskId": None,
                "placement": "afterbegin",
                "contentType": "text/markdown",
                "content": content_md,
                "title": title or DASHBOARD_TITLE
            }]
        }
        
        logger.info(f"Creating task at {url}")
        resp = http_request("POST", url, self.headers, json_body=payload)
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"Create task failed: {resp.status_code} {resp.text}")
        
        response_data = resp.json()
        logger.info(f"DEBUG: Full API Response for Create Task: {json.dumps(response_data, indent=2)}")
        
        # Parse task ID using correct path from Colab learnings
        try:
            task_id = response_data['item'][0]['id']
            logger.info(f"✅ Successfully created task. Task ID: {task_id}")
            return {"id": task_id, "response": response_data}
        except KeyError as e:
            logger.error(f"❌ Error parsing API response. Key not found: {e}")
            logger.error("Please check the DEBUG output above to see the actual API response.")
            raise

    def update_task(self, task_id: str, content_md: str) -> Dict[str, Any]:
        # Using correct Taskade API structure from Colab learnings
        url = f"{self.base}/tasks/{task_id}"
        payload = {"content": content_md}
        
        logger.info(f"Updating task {task_id} at {url}")
        resp = http_request("PUT", url, self.headers, json_body=payload)
        if resp.status_code not in (200, 204):
            raise RuntimeError(f"Update task failed: {resp.status_code} {resp.text}")
        
        logger.info(f"✅ Successfully updated task {task_id}")
        return {"task_id": task_id}

    def list_tasks(self, project_id: str) -> List[Dict[str, Any]]:
        url = f"{self.base}/projects/{project_id}/tasks"
        resp = http_request("GET", url, self.headers)
        if resp.status_code != 200:
            raise RuntimeError(f"List tasks failed: {resp.status_code} {resp.text}")
        data = resp.json()
        if isinstance(data, dict) and "items" in data:
            return data["items"]
        if isinstance(data, list):
            return data
        return []

    def find_task_by_title(self, project_id: str, title: str) -> Optional[Dict[str, Any]]:
        items = self.list_tasks(project_id)
        logger.info(f"Searching through {len(items)} tasks for title: '{title}'")
        for it in items:
            t = (it.get("title") or "").strip()
            logger.info(f"Found task with title: '{t}'")
            # Exact match (case insensitive)
            if t.lower() == title.lower():
                logger.info(f"✅ Found exact matching task: {t}")
                return it
            # Partial match for KTM dashboard tasks
            if "ktm" in t.lower() and "status" in t.lower() and "update" in t.lower():
                logger.info(f"✅ Found KTM dashboard task by partial match: {t}")
                return it
        logger.info("No matching task found")
        return None


def main() -> int:
    if not TASKADE_PROJECT_ID:
        logger.error("❌ TASKADE_PROJECT_ID is required")
        return 2

    if not TASKADE_API_TOKEN:
        logger.error("❌ TASKADE_API_TOKEN is required")
        return 2

    try:
        client = TaskadeClient(TASKADE_BASE_URL, TASKADE_API_TOKEN)

        logger.info(f"🚀 Fetching data from API at {ts_fmt(now_myt())}...")
        feed = fetch_gtfs_realtime_feed(GTFSR_URL)
        feed_ts, vehicles = parse_feed(feed)
        content_md = format_markdown(feed_ts, vehicles)

        task_id = TASKADE_TASK_ID.strip() if TASKADE_TASK_ID else ""
        
        # If we have a task ID, update existing task
        if task_id:
            logger.info(f"Updating existing Taskade task: {task_id}")
            client.update_task(task_id, content_md)
            logger.info("✅ Update complete")
            return 0

        # Fallback: search for existing task by title
        logger.info(f"Searching for existing task titled '{DASHBOARD_TITLE}' in project {TASKADE_PROJECT_ID}")
        existing = client.find_task_by_title(TASKADE_PROJECT_ID, DASHBOARD_TITLE)
        if existing:
            discovered_id = str(existing.get("id") or existing.get("task_id") or "")
            if not discovered_id:
                logger.warning("Found task by title but could not determine its ID field; updating may not be possible.")
            else:
                logger.info(f"Found existing task id={discovered_id}; updating.")
                client.update_task(discovered_id, content_md)
                print(json.dumps({"TASKADE_TASK_ID": discovered_id}))
                return 0

        # Create new task if not found
        logger.info("No existing task found. Creating a new dashboard task.")
        created = client.create_task(TASKADE_PROJECT_ID, content_md, DASHBOARD_TITLE)
        new_id = str(created.get("id") or created.get("task_id") or "")
        if new_id:
            logger.info(f"✅ Created task id={new_id}")
            print(json.dumps({"TASKADE_TASK_ID": new_id}))
        else:
            logger.warning("Task created but could not parse task ID from response. Please inspect API response shape.")
        return 0

    except requests.exceptions.RequestException as e:
        logger.error(f"❌ API Error at {ts_fmt(now_myt())}: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Error Response: {e.response.text}")
        return 1
    except KeyError as e:
        logger.error(f"❌ Error parsing API response. Unexpected structure. Key not found: {e}")
        logger.error("Please check the DEBUG output above to see the actual API response.")
        return 1
    except Exception as e:
        logger.error(f"❌ An unexpected error occurred at {ts_fmt(now_myt())}: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)



