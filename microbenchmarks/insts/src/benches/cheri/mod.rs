#![cfg(target_arch = "aarch64")]

use crate::benches::shared::{InstResult, time_ops_per_ns};
use crate::cli::Options;
use anyhow::bail;
use serde::Serialize;
use std::fmt::Display;
use std::slice;

unsafe extern "C" {
    fn clktest(iterations: u64) -> u64;
    fn ldr_throughput_loop(iterations: u64, tmp: *mut u8);
    fn str_throughput_loop(iterations: u64, tmp: *mut u8);
    fn ldar_throughput_loop(iterations: u64, tmp: *mut u8);
    fn stlr_throughput_loop(iterations: u64, tmp: *mut u8);
    fn ldr_cap_throughput_loop(iterations: u64, tmp_cap: *mut u8);
    fn str_cap_throughput_loop(iterations: u64, tmp_cap: *mut u8);
    fn ldp_throughput_loop(iterations: u64, tmp_cap: *mut u8);
    fn ldp_cap_throughput_loop(iterations: u64, tmp_cap: *mut u8);
    fn stp_throughput_loop(iterations: u64, tmp_cap: *mut u8);
    fn stp_cap_throughput_loop(iterations: u64, tmp_cap: *mut u8, tmp1_cap: *mut u8);
    fn cvtd_tocap_throughput_loop(iterations: u64, tmp: u64);
    fn cfhi_throughput_loop(iterations: u64, tmp: *mut u8);
    fn cthi_throughput_loop(iterations: u64, tmp: *mut u8);
    fn cvtd_toptr_throughput_loop(iterations: u64, tmp: u64);
    fn cvtp_tocap_throughput_loop(iterations: u64, tmp: u64);
    fn cvtp_toptr_throughput_loop(iterations: u64, tmp: u64);
    fn cvt_tocap_throughput_loop(iterations: u64, tmp: u64);
    fn cvt_toptr_throughput_loop(iterations: u64, tmp: u64);
    fn str_inplace_throughput_loop(iterations: u64, tmp: *mut u8);
    fn str_cap_inplace_throughput_loop(iterations: u64, tmp_cap: *mut u8);
    fn stp_inplace_throughput_loop(iterations: u64, tmp_cap: *mut u8);
    fn stp_cap_inplace_throughput_loop(iterations: u64, tmp_cap: *mut u8, tmp1_cap: *mut u8);
    fn ldr_latency_loop(iterations: u64, tmp: *mut u8);
    fn ldr_cap_latency_loop(iterations: u64, tmp: *mut u8);
    fn ldp_cap_latency_loop(iterations: u64, tmp: *mut u8);
    fn cvtd_tocap_latency_loop(iterations: u64, tmp: u64);
    fn cfhi_latency_loop(iterations: u64, tmp: *mut u8);
    fn cthi_latency_loop(iterations: u64, tmp: *mut u8);
    fn cvtd_toptr_latency_loop(iterations: u64, tmp: u64);
    fn cvtp_tocap_latency_loop(iterations: u64, tmp: u64);
    fn cvtp_toptr_latency_loop(iterations: u64, tmp: u64);
    fn cvt_tocap_latency_loop(iterations: u64, tmp: u64);
    fn cvt_toptr_latency_loop(iterations: u64, tmp: u64);

    // Z conversions
    fn cvtdz_tocap_latency_loop(iterations: u64, tmp: u64);
    fn cvtdz_tocap_throughput_loop(iterations: u64, tmp: u64);
    fn cvtpz_tocap_latency_loop(iterations: u64, tmp: u64);
    fn cvtpz_tocap_throughput_loop(iterations: u64, tmp: u64);
    fn cvtz_tocap_latency_loop(iterations: u64, tmp: *mut u8);
    fn cvtz_tocap_throughput_loop(iterations: u64, tmp: *mut u8);

    // Getters
    fn gcbase_throughput_loop(iterations: u64, tmp: *mut u8);
    fn gclen_throughput_loop(iterations: u64, tmp: *mut u8);
    fn gclim_throughput_loop(iterations: u64, tmp: *mut u8);
    fn gcoff_throughput_loop(iterations: u64, tmp: *mut u8);
    fn gcperm_throughput_loop(iterations: u64, tmp: *mut u8);
    fn gctype_throughput_loop(iterations: u64, tmp: *mut u8);
    fn gcvalue_throughput_loop(iterations: u64, tmp: *mut u8);
    fn gcflgs_throughput_loop(iterations: u64, tmp: *mut u8);
    fn gcseal_throughput_loop(iterations: u64, tmp: *mut u8);
    fn gctag_throughput_loop(iterations: u64, tmp: *mut u8);

    // Copies and type/value copies
    fn cpy_latency_loop(iterations: u64, tmp: *mut u8);
    fn cpy_throughput_loop(iterations: u64, tmp: *mut u8);
    fn cpytype_latency_loop(iterations: u64, tmp: *mut u8);
    fn cpytype_throughput_loop(iterations: u64, tmp: *mut u8);
    fn cpyvalue_latency_loop(iterations: u64, tmp: *mut u8);
    fn cpyvalue_throughput_loop(iterations: u64, tmp: *mut u8);

    // Rounding and alignment
    fn rrlen_latency_loop(iterations: u64, tmp: u64);
    fn rrlen_throughput_loop(iterations: u64, tmp: u64);
    fn rrmask_latency_loop(iterations: u64, tmp: u64);
    fn rrmask_throughput_loop(iterations: u64, tmp: u64);
    fn alignd_latency_loop(iterations: u64, tmp: *mut u8);
    fn alignd_throughput_loop(iterations: u64, tmp: *mut u8);
    fn alignu_latency_loop(iterations: u64, tmp: *mut u8);
    fn alignu_throughput_loop(iterations: u64, tmp: *mut u8);

    // Permission, tag, offset, flags, value setters
    fn clrperm_throughput_loop(iterations: u64, tmp: *mut u8);
    // fn sctag_throughput_loop(iterations: u64, tmp: *mut u8);
    fn scoff_throughput_loop(iterations: u64, tmp: *mut u8);
    fn scflgs_throughput_loop(iterations: u64, tmp: *mut u8);
    fn scvalue_throughput_loop(iterations: u64, tmp: *mut u8);
    fn scbnds_throughput_loop(iterations: u64, tmp: *mut u8);
    fn scbndse_throughput_loop(iterations: u64, tmp: *mut u8);

    // Sealing
    fn seal_throughput_loop(iterations: u64, tmp: *mut u8);
    fn cseal_throughput_loop(iterations: u64, tmp: *mut u8);
    fn unseal_throughput_loop(iterations: u64, tmp: *mut u8);

    // Checks
    fn chkss_throughput_loop(iterations: u64, tmp: *mut u8);
    fn chkssu_throughput_loop(iterations: u64, tmp: *mut u8);
    fn chktgd_throughput_loop(iterations: u64, tmp: *mut u8);

    // Pointer Arithmetic
    fn add_throughput_loop(iterations: u64, tmp: *mut u8);
    fn sub_throughput_loop(iterations: u64, tmp: *mut u8);

    // Atomics
    fn cas_throughput_loop(iterations: u64, tmp: *mut u8);
    fn swp_throughput_loop(iterations: u64, tmp: *mut u8);
    fn ldxr_throughput_loop(iterations: u64, tmp: *mut u8);
    fn stxr_throughput_loop(iterations: u64, tmp: *mut u8);
    fn ldxr_cap_throughput_loop(iterations: u64, tmp: *mut u8);
    fn stxr_cap_throughput_loop(iterations: u64, tmp: *mut u8);

    // Flag Bitwise Ops
    fn orrflgs_throughput_loop(iterations: u64, tmp: *mut u8);
    fn bicflgs_throughput_loop(iterations: u64, tmp: *mut u8);

    // Equality Check
    fn chkeq_throughput_loop(iterations: u64, tmp: *mut u8);

    // helpers to create capability ptrs
    fn call_cap_ptr_fn(iterations: u64, ptr: *mut u8, f: unsafe extern "C" fn(u64, *mut u8));
}

