#![cfg(target_arch = "aarch64")]

use crate::benches::shared::{InstResult, call_throughput_fn, time_ops_per_ns};
use crate::cli::Options;
use serde::Serialize;
use std::fmt::Display;

unsafe extern "C" {
    fn clktest(iterations: u64) -> u64;
    fn pacdzatest(iterations: u64) -> u64;
    fn pacdzalatencytest(iterations: u64) -> u64;
    fn pacdatest(iterations: u64) -> u64;
    fn pacdalatencytest(iterations: u64) -> u64;
    fn autdzatest(iterations: u64) -> u64;
    fn autdzalatencytest(iterations: u64) -> u64;
    fn autdatest(iterations: u64) -> u64;
    fn autdalatencytest(iterations: u64) -> u64;
    fn xpacdtest(iterations: u64) -> u64;
    fn xpacdlatencytest(iterations: u64) -> u64;
}

#[derive(Serialize)]
pub struct PacResult {
    pub clk_speed_ghz: f64,

    pub pacdza: InstResult,
    pub pacda: InstResult,
    pub autdza: InstResult,
    pub autda: InstResult,
    pub xpacd: InstResult,
}

impl Display for PacResult {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        // this way we don't forget to write newly added fields
        let Self {
            clk_speed_ghz,
            pacdza,
            pacda,
            autdza,
            autda,
            xpacd,
        } = self;

        writeln!(f, "clk_speed_ghz: {}", clk_speed_ghz)?;
        write!(f, "pacdza:\n{}", pacdza)?;
        write!(f, "pacda:\n{}", pacda)?;
        write!(f, "autdza:\n{}", autdza)?;
        write!(f, "autda:\n{}", autda)?;
        write!(f, "xpacd:\n{}", xpacd)?;

        Ok(())
    }
}

pub fn run_pac(options: &Options) -> anyhow::Result<PacResult> {
    let clk_speed_ghz = time_ops_per_ns(options.iterations, |it| unsafe { clktest(it) });

    let pacdza_throughput = call_throughput_fn(options, pacdzatest, clk_speed_ghz);
    let pacdza_latency = 1.0 / call_throughput_fn(options, pacdzalatencytest, clk_speed_ghz);
    let pacda_throughput = call_throughput_fn(options, pacdatest, clk_speed_ghz);
    let pacda_latency = 1.0 / call_throughput_fn(options, pacdalatencytest, clk_speed_ghz);
    let autdza_throughput = call_throughput_fn(options, autdzatest, clk_speed_ghz);
    let autdza_latency = 1.0 / call_throughput_fn(options, autdzalatencytest, clk_speed_ghz);
    let autda_throughput = call_throughput_fn(options, autdatest, clk_speed_ghz);
    let autda_latency = 1.0 / call_throughput_fn(options, autdalatencytest, clk_speed_ghz);
    let xpacd_throughput = call_throughput_fn(options, xpacdtest, clk_speed_ghz);
    let xpacd_latency = 1.0 / call_throughput_fn(options, xpacdlatencytest, clk_speed_ghz);

    Ok(PacResult {
        clk_speed_ghz,
        pacdza: InstResult {
            throughput: pacdza_throughput,
            latency: Some(pacdza_latency),
        },
        pacda: InstResult {
            throughput: pacda_throughput,
            latency: Some(pacda_latency),
        },
        autdza: InstResult {
            throughput: autdza_throughput,
            latency: Some(autdza_latency),
        },
        autda: InstResult {
            throughput: autda_throughput,
            latency: Some(autda_latency),
        },
        xpacd: InstResult {
            throughput: xpacd_throughput,
            latency: Some(xpacd_latency),
        },
    })
}
