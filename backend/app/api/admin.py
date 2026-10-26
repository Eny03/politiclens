"""
Admin & Visitor Analytics API Router (Accesso Esclusivo per Questo PC).
Tracks real-time visitor sessions, active users online, and IP logs with device and browser breakdown.
Strictly secured to ensure only this authorized PC / admin token can access telemetry data.
"""

import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request, Query, Header, Cookie
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_
from pydantic import BaseModel

from app.database import get_db
from app.config import settings
from app.models import VisitorLog

router = APIRouter(prefix="/api/admin", tags=["Admin & Telemetria Visitatori"])

class AdminLoginRequest(BaseModel):
    secret_key: str

def extract_client_ip(request: Request) -> str:
    """Extracts client IP respecting reverse proxies (Cloudflare, Render, Nginx)."""
    cf_ip = request.headers.get("cf-connecting-ip")
    if cf_ip and cf_ip.strip():
        return cf_ip.strip()
    x_real = request.headers.get("x-real-ip")
    if x_real and x_real.strip():
        return x_real.strip()
    x_forwarded = request.headers.get("x-forwarded-for")
    if x_forwarded and x_forwarded.strip():
        return x_forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"

def is_request_authorized(request: Request, token: Optional[str] = None) -> bool:
    """
    Validates if the request is originated from this authorized PC:
    1. Localhost / local machine access (127.0.0.1, ::1, testclient) is always authorized.
    2. Remote / Render access requires the matching master Admin Secret Key via header, query, or cookie.
    """
    client_ip = extract_client_ip(request)
    
    # Check if direct local machine access
    if client_ip in ["127.0.0.1", "::1", "localhost", "testclient"]:
        return True

    # Check token from parameter, header, query, or cookie
    auth_header = token or request.headers.get("x-admin-token") or request.headers.get("authorization")
    if auth_header:
        cleaned_token = auth_header.replace("Bearer ", "").strip()
        if cleaned_token == settings.ADMIN_SECRET_KEY:
            return True

    query_key = request.query_params.get("auth_key") or request.query_params.get("key")
    if query_key and query_key.strip() == settings.ADMIN_SECRET_KEY:
        return True

    cookie_token = request.cookies.get("admin_auth_token")
    if cookie_token and cookie_token.strip() == settings.ADMIN_SECRET_KEY:
        return True

    return False

def verify_admin_access(request: Request):
    """FastAPI Dependency for admin routes."""
    if not is_request_authorized(request):
        raise HTTPException(
            status_code=403,
            detail="Accesso Negato: Questa sezione è riservata all'amministratore su dispositivo autorizzato (questo PC)."
        )
    return True

@router.post("/verify")
def check_admin_verification(request: Request, data: Optional[AdminLoginRequest] = None):
    """Checks whether the current browser session is authorized."""
    token = data.secret_key if data else None
    authorized = is_request_authorized(request, token=token)
    client_ip = extract_client_ip(request)
    is_local = client_ip in ["127.0.0.1", "::1", "localhost", "testclient"]
    return {
        "authorized": authorized,
        "is_localhost": is_local,
        "client_ip": client_ip
    }

@router.post("/login")
def admin_login(data: AdminLoginRequest, request: Request):
    """Authenticates this PC / browser with the master admin secret key."""
    if data.secret_key.strip() == settings.ADMIN_SECRET_KEY:
        return {
            "success": True,
            "token": settings.ADMIN_SECRET_KEY,
            "message": "Dispositivo autorizzato con successo per questo PC."
        }
    raise HTTPException(status_code=401, detail="Chiave di autorizzazione non corretta.")

@router.get("/visitors/stats")
def get_visitor_stats(
    request: Request,
    auth: bool = Depends(verify_admin_access),
    db: Session = Depends(get_db)
):
    """Returns high-level visitor metrics: online now, unique visitors today, total, and device distribution."""
    now = datetime.datetime.utcnow()
    five_min_ago = now - datetime.timedelta(minutes=5)
    midnight_today = datetime.datetime(now.year, now.month, now.day)

    # 1. Online Adesso (ultimi 5 minuti)
    online_now_count = db.query(VisitorLog.ip_address).filter(
        VisitorLog.timestamp >= five_min_ago
    ).distinct().count()

    # 2. Visitatori Unici Oggi
    today_visitors_count = db.query(VisitorLog.ip_address).filter(
        VisitorLog.timestamp >= midnight_today
    ).distinct().count()

    # 3. Visitatori Unici Totali
    total_visitors_count = db.query(VisitorLog.ip_address).distinct().count()

    # 4. Totale Visualizzazioni / Richieste
    total_page_views = db.query(VisitorLog).count()

    # 5. Device Breakdown
    device_rows = db.query(
        VisitorLog.device_type, func.count(VisitorLog.id)
    ).group_by(VisitorLog.device_type).all()
    device_breakdown = {row[0] or "Desktop": row[1] for row in device_rows}

    # 6. Browser Breakdown
    browser_rows = db.query(
        VisitorLog.browser, func.count(VisitorLog.id)
    ).group_by(VisitorLog.browser).all()
    browser_breakdown = {row[0] or "Altro": row[1] for row in browser_rows}

    # 7. OS Breakdown
    os_rows = db.query(
        VisitorLog.os_name, func.count(VisitorLog.id)
    ).group_by(VisitorLog.os_name).all()
    os_breakdown = {row[0] or "Sconosciuto": row[1] for row in os_rows}

    # 8. Top 8 Visited Paths
    path_rows = db.query(
        VisitorLog.path, func.count(VisitorLog.id)
    ).group_by(VisitorLog.path).order_by(desc(func.count(VisitorLog.id))).limit(8).all()
    top_paths = [{"path": row[0], "count": row[1]} for row in path_rows]

    return {
        "online_now_count": online_now_count,
        "today_visitors_count": today_visitors_count,
        "total_visitors_count": total_visitors_count,
        "total_page_views": total_page_views,
        "device_breakdown": device_breakdown,
        "browser_breakdown": browser_breakdown,
        "os_breakdown": os_breakdown,
        "top_paths": top_paths,
        "server_time": now.isoformat()
    }

