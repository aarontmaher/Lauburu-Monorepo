"""
Canonical Port 4000 Web & Compute Hub.
Unified high-performance FastAPI/ASGI application serving authentication,
Shopify membership integration, 128Hz Movesense/Polar telemetry ingestion,
WebSocket streaming, and App Store catalog.
"""

import asyncio
import datetime
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Set, Union
from fastapi import Cookie, Depends, FastAPI, Header, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

try:
    from .services.shopify_service import ShopifyService, get_shopify_service
    from .services.telemetry_service import TelemetryService, get_telemetry_service
    from .services.edge_ai_service import EdgeAIService, get_edge_ai_service
    from .storage.sqlite_manager import SqliteManager, get_sqlite_manager
except (ImportError, ValueError):
    from services.shopify_service import ShopifyService, get_shopify_service
    from services.telemetry_service import TelemetryService, get_telemetry_service
    from services.edge_ai_service import EdgeAIService, get_edge_ai_service
    from storage.sqlite_manager import SqliteManager, get_sqlite_manager

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] port_4000_hub: %(message)s"
)
logger = logging.getLogger("port_4000_hub")

# Initialize FastAPI App
app = FastAPI(
    title="Lauburu Port 4000 Canonical Web & Compute Hub",
    description="Unified API server for authentication, Shopify membership, and 128Hz BLE telemetry ingestion",
    version="2.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== Pydantic Models ====================

class RegisterRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., description="User password")
    name: str = Field(..., description="User full name")
    role: Optional[str] = Field("user", description="Account role ('user'|'admin'|'contributor')")


class LoginRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class ShopifyLoginRequest(BaseModel):
    email: Optional[str] = Field(None, description="Shopify customer email")
    password: Optional[str] = Field(None, description="Shopify customer password")
    token: Optional[str] = Field(None, description="Shopify Customer Access Token")


class TelemetryIngestRequest(BaseModel):
    session_token: Optional[str] = Field(None, description="Active session token")
    sensor_type: str = Field("movesense", description="Sensor type ('movesense'|'polar'|'auxiliary_ble'|'phone_ppg')")
    heart_rate: Optional[float] = Field(None, description="Heart rate in BPM")
    rr_intervals_ms: Optional[List[float]] = Field(None, description="Array of RR intervals in ms")
    rmssd: Optional[float] = Field(None, description="RMSSD HRV metric in ms")
    dfa_alpha1: Optional[float] = Field(None, description="DFA alpha-1 scaling exponent")
    ecg_mv: Optional[Union[List[float], float]] = Field(None, description="Raw ECG sample or array in mV")
    acc_g: Optional[Union[Dict[str, float], float]] = Field(None, description="3-axis accelerometer g-forces")
    skin_temp_c: Optional[float] = Field(None, description="Skin temperature in Celsius")
    ptt_ms: Optional[float] = Field(None, description="Pulse Transit Time in ms")
    delta_time_ms: Optional[int] = Field(0, description="Delta time offset from session start in ms")
    epoch_ms: Optional[int] = Field(None, description="Monotonic timestamp in ms")


class TrendInsightRequest(BaseModel):
    session_token: str = Field(..., description="Session token")
    timestamp_epoch_ms: Optional[int] = Field(None, description="Insight timestamp in ms")
    window_size_sec: int = Field(120, description="Analysis window duration in seconds")
    arterial_stiffness_drift_pct: float = Field(0.0, description="Arterial stiffness drift percentage")
    vascular_fatigue_index: float = Field(0.0, description="Vascular fatigue index score")
    cardiac_drift_detected: bool = Field(False, description="Cardiac drift flag")
    endothelial_reserve_status: str = Field("OPTIMAL", description="Endothelial reserve status")
    zone2_compliance: str = Field("IN_ZONE", description="Zone 2 compliance status")


class EdgeChatRequest(BaseModel):
    message: str = Field(..., description="User prompt or action directive")
    history: Optional[List[Dict[str, str]]] = Field(default_factory=list, description="Conversation history")
    device_profile: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Client device hardware specs")


class EdgeMaintenanceRequest(BaseModel):
    force_cleanup: Optional[bool] = Field(False, description="Force cleanup of local cache buffers")



# ==================== Application Catalog Registry ====================