#[derive(Serialize)]
pub struct CheriResult {
    pub clk_speed_ghz: f64,

    // --- Memory Operations (Load/Store) ---
    pub ldr: InstResult,
    pub str: InstResult,
    pub ldar: InstResult,
    pub stlr: InstResult,
    pub ldp: InstResult,
    pub stp: InstResult,
    pub ldxr: InstResult,
    pub stxr: InstResult,

    // Capability Loads/Stores
    pub ldr_cap: InstResult,
    pub str_cap: InstResult,
    pub ldp_cap: InstResult,
    pub stp_cap: InstResult,
    pub ldxr_cap: InstResult,
    pub stxr_cap: InstResult,

    // In-place
    pub str_inplace: InstResult,
    pub str_cap_inplace: InstResult,
    pub stp_inplace: InstResult,
    pub stp_cap_inplace: InstResult,

    // --- Atomics ---
    pub cas: InstResult,
    pub swp: InstResult,

    // --- Arithmetic & Logic ---
    pub add: InstResult,
    pub sub: InstResult,
    pub orrflgs: InstResult,
    pub bicflgs: InstResult,

    // --- Conversions ---
    // Standard
    pub cvtd_tocap: InstResult,
    pub cvtd_toptr: InstResult,
    pub cvtp_tocap: InstResult,
    pub cvtp_toptr: InstResult,
    pub cvt_tocap: InstResult,
    pub cvt_toptr: InstResult,
    pub cfhi: InstResult,
    pub cthi: InstResult,

    // Zero extending
    pub cvtdz_tocap: InstResult,
    pub cvtpz_tocap: InstResult,
    pub cvtz_tocap: InstResult,

    // --- Capability Getters ---
    pub gcbase: InstResult,
    pub gclen: InstResult,
    pub gclim: InstResult,
    pub gcoff: InstResult,
    pub gcperm: InstResult,
    pub gctype: InstResult,
    pub gcvalue: InstResult,
    pub gcflgs: InstResult,
    pub gcseal: InstResult,
    pub gctag: InstResult,

