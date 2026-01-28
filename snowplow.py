#!/usr/bin/env python3
"""
Pittsburgh Snow Plow Tracker

Track snow plow locations and check if your street has been plowed.
Uses live data from the City of Pittsburgh's Snow Response Dashboard.

Usage:
    snowplow.py status [--active]
    snowplow.py near <location> [--radius <miles>] [--limit <n>]
    snowplow.py check <address> [--hours <n>] [--radius <feet>]
    snowplow.py history <vehicle> [--hours <n>]

Data source: https://pittsburghpa.gov/dpw/snow-plow-tracker
"""

import argparse
import json
import math
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus, urlencode

# ArcGIS REST API endpoints
VEHICLES_URL = "https://services1.arcgis.com/YZCmUqbcsUpOKfj7/arcgis/rest/services/TEST_TEST/FeatureServer/0/query"
HISTORY_URL = "https://pghbridgis.pittsburghpa.gov/hosting/rest/services/Hosted/samsara_history/FeatureServer/0/query"

# Nominatim for geocoding
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"


def fetch_json(url: str, params: dict = None) -> dict:
    """Fetch JSON from a URL with optional query parameters."""
    if params:
        url = f"{url}?{urlencode(params)}"
    
    try:
        req = Request(url, headers={"User-Agent": "SnowPlow-Skill/1.0"})
        with urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())
    except (HTTPError, URLError) as e:
        print(f"Error fetching data: {e}", file=sys.stderr)
        return {}
    except json.JSONDecodeError as e:
        print(f"Error parsing response: {e}", file=sys.stderr)
        return {}


