use std::sync::atomic::AtomicBool;
use tracing_subscriber::{EnvFilter, FmtSubscriber};

static LOGGING_SETUP: AtomicBool = AtomicBool::new(false);

/// Initialize logging.
pub fn init() {
    if LOGGING_SETUP.swap(true, std::sync::atomic::Ordering::Relaxed) {
        return;
    }

    let b = FmtSubscriber::builder()
        .with_writer(std::io::stderr)
        .with_env_filter(EnvFilter::from_env("RUST_LOG"))
        .with_ansi(true);
    b.init();
}