    // --- Capability Setters ---
    pub scoff: InstResult,
    pub scflgs: InstResult,
    pub scvalue: InstResult,
    pub scbnds: InstResult,
    pub scbndse: InstResult,
    pub clrperm: InstResult,

    // --- Manipulation (Copy/Align/Seal) ---
    pub cpy: InstResult,
    pub cpytype: InstResult,
    pub cpyvalue: InstResult,
    pub rrlen: InstResult,
    pub rrmask: InstResult,
    pub alignd: InstResult,
    pub alignu: InstResult,
    pub seal: InstResult,
    pub cseal: InstResult,
    pub unseal: InstResult,

    // --- Checks ---
    pub chkss: InstResult,
    pub chkssu: InstResult,
    pub chktgd: InstResult,
    pub chkeq: InstResult,
}

impl Display for CheriResult {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        // Deconstruct to ensure we don't miss fields
        let Self {
            clk_speed_ghz,
            ldr,
            str,
            ldar,
            stlr,
            ldxr,
            stxr,
            ldr_cap,
            str_cap,
            ldp,
            ldp_cap,
            stp,
            stp_cap,
            ldxr_cap,
            stxr_cap,
            str_inplace,
            str_cap_inplace,
            stp_inplace,
            stp_cap_inplace,
            cvtd_tocap,
            cfhi,
            cthi,
            cvtd_toptr,
            cvtp_tocap,
            cvtp_toptr,
            cvt_tocap,
            cvt_toptr,
            cvtdz_tocap,
            cvtpz_tocap,
            cvtz_tocap,
            gcbase,
            gclen,
            gclim,
            gcoff,
            gcperm,
            gctype,
            gcvalue,
            gcflgs,
            gcseal,
            gctag,
            cpy,
            cpytype,
            cpyvalue,
            rrlen,
            rrmask,
            alignd,
            alignu,
            clrperm,
            // sctag,
            scoff,
            scflgs,
            scvalue,
            scbnds,
            scbndse,
            seal,
            cseal,
            unseal,
            chkss,
            chkssu,
            chktgd,
            add,
            sub,
            cas,
            swp,
            orrflgs,
            bicflgs,
            chkeq,
        } = self;

        writeln!(f, "clk_speed_ghz: {}", clk_speed_ghz)?;

        writeln!(f, "\n--- Memory Operations ---")?;
        write!(f, "ldr:\n{}", ldr)?;
        write!(f, "str:\n{}", str)?;
        write!(f, "ldar:\n{}", ldar)?;
        write!(f, "stlr:\n{}", stlr)?;
        write!(f, "ldp:\n{}", ldp)?;
        write!(f, "stp:\n{}", stp)?;
        write!(f, "ldxr:\n{}", ldxr)?;
        write!(f, "stxr:\n{}", stxr)?;
        write!(f, "ldr_cap:\n{}", ldr_cap)?;
        write!(f, "str_cap:\n{}", str_cap)?;
        write!(f, "ldp_cap:\n{}", ldp_cap)?;
        write!(f, "stp_cap:\n{}", stp_cap)?;
        write!(f, "ldxr_cap:\n{}", ldxr_cap)?;
        write!(f, "stxr_cap:\n{}", stxr_cap)?;
        write!(f, "str_inplace:\n{}", str_inplace)?;
        write!(f, "str_cap_inplace:\n{}", str_cap_inplace)?;
        write!(f, "stp_inplace:\n{}", stp_inplace)?;
        write!(f, "stp_cap_inplace:\n{}", stp_cap_inplace)?;
        write!(f, "cas:\n{}", cas)?;
        write!(f, "swp:\n{}", swp)?;

        writeln!(f, "\n--- Arithmetic & Logic ---")?;
        write!(f, "add:\n{}", add)?;
        write!(f, "sub:\n{}", sub)?;
        write!(f, "orrflgs:\n{}", orrflgs)?;
        write!(f, "bicflgs:\n{}", bicflgs)?;

        writeln!(f, "\n--- Conversions ---")?;
        write!(f, "cvtd_tocap:\n{}", cvtd_tocap)?;
        write!(f, "cvtd_toptr:\n{}", cvtd_toptr)?;
        write!(f, "cvtp_tocap:\n{}", cvtp_tocap)?;
        write!(f, "cvtp_toptr:\n{}", cvtp_toptr)?;
        write!(f, "cvt_tocap:\n{}", cvt_tocap)?;
        write!(f, "cvt_toptr:\n{}", cvt_toptr)?;
        write!(f, "cfhi:\n{}", cfhi)?;
        write!(f, "cthi:\n{}", cthi)?;
        write!(f, "cvtdz_tocap:\n{}", cvtdz_tocap)?;
        write!(f, "cvtpz_tocap:\n{}", cvtpz_tocap)?;
        write!(f, "cvtz_tocap:\n{}", cvtz_tocap)?;

