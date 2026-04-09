#![cfg(all(target_os = "linux", target_arch = "x86_64"))]

use crate::benches::shared::InstResult;
use crate::cli::Options;
use anyhow::{Result, bail};
use serde::Serialize;
use std::fmt::Display;

mod sys;

unsafe extern "C" {
    fn rdpkru_throughput_loop(iterations: u64) -> u64;
    fn wrpkru_throughput_loop(iterations: u64) -> u64;

    fn pkru_roundtrip_latency_loop(iterations: u64) -> u64;
}

#[inline]
fn rdtscp() -> u64 {
    let lo: u32;
    let hi: u32;
    let _aux: u32;
    unsafe {
        core::arch::asm!(
            "rdtscp",
            out("eax") lo,
            out("edx") hi,
            out("ecx") _aux,
            options(nomem, nostack)
        );
    }
    ((hi as u64) << 32) | (lo as u64)
}

#[inline]
fn measure_cycles<F: FnOnce()>(f: F) -> u64 {
    let start = rdtscp();
    f();
    let end = rdtscp();
    end.wrapping_sub(start)
}

#[derive(Serialize)]
pub struct MpkResult {
    pub rdpkru: InstResult,
    pub wrpkru: InstResult,
    /// Combined rdpkru + xor + wrpkru pair
    pub pkru_roundtrip: InstResult,

    /// cycles per pkey_alloc call
    pub pkey_alloc_cycles: InstResult,
    /// cycles per pkey_free call
    pub pkey_free_cycles: InstResult,
    /// cycles per pkey_mprotect call
    pub pkey_mprotect_cycles: InstResult,
}

impl Display for MpkResult {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        let Self {
            rdpkru,
            wrpkru,
            pkru_roundtrip,
            pkey_alloc_cycles,
            pkey_free_cycles,
            pkey_mprotect_cycles,
        } = self;

        write!(f, "rdpkru:\n{}", rdpkru)?;
        write!(f, "wrpkru:\n{}", wrpkru)?;
        write!(f, "pkru_roundtrip:\n{}", pkru_roundtrip)?;
        write!(f, "pkey_alloc_cycles:\n{}", pkey_alloc_cycles)?;
        write!(f, "pkey_free_cycles:\n{}", pkey_free_cycles)?;
        write!(f, "pkey_mprotect_cycles:\n{}", pkey_mprotect_cycles)?;
        Ok(())
    }
}

pub fn run_mpk(options: &Options) -> Result<MpkResult> {
    let iterations = options.iterations;

    // rdpkru throughput
    let rdpkru_cycles = measure_cycles(|| unsafe {
        rdpkru_throughput_loop(iterations);
    });
    let rdpkru_cycles_per_op = rdpkru_cycles as f64 / iterations as f64;
    let rdpkru_throughput_ops_per_cycle = 1.0 / rdpkru_cycles_per_op;

    // wrpkru throughput
    let wrpkru_cycles = measure_cycles(|| unsafe {
        wrpkru_throughput_loop(iterations);
    });
    let wrpkru_cycles_per_op = wrpkru_cycles as f64 / iterations as f64;
    let wrpkru_throughput_ops_per_cycle = 1.0 / wrpkru_cycles_per_op;

    // pkru roundtrip latency: one rdpkru + xor + wrpkru per iteration
    let pkru_roundtrip_cycles = measure_cycles(|| unsafe {
        pkru_roundtrip_latency_loop(iterations);
    });
    let pkru_roundtrip_cycles_per_op = pkru_roundtrip_cycles as f64 / iterations as f64;
    let pkru_roundtrip_throughput_ops_per_cycle = 1.0 / pkru_roundtrip_cycles_per_op;

    // fewer iterations for syscalls
    let syscall_iterations = iterations / 1000;
    let pkey_alloc_cycles = measure_pkey_alloc_cycles(syscall_iterations)?;
    let pkey_free_cycles = measure_pkey_free_cycles(syscall_iterations)?;
    let pkey_mprotect_cycles = measure_pkey_mprotect_cycles(syscall_iterations)?;

    Ok(MpkResult {
        rdpkru: InstResult {
            throughput: rdpkru_throughput_ops_per_cycle,
            // cycles per rdpkru
            latency: Some(rdpkru_cycles_per_op),
        },
        wrpkru: InstResult {
            throughput: wrpkru_throughput_ops_per_cycle,
            // cycles per wrpkru
            latency: Some(wrpkru_cycles_per_op),
        },
        pkru_roundtrip: InstResult {
            throughput: pkru_roundtrip_throughput_ops_per_cycle,
            // cycles per rdpkru + xor + wrpkru
            latency: Some(pkru_roundtrip_cycles_per_op),
        },
        pkey_alloc_cycles: InstResult {
            throughput: 0.0,
            latency: Some(pkey_alloc_cycles),
        },
        pkey_free_cycles: InstResult {
            throughput: 0.0,
            latency: Some(pkey_free_cycles),
        },
        pkey_mprotect_cycles: InstResult {
            throughput: 0.0,
            latency: Some(pkey_mprotect_cycles),
        },
    })
}

