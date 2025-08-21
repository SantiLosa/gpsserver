# GPS Tracking Protocol Challenge (IGX v1.2) – with persistence and Admin

This repository contains a **technical challenge** based on an extended commercial GPS protocol.  
The goal is to parse, validate, and process frames with position data, odometer, and additional parameters, **store them in Django/DRF models**, and provide a **simple Admin view** to manually upload frames.

---

## Example frame

```
$IGX,1.2,359710123456789,0045,210825,160455,3436.2233,S,05822.8955,W,31.5,270,12.4,3,11,0.8,12345.6,54.3,12.1,00A3,ODO_MODE=ABS;TEMP_C=36.7;DRIVER_ID=AB12-XY9;FW=2025.08.1*07
```

---

## IGX v1.2 Protocol

### Delimiters
- Start: `$`
- End: `\r\n`
- Checksum: `*CC` (XOR of all ASCII bytes between `$` and `*`), 2-digit uppercase hex.

### Separators
- Fields: `,`
- Extensions: `;` in the format `KEY=VALUE`

### Fields (order)

1. `proto` – Identifier (`IGX`)
2. `ver` – Version (e.g. `1.2`)
3. `imei` – Unique identifier (14–17 digits)
4. `seq` – Sequence 0000–9999 with wrap-around
5. `date` – UTC date `DDMMYY`
6. `time` – UTC time `HHMMSS`
7. `lat` – Latitude `DDMM.mmmm`
8. `lat_hemi` – Hemisphere N/S
9. `lon` – Longitude `DDDMM.mmmm`
10. `lon_hemi` – Hemisphere E/W
11. `speed_kmh` – Speed in km/h
12. `course_deg` – Course 0–359°
13. `alt_m` – Altitude (m)
14. `fix` – Fix quality (0=no fix,2=2D,3=3D)
15. `sats` – Number of satellites
16. `hdop` – HDOP
17. `odom_km` – Odometer (km)
18. `fuel_pct` – Fuel percentage
19. `batt_v` – Battery (V)
20. `io_hex` – IO bitmask in hex (4 digits)
21. `ext` – Extensions `key=value` separated by `;`

### Coordinates example
- `3436.2233,S` → -34° 36.2233′
- `05822.8955,W` → -58° 22.8955′

---

## Bitmask `io_hex`

Example: `00A3` → `0000 0000 1010 0011` → active bits 0,1,5,7.

- bit 0: Ignition ON
- bit 1: External power
- bit 2: Door open
- bit 3: Panic button
- bit 4: Towing
- bit 5: Geofence active
- bit 6: Jamming detected
- bit 7: Impact
- 8–15: reserved

---

## Challenge

1. Parse the frame into a data structure.
2. Validate checksum and value ranges (e.g. lat, lon, fuel%).
3. Convert coordinates to decimal (e.g. -34.6037, -58.3810).
4. Interpret the `io_hex` bitmask.
5. Process extensions (`ext`) as a dictionary.
6. **Persist** using Django/DRF models:
   - Always save the raw frame in `FrameRaw`.
   - Generate a `Position` with coordinates, fix, odometer, etc.
   - Relate to a `Device` (IMEI).
7. **Admin view**: allow pasting multiple frames (one per line) and process them in bulk.

---

## Persistence requirements

- **Device**: stores IMEI and optional alias.
- **FrameRaw**: saves the original frame, whether checksum was valid, whether it was processed, and any error.
- **Position**: stores parsed data (decimal lat/lon, speed, fix, odometer, etc.) + extensions.
- **ProcessingLog** (optional): to log events or errors.

---

## Admin view (manual frame upload)

- Simple form with a textarea.
- Processes line by line:
  - Validates format + checksum.
  - Saves `FrameRaw`.
  - If valid, generates `Position`.
  - If invalid, fills the `error` field.
- Result: shows summary “Processed N lines. OK=X, errors=Y”.

---

## Minimum test cases

1. Valid frame → `FrameRaw` + `Position`.
2. Invalid checksum → `FrameRaw` with error, no `Position`.
3. Duplicate (`device+seq`) → must not duplicate `Position`.
4. Out-of-range values → rejection with error.
5. Multiple extensions → stored as key–value structure.
6. IO bitmask → persisted and interpreted according to the table.
7. Bulk upload in Admin → correct OK/error counts displayed.

---

## Bonus

- Unit tests with valid and invalid frames.
- Simulation of multiple frame ingestion and distance calculation using odometer.
- Export positions to JSON.
- Basic metrics: valid/invalid frames, duplicates avoided, parsing errors.

---