        writeln!(f, "\n--- Capability Getters ---")?;
        write!(f, "gcbase:\n{}", gcbase)?;
        write!(f, "gclen:\n{}", gclen)?;
        write!(f, "gclim:\n{}", gclim)?;
        write!(f, "gcoff:\n{}", gcoff)?;
        write!(f, "gcperm:\n{}", gcperm)?;
        write!(f, "gctype:\n{}", gctype)?;
        write!(f, "gcvalue:\n{}", gcvalue)?;
        write!(f, "gcflgs:\n{}", gcflgs)?;
        write!(f, "gcseal:\n{}", gcseal)?;
        write!(f, "gctag:\n{}", gctag)?;

        writeln!(f, "\n--- Capability Setters ---")?;
        write!(f, "scoff:\n{}", scoff)?;
        write!(f, "scflgs:\n{}", scflgs)?;
        write!(f, "scvalue:\n{}", scvalue)?;
        write!(f, "scbnds:\n{}", scbnds)?;
        write!(f, "scbndse:\n{}", scbndse)?;
        // write!(f, "sctag:\n{}", sctag)?;
        write!(f, "clrperm:\n{}", clrperm)?;

        writeln!(f, "\n--- Manipulation (Copy/Align/Seal) ---")?;
        write!(f, "cpy:\n{}", cpy)?;
        write!(f, "cpytype:\n{}", cpytype)?;
        write!(f, "cpyvalue:\n{}", cpyvalue)?;
        write!(f, "rrlen:\n{}", rrlen)?;
        write!(f, "rrmask:\n{}", rrmask)?;
        write!(f, "alignd:\n{}", alignd)?;
        write!(f, "alignu:\n{}", alignu)?;
        write!(f, "seal:\n{}", seal)?;
        write!(f, "cseal:\n{}", cseal)?;
        write!(f, "unseal:\n{}", unseal)?;

        writeln!(f, "\n--- Checks ---")?;
        write!(f, "chkss:\n{}", chkss)?;
        write!(f, "chkssu:\n{}", chkssu)?;
        write!(f, "chktgd:\n{}", chktgd)?;
        write!(f, "chkeq:\n{}", chkeq)?;

        Ok(())
    }
}

