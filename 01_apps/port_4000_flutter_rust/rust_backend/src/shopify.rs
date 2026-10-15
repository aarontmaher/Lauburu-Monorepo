//! Shopify Membership & Edge AI Compute Token Governance Engine.
//! Governs Free, Pro ($19/mo), and Crowdsourced Compute tiers across the Lauburu ecosystem.

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum MembershipTier {
    FreeCommunity,
    ProAthlete,
    CrowdsourcedComputeLifetime,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ShopifyMembershipState {
    pub tier: MembershipTier,
    pub customer_id: String,
    pub active_subscription: bool,
    pub compute_credits_gflops: u64,
    pub token_hash: String,
    pub allowed_features: Vec<String>,
}

impl ShopifyMembershipState {
    pub fn new_free(customer_id: &str) -> Self {
        Self {
            tier: MembershipTier::FreeCommunity,
            customer_id: customer_id.to_string(),
            active_subscription: false,
            compute_credits_gflops: 100,
            token_hash: "free_token_community".to_string(),
            allowed_features: vec![
                "Basic Biometrics".to_string(),
                "128Hz ECG Stream".to_string(),
                "Local AI Offline RAG".to_string(),
            ],
        }
    }

    pub fn new_pro(customer_id: &str, token_hash: &str) -> Self {
        Self {
            tier: MembershipTier::ProAthlete,
            customer_id: customer_id.to_string(),
            active_subscription: true,
            compute_credits_gflops: 50_000,
            token_hash: token_hash.to_string(),
            allowed_features: vec![
                "512Hz Medical-Grade ECG".to_string(),
                "Real-Time DFA-Alpha1 Zone 2 Coach".to_string(),
                "Pan-Tompkins DSP Raw Stream".to_string(),
                "Priority 7-Layer Mesh Sharding".to_string(),
                "24/7 LoRA Distillation Access".to_string(),
            ],
        }
    }

    pub fn new_crowdsourced(node_id: &str) -> Self {
        Self {
            tier: MembershipTier::CrowdsourcedComputeLifetime,
            customer_id: format!("mesh_contributor_{}", node_id),
            active_subscription: true,
            compute_credits_gflops: 999_999,
            token_hash: format!("lauburu_node_credit_{}", node_id),
            allowed_features: vec![
                "All Pro Features (Lifetime Free)".to_string(),
                "Uncapped 512Hz Raw Data Pipeline".to_string(),
                "Zero-Cost Mesh AI Inference".to_string(),
                "Distributed Petals/Prima Ring Worker Access".to_string(),
            ],
        }
    }

    /// Validate token string and return granted tier code (0: Free, 1: Pro, 2: Crowdsourced Lifetime)
    pub fn verify_token(token: &str) -> (MembershipTier, i32) {
        if token.starts_with("lauburu_pro_") || token.contains("tier_pro") {
            (MembershipTier::ProAthlete, 1)
        } else if token.starts_with("lauburu_mesh_") || token.starts_with("node_") || token.starts_with("lauburu_lifetime_") {
            (MembershipTier::CrowdsourcedComputeLifetime, 2)
        } else {
            (MembershipTier::FreeCommunity, 0)
        }
    }
}