@router.get("/visitors/list")
def get_visitor_ip_list(
    request: Request,
    search: Optional[str] = None,
    filter_type: str = "all", # "all", "online_now", "today"
    limit: int = Query(100, ge=1, le=500),
    auth: bool = Depends(verify_admin_access),
    db: Session = Depends(get_db)
):
    """
    Returns the comprehensive list of unique visitor IPs with online status,
    visit counts, first/last seen timestamps, device/browser details, and recent paths.
    """
    now = datetime.datetime.utcnow()
    five_min_ago = now - datetime.timedelta(minutes=5)
    midnight_today = datetime.datetime(now.year, now.month, now.day)

    # Base query grouping by IP
    group_query = db.query(
        VisitorLog.ip_address,
        func.min(VisitorLog.timestamp).label("first_seen"),
        func.max(VisitorLog.timestamp).label("last_seen"),
        func.count(VisitorLog.id).label("total_visits")
    )

    if search and search.strip():
        q_term = f"%{search.strip()}%"
        group_query = group_query.filter(
            or_(
                VisitorLog.ip_address.ilike(q_term),
                VisitorLog.path.ilike(q_term),
                VisitorLog.browser.ilike(q_term),
                VisitorLog.os_name.ilike(q_term)
            )
        )

    if filter_type == "online_now":
        group_query = group_query.filter(VisitorLog.timestamp >= five_min_ago)
    elif filter_type == "today":
        group_query = group_query.filter(VisitorLog.timestamp >= midnight_today)

    grouped_results = group_query.group_by(VisitorLog.ip_address).order_by(desc("last_seen")).limit(limit).all()

    ip_list = []
    for row in grouped_results:
        ip = row.ip_address
        first_seen = row.first_seen
        last_seen = row.last_seen
        total_visits = row.total_visits
        is_online = (last_seen >= five_min_ago) if last_seen else False

        # Get latest metadata for this IP
        latest_record = db.query(VisitorLog).filter(
            VisitorLog.ip_address == ip
        ).order_by(desc(VisitorLog.timestamp)).first()

        # Get distinct recent paths
        recent_path_records = db.query(VisitorLog.path).filter(
            VisitorLog.ip_address == ip
        ).order_by(desc(VisitorLog.timestamp)).limit(6).all()
        recent_paths = list(dict.fromkeys([p[0] for p in recent_path_records]))

        ip_list.append({
            "ip_address": ip,
            "first_seen": first_seen.isoformat() if first_seen else None,
            "last_seen": last_seen.isoformat() if last_seen else None,
            "is_online_now": is_online,
            "total_visits": total_visits,
            "device_type": latest_record.device_type if latest_record else "Desktop",
            "browser": latest_record.browser if latest_record else "Altro",
            "os_name": latest_record.os_name if latest_record else "Sconosciuto",
            "country": latest_record.country if latest_record else None,
            "last_path": latest_record.path if latest_record else "/",
            "recent_paths": recent_paths
        })

    # Sort so active online visitors are always at the top, then newest last_seen
    ip_list.sort(key=lambda x: (1 if x["is_online_now"] else 0, x["last_seen"] or ""), reverse=True)

    return {
        "total_records": len(ip_list),
        "filter_applied": filter_type,
        "visitors": ip_list
    }

@router.delete("/visitors/clear")
def clear_visitor_logs(
    request: Request,
    auth: bool = Depends(verify_admin_access),
    db: Session = Depends(get_db)
):
    """Admin endpoint to reset or clear visitor tracking logs."""
    count = db.query(VisitorLog).delete()
    db.commit()
    return {"success": True, "deleted_logs": count}
