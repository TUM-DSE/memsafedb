#![cfg(all(target_os = "linux", target_arch = "aarch64"))]

use crate::benches::shared::{
    InstResult, call_throughput_fn, call_throughput_ptr_fn, time_ops_per_ns,
};
use crate::cli::Options;
use anyhow::{Result, bail};
use serde::Serialize;
use std::fmt::Display;

unsafe extern "C" {
    fn clktest(iterations: u64) -> u64;
    fn irgtest(iterations: u64) -> u64;
    fn irglatencytest(iterations: u64) -> u64;
    fn addgtest(iterations: u64) -> u64;
    fn addglatencytest(iterations: u64) -> u64;
    fn subgtest(iterations: u64) -> u64;
    fn subglatencytest(iterations: u64) -> u64;
    fn subptest(iterations: u64) -> u64;
    fn subplatencytest(iterations: u64) -> u64;
    fn subpstest(iterations: u64) -> u64;
    fn subpslatencytest(iterations: u64) -> u64;
    fn stgtest(iterations: u64, ptr: *mut u8) -> u64;
    fn st2gtest(iterations: u64, ptr: *mut u8) -> u64;
    fn stzgtest(iterations: u64, ptr: *mut u8) -> u64;
    fn stz2gtest(iterations: u64, ptr: *mut u8) -> u64;
    fn stgptest(iterations: u64, ptr: *mut u8) -> u64;
    fn ldgtest(iterations: u64, ptr: *mut u8) -> u64;
}

#[derive(Serialize)]
pub struct MteResult {
    pub clk_speed_ghz: f64,

    pub irg: InstResult,
    pub addg: InstResult,
    pub subg: InstResult,
    pub subp: InstResult,
    pub subps: InstResult,
    pub stg: InstResult,
    pub st2g: InstResult,
    pub stzg: InstResult,
    pub stz2g: InstResult,
    pub stgp: InstResult,
    pub ldg: InstResult,
}

impl Display for MteResult {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        // this way we don't forget to write newly added fields
        let Self {
            clk_speed_ghz,
            irg,
            addg,
            subg,
            subp,
            subps,
            stg,
            st2g,
            stzg,
            stz2g,
            stgp,
            ldg,
        } = self;
        writeln!(f, "clk_speed_ghz: {}", clk_speed_ghz)?;
        write!(f, "irg:\n{}", irg)?;
        write!(f, "addg:\n{}", addg)?;
        write!(f, "subg:\n{}", subg)?;
        write!(f, "subp:\n{}", subp)?;
        write!(f, "subps:\n{}", subps)?;
        write!(f, "stg:\n{}", stg)?;
        write!(f, "st2g:\n{}", st2g)?;
        write!(f, "stzg:\n{}", stzg)?;
        write!(f, "stz2g:\n{}", stz2g)?;
        write!(f, "stgp:\n{}", stgp)?;
        write!(f, "ldg:\n{}", ldg)?;
        Ok(())
    }
}

