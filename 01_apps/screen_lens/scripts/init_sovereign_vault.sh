#!/bin/bash
# Initializes the isolated Sovereign Credential Vault for Screen Lens.

VAULT_DIR="/Users/aaron/.lauburu_sovereign_vault"
ENV_FILE="$VAULT_DIR/.env.lens_secrets"

if [ ! -d "$VAULT_DIR" ]; then
    mkdir -p "$VAULT_DIR"
    chmod 700 "$VAULT_DIR"
fi

if [ ! -f "$ENV_FILE" ]; then
    cat << 'ENV_TEMPLATE' > "$ENV_FILE"
# ==============================================================================
# 🛑 LAUBURU SOVEREIGN CREDENTIAL VAULT (AIR-GAPPED)
# ==============================================================================
# RULE 9 STRICT ENFORCEMENT: 
# The Cloud AI (Antigravity/Gemini/OpenAI) MUST NEVER READ THIS FILE.
# Only local Python daemons and Qwen 3.8 Max on 127.0.0.1:8082 may parse these.
# ==============================================================================

# -- MESH AUTHENTICATION --
L2_MACBOOK_USER="aaron"
L2_MACBOOK_PASS=""
L3_LINUX_PASS=""

# -- API KEYS (ZERO-CLOUD LEAKAGE) --
SHOPIFY_ADMIN_TOKEN=""
HUGGINGFACE_TOKEN=""

# -- IDENTITIES --
SOVEREIGN_EMAIL=""

ENV_TEMPLATE
    chmod 600 "$ENV_FILE"
    echo "✅ Sovereign Vault initialized at $ENV_FILE"
else
    echo "ℹ️ Sovereign Vault already exists."
fi
