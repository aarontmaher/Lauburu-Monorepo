//! Port 4000 Standalone Server Entrypoint.

use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    tracing_subscriber::registry()
        .with(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "lauburu_core=info,tower_http=info".into()),
        )
        .with(tracing_subscriber::fmt::layer())
        .init();

    let port = std::env::var("PORT")
        .ok()
        .and_then(|p| p.parse::<u16>().ok())
        .unwrap_or(4000);

    println!("============================================================");
    println!("🚀 LAUBURU SOVEREIGN RUST CORE ENGINE");
    println!("   Endpoints:");
    println!("   • Dashboard UI:  http://0.0.0.0:{}", port);
    println!("   • Health:        http://0.0.0.0:{}/health", port);
    println!("   • NPU Status:    http://0.0.0.0:{}/api/npu/status", port);
    println!("   • NPU Inference: http://0.0.0.0:{}/api/npu/analysis", port);
    println!("   • Biometrics:    http://0.0.0.0:{}/api/biometrics/snapshot", port);
    println!("   • WebSocket:     ws://0.0.0.0:{}/ws/telemetry", port);
    println!("============================================================");

    lauburu_core::server::run_server(port).await
}
