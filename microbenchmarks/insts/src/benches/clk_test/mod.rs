#![cfg(target_arch = "aarch64")]

use crate::{benches::shared::time_ops_per_ns, cli::Options};
use anyhow::Result;
use serde::Serialize;
use std::fmt::Display;

unsafe extern "C" {
    fn clktest(iterations: u64) -> u64;
}

#[derive(Serialize)]
pub struct ClkTestResult {
    pub clk_speed_ghz: f64,
}

impl Display for ClkTestResult {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        writeln!(f, "Clock Speed: {:.3} GHz", self.clk_speed_ghz)
    }
}

pub fn run_clock_test(options: &Options) -> Result<ClkTestResult> {
    let clk_speed_ghz = time_ops_per_ns(options.iterations, |it| unsafe { clktest(it) });

    Ok(ClkTestResult { clk_speed_ghz })
}