pub fn run_cheri(options: &Options) -> anyhow::Result<CheriResult> {
    let clk_speed_ghz = time_ops_per_ns(options.iterations, |it| unsafe { clktest(it) });

    let mut ptr = MappedMemory::new()?;
    let mut ptr2 = MappedMemory::new()?;

    let ldr_throughput =
        call_throughput_cap_ptr_fn(options, ldr_throughput_loop, clk_speed_ghz, &mut ptr);
    let str_throughput =
        call_throughput_cap_ptr_fn(options, str_throughput_loop, clk_speed_ghz, &mut ptr);
    let ldar_throughput =
        call_throughput_ptr_fn(options, ldar_throughput_loop, clk_speed_ghz, &mut ptr);
    let stlr_throughput =
        call_throughput_ptr_fn(options, stlr_throughput_loop, clk_speed_ghz, &mut ptr);
    let ldr_cap_throughput =
        call_throughput_cap_ptr_fn(options, ldr_cap_throughput_loop, clk_speed_ghz, &mut ptr);
    let str_cap_throughput =
        call_throughput_cap_ptr_fn(options, str_cap_throughput_loop, clk_speed_ghz, &mut ptr);
    let ldp_throughput =
        call_throughput_ptr_fn(options, ldp_throughput_loop, clk_speed_ghz, &mut ptr);
    let ldp_cap_throughput =
        call_throughput_ptr_fn(options, ldp_cap_throughput_loop, clk_speed_ghz, &mut ptr);
    let stp_throughput =
        call_throughput_ptr_fn(options, stp_throughput_loop, clk_speed_ghz, &mut ptr);
    let stp_cap_throughput = call_throughput_cap_ptr2_fn(
        options,
        stp_cap_throughput_loop,
        clk_speed_ghz,
        &mut ptr,
        &mut ptr2,
    );

    let ldxr_throughput =
        call_throughput_ptr_fn(options, ldxr_throughput_loop, clk_speed_ghz, &mut ptr);
    let stxr_throughput =
        call_throughput_ptr_fn(options, stxr_throughput_loop, clk_speed_ghz, &mut ptr);
    let ldxr_cap_throughput =
        call_throughput_cap_ptr_fn(options, ldxr_cap_throughput_loop, clk_speed_ghz, &mut ptr);
    let stxr_cap_throughput =
        call_throughput_cap_ptr_fn(options, stxr_cap_throughput_loop, clk_speed_ghz, &mut ptr);

    let cvtd_tocap_throughput =
        call_throughput_fn(options, cvtd_tocap_throughput_loop, clk_speed_ghz, 0);
    let cfhi_throughput =
        call_throughput_ptr_fn(options, cfhi_throughput_loop, clk_speed_ghz, &mut ptr);
    let cthi_throughput =
        call_throughput_ptr_fn(options, cthi_throughput_loop, clk_speed_ghz, &mut ptr);
    let cvtd_toptr_throughput =
        call_throughput_fn(options, cvtd_toptr_throughput_loop, clk_speed_ghz, 0);
    let cvtp_tocap_throughput =
        call_throughput_fn(options, cvtp_tocap_throughput_loop, clk_speed_ghz, 0);
    let cvtp_toptr_throughput =
        call_throughput_fn(options, cvtp_toptr_throughput_loop, clk_speed_ghz, 0);
    let cvt_tocap_throughput =
        call_throughput_fn(options, cvt_tocap_throughput_loop, clk_speed_ghz, 0);
    let cvt_toptr_throughput =
        call_throughput_fn(options, cvt_toptr_throughput_loop, clk_speed_ghz, 0);

    // Existing In-place
    let str_inplace_throughput = call_throughput_cap_ptr_fn(
        options,
        str_inplace_throughput_loop,
        clk_speed_ghz,
        &mut ptr,
    );
    let str_cap_inplace_throughput = call_throughput_cap_ptr_fn(
        options,
        str_cap_inplace_throughput_loop,
        clk_speed_ghz,
        &mut ptr,
    );
    let stp_inplace_throughput = call_throughput_ptr_fn(
        options,
        stp_inplace_throughput_loop,
        clk_speed_ghz,
        &mut ptr,
    );
    let stp_cap_inplace_throughput = call_throughput_cap_ptr2_fn(
        options,
        stp_cap_inplace_throughput_loop,
        clk_speed_ghz,
        &mut ptr,
        &mut ptr2,
    );

    // Z Conversions
    let cvtdz_tocap_throughput =
        call_throughput_fn(options, cvtdz_tocap_throughput_loop, clk_speed_ghz, 0);
    let cvtpz_tocap_throughput =
        call_throughput_fn(options, cvtpz_tocap_throughput_loop, clk_speed_ghz, 0);
    let cvtz_tocap_throughput =
        call_throughput_cap_ptr_fn(options, cvtz_tocap_throughput_loop, clk_speed_ghz, &mut ptr);

    // Getters (GC*)
    let gcbase_throughput =
        call_throughput_cap_ptr_fn(options, gcbase_throughput_loop, clk_speed_ghz, &mut ptr);
    let gclen_throughput =
        call_throughput_cap_ptr_fn(options, gclen_throughput_loop, clk_speed_ghz, &mut ptr);
    let gclim_throughput =
        call_throughput_cap_ptr_fn(options, gclim_throughput_loop, clk_speed_ghz, &mut ptr);
    let gcoff_throughput =
        call_throughput_cap_ptr_fn(options, gcoff_throughput_loop, clk_speed_ghz, &mut ptr);
    let gcperm_throughput =
        call_throughput_cap_ptr_fn(options, gcperm_throughput_loop, clk_speed_ghz, &mut ptr);
    let gctype_throughput =
        call_throughput_cap_ptr_fn(options, gctype_throughput_loop, clk_speed_ghz, &mut ptr);
    let gcvalue_throughput =
        call_throughput_cap_ptr_fn(options, gcvalue_throughput_loop, clk_speed_ghz, &mut ptr);
    let gcflgs_throughput =
        call_throughput_cap_ptr_fn(options, gcflgs_throughput_loop, clk_speed_ghz, &mut ptr);
    let gcseal_throughput =
        call_throughput_cap_ptr_fn(options, gcseal_throughput_loop, clk_speed_ghz, &mut ptr);
    let gctag_throughput =
        call_throughput_cap_ptr_fn(options, gctag_throughput_loop, clk_speed_ghz, &mut ptr);

    // Copies
    let cpy_throughput =
        call_throughput_cap_ptr_fn(options, cpy_throughput_loop, clk_speed_ghz, &mut ptr);
    let cpytype_throughput =
        call_throughput_cap_ptr_fn(options, cpytype_throughput_loop, clk_speed_ghz, &mut ptr);
    let cpyvalue_throughput =
        call_throughput_cap_ptr_fn(options, cpyvalue_throughput_loop, clk_speed_ghz, &mut ptr);

    // Round/Align
    let rrlen_throughput = call_throughput_fn(options, rrlen_throughput_loop, clk_speed_ghz, 0);
    let rrmask_throughput = call_throughput_fn(options, rrmask_throughput_loop, clk_speed_ghz, 0);
    let alignd_throughput =
        call_throughput_cap_ptr_fn(options, alignd_throughput_loop, clk_speed_ghz, &mut ptr);
    let alignu_throughput =
        call_throughput_cap_ptr_fn(options, alignu_throughput_loop, clk_speed_ghz, &mut ptr);

    // Setters
    let clrperm_throughput =
        call_throughput_cap_ptr_fn(options, clrperm_throughput_loop, clk_speed_ghz, &mut ptr);
    // let sctag_throughput: f64 =
    //     call_throughput_cap_ptr_fn(options, sctag_throughput_loop, clk_speed_ghz, &mut ptr);
    let scoff_throughput =
        call_throughput_cap_ptr_fn(options, scoff_throughput_loop, clk_speed_ghz, &mut ptr);
    let scflgs_throughput =
        call_throughput_cap_ptr_fn(options, scflgs_throughput_loop, clk_speed_ghz, &mut ptr);
    let scvalue_throughput =
        call_throughput_cap_ptr_fn(options, scvalue_throughput_loop, clk_speed_ghz, &mut ptr);
    let scbnds_throughput =
        call_throughput_cap_ptr_fn(options, scbnds_throughput_loop, clk_speed_ghz, &mut ptr);
    let scbndse_throughput =
        call_throughput_cap_ptr_fn(options, scbndse_throughput_loop, clk_speed_ghz, &mut ptr);

    // Sealing
    let seal_throughput =
        call_throughput_cap_ptr_fn(options, seal_throughput_loop, clk_speed_ghz, &mut ptr);
    let cseal_throughput =
        call_throughput_cap_ptr_fn(options, cseal_throughput_loop, clk_speed_ghz, &mut ptr);
    let unseal_throughput =
        call_throughput_cap_ptr_fn(options, unseal_throughput_loop, clk_speed_ghz, &mut ptr);

    // Checks
    let chkss_throughput =
        call_throughput_cap_ptr_fn(options, chkss_throughput_loop, clk_speed_ghz, &mut ptr);
    let chkssu_throughput =
        call_throughput_cap_ptr_fn(options, chkssu_throughput_loop, clk_speed_ghz, &mut ptr);
    let chktgd_throughput =
        call_throughput_cap_ptr_fn(options, chktgd_throughput_loop, clk_speed_ghz, &mut ptr);

    // Arithmetic
    let add_throughput =
        call_throughput_cap_ptr_fn(options, add_throughput_loop, clk_speed_ghz, &mut ptr);
    let sub_throughput =
        call_throughput_cap_ptr_fn(options, sub_throughput_loop, clk_speed_ghz, &mut ptr);

    // Atomics
    let cas_throughput =
        call_throughput_cap_ptr_fn(options, cas_throughput_loop, clk_speed_ghz, &mut ptr);
    let swp_throughput =
        call_throughput_cap_ptr_fn(options, swp_throughput_loop, clk_speed_ghz, &mut ptr);

    // Flag Bitwise
    let orrflgs_throughput =
        call_throughput_cap_ptr_fn(options, orrflgs_throughput_loop, clk_speed_ghz, &mut ptr);
    let bicflgs_throughput =
        call_throughput_cap_ptr_fn(options, bicflgs_throughput_loop, clk_speed_ghz, &mut ptr);

    // Equality
    let chkeq_throughput =
        call_throughput_cap_ptr_fn(options, chkeq_throughput_loop, clk_speed_ghz, &mut ptr);

    // Latencies
    let ldr_latency =
        1.0 / call_throughput_cap_ptr_fn(options, ldr_latency_loop, clk_speed_ghz, &mut ptr);
    let ldr_cap_latency =
        1.0 / call_throughput_cap_ptr_fn(options, ldr_cap_latency_loop, clk_speed_ghz, &mut ptr);
    let ldp_cap_latency =
        1.0 / call_throughput_ptr_fn(options, ldp_cap_latency_loop, clk_speed_ghz, &mut ptr);
    let cvtd_tocap_latency =
        1.0 / call_throughput_fn(options, cvtd_tocap_latency_loop, clk_speed_ghz, 0);
    let cfhi_latency =
        1.0 / call_throughput_ptr_fn(options, cfhi_latency_loop, clk_speed_ghz, &mut ptr);
    let cthi_latency =
        1.0 / call_throughput_ptr_fn(options, cthi_latency_loop, clk_speed_ghz, &mut ptr);
    let cvtd_toptr_latency =
        1.0 / call_throughput_fn(options, cvtd_toptr_latency_loop, clk_speed_ghz, 0);
    let cvtp_tocap_latency =
        1.0 / call_throughput_fn(options, cvtp_tocap_latency_loop, clk_speed_ghz, 0);
    let cvtp_toptr_latency =
        1.0 / call_throughput_fn(options, cvtp_toptr_latency_loop, clk_speed_ghz, 0);
    let cvt_tocap_latency =
        1.0 / call_throughput_fn(options, cvt_tocap_latency_loop, clk_speed_ghz, 0);
    let cvt_toptr_latency =
        1.0 / call_throughput_fn(options, cvt_toptr_latency_loop, clk_speed_ghz, 0);

    // New Latencies
    let cvtdz_tocap_latency =
        1.0 / call_throughput_fn(options, cvtdz_tocap_latency_loop, clk_speed_ghz, 0);
    let cvtpz_tocap_latency =
        1.0 / call_throughput_fn(options, cvtpz_tocap_latency_loop, clk_speed_ghz, 0);
    let cvtz_tocap_latency =
        1.0 / call_throughput_cap_ptr_fn(options, cvtz_tocap_latency_loop, clk_speed_ghz, &mut ptr);
    let cpy_latency =
        1.0 / call_throughput_cap_ptr_fn(options, cpy_latency_loop, clk_speed_ghz, &mut ptr);
    let cpytype_latency =
        1.0 / call_throughput_cap_ptr_fn(options, cpytype_latency_loop, clk_speed_ghz, &mut ptr);
    let cpyvalue_latency =
        1.0 / call_throughput_cap_ptr_fn(options, cpyvalue_latency_loop, clk_speed_ghz, &mut ptr);
    let rrlen_latency = 1.0 / call_throughput_fn(options, rrlen_latency_loop, clk_speed_ghz, 0);
    let rrmask_latency = 1.0 / call_throughput_fn(options, rrmask_latency_loop, clk_speed_ghz, 0);
    let alignd_latency =
        1.0 / call_throughput_cap_ptr_fn(options, alignd_latency_loop, clk_speed_ghz, &mut ptr);
    let alignu_latency =
        1.0 / call_throughput_cap_ptr_fn(options, alignu_latency_loop, clk_speed_ghz, &mut ptr);

    Ok(CheriResult {
        clk_speed_ghz,
        ldr: InstResult {
            throughput: ldr_throughput,
            latency: Some(ldr_latency),
        },
        str: InstResult {
            throughput: str_throughput,
            latency: None,
        },
        ldar: InstResult {
            throughput: ldar_throughput,
            latency: None,
        },
        stlr: InstResult {
            throughput: stlr_throughput,
            latency: None,
        },
        ldxr: InstResult {
            throughput: ldxr_throughput,
            latency: None,
        },
        stxr: InstResult {
            throughput: stxr_throughput,
            latency: None,
        },
        ldr_cap: InstResult {
            throughput: ldr_cap_throughput,
            latency: Some(ldr_cap_latency),
        },
        str_cap: InstResult {
            throughput: str_cap_throughput,
            latency: None,
        },
        ldp: InstResult {
            throughput: ldp_throughput,
            latency: None,
        },
        ldp_cap: InstResult {
            throughput: ldp_cap_throughput,
            latency: Some(ldp_cap_latency),
        },
        stp: InstResult {
            throughput: stp_throughput,
            latency: None,
        },
        stp_cap: InstResult {
            throughput: stp_cap_throughput,
            latency: None,
        },
        ldxr_cap: InstResult {
            throughput: ldxr_cap_throughput,
            latency: None,
        },
        stxr_cap: InstResult {
            throughput: stxr_cap_throughput,
            latency: None,
        },
        cvtd_tocap: InstResult {
            throughput: cvtd_tocap_throughput,
            latency: Some(cvtd_tocap_latency),
        },
        cfhi: InstResult {
            throughput: cfhi_throughput,
            latency: Some(cfhi_latency),
        },
        cthi: InstResult {
            throughput: cthi_throughput,
            latency: Some(cthi_latency),
        },
        cvtd_toptr: InstResult {
            throughput: cvtd_toptr_throughput,
            latency: Some(cvtd_toptr_latency),
        },
        cvtp_tocap: InstResult {
            throughput: cvtp_tocap_throughput,
            latency: Some(cvtp_tocap_latency),
        },
        cvtp_toptr: InstResult {
            throughput: cvtp_toptr_throughput,
            latency: Some(cvtp_toptr_latency),
        },
        cvt_tocap: InstResult {
            throughput: cvt_tocap_throughput,
            latency: Some(cvt_tocap_latency),
        },
        cvt_toptr: InstResult {
            throughput: cvt_toptr_throughput,
            latency: Some(cvt_toptr_latency),
        },
        str_inplace: InstResult {
            throughput: str_inplace_throughput,
            latency: None,
        },
        str_cap_inplace: InstResult {
            throughput: str_cap_inplace_throughput,
            latency: None,
        },
        stp_inplace: InstResult {
            throughput: stp_inplace_throughput,
            latency: None,
        },
        stp_cap_inplace: InstResult {
            throughput: stp_cap_inplace_throughput,
            latency: None,
        },

        cvtdz_tocap: InstResult {
            throughput: cvtdz_tocap_throughput,
            latency: Some(cvtdz_tocap_latency),
        },
        cvtpz_tocap: InstResult {
            throughput: cvtpz_tocap_throughput,
            latency: Some(cvtpz_tocap_latency),
        },
        cvtz_tocap: InstResult {
            throughput: cvtz_tocap_throughput,
            latency: Some(cvtz_tocap_latency),
        },

        gcbase: InstResult {
            throughput: gcbase_throughput,
            latency: None,
        },
        gclen: InstResult {
            throughput: gclen_throughput,
            latency: None,
        },
        gclim: InstResult {
            throughput: gclim_throughput,
            latency: None,
        },
        gcoff: InstResult {
            throughput: gcoff_throughput,
            latency: None,
        },
        gcperm: InstResult {
            throughput: gcperm_throughput,
            latency: None,
        },
        gctype: InstResult {
            throughput: gctype_throughput,
            latency: None,
        },
        gcvalue: InstResult {
            throughput: gcvalue_throughput,
            latency: None,
        },
        gcflgs: InstResult {
            throughput: gcflgs_throughput,
            latency: None,
        },
        gcseal: InstResult {
            throughput: gcseal_throughput,
            latency: None,
        },
        gctag: InstResult {
            throughput: gctag_throughput,
            latency: None,
        },

        cpy: InstResult {
            throughput: cpy_throughput,
            latency: Some(cpy_latency),
        },
        cpytype: InstResult {
            throughput: cpytype_throughput,
            latency: Some(cpytype_latency),
        },
        cpyvalue: InstResult {
            throughput: cpyvalue_throughput,
            latency: Some(cpyvalue_latency),
        },

        rrlen: InstResult {
            throughput: rrlen_throughput,
            latency: Some(rrlen_latency),
        },
        rrmask: InstResult {
            throughput: rrmask_throughput,
            latency: Some(rrmask_latency),
        },
        alignd: InstResult {
            throughput: alignd_throughput,
            latency: Some(alignd_latency),
        },
        alignu: InstResult {
            throughput: alignu_throughput,
            latency: Some(alignu_latency),
        },

        clrperm: InstResult {
            throughput: clrperm_throughput,
            latency: None,
        },
        // sctag: InstResult {
        //     throughput: sctag_throughput,
        //     latency: None,
        // },
        scoff: InstResult {
            throughput: scoff_throughput,
            latency: None,
        },
        scflgs: InstResult {
            throughput: scflgs_throughput,
            latency: None,
        },
        scvalue: InstResult {
            throughput: scvalue_throughput,
            latency: None,
        },
        scbnds: InstResult {
            throughput: scbnds_throughput,
            latency: None,
        },
        scbndse: InstResult {
            throughput: scbndse_throughput,
            latency: None,
        },

        seal: InstResult {
            throughput: seal_throughput,
            latency: None,
        },
        cseal: InstResult {
            throughput: cseal_throughput,
            latency: None,
        },
        unseal: InstResult {
            throughput: unseal_throughput,
            latency: None,
        },

        chkss: InstResult {
            throughput: chkss_throughput,
            latency: None,
        },
        chkssu: InstResult {
            throughput: chkssu_throughput,
            latency: None,
        },
        chktgd: InstResult {
            throughput: chktgd_throughput,
            latency: None,
        },

        add: InstResult {
            throughput: add_throughput,
            latency: None,
        },
        sub: InstResult {
            throughput: sub_throughput,
            latency: None,
        },
        cas: InstResult {
            throughput: cas_throughput,
            latency: None,
        },
        swp: InstResult {
            throughput: swp_throughput,
            latency: None,
        },
        orrflgs: InstResult {
            throughput: orrflgs_throughput,
            latency: None,
        },
        bicflgs: InstResult {
            throughput: bicflgs_throughput,
            latency: None,
        },
        chkeq: InstResult {
            throughput: chkeq_throughput,
            latency: None,
        },
    })
}

