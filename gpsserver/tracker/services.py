from typing import Dict, Any
from .models import Device, FrameRaw, Position, ProcessingLog
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

Q1 = Decimal("0.0")


def d1(s: str) -> Decimal:
    return Decimal(s).quantize(Q1, rounding=ROUND_HALF_UP)


def calculate_checksum(payload: str) -> str:
    """Calculate XOR checksum for frame payload (between $ and *)."""
    cs = 0
    for char in payload:
        cs ^= ord(char)
    return f"{cs:02X}"


def parse_coordinate(value: str, hemi: str) -> Decimal:
    """
    Convert NMEA-style coordinates (DDMM.mmmm or DDDMM.mmmm) to decimal degrees,
    using Decimal math and quantize to 6 dp.
    """
    if not value:
        return None
    if len(value) < 4:
        raise ValueError("Invalid coordinate format")
    if "." not in value:
        raise ValueError("Coordinate missing decimal part")

    # Determine degree length by integer-part length before the dot
    int_part_len = len(value.split(".")[0])
    deg_len = 3 if int_part_len > 4 else 2  # 3 for lon, 2 for lat

    deg = Decimal(value[:deg_len])
    minutes = Decimal(value[deg_len:])
    decimal = deg + (minutes / Decimal("60"))

    if hemi in ("S", "W"):
        decimal = -decimal

    # Quantize to 6 decimal places for model's DecimalField(decimal_places=6)
    return decimal.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)


def parse_extensions(ext_str: str) -> Dict[str, Any]:
    """Parse key=value;key=value extensions into dict."""
    if not ext_str:
        return {}
    parts = ext_str.split(";")
    extensions = {}
    for p in parts:
        if "=" in p:
            k, v = p.split("=", 1)
            extensions[k] = v
    return extensions


def parse_io_bitmask(io_hex: str) -> Dict[str, bool]:
    """Interpret IO hex bitmask into flags according to spec."""
    mapping = {
        0: "ignition_on",
        1: "external_power",
        2: "door_open",
        3: "panic_button",
        4: "towing",
        5: "geofence_active",
        6: "jamming_detected",
        7: "impact",
    }
    bits = bin(int(io_hex, 16))[2:].zfill(16)
    return {name: bits[::-1][i] == "1" for i, name in mapping.items()}


def parse_frame(frame: str) -> Dict[str, Any]:
    """
    Parse one raw frame into structured dict.
    Raises ValueError if invalid.
    """
    frame = frame.strip()
    if not frame.startswith("$IGX"):
        raise ValueError("Invalid protocol header")

    # Split checksum
    try:
        payload, checksum = frame[1:].split("*")
    except ValueError as exc:
        raise ValueError("Missing checksum") from exc

    # Validate checksum
    calc_cs = calculate_checksum(payload)
    if checksum.upper() != calc_cs:
        raise ValueError(f"Checksum mismatch (got {checksum}, expected {calc_cs})")

    # Split fields
    parts = payload.split(",")
    print(f"Lenparts {len(parts)}")
    if len(parts) < 20:
        raise ValueError("Incomplete frame")

    (
        proto,
        ver,
        imei,
        seq,
        date,
        time,
        lat,
        lat_hemi,
        lon,
        lon_hemi,
        speed,
        course,
        alt,
        fix,
        sats,
        hdop,
        odom,
        fuel,
        batt,
        io_hex,
        ext_str,
    ) = parts[:21]

    # Convert values
    lat_dec = parse_coordinate(lat, lat_hemi)
    lon_dec = parse_coordinate(lon, lon_hemi)
    extensions = parse_extensions(ext_str)
    io_flags = parse_io_bitmask(io_hex)

    return {
        "proto": proto,
        "ver": ver,
        "imei": imei,
        "seq": int(seq),
        "date": date,
        "time": time,
        "lat": lat_dec,
        "lat_hemi": lat_hemi,
        "lon": lon_dec,
        "lon_hemi": lon_hemi,
        "speed_kmh": d1(speed),
        "course_deg": int(course),
        "alt_m": d1(alt),
        "fix": int(fix),
        "sats": int(sats),
        "hdop": d1(hdop),
        "odom_km": d1(odom),
        "fuel_pct": d1(fuel),
        "batt_v": d1(batt),
        "io_raw": io_hex,
        "io_flags": io_flags,
        "extensions": extensions,
    }


def process_bulk(data: str) -> dict:
    """Process multiple frames pasted as text (newline-separated)."""
    frames = [line.strip() for line in data.strip().splitlines() if line.strip()]
    results = {"total": len(frames), "ok": 0, "errors": 0}

    for frame in frames:
        fr = process_frame(frame)
        if fr.processed:
            results["ok"] += 1
        else:
            results["errors"] += 1

    return results


def process_frame(frame: str) -> FrameRaw:
    """Save raw frame, parse, and generate Position if valid."""
    fr = FrameRaw(raw=frame)

    try:
        # Parse + checksum validation
        parsed = parse_frame(frame)  # raises ValueError if checksum/format invalid
        fr.checksum_valid = True
        fr.seq = parsed["seq"]

    except ValueError as e:
        # Even if parse/checksum fails → try to extract IMEI roughly, or fallback
        imei = None
        try:
            imei = frame.split(",")[2]  # best-effort extraction
        except Exception:
            pass

        if imei:
            device, _ = Device.objects.get_or_create(imei=imei)
            fr.device = device

        fr.checksum_valid = False
        fr.error = str(e)
        fr.processed = False
        fr.save()
        ProcessingLog.objects.create(frame=fr, level="ERROR", message=fr.error)
        return fr

    # If parsing succeeded, we’re sure we have an IMEI
    device, _ = Device.objects.get_or_create(imei=parsed["imei"])
    fr.device = device
    fr.save()

    # Build timestamp from date+time
    ts = datetime.strptime(parsed["date"] + parsed["time"], "%y%m%d%H%M%S")

    try:
        position = Position(
            device=device,
            seq=parsed["seq"],
            timestamp=ts,
            lat=parsed["lat"],
            lon=parsed["lon"],
            speed_kmh=parsed["speed_kmh"],
            course_deg=parsed["course_deg"],
            alt_m=parsed["alt_m"],
            fix=parsed["fix"],
            sats=parsed["sats"],
            hdop=parsed["hdop"],
            odom_km=parsed["odom_km"],
            fuel_pct=parsed["fuel_pct"],
            batt_v=parsed["batt_v"],
            io_hex=parsed["io_raw"],
            io_flags=parsed["io_flags"],
            extensions=parsed["extensions"],
            frame=fr,
        )

        # Validate ranges
        position.full_clean()

        # Save with transaction
        with transaction.atomic():
            position.save()

        fr.processed = True
        fr.error = None

    except ValidationError as e:
        # Multiple invalid ranges collected
        error_messages = [
            f"{field}: {', '.join(msgs)}" for field, msgs in e.message_dict.items()
        ]
        fr.processed = False
        fr.error = "; ".join(error_messages)
        ProcessingLog.objects.create(frame=fr, level="ERROR", message=fr.error)

    except IntegrityError:
        fr.processed = False
        fr.error = "Duplicate position (device_id, seq)"
        ProcessingLog.objects.create(frame=fr, level="ERROR", message=fr.error)

    fr.save()
    return fr