def geocode_location(location: str) -> tuple[float, float] | None:
    """Convert a location string to coordinates using Nominatim."""
    # Check if it looks like a zip code
    if re.match(r"^\d{5}$", location.strip()):
        location = f"{location}, PA"
    
    # Add Pittsburgh context if needed
    if not any(x in location.lower() for x in ["pa", "pennsylvania", "pittsburgh", ","]):
        location = f"{location}, Pittsburgh, PA"
    
    try:
        params = {
            "q": location,
            "format": "json",
            "limit": 1
        }
        url = f"{NOMINATIM_URL}?{urlencode(params)}"
        req = Request(url, headers={"User-Agent": "SnowPlow-Skill/1.0"})
        with urlopen(req, timeout=10) as response:
            results = json.loads(response.read().decode())
            if results:
                return float(results[0]["lat"]), float(results[0]["lon"])
    except Exception as e:
        print(f"Geocoding failed: {e}", file=sys.stderr)
    
    return None


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in miles."""
    R = 3959  # Earth's radius in miles
    
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c


def parse_timestamp(ts_str: str) -> datetime | None:
    """Parse a timestamp string to datetime."""
    if not ts_str:
        return None
    try:
        # Handle ISO format with Z
        if ts_str.endswith('Z'):
            ts_str = ts_str[:-1] + '+00:00'
        return datetime.fromisoformat(ts_str)
    except ValueError:
        try:
            # Try epoch milliseconds
            return datetime.fromtimestamp(int(ts_str) / 1000, tz=timezone.utc)
        except:
            return None


def format_time_ago(dt: datetime) -> str:
    """Format a datetime as relative time."""
    if not dt:
        return "unknown"
    
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    diff = now - dt
    
    if diff.total_seconds() < 60:
        return "just now"
    elif diff.total_seconds() < 3600:
        mins = int(diff.total_seconds() / 60)
        return f"{mins} min{'s' if mins != 1 else ''} ago"
    elif diff.total_seconds() < 86400:
        hours = int(diff.total_seconds() / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    else:
        days = int(diff.total_seconds() / 86400)
        return f"{days} day{'s' if days != 1 else ''} ago"


def get_default_address() -> str | None:
    """Try to read default address from TOOLS.md."""
    workspace_paths = [
        Path.home() / "clawd" / "TOOLS.md",
        Path.cwd() / "TOOLS.md",
        Path(os.environ.get("CLAWDBOT_WORKSPACE", "")) / "TOOLS.md",
    ]
    
    for tools_path in workspace_paths:
        if tools_path.exists():
            try:
                content = tools_path.read_text()
                match = re.search(
                    r"##\s*Snow\s*Plow.*?Default address:\s*(.+?)(?:\n|$)",
                    content,
                    re.IGNORECASE | re.DOTALL
                )
                if match:
                    return match.group(1).strip()
            except Exception:
                pass
    return None


def get_vehicles() -> list[dict]:
    """Fetch current vehicle locations."""
    params = {
        "where": "1=1",
        "outFields": "name,gps_time,gps_latitude,gps_longitude,gps_speedMilesPerHour,gps_headingDegrees",
        "f": "json",
        "resultRecordCount": 500
    }
    
    data = fetch_json(VEHICLES_URL, params)
    
    vehicles = []
    for feature in data.get("features", []):
        attr = feature.get("attributes", {})
        vehicles.append({
            "name": attr.get("name"),
            "time": parse_timestamp(attr.get("gps_time")),
            "lat": attr.get("gps_latitude"),
            "lon": attr.get("gps_longitude"),
            "speed": attr.get("gps_speedMilesPerHour", 0),
            "heading": attr.get("gps_headingDegrees"),
        })
    
    return vehicles


def get_route_history(hours: int = 12, vehicle: str = None) -> list[dict]:
    """Fetch route history."""
    # Calculate time window
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(hours=hours)
    
    # Build where clause
    where_parts = [f"gps_time >= '{start_time.isoformat()}'"]
    if vehicle:
        where_parts.append(f"name = '{vehicle}'")
    
    params = {
        "where": " AND ".join(where_parts),
        "outFields": "name,gps_time,gps_latitude,gps_longitude",
        "f": "json",
        "resultRecordCount": 2000,
        "orderByFields": "gps_time DESC"
    }
    
    data = fetch_json(HISTORY_URL, params)
    
    points = []
    for feature in data.get("features", []):
        attr = feature.get("attributes", {})
        geom = feature.get("geometry", {})
        
        lat = attr.get("gps_latitude") or (geom.get("y") if geom else None)
        lon = attr.get("gps_longitude") or (geom.get("x") if geom else None)
        
        if lat and lon:
            points.append({
                "name": attr.get("name"),
                "time": parse_timestamp(attr.get("gps_time")),
                "lat": lat,
                "lon": lon,
            })
    
    return points


def cmd_status(args):
    """Show current plow status."""
    vehicles = get_vehicles()
    
    if not vehicles:
        print("No vehicle data available. There may not be an active snow event.")
        return 1
    
    # Filter to active if requested
    if args.active:
        vehicles = [v for v in vehicles if v.get("speed", 0) > 0.5]
    
    # Sort by speed (active first), then name
    vehicles.sort(key=lambda v: (-v.get("speed", 0), v.get("name", "")))
    
    if not vehicles:
        print("No active plows currently moving.")
        return 0
    
    print(f"{'🚛 Active' if args.active else '📊 All'} Snow Plows ({len(vehicles)} vehicles):\n")
    
    for v in vehicles:
        speed = v.get("speed", 0)
        status = "🟢 Moving" if speed > 0.5 else "🔴 Stopped"
        speed_str = f"{speed:.1f} mph" if speed > 0 else "parked"
        time_ago = format_time_ago(v.get("time"))
        
        print(f"{v['name']}")
        print(f"  Status: {status} ({speed_str})")
        print(f"  Location: {v.get('lat', 'N/A'):.5f}, {v.get('lon', 'N/A'):.5f}")
        print(f"  Last update: {time_ago}")
        print()
    
    return 0


def cmd_near(args):
    """Find plows near a location."""
    # Geocode the location
    coords = geocode_location(args.location)
    if not coords:
        print(f"Error: Could not find location '{args.location}'")
        return 1
    
    lat, lon = coords
    print(f"Searching near: {args.location} ({lat:.4f}, {lon:.4f})\n", file=sys.stderr)
    
    vehicles = get_vehicles()
    if not vehicles:
        print("No vehicle data available.")
        return 1
    
    # Calculate distances
    results = []
    for v in vehicles:
        if v.get("lat") and v.get("lon"):
            dist = haversine_distance(lat, lon, v["lat"], v["lon"])
            if dist <= args.radius:
                results.append((v, dist))
    
    # Sort by distance
    results.sort(key=lambda x: x[1])
    
    if not results:
        print(f"No plows found within {args.radius} miles.")
        return 0
    
    print(f"Found {len(results)} plows within {args.radius} miles:\n")
    
    for v, dist in results[:args.limit]:
        speed = v.get("speed", 0)
        status = "🟢 Moving" if speed > 0.5 else "🔴 Stopped"
        time_ago = format_time_ago(v.get("time"))
        
        print(f"🚛 {v['name']} — {dist:.2f} miles away")
        print(f"   {status} ({speed:.1f} mph)")
        print(f"   Updated: {time_ago}")
        print()
    
    return 0


def cmd_check(args):
    """Check if a street has been plowed."""
    address = args.address
    
    # Use default if no address provided
    if not address:
        address = get_default_address()
        if not address:
            print("Error: Address required.")
            print("Usage: snowplow.py check \"123 Main St, Pittsburgh\"")
            print("\nOr set a default in TOOLS.md:")
            print("  ## Snow Plow")
            print("  Default address: 123 Main St, Pittsburgh, PA 15213")
            return 1
        print(f"Using default address: {address}\n", file=sys.stderr)
    
    # Geocode the address
    coords = geocode_location(address)
    if not coords:
        print(f"Error: Could not find address '{address}'")
        return 1
    
    lat, lon = coords
    
    # Convert radius from feet to miles
    radius_miles = args.radius / 5280
    
    print(f"Checking plow activity near: {address}")
    print(f"Looking back {args.hours} hours, within {args.radius} feet\n")
    
    # Get route history
    history = get_route_history(hours=args.hours)
    
    if not history:
        print("No route history available. There may not be recent snow activity.")
        return 0
    
    # Find points near the address
    nearby = []
    for point in history:
        if point.get("lat") and point.get("lon"):
            dist = haversine_distance(lat, lon, point["lat"], point["lon"])
            if dist <= radius_miles:
                nearby.append((point, dist * 5280))  # Convert back to feet
    
    if not nearby:
        print(f"❌ No plow activity found within {args.radius} feet of this address")
        print(f"   in the last {args.hours} hours.")
        return 0
    
    # Sort by time (most recent first)
    nearby.sort(key=lambda x: x[0].get("time") or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    
    # Get unique plows that passed
    plows = set(p[0]["name"] for p in nearby)
    most_recent = nearby[0]
    
    print(f"✅ YES — Your street has been plowed!")
    print(f"\n   Most recent: {format_time_ago(most_recent[0].get('time'))}")
    print(f"   Plow: {most_recent[0]['name']}")
    print(f"   Distance: {most_recent[1]:.0f} feet from address")
    
    if len(plows) > 1:
        print(f"\n   {len(nearby)} total passes by {len(plows)} different plows:")
        for plow in sorted(plows):
            passes = [p for p in nearby if p[0]["name"] == plow]
            print(f"     {plow}: {len(passes)} passes")
    
    return 0


def cmd_history(args):
    """Show route history for a vehicle."""
    print(f"Route history for {args.vehicle} (last {args.hours} hours):\n")
    
    history = get_route_history(hours=args.hours, vehicle=args.vehicle)
    
    if not history:
        print(f"No history found for {args.vehicle}.")
        print("The vehicle ID may be incorrect, or no data in this time window.")
        return 1
    
    print(f"Found {len(history)} GPS points:\n")
    
    # Group by time chunks (every 15 mins)
    current_time = None
    for point in history[:50]:  # Limit output
        pt_time = point.get("time")
        time_str = pt_time.strftime("%H:%M") if pt_time else "??:??"
        date_str = pt_time.strftime("%Y-%m-%d") if pt_time else ""
        
        # Print date header when it changes
        if current_time is None or (pt_time and pt_time.date() != current_time.date()):
            if pt_time:
                print(f"--- {pt_time.strftime('%A, %B %d')} ---")
                current_time = pt_time
        
        print(f"  {time_str}  ({point.get('lat', 0):.5f}, {point.get('lon', 0):.5f})")
    
    if len(history) > 50:
        print(f"\n  ... and {len(history) - 50} more points")
    
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Pittsburgh Snow Plow Tracker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Show current plow status")
    status_parser.add_argument("--active", action="store_true", help="Only show moving plows")
    
    # Near command
    near_parser = subparsers.add_parser("near", help="Find plows near a location")
    near_parser.add_argument("location", help="Address, zip, or neighborhood")
    near_parser.add_argument("--radius", "-r", type=float, default=2, help="Search radius in miles")
    near_parser.add_argument("--limit", "-n", type=int, default=10, help="Max results")
    
    # Check command
    check_parser = subparsers.add_parser("check", help="Check if a street was plowed")
    check_parser.add_argument("address", nargs="?", help="Street address to check")
    check_parser.add_argument("--hours", "-t", type=int, default=12, help="Hours to look back")
    check_parser.add_argument("--radius", "-r", type=int, default=200, help="Radius in feet")
    
    # History command
    history_parser = subparsers.add_parser("history", help="Show vehicle route history")
    history_parser.add_argument("vehicle", help="Vehicle ID (e.g., PW-110)")
    history_parser.add_argument("--hours", "-t", type=int, default=6, help="Hours to show")
    
    args = parser.parse_args()
    
    if args.command == "status":
        return cmd_status(args)
    elif args.command == "near":
        return cmd_near(args)
    elif args.command == "check":
        return cmd_check(args)
    elif args.command == "history":
        return cmd_history(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