/// Measure cycles per pkey_alloc call.
fn measure_pkey_alloc_cycles(iterations: u64) -> Result<f64> {
    unsafe {
        // sanity check that pkeys work
        let test_key = sys::pkey_alloc(0, 0);
        if test_key == -1 {
            bail!(
                "pkey_alloc failed during setup: {}",
                std::io::Error::last_os_error()
            );
        }
        if sys::pkey_free(test_key) != 0 {
            bail!(
                "pkey_free failed during setup: {}",
                std::io::Error::last_os_error()
            );
        }
    }

    let mut total_cycles: u64 = 0;
    let mut done: u64 = 0;

    for _ in 0..iterations {
        unsafe {
            let t0 = rdtscp();
            let key = sys::pkey_alloc(0, 0);
            let t1 = rdtscp();

            if key == -1 {
                break;
            }
            let ret = sys::pkey_free(key);
            if ret != 0 {
                break;
            }

            total_cycles = total_cycles.wrapping_add(t1.wrapping_sub(t0));
            done += 1;
        }
    }

    if done == 0 {
        bail!("pkey_alloc measurement did not complete any iterations");
    }

    Ok(total_cycles as f64 / done as f64)
}

/// Measure cycles per pkey_free call.
fn measure_pkey_free_cycles(iterations: u64) -> Result<f64> {
    unsafe {
        // sanity check
        let test_key = sys::pkey_alloc(0, 0);
        if test_key == -1 {
            bail!(
                "pkey_alloc failed during setup for free: {}",
                std::io::Error::last_os_error()
            );
        }
        if sys::pkey_free(test_key) != 0 {
            bail!(
                "pkey_free failed during setup for free: {}",
                std::io::Error::last_os_error()
            );
        }
    }

    let mut total_cycles: u64 = 0;
    let mut done: u64 = 0;

    for _ in 0..iterations {
        unsafe {
            let key = sys::pkey_alloc(0, 0);
            if key == -1 {
                break;
            }

            let t0 = rdtscp();
            let ret = sys::pkey_free(key);
            let t1 = rdtscp();

            if ret != 0 {
                break;
            }

            total_cycles = total_cycles.wrapping_add(t1.wrapping_sub(t0));
            done += 1;
        }
    }

    if done == 0 {
        bail!("pkey_free measurement did not complete any iterations");
    }

    Ok(total_cycles as f64 / done as f64)
}

/// Measure cycles per pkey_mprotect call on a single page,
/// alternating between two keys.
fn measure_pkey_mprotect_cycles(iterations: u64) -> Result<f64> {
    use std::ptr;

    let page_size = unsafe { libc::sysconf(libc::_SC_PAGESIZE) };
    if page_size <= 0 {
        bail!("sysconf(_SC_PAGESIZE) failed");
    }

    let len = page_size as usize;

    // map one page as RW
    let addr = unsafe {
        libc::mmap(
            ptr::null_mut(),
            len,
            libc::PROT_READ | libc::PROT_WRITE,
            libc::MAP_PRIVATE | libc::MAP_ANONYMOUS,
            -1,
            0,
        )
    };

    if addr == libc::MAP_FAILED {
        bail!("mmap failed: {}", std::io::Error::last_os_error());
    }

    // allocate two keys
    let key0;
    let key1;
    unsafe {
        key0 = sys::pkey_alloc(0, 0);
        if key0 == -1 {
            let err = std::io::Error::last_os_error();
            libc::munmap(addr, len);
            bail!("pkey_alloc key0 failed: {}", err);
        }
        key1 = sys::pkey_alloc(0, 0);
        if key1 == -1 {
            let err = std::io::Error::last_os_error();
            sys::pkey_free(key0);
            libc::munmap(addr, len);
            bail!("pkey_alloc key1 failed: {}", err);
        }

        if sys::pkey_mprotect(addr, len, libc::PROT_READ | libc::PROT_WRITE, key0) != 0 {
            let err = std::io::Error::last_os_error();
            sys::pkey_free(key0);
            sys::pkey_free(key1);
            libc::munmap(addr, len);
            bail!("initial pkey_mprotect failed: {}", err);
        }
    }

    let cycles = measure_cycles(|| {
        let mut use_key0 = true;
        for _ in 0..iterations {
            unsafe {
                let key = if use_key0 { key0 } else { key1 };
                let ret = sys::pkey_mprotect(addr, len, libc::PROT_READ | libc::PROT_WRITE, key);
                if ret != 0 {
                    break;
                }
                use_key0 = !use_key0;
            }
        }
    });

    let cycles_per_op = cycles as f64 / iterations as f64;

    unsafe {
        sys::pkey_free(key0);
        sys::pkey_free(key1);
        libc::munmap(addr, len);
    }

    Ok(cycles_per_op)
}