CATALOG_APPS: List[Dict[str, Any]] = [
    {
        "id": "lauburu_super_app",
        "name": "Lauburu Super App",
        "category": "lifestyle",
        "category_label": "Health & Lifestyle",
        "icon": "❤️",
        "badge": "Flagship",
        "description": "Unified consumer super app integrating daily recovery, sleep diagnostics, workout readiness, Shopify store, and AI assistant.",
        "route": "/apps/lauburu_super_app/",
        "port": 4000,
        "features": ["Daily Recovery Score", "Sleep Architecture", "Zone 2 Summary", "AI Chat", "Shopify Store"],
        "telemetry_supported": True,
        "installed": True
    },
    {
        "id": "lauburu_zone2_endurance",
        "name": "Zone 2 Endurance",
        "category": "fitness",
        "category_label": "Fitness & Biometrics",
        "icon": "🚴",
        "badge": "Active Telemetry",
        "description": "Autonomous sales-ready endurance app with real-time DFA-α1 aerobic threshold calculation, Rogue Echo Bike FTMS power/cadence, and live blood pressure.",
        "route": "/apps/lauburu_zone2_endurance/",
        "port": 4000,
        "features": ["Live DFA-α1 Engine", "Echo Bike FTMS Power & Cadence", "Continuous SBP/DBP", "Dynamic AI Audio Coach"],
        "telemetry_supported": True,
        "installed": True
    },
    {
        "id": "lauburu_bluetooth_sensor",
        "name": "Bluetooth & PPG Sensor",
        "category": "fitness",
        "category_label": "Fitness & Biometrics",
        "icon": "⚡",
        "badge": "Hardware Ingestion",
        "description": "Movesense ECG & IMU sensor connection hub, 10-second camera flashlight PPG calibrator, and live TKEO-filtered ECG oscilloscope.",
        "route": "/apps/lauburu_bluetooth_sensor/",
        "port": 4000,
        "features": ["10s Camera PPG Calibrator", "Movesense 128-512Hz ECG", "Real-Time TKEO Filter", "WebSocket IPC Server :4000"],
        "telemetry_supported": True,
        "installed": True
    },
    {
        "id": "lauburu_compute_hub",
        "name": "Lauburu Compute Hub",
        "category": "mesh",
        "category_label": "Distributed AI & Compute",
        "icon": "🧠",
        "badge": "Distributed AI",
        "description": "Decentralized llama.cpp RPC, Petals DHT, and Exo compute node running 70B quantized LLMs across the multi-device mesh.",
        "route": "/apps/lauburu_compute_hub/",
        "port": 4000,
        "features": ["llama.cpp RPC Server", "Petals BitTorrent Sharding", "Dynamic VRAM Pooling", "Zero-Cloud Token Execution"],
        "telemetry_supported": False,
        "installed": True
    },
    {
        "id": "lauburu_grappling_3d",
        "name": "3D Spatial Grappling Kinematics",
        "category": "martial_arts",
        "category_label": "Martial Arts & Kinematics",
        "icon": "🥋",
        "badge": "Biomechanics",
        "description": "Interactive Three.js 3D tatami viewer exploring 955 submission techniques, spatial transitions, and joint torque kinematics.",
        "route": "/apps/spatial_grappling_3d/",
        "port": 5001,
        "features": ["955-Node Technique Hierarchy", "Three.js Inverse Kinematics", "Torque Stress Heatmaps", "Real-Time Pose Estimation"],
        "telemetry_supported": True,
        "installed": True
    },
    {
        "id": "lauburu_termux_daemon",
        "name": "Termux Edge Daemon",
        "category": "infrastructure",
        "category_label": "Infrastructure & Edge",
        "icon": "📱",
        "badge": "Keepalive",
        "description": "Android Termux background daemon maintaining wake-lock, ADB over TCP/IP, and local SQLite telemetry persistence.",
        "route": "/apps/termux_edge_daemon/",
        "port": 8088,
        "features": ["termux-wake-lock", "ADB TCP/IP Port 5555", "Doze Mode Bypass", "Local SQLite Persistence"],
        "telemetry_supported": True,
        "installed": True
    },
    {
        "id": "lauburu_shopify_ai",
        "name": "Shopify AI Merchant",
        "category": "commerce",
        "category_label": "Commerce & Subscription",
        "icon": "🛍️",
        "badge": "Storefront",
        "description": "Automated Shopify storefront assistant managing subscriber tiers, equipment checkout, and crowdsourced compute token billing.",
        "route": "/apps/shopify_ai/",
        "port": 4000,
        "features": ["Storefront GraphQL API", "Customer Account Tokens", "Membership Verification", "Token Economics"],
        "telemetry_supported": False,
        "installed": True
    },
    {
        "id": "lauburu_swarm_dashboard",
        "name": "Swarm Orchestrator & ELO",
        "category": "ai",
        "category_label": "Multi-Agent AI",
        "icon": "🐝",
        "badge": "Multi-Agent",
        "description": "Dynamic Looping Tri-Orchestrator debate dashboard with Stagnation Failsafes on port 3000 evaluating top-tier models (Kimi, Claude 4.6, Gemini 3.7) with ELO governance.",
        "route": "/apps/swarm_dashboard/",
        "port": 3000,
        "features": ["Tri-Orchestrator Protocol", "Canonical JSON ELO Ledger", "Swarm Truth Audit", "Zero-Mock Visual Verification"],
        "telemetry_supported": False,
        "installed": True
    },
    {
        "id": "lauburu_movesense_hub",
        "name": "Movesense 128Hz Ingestion Satellite",
        "category": "biometrics",
        "category_label": "Medical DSP",
        "icon": "💓",
        "badge": "DSP",
        "description": "High-frequency BLE GATT listener streaming 128Hz raw ECG and 9-DoF IMU packets directly to Port 4000.",
        "route": "/apps/movesense_hub/",
        "port": 4000,
        "features": ["128Hz Raw ECG Streaming", "Kamath 20% Artifact Filter", "52Hz IMU Dynamic G", "PTT Blood Pressure"],
        "telemetry_supported": True,
        "installed": True
    },
    {
        "id": "lauburu_hemodynamics_cloud",
        "name": "Hemodynamics & Arterial Cloud",
        "category": "clinical",
        "category_label": "Clinical Biometrics",
        "icon": "🩺",
        "badge": "Blood Pressure",
        "description": "Moens-Korteweg & Bramwell-Hill physics inversion engine calculating continuous SBP, DBP, MAP, and arterial stiffness.",
        "route": "/apps/hemodynamics_cloud/",
        "port": 4000,
        "features": ["Moens-Korteweg Model", "Bramwell-Hill Elasticity", "Cardiac Drift Detection", "Endothelial Reserve Scoring"],
        "telemetry_supported": True,
        "installed": True
    },
    {
        "id": "lauburu_openclaw",
        "name": "OpenClaw Research Agent",
        "category": "ai",
        "category_label": "Autonomous AI",
        "icon": "🦅",
        "badge": "Scout",
        "description": "Autonomous open-source software and hardware market scout analyzing repos and Australian hardware pricing.",
        "route": "/apps/openclaw/",
        "port": 4000,
        "features": ["Open-Source Tool Discovery", "Empirical Price Verification", "Visual UI Auditing", "LoRA Dataset Harvesting"],
        "telemetry_supported": False,
        "installed": True
    },
    {
        "id": "lauburu_memory_sync",
        "name": "Data Memory & Vector Sync",
        "category": "storage",
        "category_label": "Data & Persistence",
        "icon": "💾",
        "badge": "WAL Mode",
        "description": "ACID SQLite WAL mode persistence engine and ChromaDB vector synchronization across the local mesh.",
        "route": "/apps/memory_sync/",
        "port": 4000,
        "features": ["SQLite WAL Mode", "Zero-PII Sanitization", "ChromaDB RAG Vectors", "Automated WAL Checkpoints"],
        "telemetry_supported": True,
        "installed": True
    },
    {
        "id": "lauburu_red_blue_security",
        "name": "Red/Blue Security Suite",
        "category": "security",
        "category_label": "Security & Isolation",
        "icon": "🛡️",
        "badge": "Audit",
        "description": "Continuous penetration testing and hardware isolation auditor enforcing zero source-code leakage and RPC socket encryption.",
        "route": "/apps/security_suite/",
        "port": 4000,
        "features": ["Zero-PII Enforcement", "HMAC Socket Auth", "Cloudflare Tunnel Verification", "RAM Isolation Safeguards"],
        "telemetry_supported": False,
        "installed": True
    },
    {
        "id": "lauburu_lora_evolution",
        "name": "Continuous LoRA Evolution",
        "category": "training",
        "category_label": "AI Training",
        "icon": "🧬",
        "badge": "24/7 LoRA",
        "description": "Continuous local LoRA distillation engine harvesting execution traces and merging Genetic MoE weights.",
        "route": "/apps/lora_evolution/",
        "port": 4000,
        "features": ["24/7 Trace Harvesting", "Loss Tracking", "Genetic MoE Weight Merge", "$0 Cloud Compute Target"],
        "telemetry_supported": False,
        "installed": True
    },
    {
        "id": "lauburu_kinematics_lab",
        "name": "Spatial Kinematics Lab",
        "category": "physics",
        "category_label": "Physics & Biomechanics",
        "icon": "📐",
        "badge": "955-Node OPML",
        "description": "Biomechanical laboratory modeling grappling joint articulation, torque distribution, and kinematic chain dynamics.",
        "route": "/apps/kinematics_lab/",
        "port": 5001,
        "features": ["Joint Torque Vectors", "Angular Velocity DSP", "Submission Counters", "Kinematic Heatmaps"],
        "telemetry_supported": True,
        "installed": True
    },
    {
        "id": "lauburu_nomad_courier",
        "name": "Nomad Courier Mesh Governor",
        "category": "network",
        "category_label": "Mesh & Networking",
        "icon": "🌐",
        "badge": "5-Tier Failover",
        "description": "Autonomous 5-tier self-healing network governor managing ports 3000, 4000, 18802, and 50052 with Wake-on-LAN.",
        "route": "/apps/nomad_courier/",
        "port": 18802,
        "features": ["7-Tier Network Failover", "Port 4000 Watchdog", "Wake-on-LAN Resurrector", "24/7 LoRA Action Logging"],
        "telemetry_supported": False,
        "installed": True
    },
    {
        "id": "lauburu_app_store",
        "name": "Lauburu Port 4000 Hub & Store",
        "category": "hub",
        "category_label": "System Hub",
        "icon": "🏪",
        "badge": "Canonical",
        "description": "Canonical Port 4000 Central Hub providing unified account authentication, telemetry ingestion, and app catalog registry.",
        "route": "/",
        "port": 4000,
        "features": ["Unified PBKDF2 Auth", "Shopify Storefront Sync", "128Hz Movesense Ingestion", "WebSocket Broadcast"],
        "telemetry_supported": True,
        "installed": True
    }
]


