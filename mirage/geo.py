import ipaddress
import json
import urllib.request
from typing import Any, Dict, Optional


class GeoLookupError(RuntimeError):
    pass


def is_private_ip(ip: str) -> bool:
    try:
        return ipaddress.ip_address(ip).is_private
    except ValueError:
        return False


def lookup_public_ip() -> str:
    try:
        with urllib.request.urlopen("https://api.ipify.org?format=json", timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return payload.get("ip", "unknown")
    except Exception:
        return "unknown"


def _parse_payload(payload: Dict[str, Any], ip: str) -> Dict[str, Any]:
    if not payload:
        return {}
    if isinstance(payload.get("status"), str) and payload.get("status") != "success":
        return {}
    return {
        "ip": payload.get("ip") or ip,
        "country": payload.get("country") or payload.get("countryName") or "unknown",
        "region": payload.get("region") or payload.get("regionName") or "unknown",
        "city": payload.get("city") or "unknown",
        "org": payload.get("org") or payload.get("as") or "unknown",
        "loc": payload.get("loc") or payload.get("lat") and payload.get("lon") and f"{payload.get('lat')},{payload.get('lon')}" or "unknown",
    }


def lookup_geo(ip: str) -> Dict[str, Any]:
    if not ip or ip == "unknown":
        return {}
    if is_private_ip(ip):
        return {"ip": ip, "private": True, "note": "private address"}

    endpoints = [
        ("https://ipinfo.io/{ip}/json", _parse_payload),
        ("http://ip-api.com/json/{ip}", _parse_payload),
        ("https://ipwho.is/{ip}", _parse_payload),
    ]

    for url_template, parser in endpoints:
        try:
            request = urllib.request.Request(url_template.format(ip=ip), headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(request, timeout=6) as response:
                payload = json.loads(response.read().decode("utf-8"))
            parsed = parser(payload, ip)
            if parsed.get("country") != "unknown" or parsed.get("city") != "unknown" or parsed.get("region") != "unknown":
                return parsed
        except Exception:
            continue

    return {"ip": ip, "country": "unknown", "region": "unknown", "city": "unknown"}


def build_location_summary(geo_payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    payload = geo_payload or {}
    return {
        "public_ip": payload.get("ip") or "unknown",
        "country": payload.get("country", "unknown"),
        "region": payload.get("region", "unknown"),
        "city": payload.get("city", "unknown"),
        "org": payload.get("org", "unknown"),
        "loc": payload.get("loc", "unknown"),
        "private": payload.get("private", False),
        "note": payload.get("note", ""),
    }
