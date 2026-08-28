"""
Data models and request/response schemas.
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field, field_validator


class TransitHemodynamics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ptt_ms: float = Field(..., ge=10.0, le=2000.0, description="Pulse transit time in ms")
    pat_ms: float = Field(default=0.0, ge=0.0, le=3000.0, description="Pulse Arrival Time in milliseconds")
    ptt_rr_ratio: float = Field(default=0.0, ge=0.0, le=5.0, description="Ratio of PTT to RR interval")


class CardiacAutonomic(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hr_bpm: float = Field(..., ge=20.0, le=300.0, description="Heart rate in bpm")
    hr_acceleration_bpm_s: float = Field(default=0.0, description="Heart Rate acceleration")
    hrv_rmssd_ms: float = Field(default=0.0, ge=0.0, le=1000.0, description="HRV RMSSD in milliseconds")
    hrv_sdnn_ms: float = Field(default=0.0, ge=0.0, le=1000.0, description="HRV SDNN in milliseconds")
    dfa_alpha1: float = Field(default=1.0, ge=0.0, le=3.0, description="Detrended Fluctuation Analysis alpha 1")


class VascularMorphology(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stiffness_index_m_s: float = Field(default=6.5, ge=0.5, le=50.0, description="Arterial stiffness index (m/s)")
    reflection_index_pct: float = Field(default=55.0, ge=0.0, le=100.0, description="Pulse reflection index (%)")
    aging_index: float = Field(default=-0.25, ge=-2.0, le=2.0, description="Vascular aging index")
    elasticity_baseline_e0: float = Field(default=1.0, ge=0.01, le=100.0, description="Dimensionless normalized elasticity modulus")


class BiomechanicalContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    imu_acc_variance_g2: float = Field(default=0.0, ge=0.0, le=50.0, description="IMU acceleration variance in g^2")
    pedal_power_watts: float = Field(default=0.0, ge=0.0, le=3000.0, description="Cycling power in watts")
    cadence_rpm: float = Field(default=0.0, ge=0.0, le=300.0, description="Cadence in RPM")
    power_to_hr_ratio: float = Field(default=0.0, ge=0.0, le=50.0, description="Power to HR ratio")


class ZeroPiiTelemetryVector(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transit_hemodynamics: TransitHemodynamics
    cardiac_autonomic: CardiacAutonomic
    vascular_morphology: VascularMorphology = Field(default_factory=VascularMorphology)
    biomechanical_context: BiomechanicalContext = Field(default_factory=BiomechanicalContext)


class VectorU(BaseModel):
    """Direct 6D telemetry vector u = [PTT, HR, RR, Delta_T_dia, ||a_IMU||, E_0]."""
    model_config = ConfigDict(extra="forbid")

    ptt_ms: float = Field(..., ge=10.0, le=2000.0, description="Pulse transit time in ms")
    hr_bpm: float = Field(..., ge=20.0, le=300.0, description="Heart rate in bpm")
    rr_ms: float = Field(default=800.0, ge=100.0, le=3000.0, description="R-R interval in ms")
    delta_t_dia_ms: float = Field(default=280.0, ge=20.0, le=2000.0, description="Diastolic decay time in ms")
    imu_acc_g: float = Field(default=1.0, ge=0.0, le=30.0, description="IMU acceleration magnitude in g")
    e0_elasticity: float = Field(default=400.0, ge=10.0, le=50000.0, description="Elastic modulus in kPa")


class InversionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    protocol_version: str = Field(default="1.0.0", description="Protocol version")
    session_token: str = Field(..., description="64-char HMAC-SHA256 session token")
    delta_time_ms: int = Field(default=0, ge=0, description="Session elapsed time in milliseconds")
    telemetry_vector: Optional[ZeroPiiTelemetryVector] = None
    vector_u: Optional[VectorU] = None

    @field_validator("session_token")
    def validate_token(cls, v: str) -> str:
        v_clean = v.strip()
        if len(v_clean) != 64:
            raise ValueError("session_token must be a 64-character hex SHA-256 string")
        try:
            int(v_clean, 16)
        except ValueError:
            raise ValueError("session_token must be a hexadecimal string")
        return v_clean


# Alias for Zero-PII payload contract
ZeroPiiPayload = InversionRequest


class BatchInversionTick(BaseModel):
    model_config = ConfigDict(extra="forbid")

    delta_time_ms: int = Field(default=0, ge=0)
    telemetry_vector: Optional[ZeroPiiTelemetryVector] = None
    vector_u: Optional[VectorU] = None


class BatchInversionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    protocol_version: str = Field(default="1.0.0")
    session_token: str = Field(..., description="64-char HMAC-SHA256 session token")
    ticks: List[BatchInversionTick] = Field(..., min_length=1)

    @field_validator("session_token")
    def validate_token(cls, v: str) -> str:
        v_clean = v.strip()
        if len(v_clean) != 64:
            raise ValueError("session_token must be a 64-character hex SHA-256 string")
        try:
            int(v_clean, 16)
        except ValueError:
            raise ValueError("session_token must be a hexadecimal string")
        return v_clean


class HemodynamicEdgeState(BaseModel):
    systolic_bp_mmHg: float = Field(..., description="Systolic Blood Pressure in mmHg")
    diastolic_bp_mmHg: float = Field(..., description="Diastolic Blood Pressure in mmHg")
    mean_arterial_pressure_mmHg: float = Field(..., description="Mean Arterial Pressure in mmHg")
    pulse_pressure_mmHg: float = Field(..., description="Pulse Pressure in mmHg")
    arterial_compliance: float = Field(..., description="Arterial compliance (mL/mmHg)")
    vascular_resistance: float = Field(..., description="Systemic Vascular Resistance (mmHg*s/mL)")
    pwv_m_s: float = Field(..., description="Pulse Wave Velocity in m/s")
    confidence_score: float = Field(..., description="Confidence score [0.0 - 1.0]")


class TrendHuntingInsights(BaseModel):
    arterial_stiffness_drift_pct: float = Field(default=0.0, description="Stiffness drift percentage")
    vascular_fatigue_index: float = Field(default=0.0, description="Vascular fatigue index [0-1]")
    endothelial_reserve_status: str = Field(default="optimal", description="Reserve status: optimal / strained / exhausted")
    cardiac_drift_detected: bool = Field(default=False, description="Whether cardiovascular drift is present")
    zone2_compliance: str = Field(default="in_zone2_aerobic", description="Zone 2 compliance status")


class ZeroPiiEdgeResponse(BaseModel):
    protocol_version: str = "1.0.0"
    session_token: str
    delta_time_ms: int
    hemodynamic_state: HemodynamicEdgeState
    trend_hunting_insights: TrendHuntingInsights


class BatchInversionResponse(BaseModel):
    protocol_version: str = "1.0.0"
    session_token: str
    total_processed: int
    results: List[ZeroPiiEdgeResponse]


class SessionInitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_nonce: Optional[str] = None


class SessionInitResponse(BaseModel):
    session_token: str
    status: str = "initialized"
    created_at_epoch_ms: int


class SessionSummaryResponse(BaseModel):
    session_hash: str
    created_at_epoch_ms: int
    updated_at_epoch_ms: int
    duration_sec: int
    total_ticks: int
    mean_sbp: float
    mean_dbp: float
    mean_map: float
    mean_hr: float
    mean_rmssd: float
    cardiac_drift_detected: bool
    zone2_compliance_ratio: float
    status: str


class RagQueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_token: str = Field(..., description="64-character hex HMAC-SHA256 session token")
    query: str = Field(..., min_length=1, max_length=2000, description="User question")
    top_k: int = Field(default=3, ge=1, le=20, description="Number of historical session matches to retrieve")
    include_historical_context: bool = Field(default=True, description="Whether to perform RAG vector retrieval")
    filter_session_hash: Optional[str] = Field(default=None, description="Optional filter for specific session hash")
    telemetry_context: Optional[Dict[str, Any]] = Field(default=None, description="Optional live telemetry snapshot")
    image_payload_b64: Optional[str] = Field(default=None, description="Optional base64 ECG/PPG image payload for Qwen3-VL")

    @field_validator("session_token")
    def validate_token(cls, v: str) -> str:
        v_clean = v.strip()
        if len(v_clean) != 64:
            raise ValueError("session_token must be a 64-character hex SHA-256 string")
        try:
            int(v_clean, 16)
        except ValueError:
            raise ValueError("session_token must be a hexadecimal string")
        return v_clean


class RagQueryResultItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document: str = Field(..., description="Indexed session summary text")
    session_hash: str = Field(..., description="Anonymized session hash")
    score: float = Field(..., ge=-1.0, le=1.0, description="Cosine similarity score")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Session metadata")


class RagQueryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    selected_expert_model: str
    expert_rationale: str
    endpoint_url: Optional[str] = None
    results: List[RagQueryResultItem]
    injected_prompt_preview: Optional[str] = None
    executed_response: Optional[str] = None
    latency_ms: float = Field(default=0.0)


class IndexSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_token: str = Field(..., description="64-character hex HMAC-SHA256 session token")
    session_hash: str = Field(..., description="Anonymized session hash")
    document_text: Optional[str] = Field(None, description="Optional custom summary text")
    summary_metadata: Optional[Dict[str, Any]] = Field(None, description="Optional custom metadata")

    @field_validator("session_token")
    def validate_token(cls, v: str) -> str:
        v_clean = v.strip()
        if len(v_clean) != 64:
            raise ValueError("session_token must be a 64-character hex SHA-256 string")
        try:
            int(v_clean, 16)
        except ValueError:
            raise ValueError("session_token must be a hexadecimal string")
        return v_clean


class IndexSessionResponse(BaseModel):
    status: str = "indexed"
    session_hash: str
    document_indexed: str


class DiagnosticTelemetryContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ptt_ms: Optional[float] = Field(None, ge=10.0, le=2000.0, description="Pulse transit time in ms")
    hr_bpm: Optional[float] = Field(None, ge=20.0, le=300.0, description="Heart rate in bpm")
    rr_ms: Optional[float] = Field(None, ge=100.0, le=3000.0, description="RR inter-beat interval in ms")
    delta_t_dia_ms: Optional[float] = Field(None, ge=20.0, le=2000.0, description="Diastolic decay time in ms")
    imu_acc_g: Optional[float] = Field(None, ge=0.0, le=30.0, description="IMU acceleration magnitude in g")
    e0_elasticity: Optional[float] = Field(None, ge=10.0, le=50000.0, description="Elastic modulus in kPa")
    sbp_mmHg: Optional[float] = Field(None, ge=50.0, le=300.0, description="Systolic Blood Pressure in mmHg")
    dbp_mmHg: Optional[float] = Field(None, ge=30.0, le=200.0, description="Diastolic Blood Pressure in mmHg")
    power_watts: Optional[float] = Field(None, ge=0.0, le=3000.0, description="Cycling power in Watts")
    cadence_rpm: Optional[float] = Field(None, ge=0.0, le=300.0, description="Cadence in RPM")
    dfa_alpha1: Optional[float] = Field(None, ge=0.0, le=3.0, description="DFA alpha-1 threshold")
    rmssd_ms: Optional[float] = Field(None, ge=0.0, le=1000.0, description="HRV RMSSD in ms")
    cardiovascular_drift_pct: Optional[float] = Field(None, ge=-100.0, le=100.0, description="Observed cardiac drift %")


class DiagnosticStreamRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    protocol_version: str = Field(default="1.0.0", description="Protocol contract version")
    session_token: str = Field(..., description="64-character hex HMAC-SHA256 session token")
    query: str = Field(..., min_length=1, max_length=2000, description="User exercise physiology query")
    telemetry_context: Optional[Union[DiagnosticTelemetryContext, Dict[str, Any]]] = None
    target_model: Optional[str] = Field(None, description="Optional explicit Genetic MoE model override")
    include_thinking: bool = Field(default=True, description="Whether to stream thinking_delta events")
    top_k_rag: int = Field(default=3, ge=0, le=10, description="Number of historical session context chunks")
    image_payload_b64: Optional[str] = Field(default=None, description="Optional base64 ECG/PPG image payload")

    @field_validator("session_token")
    def validate_token(cls, v: str) -> str:
        v_clean = v.strip()
        if len(v_clean) != 64:
            raise ValueError("session_token must be a 64-character hex SHA-256 string")
        try:
            int(v_clean, 16)
        except ValueError:
            raise ValueError("session_token must be a hexadecimal string")
        return v_clean


class HealthStatusResponse(BaseModel):
    status: str
    version: str
    physics_engine_ready: bool
    sqlite_status: str
    chromadb_status: str
    uptime_seconds: float