# ==================== WebSocket Connection Manager ====================

class ConnectionManager:
    """Manages active live WebSocket subscribers for real-time telemetry broadcast."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            self.active_connections.discard(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        async with self._lock:
            dead_connections = set()
            for connection in self.active_connections:
                try:
                    await connection.send_json(message)
                except Exception:
                    dead_connections.add(connection)
            for dead in dead_connections:
                self.active_connections.discard(dead)


ws_manager = ConnectionManager()


# ==================== Dependency Helpers ====================

async def get_current_user_and_session(
    authorization: Optional[str] = Header(None),
    lauburu_auth_token: Optional[str] = Cookie(None),
    token: Optional[str] = Query(None)
) -> Optional[Dict[str, Any]]:
    """Extract and resolve session token from Header, Cookie, or Query parameter."""
    session_token = None
    if authorization and authorization.startswith("Bearer "):
        session_token = authorization.split(" ")[1].strip()
    elif lauburu_auth_token:
        session_token = lauburu_auth_token.strip()
    elif token:
        session_token = token.strip()

    if not session_token:
        return None

    storage = get_sqlite_manager()
    result = await storage.get_user_and_session(session_token)
    if not result:
        return None

    user, session = result
    return {"user": user, "session": session}


# ==================== API Routes ====================

@app.get("/health", tags=["Health"])
@app.get("/api/health", tags=["Health"])
async def health_check():
    """Health check probe."""
    return {
        "status": "healthy",
        "service": "canonical_port_4000_hub",
        "port": 4000,
        "database": "sqlite_wal",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    }


@app.get("/api/apps", tags=["Catalog"])
async def get_app_catalog():
    """Returns list of all 17 registered applications in the monorepo catalog."""
    return CATALOG_APPS


# ==================== Authentication Endpoints ====================

@app.post("/api/auth/register", status_code=status.HTTP_201_CREATED, tags=["Auth"])
async def register(req: RegisterRequest):
    """
    Registers a new user with PBKDF2 salted password hashing,
    creates an active session, and returns session token and user profile.
    """
    storage = get_sqlite_manager()
    existing = await storage.get_user_by_email(req.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    user = await storage.create_user(
        email=req.email,
        password=req.password,
        name=req.name,
        role=req.role or "user"
    )

    session = await storage.create_session(user_id=user["id"])

    response_data = {
        "token": session["session_token"],
        "session_token": session["session_token"],
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "role": user["role"],
            "membership_tier": user["membership_tier"],
            "is_paid_subscriber": user["is_paid_subscriber"],
            "installed_apps": user["installed_apps"],
            "paired_devices": user["paired_devices"],
            "created_at": user["created_at_epoch"]
        }
    }
    return response_data


@app.post("/api/auth/login", tags=["Auth"])
async def login(req: LoginRequest):
    """
    Authenticates user against stored PBKDF2 password hash and issues a 64-char session token.
    """
    storage = get_sqlite_manager()
    user = await storage.get_user_by_email(req.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    from .storage.sqlite_manager import verify_password
    if not verify_password(user["password_hash"], req.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    session = await storage.create_session(user_id=user["id"])

    return {
        "token": session["session_token"],
        "session_token": session["session_token"],
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "role": user["role"],
            "membership_tier": user["membership_tier"],
            "is_paid_subscriber": user["is_paid_subscriber"],
            "installed_apps": user["installed_apps"],
            "paired_devices": user["paired_devices"],
            "created_at": user["created_at_epoch"]
        }
    }


@app.post("/api/auth/shopify-login", tags=["Auth"])
async def shopify_login(req: ShopifyLoginRequest):
    """
    Authenticates or verifies a customer via Shopify Storefront GraphQL API.
    Auto-provisions local user in SQLite, creates session token, and returns verified tier.
    """
    shopify_service = get_shopify_service()
    storage = get_sqlite_manager()

    shopify_token = req.token
    profile = None

    if shopify_token:
        valid, result = await shopify_service.verify_customer_access_token(shopify_token)
        if not valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=result.get("error", "Invalid or expired Shopify customer token")
            )
        profile = result
    elif req.email and req.password:
        valid, result = await shopify_service.authenticate_customer_credentials(req.email, req.password)
        if not valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=result.get("error", "Shopify customer credentials invalid")
            )
        shopify_token = result.get("token")
        profile = result.get("profile")
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide either Shopify token or email/password"
        )

    # Resolve or create local user record in SQLite
    customer_id = profile.get("customer_id")
    email = profile.get("email", req.email or "shopify_user@lauburu.local")
    name = profile.get("name", "Shopify Customer")
    tier = profile.get("tier", "PAID_PRO")
    is_paid = profile.get("is_paid_subscriber", True)

    user = None
    if customer_id:
        user = await storage.get_user_by_shopify_id(customer_id)
    if not user and email:
        user = await storage.get_user_by_email(email)

    if user:
        # Update user tier if changed
        user = await storage.update_user(
            user_id=user["id"],
            shopify_customer_id=customer_id,
            membership_tier=tier,
            is_paid_subscriber=is_paid
        )
    else:
        user = await storage.create_user(
            email=email,
            password="shopify_managed_account",
            name=name,
            role="user",
            membership_tier=tier,
            shopify_customer_id=customer_id,
            is_paid_subscriber=is_paid
        )

    session = await storage.create_session(user_id=user["id"])

    return {
        "success": True,
        "shopify_access_token": shopify_token,
        "session_token": session["session_token"],
        "profile": profile,
        "membership": {
            "tier": tier,
            "access_granted": True,
            "reason": f"Shopify Active Subscription ({email})"
        }
    }


@app.get("/api/auth/me", tags=["Auth"])
async def get_me(auth_data: Optional[Dict[str, Any]] = Depends(get_current_user_and_session)):
    """
    Resolves session token from Authorization header or cookie.
    Returns user profile and active session.
    """
    if not auth_data:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"authenticated": False, "error": "No active session found"}
        )

    user = auth_data["user"]
    session = auth_data["session"]
    return {
        "authenticated": True,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "role": user["role"],
            "membership_tier": user["membership_tier"],
            "is_paid_subscriber": user["is_paid_subscriber"],
            "installed_apps": user["installed_apps"],
            "paired_devices": user["paired_devices"],
            "created_at": user["created_at_epoch"]
        },
        "session": session
    }


# ==================== Telemetry & Sensor Endpoints ====================

@app.post("/api/sensors/ingest", tags=["Telemetry"])
async def ingest_sensor_telemetry(req: TelemetryIngestRequest):
    """
    Ingests live 128Hz Movesense/Polar BLE telemetry, performs real-time DSP
    (Kamath 20% filter, RMSSD, DFA-α1 zone, PTT blood pressure), persists tick
    to SQLite WAL under the user's session_token, and broadcasts frame over WebSockets.
    """
    telemetry_service = get_telemetry_service()
    payload = req.model_dump()
    result = await telemetry_service.ingest_telemetry_payload(payload)

    # Broadcast live tick to connected WebSocket clients
    now_ms = int(time.time() * 1000)
    broadcast_frame = {
        "type": "live_telemetry_broadcast",
        "timestamp_epoch_ms": payload.get("epoch_ms") or now_ms,
        "session_token": req.session_token,
        "sensor_type": req.sensor_type,
        "biometrics": {
            "heart_rate_bpm": req.heart_rate,
            "rr_interval_ms": req.rr_intervals_ms,
            "rmssd_ms": result["dsp_summary"]["rmssd_ms"],
            "dfa_alpha1": result["dsp_summary"]["dfa_alpha1"],
            "training_zone": result["dsp_summary"]["training_zone"],
            "zone_color": result["dsp_summary"]["zone_color"],
            "sbp_calc": result["dsp_summary"]["sbp_calc"],
            "dbp_calc": result["dsp_summary"]["dbp_calc"],
            "map_calc": result["dsp_summary"]["map_calc"]
        },
        "kinematics": {
            "total_dynamic_g": result["dsp_summary"]["total_dynamic_g"]
        }
    }
    asyncio.create_task(ws_manager.broadcast(broadcast_frame))

    return result


@app.get("/api/sensors/status", tags=["Telemetry"])
async def get_sensor_status():
    """
    Zero-mock sensor status probe: disconnected sensors strictly return
    connected: false and heart_rate: null.
    """
    telemetry_service = get_telemetry_service()
    return telemetry_service.get_sensor_status()


# ==================== Session & Trend Insights Endpoints ====================

@app.get("/api/sessions/{session_token}", tags=["Sessions"])
async def get_session_details(session_token: str):
    """Retrieves session summary statistics and user information."""
    storage = get_sqlite_manager()
    summary = await storage.get_session_summary(session_token)
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    return summary


@app.get("/api/sessions/{session_token}/ticks", tags=["Sessions"])
async def get_session_ticks(
    session_token: str,
    limit: int = Query(1000, ge=1, le=10000),
    offset: int = Query(0, ge=0)
):
    """Retrieves historical telemetry ticks for a session."""
    storage = get_sqlite_manager()
    ticks = await storage.get_session_ticks(session_token, limit=limit, offset=offset)
    return {"session_token": session_token, "count": len(ticks), "ticks": ticks}


@app.post("/api/sessions/{session_token}/trends", status_code=status.HTTP_201_CREATED, tags=["Sessions"])
async def log_session_trend(session_token: str, req: TrendInsightRequest):
    """Logs a trend insight evaluation for a session."""
    storage = get_sqlite_manager()
    now_ms = req.timestamp_epoch_ms or int(time.time() * 1000)
    insight_id = await storage.log_trend_insight(
        session_token=session_token,
        timestamp_epoch_ms=now_ms,
        window_size_sec=req.window_size_sec,
        arterial_stiffness_drift_pct=req.arterial_stiffness_drift_pct,
        vascular_fatigue_index=req.vascular_fatigue_index,
        cardiac_drift_detected=req.cardiac_drift_detected,
        endothelial_reserve_status=req.endothelial_reserve_status,
        zone2_compliance=req.zone2_compliance
    )
    return {"status": "success", "insight_id": insight_id, "session_token": session_token}


@app.get("/api/sessions/{session_token}/trends", tags=["Sessions"])
async def get_session_trends(session_token: str, limit: int = Query(100, ge=1, le=500)):
    """Retrieves trend insights for a session."""
    storage = get_sqlite_manager()
    trends = await storage.get_trend_insights(session_token, limit=limit)
    return {"session_token": session_token, "count": len(trends), "insights": trends}


# ==================== WebSocket Telemetry Streaming ====================

@app.websocket("/ws/telemetry")
async def websocket_telemetry_endpoint(websocket: WebSocket):
    """
    Bidirectional WebSocket stream for live high-frequency telemetry frames.
    Accepts push_tick actions and broadcasts live_telemetry_broadcast frames.
    """
    await ws_manager.connect(websocket)
    telemetry_service = get_telemetry_service()
    try:
        while True:
            raw_text = await websocket.receive_text()
            try:
                data = json.loads(raw_text)
            except Exception:
                continue

            action = data.get("action")
            if action == "push_tick" or "tick" in data:
                tick_data = data.get("tick", data)
                session_token = data.get("session_token") or tick_data.get("session_token")
                sensor_type = tick_data.get("sensor_type", "movesense")

                # Ingest through telemetry service
                ingest_payload = {
                    "session_token": session_token,
                    "sensor_type": sensor_type,
                    "heart_rate": tick_data.get("hr_bpm") or tick_data.get("heart_rate"),
                    "rr_intervals_ms": tick_data.get("rr_ms") or tick_data.get("rr_intervals_ms"),
                    "rmssd": tick_data.get("rmssd"),
                    "dfa_alpha1": tick_data.get("dfa_alpha1"),
                    "ecg_mv": tick_data.get("ecg_sample") or tick_data.get("ecg_mv"),
                    "acc_g": tick_data.get("accel") or tick_data.get("acc_g"),
                    "skin_temp_c": tick_data.get("skin_temp_c"),
                    "ptt_ms": tick_data.get("ptt_ms"),
                    "delta_time_ms": tick_data.get("delta_time_ms") or 0,
                    "epoch_ms": tick_data.get("epoch_ms") or int(time.time() * 1000)
                }
                res = await telemetry_service.ingest_telemetry_payload(ingest_payload)

                # Broadcast live frame
                broadcast_frame = {
                    "type": "live_telemetry_broadcast",
                    "timestamp_epoch_ms": ingest_payload["epoch_ms"],
                    "session_token": session_token,
                    "sensor_type": sensor_type,
                    "biometrics": {
                        "heart_rate_bpm": ingest_payload["heart_rate"],
                        "rr_interval_ms": ingest_payload["rr_intervals_ms"],
                        "rmssd_ms": res["dsp_summary"]["rmssd_ms"],
                        "dfa_alpha1": res["dsp_summary"]["dfa_alpha1"],
                        "training_zone": res["dsp_summary"]["training_zone"],
                        "zone_color": res["dsp_summary"]["zone_color"],
                        "sbp_calc": res["dsp_summary"]["sbp_calc"],
                        "dbp_calc": res["dsp_summary"]["dbp_calc"],
                        "map_calc": res["dsp_summary"]["map_calc"]
                    },
                    "kinematics": {
                        "total_dynamic_g": res["dsp_summary"]["total_dynamic_g"]
                    }
                }
                await ws_manager.broadcast(broadcast_frame)

            elif action == "ping":
                await websocket.send_json({"action": "pong", "timestamp": int(time.time() * 1000)})

    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    except Exception as e:
        logger.warning("WebSocket client encounter error: %s", str(e))
        await ws_manager.disconnect(websocket)



# ==================== In-App Edge AI & Micro-RAG Endpoints ====================

@app.post("/api/edge/chat", tags=["Edge AI"])
async def edge_chat_endpoint(req: EdgeChatRequest):
    """
    In-App Multipurpose Edge AI Chat Endpoint.
    Uses local SmolLM2 1.7B with Micro-RAG on Obsidian vault notes,
    automated network/device health inspection, and smart mesh escalation to Port 8081.
    """
    edge_service = get_edge_ai_service()
    result = await edge_service.chat(
        message=req.message,
        history=req.history,
        device_profile=req.device_profile
    )
    return result


@app.get("/api/edge/health", tags=["Edge AI"])
async def edge_health_endpoint():
    """Returns live hardware memory/CPU and mesh speedway latencies."""
    edge_service = get_edge_ai_service()
    return edge_service.get_health_status()


@app.post("/api/edge/maintenance", tags=["Edge AI"])
async def edge_maintenance_endpoint(req: Optional[EdgeMaintenanceRequest] = None):
    """Triggers autonomous on-device self-healing and cache optimization."""
    edge_service = get_edge_ai_service()
    return edge_service.execute_maintenance()


@app.get("/api/edge/rag/search", tags=["Edge AI"])
async def edge_rag_search_endpoint(q: str = Query(..., description="Query to search across local vault")):
    """Searches local Obsidian vault documentation via Micro-RAG."""
    edge_service = get_edge_ai_service()
    hits = edge_service.search_local_rag(q)
    return {"query": q, "count": len(hits), "results": hits}


@app.websocket("/ws/edge_chat")
async def websocket_edge_chat(websocket: WebSocket):
    """WebSocket endpoint for real-time streaming edge chat with local RAG."""
    await websocket.accept()
    edge_service = get_edge_ai_service()
    try:
        while True:
            raw_text = await websocket.receive_text()
            try:
                data = json.loads(raw_text)
            except Exception:
                continue

            user_msg = data.get("message", "")
            history = data.get("history", [])
            device = data.get("device", {})

            result = await edge_service.chat(user_msg, history, device)
            await websocket.send_json({"type": "edge_response", **result})
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning("WebSocket edge chat error: %s", str(e))


from fastapi.responses import HTMLResponse

@app.get("/", response_class=HTMLResponse, tags=["Dashboard"])
async def root_dashboard_view():
    """Serves the canonical Port 4000 Hub interactive web UI with the integrated In-App Edge AI Assistant."""
    html_content = """<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lauburu Port 4000 Canonical Web & Compute Hub</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    colors: {
                        brand: { 500: '#6366f1', 600: '#4f46e5', 700: '#4338ca' }
                    }
                }
            }
        }
    </script>
    <style>
        body { background-color: #0b0f19; color: #f3f4f6; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        .glass { background: rgba(17, 24, 39, 0.75); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.08); }
    </style>
</head>
<body class="min-h-screen p-4 md:p-8 flex flex-col">
    <!-- Header -->
    <header class="glass rounded-2xl p-6 mb-6 flex flex-wrap items-center justify-between gap-4">
        <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center text-xl font-bold">⚡</div>
            <div>
                <h1 class="text-xl font-bold tracking-tight">Lauburu Port 4000 Hub</h1>
                <p class="text-xs text-gray-400">Canonical Monorepo Client, 128Hz BLE Telemetry & Multipurpose Edge AI</p>
            </div>
        </div>
        <div class="flex items-center gap-3">
            <span id="node-status" class="px-3 py-1 text-xs rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 flex items-center gap-1.5">
                <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span> Port 4000 Hub Online
            </span>
            <button onclick="runMaintenance()" class="px-3 py-1.5 text-xs font-medium rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-200 border border-gray-700 transition">
                🔧 Self-Heal & Maintain
            </button>
        </div>
    </header>

    <!-- Main Grid -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 flex-1">
        <!-- Left: Telemetry & System Health (5 cols) -->
        <div class="lg:col-span-5 flex flex-col gap-6">
            <!-- System & Network Health Card -->
            <div class="glass rounded-2xl p-6 flex-1">
                <h2 class="text-sm font-semibold uppercase tracking-wider text-gray-400 mb-4 flex items-center gap-2">
                    <span>🩺</span> Hardware & Mesh Speedway
                </h2>
                <div class="grid grid-cols-2 gap-3 mb-4">
                    <div class="p-3.5 rounded-xl bg-gray-800/60 border border-gray-700/50">
                        <div class="text-xs text-gray-400">Memory (RAM)</div>
                        <div id="stat-ram" class="text-lg font-bold text-indigo-400">--</div>
                    </div>
                    <div class="p-3.5 rounded-xl bg-gray-800/60 border border-gray-700/50">
                        <div class="text-xs text-gray-400">CPU Load</div>
                        <div id="stat-cpu" class="text-lg font-bold text-emerald-400">--</div>
                    </div>
                </div>
                <div class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Active Mesh Latencies</div>
                <div id="network-matrix" class="space-y-2 text-xs">
                    <div class="p-2 rounded-lg bg-gray-900/50 text-gray-400">Scanning mesh nodes...</div>
                </div>
            </div>

            <!-- Biometrics & Readiness -->
            <div class="glass rounded-2xl p-6">
                <h2 class="text-sm font-semibold uppercase tracking-wider text-gray-400 mb-3 flex items-center gap-2">
                    <span>💓</span> Movesense 128Hz Ingestion
                </h2>
                <div class="flex items-center justify-between p-3 rounded-xl bg-gray-800/40 border border-gray-700/40 mb-3">
                    <div>
                        <div class="text-xs text-gray-400">Heart Rate (Kamath 20% Filter)</div>
                        <div id="stat-hr" class="text-2xl font-bold text-rose-400">-- <span class="text-xs text-gray-400">BPM</span></div>
                    </div>
                    <div class="text-right">
                        <div class="text-xs text-gray-400">Zone 2 Aerobic (DFA-α1)</div>
                        <div id="stat-zone2" class="text-sm font-semibold text-emerald-400">Optimal</div>
                    </div>
                </div>
                <div class="text-[11px] text-gray-500">Zero-Mock Rule #0 Enforced. Clean standby when sensors are disconnected.</div>
            </div>
        </div>

        <!-- Right: In-App Multipurpose Edge AI Chat (7 cols) -->
        <div class="lg:col-span-7 glass rounded-2xl p-6 flex flex-col flex-1">
            <div class="flex items-center justify-between mb-4 pb-3 border-b border-gray-800">
                <div class="flex items-center gap-2">
                    <span class="text-base">🤖</span>
                    <div>
                        <h2 class="text-sm font-bold text-gray-200">In-App Multipurpose Edge AI</h2>
                        <p class="text-[11px] text-gray-400">SmolLM2 1.7B (&le;0.98 GB RAM) • Micro-RAG • Mesh Escalation</p>
                    </div>
                </div>
                <span class="text-[11px] px-2.5 py-0.5 rounded-full bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
                    Sovereign Edge
                </span>
            </div>

            <!-- Messages Log -->
            <div id="chat-box" class="flex-1 overflow-y-auto space-y-3 p-3 rounded-xl bg-gray-900/60 border border-gray-800 text-xs min-h-[280px] max-h-[420px]">
                <div class="p-3 rounded-lg bg-gray-800/60 border border-gray-700/40 text-gray-300">
                    👋 <b>Lauburu Edge AI Assistant Online!</b> Ask about system health, execute network maintenance, search local Obsidian notes, or write code.
                </div>
            </div>

            <!-- Input Bar -->
            <form onsubmit="handleChatSubmit(event)" class="mt-4 flex gap-2">
                <input id="chat-input" type="text" placeholder="Type prompt (e.g. 'Check network and RAM' or 'Search storage rule')..." 
                       class="flex-1 bg-gray-800 border border-gray-700 rounded-xl px-4 py-2.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition">
                <button type="submit" class="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold shadow-lg shadow-indigo-600/30 transition">
                    Send
                </button>
            </form>
        </div>
    </div>

    <!-- Client Script -->
    <script>
        async function fetchHealth() {
            try {
                const res = await fetch('/api/edge/health');
                const data = await res.json();
                document.getElementById('stat-ram').innerText = `${data.device.ram_used_gb} / ${data.device.ram_total_gb} GB (${data.device.ram_percent}%)`;
                document.getElementById('stat-cpu').innerText = `${data.device.cpu_percent}%`;

                const matrixDiv = document.getElementById('network-matrix');
                matrixDiv.innerHTML = '';
                for (const [target, info] of Object.entries(data.network)) {
                    const rtt = info.rtt_ms ? `${info.rtt_ms} ms` : 'Offline';
                    const isOk = info.status === 'ONLINE';
                    matrixDiv.innerHTML += `
                        <div class="flex items-center justify-between p-2 rounded-lg bg-gray-800/40 border border-gray-700/30">
                            <span class="font-mono text-gray-300">${target}</span>
                            <span class="font-semibold ${isOk ? 'text-emerald-400' : 'text-gray-500'}">${info.status} (${rtt})</span>
                        </div>
                    `;
                }
            } catch (e) {
                console.error(e);
            }
        }

        async function runMaintenance() {
            const btn = event.target;
            btn.innerText = '⏳ Healing...';
            try {
                const res = await fetch('/api/edge/maintenance', { method: 'POST' });
                const data = await res.json();
                alert(`Maintenance: ${data.actions_executed.join(' | ')}`);
            } catch (e) {
                alert('Maintenance error: ' + e);
            } finally {
                btn.innerText = '🔧 Self-Heal & Maintain';
                fetchHealth();
            }
        }

        async function handleChatSubmit(e) {
            e.preventDefault();
            const input = document.getElementById('chat-input');
            const msg = input.value.trim();
            if (!msg) return;

            const chatBox = document.getElementById('chat-box');
            chatBox.innerHTML += `<div class="p-2.5 rounded-lg bg-indigo-600/30 border border-indigo-500/30 text-indigo-200 self-end text-right"><b>You:</b> ${msg}</div>`;
            input.value = '';
            chatBox.scrollTop = chatBox.scrollHeight;

            const typingId = 'typing-' + Date.now();
            chatBox.innerHTML += `<div id="${typingId}" class="p-2.5 rounded-lg bg-gray-800/40 text-gray-400 animate-pulse">Thinking on-device...</div>`;
            chatBox.scrollTop = chatBox.scrollHeight;

            try {
                const res = await fetch('/api/edge/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: msg })
                });
                const data = await res.json();
                document.getElementById(typingId)?.remove();

                const ragBadge = data.rag_used ? `<span class="px-1.5 py-0.5 rounded text-[10px] bg-purple-500/20 text-purple-300 border border-purple-500/30 mr-1">RAG: ${data.rag_sources.join(', ')}</span>` : '';
                const escBadge = data.escalated ? `<span class="px-1.5 py-0.5 rounded text-[10px] bg-amber-500/20 text-amber-300 border border-amber-500/30 mr-1">Cluster Master :8081</span>` : `<span class="px-1.5 py-0.5 rounded text-[10px] bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 mr-1">Local Edge</span>`;

                chatBox.innerHTML += `
                    <div class="p-3 rounded-lg bg-gray-800/70 border border-gray-700/50 text-gray-200">
                        <div class="flex items-center gap-1 mb-1.5">${escBadge}${ragBadge}<span class="text-[10px] text-gray-400">(${data.latency_ms}ms)</span></div>
                        <div class="whitespace-pre-wrap leading-relaxed">${data.response}</div>
                    </div>
                `;
            } catch (err) {
                document.getElementById(typingId)?.remove();
                chatBox.innerHTML += `<div class="p-2.5 rounded-lg bg-rose-500/20 text-rose-300">Error processing edge query.</div>`;
            }
            chatBox.scrollTop = chatBox.scrollHeight;
        }

        fetchHealth();
        setInterval(fetchHealth, 15000);
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)


