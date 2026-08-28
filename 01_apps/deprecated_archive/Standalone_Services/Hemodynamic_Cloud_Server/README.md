# Private Cloud Hemodynamic Inversion & Zero-PII Telemetry Server

High-performance Python/FastAPI microservice executing server-side non-linear Moens-Korteweg, Bramwell-Hill, and Windkessel (WK2/WK3) hemodynamic inversions with Zero-PII cryptographic session tokenization, SQLite WAL storage, and ChromaDB vector retrieval for Genetic MoE Hierarchical RAG.

## Architecture

1. **Proprietary Hemodynamic Math & IP Obfuscation**:
   - Moens-Korteweg hydrodynamic wave speed $PWV_0 = \sqrt{\frac{E_0 h}{\rho D}}$
   - Hughes non-linear strain-stiffening $E(P) = E_0 e^{\gamma P}$
   - Bramwell-Hill volumetric distensibility $D_v = \frac{1}{\rho PWV^2}$ and compliance $C_{\text{art}} = \frac{V_0}{\rho PWV^2}$
   - Windkessel (WK2/WK3) analytical diastolic decay $\tau = R_p C = \frac{\Delta T_{\text{dia}}}{\ln(P_{\text{notch}}/DBP)}$ and numerical ODE solvers (Trapezoidal, RK4)
   - 6D Vector Inversion $\mathbf{u} = [PTT, HR, RR, \Delta T_{\text{dia}}, \|\mathbf{a}_{\text{IMU}}\|, E_0] \to [SBP, DBP, MAP, PP, SVR, TAC, PWV]$
2. **Zero-PII & Cryptographic Tokenization**:
   - Constant-time HMAC-SHA256 session token generation and verification
   - Strict Zero-PII sanitization middleware rejecting prohibited PII keys with `HTTP 422`
3. **Storage Engine**:
   - SQLite with Write-Ahead Logging (WAL) mode for high-throughput time-series logging
   - ChromaDB vector store wrapper with persistent storage and cosine similarity ranking
4. **API Endpoints**:
   - `POST /api/v1/hemodynamics/invert`
   - `POST /api/v1/hemodynamics/batch`
   - `POST /api/v1/session/init`
   - `GET /api/v1/session/{session_hash}/summary`
   - `POST /api/v1/rag/query`
   - `GET /health`
   - `WS /ws/live-stream`

## Running Tests

```bash
pytest tests/ -v
```

## Running the Server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8085
```
