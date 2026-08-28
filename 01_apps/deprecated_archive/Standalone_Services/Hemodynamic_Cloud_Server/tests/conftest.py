"""
Pytest fixtures and test client configuration.
"""

import os
import shutil
import tempfile
import pytest
from starlette.testclient import TestClient

from app.core.config import settings
from app.core.security import generate_session_token
from app.main import app
from app.storage.sqlite_manager import SqliteManager, get_sqlite_manager
from app.storage.chroma_manager import ChromaManager, get_chroma_manager
from app.services.inversion_service import InversionService
from app.services.trend_hunting_service import TrendHuntingService


@pytest.fixture(scope="session")
def temp_test_dir():
    temp_dir = tempfile.mkdtemp(prefix="hemodynamic_test_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sqlite_test_db(temp_test_dir):
    db_path = os.path.join(temp_test_dir, f"test_sessions_{os.urandom(4).hex()}.db")
    mgr = SqliteManager(db_path=db_path)
    yield mgr


@pytest.fixture
def chroma_test_store(temp_test_dir):
    persist_dir = os.path.join(temp_test_dir, f"test_chroma_{os.urandom(4).hex()}")
    mgr = ChromaManager(persist_dir=persist_dir)
    yield mgr


@pytest.fixture
def client(sqlite_test_db, chroma_test_store):
    from app.api import deps
    app.dependency_overrides[deps.get_db] = lambda: sqlite_test_db
    app.dependency_overrides[deps.get_vector_store] = lambda: chroma_test_store
    app.dependency_overrides[deps.get_inversion] = lambda: InversionService(
        sqlite_manager=sqlite_test_db,
        trend_service=TrendHuntingService()
    )
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_session_token():
    return generate_session_token()


@pytest.fixture
def sample_valid_vector_u():
    return {
        "ptt_ms": 224.5,
        "hr_bpm": 138.0,
        "rr_ms": 435.0,
        "delta_t_dia_ms": 280.0,
        "imu_acc_g": 1.12,
        "e0_elasticity": 400.0
    }


@pytest.fixture
def sample_valid_telemetry_vector():
    return {
        "transit_hemodynamics": {
            "ptt_ms": 224.5,
            "pat_ms": 254.5,
            "ptt_rr_ratio": 0.51
        },
        "cardiac_autonomic": {
            "hr_bpm": 138.0,
            "hr_acceleration_bpm_s": 0.2,
            "hrv_rmssd_ms": 32.5,
            "hrv_sdnn_ms": 45.0,
            "dfa_alpha1": 0.88
        },
        "vascular_morphology": {
            "stiffness_index_m_s": 6.8,
            "reflection_index_pct": 58.0,
            "aging_index": -0.22,
            "elasticity_baseline_e0": 1.05
        },
        "biomechanical_context": {
            "imu_acc_variance_g2": 0.04,
            "pedal_power_watts": 185.0,
            "cadence_rpm": 90.0,
            "power_to_hr_ratio": 1.34
        }
    }