fn call_throughput_fn(
    options: &Options,
    f: unsafe extern "C" fn(u64, u64),
    clk_speed_ghz: f64,
    val: u64,
) -> f64 {
    let ops_per_ns = time_ops_per_ns(options.iterations, |it| unsafe {
        f(it, val);
        0
    });
    ops_per_ns / clk_speed_ghz
}

fn call_throughput_ptr_fn(
    options: &Options,
    f: unsafe extern "C" fn(u64, *mut u8),
    clk_speed_ghz: f64,
    mem: &mut MappedMemory,
) -> f64 {
    mem.clear();
    let ops_per_ns = time_ops_per_ns(options.iterations, |it| unsafe {
        f(it, mem.ptr);
        0
    });
    ops_per_ns / clk_speed_ghz
}

fn call_throughput_cap_ptr_fn(
    options: &Options,
    f: unsafe extern "C" fn(u64, *mut u8),
    clk_speed_ghz: f64,
    mem: &mut MappedMemory,
) -> f64 {
    mem.clear();
    let ops_per_ns = time_ops_per_ns(options.iterations, |it| unsafe {
        call_cap_ptr_fn(it, mem.ptr, f);
        0
    });
    ops_per_ns / clk_speed_ghz
}

fn call_throughput_cap_ptr2_fn(
    options: &Options,
    f: unsafe extern "C" fn(u64, *mut u8, *mut u8),
    clk_speed_ghz: f64,
    mem: &mut MappedMemory,
    mem2: &mut MappedMemory,
) -> f64 {
    mem.clear();
    mem2.clear();
    let ops_per_ns = time_ops_per_ns(options.iterations, |it| unsafe {
        f(it, mem.ptr, mem2.ptr);
        0
    });
    ops_per_ns / clk_speed_ghz
}

struct MappedMemory {
    ptr: *mut u8,
    len: usize,
}

impl MappedMemory {
    pub fn new() -> anyhow::Result<Self> {
        use std::ptr;

        let page_size = unsafe { libc::sysconf(libc::_SC_PAGESIZE) };
        if page_size <= 0 {
            bail!("sysconf(_SC_PAGESIZE) failed");
        }

        let len = page_size as usize;
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
            let err = std::io::Error::last_os_error();
            bail!("mmap(PROT_MTE) failed: {}", err);
        }

        let ptr = addr as *mut u8;

        if (ptr as usize & 63) != 0 {
            panic!("Warning load may not be 64B aligned");
        }

        Ok(Self { ptr, len })
    }

    pub fn clear(&mut self) {
        unsafe {
            let slice = slice::from_raw_parts_mut(self.ptr, self.len);
            slice.fill(0);
        }
    }
}

impl Drop for MappedMemory {
    fn drop(&mut self) {
        unsafe {
            libc::munmap(self.ptr as *mut libc::c_void, self.len);
        }
    }
}