pub fn run_mte(options: &Options) -> Result<MteResult> {
    let mte_mem = setup_mte()?;

    let clk_speed_ghz = time_ops_per_ns(options.iterations, |it| unsafe { clktest(it) });

    let irg_throughput = call_throughput_fn(options, irgtest, clk_speed_ghz);
    let irg_latency = 1.0 / call_throughput_fn(options, irglatencytest, clk_speed_ghz);

    let addg_throughput = call_throughput_fn(options, addgtest, clk_speed_ghz);
    let addg_latency = 1.0 / call_throughput_fn(options, addglatencytest, clk_speed_ghz);

    let subg_throughput = call_throughput_fn(options, subgtest, clk_speed_ghz);
    let subg_latency = 1.0 / call_throughput_fn(options, subglatencytest, clk_speed_ghz);

    let subp_throughput = call_throughput_fn(options, subptest, clk_speed_ghz);
    let subp_latency = 1.0 / call_throughput_fn(options, subplatencytest, clk_speed_ghz);

    let subps_throughput = call_throughput_fn(options, subpstest, clk_speed_ghz);
    let subps_latency = 1.0 / call_throughput_fn(options, subpslatencytest, clk_speed_ghz);

    let stg_throughput = call_throughput_ptr_fn(options, stgtest, clk_speed_ghz, mte_mem.0);
    let st2g_throughput = call_throughput_ptr_fn(options, st2gtest, clk_speed_ghz, mte_mem.0);
    let stzg_throughput = call_throughput_ptr_fn(options, stzgtest, clk_speed_ghz, mte_mem.0);
    let stz2g_throughput = call_throughput_ptr_fn(options, stz2gtest, clk_speed_ghz, mte_mem.0);
    let stgp_throughput = call_throughput_ptr_fn(options, stgptest, clk_speed_ghz, mte_mem.0);
    let ldg_throughput = call_throughput_ptr_fn(options, ldgtest, clk_speed_ghz, mte_mem.0);

    Ok(MteResult {
        clk_speed_ghz,
        irg: InstResult {
            throughput: irg_throughput,
            latency: Some(irg_latency),
        },
        addg: InstResult {
            throughput: addg_throughput,
            latency: Some(addg_latency),
        },
        subg: InstResult {
            throughput: subg_throughput,
            latency: Some(subg_latency),
        },
        subp: InstResult {
            throughput: subp_throughput,
            latency: Some(subp_latency),
        },
        subps: InstResult {
            throughput: subps_throughput,
            latency: Some(subps_latency),
        },
        stg: InstResult {
            throughput: stg_throughput,
            latency: None,
        },
        st2g: InstResult {
            throughput: st2g_throughput,
            latency: None,
        },
        stzg: InstResult {
            throughput: stzg_throughput,
            latency: None,
        },
        stz2g: InstResult {
            throughput: stz2g_throughput,
            latency: None,
        },
        stgp: InstResult {
            throughput: stgp_throughput,
            latency: None,
        },
        ldg: InstResult {
            throughput: ldg_throughput,
            latency: None,
        },
    })
}

fn setup_mte() -> Result<MteMemory> {
    use std::ptr;

    // constants from linux uapi headers
    const PR_SET_TAGGED_ADDR_CTRL: libc::c_int = 55;
    const PR_TAGGED_ADDR_ENABLE: libc::c_ulong = 1 << 0;
    const PR_MTE_TCF_SYNC: libc::c_ulong = 1 << 1;
    const PR_MTE_TAG_SHIFT: u32 = 3;
    const PROT_MTE: libc::c_int = 0x20;

    // enable MTE in userspace
    let tagged_ctrl: libc::c_ulong =
        PR_TAGGED_ADDR_ENABLE | PR_MTE_TCF_SYNC | ((0xfffe as libc::c_ulong) << PR_MTE_TAG_SHIFT);

    let prctl_ret = unsafe { libc::prctl(PR_SET_TAGGED_ADDR_CTRL, tagged_ctrl, 0, 0, 0) };
    if prctl_ret != 0 {
        let err = std::io::Error::last_os_error();
        bail!("prctl(PR_SET_TAGGED_ADDR_CTRL) failed: {}", err);
    }

    let page_size = unsafe { libc::sysconf(libc::_SC_PAGESIZE) };
    if page_size <= 0 {
        bail!("sysconf(_SC_PAGESIZE) failed");
    }

    let len = page_size as usize;
    let addr = unsafe {
        libc::mmap(
            ptr::null_mut(),
            len,
            libc::PROT_READ | libc::PROT_WRITE | PROT_MTE,
            libc::MAP_PRIVATE | libc::MAP_ANONYMOUS,
            -1,
            0,
        )
    };

    if addr == libc::MAP_FAILED {
        let err = std::io::Error::last_os_error();
        bail!("mmap(PROT_MTE) failed: {}", err);
    }

    let mte_arr = addr as *mut u8;

    if (mte_arr as usize & 63) != 0 {
        eprintln!("Warning load may not be 64B aligned");
    }

    Ok(MteMemory(mte_arr))
}

struct MteMemory(*mut u8);

impl Drop for MteMemory {
    fn drop(&mut self) {
        unsafe {
            let page_size = libc::sysconf(libc::_SC_PAGESIZE) as usize;
            libc::munmap(self.0 as *mut libc::c_void, page_size);
        }
    }
}
