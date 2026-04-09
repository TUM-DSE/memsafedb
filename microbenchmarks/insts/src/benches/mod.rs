use crate::cli::{BenchmarkingMode, Options};
use anyhow::{Ok, Result};
use serde::Serialize;
use std::fmt::Display;
use std::fs::File;

mod cheri;
mod clk_test;
mod mpk;
mod mte;
mod pac;
mod shared;

pub trait BenchmarkOutput: Serialize + Display {}
impl<T> BenchmarkOutput for T where T: Serialize + Display {}
pub fn run_benchmark(options: Options) -> Result<()> {
    match options.mode {
        BenchmarkingMode::Mte => {
            #[cfg(all(target_os = "linux", target_arch = "aarch64"))]
            run_bench(&options, mte::run_mte)?;
            #[cfg(not(all(target_os = "linux", target_arch = "aarch64")))]
            anyhow::bail!("MTE benchmarks are only supported on aarch64 linux");
        }
        BenchmarkingMode::Pac => {
            #[cfg(target_arch = "aarch64")]
            run_bench(&options, pac::run_pac)?;
            #[cfg(not(target_arch = "aarch64"))]
            anyhow::bail!("PAC benchmarks are only supported on aarch64");
        }
        BenchmarkingMode::Cheri => {
            #[cfg(target_arch = "aarch64")]
            run_bench(&options, cheri::run_cheri)?;
            #[cfg(not(target_arch = "aarch64"))]
            anyhow::bail!("CHERI benchmarks are only supported on aarch64");
        }
        BenchmarkingMode::Mpk => {
            #[cfg(all(target_os = "linux", target_arch = "x86_64"))]
            run_bench(&options, mpk::run_mpk)?;
            #[cfg(not(all(target_os = "linux", target_arch = "x86_64")))]
            anyhow::bail!("MPK benchmarks are only supported on x86_64")
        }
        BenchmarkingMode::ClockTest => {
            #[cfg(target_arch = "aarch64")]
            run_bench(&options, clk_test::run_clock_test)?;
            #[cfg(not(target_arch = "aarch64"))]
            anyhow::bail!("Clock test is only supported on aarch64");
        }
    };

    Ok(())
}

#[derive(Serialize)]
struct JsonOutput<T: BenchmarkOutput> {
    benchmark: String,
    results: T,
}

fn run_bench<T: BenchmarkOutput, F: Fn(&Options) -> Result<T>>(
    options: &Options,
    f: F,
) -> Result<()> {
    let result = f(options)?;
    if let Some(path) = &options.output {
        let file = File::create(path)?;
        serde_json::to_writer_pretty(
            file,
            &JsonOutput {
                benchmark: format!("{:?}", options.mode).to_uppercase(),
                results: &result,
            },
        )?;
    } else {
        println!("{}", result);
    }
    Ok(())
}
