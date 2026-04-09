use crate::cli::Options;
use serde::Serialize;
use std::fmt::Display;
use std::time::Instant;

#[derive(Serialize)]
pub struct InstResult {
    pub throughput: f64,
    pub latency: Option<f64>,
}

impl Display for InstResult {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        writeln!(f, "  Throughput: {} insts/cycle", self.throughput)?;
        if let Some(latency) = self.latency {
            writeln!(f, "  Latency: {} cycles", latency)?;
        }

        Ok(())
    }
}

#[allow(unused)]
pub fn call_throughput_fn(
    options: &Options,
    f: unsafe extern "C" fn(u64) -> u64,
    clk_speed_ghz: f64,
) -> f64 {
    let ops_per_ns = time_ops_per_ns(options.iterations, |it| unsafe { f(it) });
    ops_per_ns / clk_speed_ghz
}

#[allow(unused)]
pub fn call_throughput_ptr_fn(
    options: &Options,
    f: unsafe extern "C" fn(u64, *mut u8) -> u64,
    clk_speed_ghz: f64,
    ptr: *mut u8,
) -> f64 {
    let ops_per_ns = time_ops_per_ns(options.iterations, |it| unsafe { f(it, ptr) });
    ops_per_ns / clk_speed_ghz
}

pub fn time_ops_per_ns<F>(iterations: u64, mut f: F) -> f64
where
    F: FnMut(u64) -> u64,
{
    let start = Instant::now();
    let _ = f(iterations);

    let duration = start.elapsed();

    let latency_ns = duration.as_nanos() as f64 / (iterations as f64);
    1.0 / latency_ns
}
