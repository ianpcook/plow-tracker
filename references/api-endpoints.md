# Pittsburgh Snow Plow API Endpoints

## Vehicle Locations (Real-time)

**URL:** `https://services1.arcgis.com/YZCmUqbcsUpOKfj7/arcgis/rest/services/TEST_TEST/FeatureServer/0/query`

**Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Vehicle ID (e.g., PW-110, ES-247) |
| `gps_time` | string | ISO timestamp of GPS reading |
| `gps_latitude` | double | Latitude |
| `gps_longitude` | double | Longitude |
| `gps_speedMilesPerHour` | double | Current speed (0 = stopped) |
| `gps_headingDegrees` | double | Direction of travel |

**Example Query:**
```
?where=1=1&outFields=name,gps_time,gps_latitude,gps_longitude,gps_speedMilesPerHour&f=json&resultRecordCount=100
```

## Route History

**URL:** `https://pghbridgis.pittsburghpa.gov/hosting/rest/services/Hosted/samsara_history/FeatureServer/0/query`

**Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Vehicle ID |
| `gps_time` | string | Timestamp |
| `gps_latitude` | double | Latitude |
| `gps_longitude` | double | Longitude |

**Example Query (last 6 hours):**
```
?where=gps_time >= '2026-01-27T12:00:00Z'&outFields=name,gps_time,gps_latitude,gps_longitude&f=json&resultRecordCount=1000
```

## City Limits (Reference)

**URL:** `https://services1.arcgis.com/YZCmUqbcsUpOKfj7/arcgis/rest/services/City_Limits/FeatureServer/0/query`

Pittsburgh city boundary polygon for reference.

## Data Source

- **Dashboard:** https://pittsburghpa.maps.arcgis.com/apps/dashboards/0dcad55f65b14d38b6e0bcf4804fcd1c
- **City page:** https://pittsburghpa.gov/dpw/snow-plow-tracker
- **Data provider:** Samsara fleet tracking

## Notes

- Vehicle locations update approximately every minute
- Locations are displayed with a short delay for driver safety
- Route history may be incomplete due to data limitations
- Stopped vehicles may be reloading, in maintenance, or awaiting next shift