# ==================== CLI Entrypoint ====================

if __name__ == "__main__":
    import uvicorn
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "4000"))
    uvicorn.run(app, host=host, port=port, log_level="info")


# ==================== GL.iNet Router Proxy ====================
import httpx
from starlette.requests import Request
from starlette.responses import StreamingResponse, Response

@app.api_route("/proxy/router/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def router_proxy(request: Request, path: str):
    """
    Reverse proxy for the GL.iNet admin panel (192.168.8.1).
    Strips X-Frame-Options to allow embedding into the Swarm Dashboard.
    """
    router_ip = "192.168.8.1"
    url = f"http://{router_ip}/{path}?{request.url.query}"
    
    # Forward the exact headers but drop host
    headers = dict(request.headers)
    headers.pop("host", None)
    
    async def stream_response():
        async with httpx.AsyncClient() as client:
            req = client.build_request(
                request.method,
                url,
                headers=headers,
                content=await request.body()
            )
            async with client.stream(req.method, req.url, **{"headers": req.headers, "content": req.content}) as response:
                yield response.content # A simple stream

    # Using standard httpx async forwarding
    async with httpx.AsyncClient() as client:
        res = await client.request(
            request.method,
            url,
            headers=headers,
            content=await request.body(),
            follow_redirects=True
        )
        
    # Strip security headers to allow <iframe> embedding
    resp_headers = dict(res.headers)
    resp_headers.pop("x-frame-options", None)
    resp_headers.pop("content-security-policy", None)
    
    return Response(content=res.content, status_code=res.status_code, headers=resp_headers)
