.global call_cap_ptr_fn
.global call_cap_ptr2_fn

// fn call_cap_ptr_fn(
//     iterations: u64,
//     ptr: *mut u8,
//     f: unsafe extern "C" fn(u64, *mut u8),
// );
call_cap_ptr_fn:
    // create a capability from ptr
    cvtd c1, x1
    br x2

.global ldr_throughput_loop
.global ldr_latency_loop
.global str_throughput_loop
.global str_cap_throughput_loop
.global ldar_throughput_loop
.global stlr_throughput_loop
.global ldr_cap_throughput_loop
.global ldp_throughput_loop
.global ldp_cap_throughput_loop
.global stp_throughput_loop
.global stp_cap_throughput_loop
.global ldr_cap_latency_loop
.global ldp_latency_loop
.global ldp_cap_latency_loop
.global cvtd_tocap_throughput_loop
.global cvtd_tocap_latency_loop
.global cfhi_throughput_loop
.global cfhi_latency_loop
.global cthi_throughput_loop
.global cthi_latency_loop
.global cvtd_toptr_throughput_loop
.global cvtd_toptr_latency_loop
.global cvtp_tocap_throughput_loop
.global cvtp_tocap_latency_loop
.global cvtp_toptr_throughput_loop
.global cvtp_toptr_latency_loop
.global cvt_tocap_throughput_loop
.global cvt_tocap_latency_loop
.global cvt_toptr_throughput_loop
.global cvt_toptr_latency_loop
.global str_inplace_throughput_loop
.global str_cap_inplace_throughput_loop
.global stp_inplace_throughput_loop
.global stp_cap_inplace_throughput_loop

cvt_toptr_latency_loop:
    cbz x0, cvttpl_end
    sub x0, x0, #16
        cvt x1, c1, c1
        cvt x1, c1, c1
        cvt x1, c1, c1
        cvt x1, c1, c1
        cvt x1, c1, c1
        cvt x1, c1, c1
        cvt x1, c1, c1
        cvt x1, c1, c1
        cvt x1, c1, c1
        cvt x1, c1, c1
        cvt x1, c1, c1
        cvt x1, c1, c1
        cvt x1, c1, c1
        cvt x1, c1, c1
        cvt x1, c1, c1
        cvt x1, c1, c1
    b cvt_toptr_latency_loop

    cvttpl_end:
        ret

cvt_toptr_throughput_loop:
    cbz x0, cvttpt_end
    sub x0, x0, #16
        cvt x9, c1, c1
        cvt x10, c1, c1
        cvt x11, c1, c1
        cvt x12, c1, c1
        cvt x13, c1, c1
        cvt x14, c1, c1
        cvt x15, c1, c1
        cvt x9, c1, c1
        cvt x10, c1, c1
        cvt x11, c1, c1
        cvt x12, c1, c1
        cvt x13, c1, c1
        cvt x14, c1, c1
        cvt x15, c1, c1
        cvt x9, c1, c1
        cvt x10, c1, c1
    b cvt_toptr_throughput_loop

    cvttpt_end:
        ret


cvt_tocap_latency_loop:
    cbz x0, cvttcl_end
    sub x0, x0, #16
        cvt c1, c1, x1
        cvt c1, c1, x1
        cvt c1, c1, x1
        cvt c1, c1, x1
        cvt c1, c1, x1
        cvt c1, c1, x1
        cvt c1, c1, x1
        cvt c1, c1, x1
        cvt c1, c1, x1
        cvt c1, c1, x1
        cvt c1, c1, x1
        cvt c1, c1, x1
        cvt c1, c1, x1
        cvt c1, c1, x1
        cvt c1, c1, x1
        cvt c1, c1, x1
    b cvt_tocap_latency_loop

    cvttcl_end:
        ret

cvt_tocap_throughput_loop:
    cbz x0, cvttct_end
    sub x0, x0, #16
        cvt c9, c1, x1
        cvt c10, c1, x1
        cvt c11, c1, x1
        cvt c12, c1, x1
        cvt c13, c1, x1
        cvt c14, c1, x1
        cvt c15, c1, x1
        cvt c9, c1, x1
        cvt c10, c1, x1
        cvt c11, c1, x1
        cvt c12, c1, x1
        cvt c13, c1, x1
        cvt c14, c1, x1
        cvt c15, c1, x1
        cvt c9, c1, x1
        cvt c10,c1, x1
    b cvt_tocap_throughput_loop

    cvttct_end:
        ret

cvtp_toptr_latency_loop:
    cbz x0, cvtptpl_end
    sub x0, x0, #16
        cvtp x1, c1
        cvtp x1, c1
        cvtp x1, c1
        cvtp x1, c1
        cvtp x1, c1
        cvtp x1, c1
        cvtp x1, c1
        cvtp x1, c1
        cvtp x1, c1
        cvtp x1, c1
        cvtp x1, c1
        cvtp x1, c1
        cvtp x1, c1
        cvtp x1, c1
        cvtp x1, c1
        cvtp x1, c1
    b cvtp_toptr_latency_loop

    cvtptpl_end:
        ret

cvtp_toptr_throughput_loop:
    cbz x0, cvtptpt_end
    sub x0, x0, #16
        cvtp x9, c1
        cvtp x10, c1
        cvtp x11, c1
        cvtp x12, c1
        cvtp x13, c1
        cvtp x14, c1
        cvtp x15, c1
        cvtp x9, c1
        cvtp x10, c1
        cvtp x11, c1
        cvtp x12, c1
        cvtp x13, c1
        cvtp x14, c1
        cvtp x15, c1
        cvtp x9, c1
        cvtp x10, c1
    b cvtp_toptr_throughput_loop

    cvtptpt_end:
        ret


cvtp_tocap_latency_loop:
    cbz x0, cvtptcl_end
    sub x0, x0, #16
        cvtp c1, x1
        cvtp c1, x1
        cvtp c1, x1
        cvtp c1, x1
        cvtp c1, x1
        cvtp c1, x1
        cvtp c1, x1
        cvtp c1, x1
        cvtp c1, x1
        cvtp c1, x1
        cvtp c1, x1
        cvtp c1, x1
        cvtp c1, x1
        cvtp c1, x1
        cvtp c1, x1
        cvtp c1, x1
    b cvtp_tocap_latency_loop

    cvtptcl_end:
        ret

cvtp_tocap_throughput_loop:
    cbz x0, cvtptct_end
    sub x0, x0, #16
        cvtp c9, x1
        cvtp c10, x1
        cvtp c11, x1
        cvtp c12, x1
        cvtp c13, x1
        cvtp c14, x1
        cvtp c15, x1
        cvtp c9, x1
        cvtp c10, x1
        cvtp c11, x1
        cvtp c12, x1
        cvtp c13, x1
        cvtp c14, x1
        cvtp c15, x1
        cvtp c9, x1
        cvtp c10, x1
    b cvtp_tocap_throughput_loop

    cvtptct_end:
        ret

cvtd_toptr_latency_loop:
    cbz x0, cvtdtpl_end
    sub x0, x0, #16
        cvtd x1, c1
        cvtd x1, c1
        cvtd x1, c1
        cvtd x1, c1
        cvtd x1, c1
        cvtd x1, c1
        cvtd x1, c1
        cvtd x1, c1
        cvtd x1, c1
        cvtd x1, c1
        cvtd x1, c1
        cvtd x1, c1
        cvtd x1, c1
        cvtd x1, c1
        cvtd x1, c1
        cvtd x1, c1
    b cvtd_toptr_latency_loop

    cvtdtpl_end:
        ret

cvtd_toptr_throughput_loop:
    cbz x0, cvtdtpt_end
    sub x0, x0, #16
        cvtd x9, c1
        cvtd x10, c1
        cvtd x11, c1
        cvtd x12, c1
        cvtd x13, c1
        cvtd x14, c1
        cvtd x15, c1
        cvtd x9, c1
        cvtd x10, c1
        cvtd x11, c1
        cvtd x12, c1
        cvtd x13, c1
        cvtd x14, c1
        cvtd x15, c1
        cvtd x9, c1
        cvtd x10, c1
    b cvtd_toptr_throughput_loop

    cvtdtpt_end:
        ret


cthi_latency_loop:
    cbz x0, cthil_end
    sub x0, x0, #16
        cthi c1, c1, x1
        cthi c1, c1, x1
        cthi c1, c1, x1
        cthi c1, c1, x1
        cthi c1, c1, x1
        cthi c1, c1, x1
        cthi c1, c1, x1
        cthi c1, c1, x1
        cthi c1, c1, x1
        cthi c1, c1, x1
        cthi c1, c1, x1
        cthi c1, c1, x1
        cthi c1, c1, x1
        cthi c1, c1, x1
        cthi c1, c1, x1
        cthi c1, c1, x1
    b cthi_latency_loop

    cthil_end:
        ret

cthi_throughput_loop:
    cbz x0, cthit_end
    sub x0, x0, #16
        cthi c1, c1, x1
        cthi c2, c2, x2
        cthi c3, c3, x3
        cthi c4, c4, x4
        cthi c5, c5, x5
        cthi c6, c6, x6
        cthi c7, c7, x7
        cthi c1, c1, x1
        cthi c2, c2, x2
        cthi c3, c3, x3
        cthi c4, c4, x4
        cthi c5, c5, x5
        cthi c6, c6, x6
        cthi c1, c1, x1
        cthi c2, c2, x2
        cthi c3, c3, x3
    b cthi_throughput_loop

    cthit_end:
        ret

cfhi_latency_loop:
    cbz x0, cfhil_end
    sub x0, x0, #16
        cfhi x1, c1
        cfhi x1, c1
        cfhi x1, c1
        cfhi x1, c1
        cfhi x1, c1
        cfhi x1, c1
        cfhi x1, c1
        cfhi x1, c1
        cfhi x1, c1
        cfhi x1, c1
        cfhi x1, c1
        cfhi x1, c1
        cfhi x1, c1
        cfhi x1, c1
        cfhi x1, c1
        cfhi x1, c1
    b cfhi_latency_loop

    cfhil_end:
        ret

cfhi_throughput_loop:
    cbz x0, cfhit_end
    sub x0, x0, #16
        cfhi x2, c2
        cfhi x3, c3
        cfhi x4, c4
        cfhi x5, c5
        cfhi x6, c6
        cfhi x7, c7
        cfhi x1, c1
        cfhi x2, c2
        cfhi x3, c3
        cfhi x4, c4
        cfhi x5, c5
        cfhi x6, c6
        cfhi x1, c1
        cfhi x2, c2
        cfhi x3, c3
        cfhi x3, c3
    b cfhi_throughput_loop

    cfhit_end:
        ret


cvtd_tocap_latency_loop:
    cbz x0, cvtdtcl_end
    sub x0, x0, #16
        cvtd c1, x1
        cvtd c1, x1
        cvtd c1, x1
        cvtd c1, x1
        cvtd c1, x1
        cvtd c1, x1
        cvtd c1, x1
        cvtd c1, x1
        cvtd c1, x1
        cvtd c1, x1
        cvtd c1, x1
        cvtd c1, x1
        cvtd c1, x1
        cvtd c1, x1
        cvtd c1, x1
        cvtd c1, x1
    b cvtd_tocap_latency_loop

    cvtdtcl_end:
        ret



cvtd_tocap_throughput_loop:
    cbz x0, cvtdtct_end
    sub x0, x0, #16
        cvtd c9, x1
        cvtd c10, x1
        cvtd c11, x1
        cvtd c12, x1
        cvtd c13, x1
        cvtd c14, x1
        cvtd c15, x1
        cvtd c9, x1
        cvtd c10, x1
        cvtd c11, x1
        cvtd c12, x1
        cvtd c13, x1
        cvtd c14, x1
        cvtd c15, x1
        cvtd c9, x1
        cvtd c10, x1
    b cvtd_tocap_throughput_loop

    cvtdtct_end:
        ret


// extern void ldr_cap_latency_loop(long iterations, int* tmp);
ldr_cap_latency_loop:
    str c1, [c1]
    ldrcl_loop:
    cbz x0, ldrcl_end
        sub x0, x0, #16
        ldr c1, [c1]
        ldr c1, [c1]
        ldr c1, [c1]
        ldr c1, [c1]
        ldr c1, [c1]
        ldr c1, [c1]
        ldr c1, [c1]
        ldr c1, [c1]
        ldr c1, [c1]
        ldr c1, [c1]
        ldr c1, [c1]
        ldr c1, [c1]
        ldr c1, [c1]
        ldr c1, [c1]
        ldr c1, [c1]
        ldr c1, [c1]
    b ldr_cap_latency_loop

    ldrcl_end:
        ret

// extern void ldp_cap_latency_loop(long iterations, intptr_t* tmp);
ldp_cap_latency_loop:
    str c1, [x1]
    cbz x0, ldpcl_end
        sub x0, x0, #16
        ldp c1, c2, [x1]
        ldp c1, c2, [x1]
        ldp c1, c2, [x1]
        ldp c1, c2, [x1]
        ldp c1, c2, [x1]
        ldp c1, c2, [x1]
        ldp c1, c2, [x1]
        ldp c1, c2, [x1]
        ldp c1, c2, [x1]
        ldp c1, c2, [x1]
        ldp c1, c2, [x1]
        ldp c1, c2, [x1]
        ldp c1, c2, [x1]
        ldp c1, c2, [x1]
        ldp c1, c2, [x1]
        ldp c1, c2, [x1]
    b ldp_cap_latency_loop

    ldpcl_end:
        ret


stp_cap_throughput_loop:
    stpct_loop:
    cbz x0, stpct_end
        sub x0, x0, #16
        stp c1, c2, [x1, #0]
        stp c1, c2, [x1, #32]
        stp c1, c2, [x1, #64]
        stp c1, c2, [x1, #96]
        stp c1, c2, [x1, #0]
        stp c1, c2, [x1, #32]
        stp c1, c2, [x1, #64]
        stp c1, c2, [x1, #96]
        stp c1, c2, [x1, #0]
        stp c1, c2, [x1, #32]
        stp c1, c2, [x1, #64]
        stp c1, c2, [x1, #96]
        stp c1, c2, [x1, #0]
        stp c1, c2, [x1, #32]
        stp c1, c2, [x1, #64]
        stp c1, c2, [x1, #96]
    b stpct_loop

    stpct_end:
        ret

stp_throughput_loop:
    mov x9, #42
    mov x10, #31
    stpt_loop:
    cbz x0, stpt_end
        sub x0, x0, #16
        stp x9, x10, [x1, #0]
        stp x9, x10, [x1, #16]
        stp x9, x10, [x1, #32]
        stp x9, x10, [x1, #48]
        stp x9, x10, [x1, #64]
        stp x9, x10, [x1, #80]
        stp x9, x10, [x1, #96]
        stp x9, x10, [x1, #112]
        stp x9, x10, [x1, #0]
        stp x9, x10, [x1, #16]
        stp x9, x10, [x1, #32]
        stp x9, x10, [x1, #48]
        stp x9, x10, [x1, #64]
        stp x9, x10, [x1, #80]
        stp x9, x10, [x1, #96]
        stp x9, x10, [x1, #112]
    b stpt_loop

    stpt_end:
        ret

stp_cap_inplace_throughput_loop:
    stpcit_loop:
    cbz x0, stpcit_end
        sub x0, x0, #16
        stp c1, c2, [x1]
        stp c1, c2, [x1]
        stp c1, c2, [x1]
        stp c1, c2, [x1]
        stp c1, c2, [x1]
        stp c1, c2, [x1]
        stp c1, c2, [x1]
        stp c1, c2, [x1]
        stp c1, c2, [x1]
        stp c1, c2, [x1]
        stp c1, c2, [x1]
        stp c1, c2, [x1]
        stp c1, c2, [x1]
        stp c1, c2, [x1]
        stp c1, c2, [x1]
        stp c1, c2, [x1]
    b stpcit_loop

    stpcit_end:
        ret

stp_inplace_throughput_loop:
    mov x9, #42
    mov x10, #31
    stpit_loop:
    cbz x0, stpit_end
        sub x0, x0, #16
        stp x9, x10, [x1]
        stp x9, x10, [x1]
        stp x9, x10, [x1]
        stp x9, x10, [x1]
        stp x9, x10, [x1]
        stp x9, x10, [x1]
        stp x9, x10, [x1]
        stp x9, x10, [x1]
        stp x9, x10, [x1]
        stp x9, x10, [x1]
        stp x9, x10, [x1]
        stp x9, x10, [x1]
        stp x9, x10, [x1]
        stp x9, x10, [x1]
        stp x9, x10, [x1]
        stp x9, x10, [x1]
    b stpit_loop

    stpit_end:
        ret

// extern void str_cap_throughput_loop(long iterations, int* tmp);
ldr_cap_throughput_loop:
    cbz x0, ldrct_end
        sub x0, x0, #16
        ldr c10, [c1]
        ldr c13, [c1]
        ldr c14, [c1]
        ldr c9, [c1]
        ldr c12, [c1]
        ldr c11, [c1]
        ldr c15, [c1]
        ldr c9, [c1]
        ldr c12, [c1]
        ldr c11, [c1]
        ldr c13, [c1]
        ldr c10, [c1]
        ldr c14, [c1]
        ldr c15, [c1]
        ldr c9, [c1]
        ldr c10, [c1]
    b ldr_cap_throughput_loop

    ldrct_end:
        ret

// extern void ldp_throughput_loop(long iterations, int* tmp);
ldp_throughput_loop:
    cbz x0, ldpt_end
        sub x0, x0, #16
        ldp x10, x11, [x1]
        ldp x12, x13, [x1]
        ldp x14, x15, [x1]
        ldp x9, x10, [x1]
        ldp x11, x12, [x1]
        ldp x13, x14, [x1]
        ldp x15, x9, [x1]
        ldp x10, x11, [x1]
        ldp x12, x13, [x1]
        ldp x14, x15, [x1]
        ldp x9, x10, [x1]
        ldp x11, x12, [x1]
        ldp x13, x14, [x1]
        ldp x15, x9, [x1]
        ldp x10, x11, [x1]
        ldp x12, x13, [x1]
    b ldp_throughput_loop

    ldpt_end:
        ret

// extern void ldp_cap_throughput_loop(long iterations, int* tmp);
ldp_cap_throughput_loop:
    cbz x0, ldpcpt_end
        sub x0, x0, #16
        ldp c10, c11, [x1]
        ldp c12, c13, [x1]
        ldp c14, c15, [x1]
        ldp c9, c10, [x1]
        ldp c11, c12, [x1]
        ldp c13, c14, [x1]
        ldp c15, c9, [x1]
        ldp c10, c11, [x1]
        ldp c12, c13, [x1]
        ldp c14, c15, [x1]
        ldp c9, c10, [x1]
        ldp c11, c12, [x1]
        ldp c13, c14, [x1]
        ldp c15, c9, [x1]
        ldp c10, c11, [x1]
        ldp c12, c13, [x1]
    b ldp_cap_throughput_loop

    ldpcpt_end:
        ret

ldr_throughput_loop:
    cbz x0, ldrt_end
        sub x0, x0, #16
        ldr x10, [c1]
        ldr x13, [c1]
        ldr x14, [c1]
        ldr x9, [c1]
        ldr x12, [c1]
        ldr x11, [c1]
        ldr x15, [c1]
        ldr x9, [c1]
        ldr x12, [c1]
        ldr x11, [c1]
        ldr x13, [c1]
        ldr x10, [c1]
        ldr x14, [c1]
        ldr x15, [c1]
        ldr x9, [c1]
        ldr x10, [c1]
    b ldr_throughput_loop

    ldrt_end:
        ret

ldr_latency_loop:
    mov x9, #0
    ldrl_loop:
    cbz x0, ldrl_end
        sub x0, x0, #16
        ldr x9, [c1, x9]
        ldr x9, [c1, x9]
        ldr x9, [c1, x9]
        ldr x9, [c1, x9]
        ldr x9, [c1, x9]
        ldr x9, [c1, x9]
        ldr x9, [c1, x9]
        ldr x9, [c1, x9]
        ldr x9, [c1, x9]
        ldr x9, [c1, x9]
        ldr x9, [c1, x9]
        ldr x9, [c1, x9]
        ldr x9, [c1, x9]
        ldr x9, [c1, x9]
        ldr x9, [c1, x9]
        ldr x9, [c1, x9]
    b ldrl_loop
    ldrl_end:
        ret

str_throughput_loop:
    mov x9, #42
    strt_loop:
    cbz x0, strt_end
        sub x0, x0, #16
        str x9, [c1, #0]
        str x9, [c1, #8]
        str x9, [c1, #16]
        str x9, [c1, #24]
        str x9, [c1, #32]
        str x9, [c1, #40]
        str x9, [c1, #48]
        str x9, [c1, #56]
        str x9, [c1, #64]
        str x9, [c1, #72]
        str x9, [c1, #80]
        str x9, [c1, #88]
        str x9, [c1, #96]
        str x9, [c1, #104]
        str x9, [c1, #112]
        str x9, [c1, #120]
            b strt_loop

    strt_end:
        ret

str_inplace_throughput_loop:
    mov x9, #42
    strit_loop:
    cbz x0, strit_end
        sub x0, x0, #16
        str x9, [c1]
        str x9, [c1]
        str x9, [c1]
        str x9, [c1]
        str x9, [c1]
        str x9, [c1]
        str x9, [c1]
        str x9, [c1]
        str x9, [c1]
        str x9, [c1]
        str x9, [c1]
        str x9, [c1]
        str x9, [c1]
        str x9, [c1]
        str x9, [c1]
        str x9, [c1]
            b strit_loop

    strit_end:
        ret

str_cap_throughput_loop:
    cbz x0, strct_end
        sub x0, x0, #16
        str c1, [c1, #0]
        str c1, [c1, #16]
        str c1, [c1, #32]
        str c1, [c1, #48]
        str c1, [c1, #64]
        str c1, [c1, #80]
        str c1, [c1, #96]
        str c1, [c1, #112]
        str c1, [c1, #0]
        str c1, [c1, #16]
        str c1, [c1, #32]
        str c1, [c1, #48]
        str c1, [c1, #64]
        str c1, [c1, #80]
        str c1, [c1, #96]
        str c1, [c1, #112]
            b str_cap_throughput_loop

    strct_end:
        ret

str_cap_inplace_throughput_loop:
    cbz x0, strcit_end
        sub x0, x0, #16
        str c1, [c1]
        str c1, [c1]
        str c1, [c1]
        str c1, [c1]
        str c1, [c1]
        str c1, [c1]
        str c1, [c1]
        str c1, [c1]
        str c1, [c1]
        str c1, [c1]
        str c1, [c1]
        str c1, [c1]
        str c1, [c1]
        str c1, [c1]
        str c1, [c1]
        str c1, [c1]
            b str_cap_inplace_throughput_loop

    strcit_end:
        ret


ldar_throughput_loop:
    cbz x0, ldart_end
        sub x0, x0, #16
        ldar x10, [x1]
        ldar x13, [x1]
        ldar x14, [x1]
        ldar x9, [x1]
        ldar x12, [x1]
        ldar x11, [x1]
        ldar x15, [x1]
        ldar x9, [x1]
        ldar x12, [x1]
        ldar x11, [x1]
        ldar x13, [x1]
        ldar x10, [x1]
        ldar x14, [x1]
        ldar x15, [x1]
        ldar x9, [x1]
        ldar x10, [x1]
    b ldar_throughput_loop

    ldart_end:
        ret

// extern void stlr_throughput_loop(long iterations, int* tmp);
stlr_throughput_loop:
    mov x9, #42
    stlrt_loop:
    cbz x0, stlrt_end
        sub x0, x0, #16
        stlr x9, [x1]
        stlr x9, [x1]
        stlr x9, [x1]
        stlr x9, [x1]
        stlr x9, [x1]
        stlr x9, [x1]
        stlr x9, [x1]
        stlr x9, [x1]
        stlr x9, [x1]
        stlr x9, [x1]
        stlr x9, [x1]
        stlr x9, [x1]
        stlr x9, [x1]
        stlr x9, [x1]
        stlr x9, [x1]
        stlr x9, [x1]
            b stlrt_loop

    stlrt_end:
        ret


// Latency loop for three operand instruction:
//   mnem dst, src1, src2
//
// x0 = iteration count (must be multiple of 16)
// You choose the operand pattern so that it creates a dependency if you care
// (for example same register in dst and src).

.macro GEN_3OP_LAT name, mnem, dst, src1, src2
.global \name
\name:
1:
    cbz     x0, 2f
    sub     x0, x0, #16
    .rept   16
        \mnem   \dst, \src1, \src2
    .endr
    cbnz    x0, 1b
2:
    ret
.endm

// Throughput loop for three operand instruction:
//   mnem dst, src1, src2
//
// Uses eight independent destination registers, repeated twice
// for 16 instructions per loop.

.macro GEN_3OP_TP name, mnem, dst0, dst1, dst2, dst3, dst4, dst5, dst6, dst7, src1, src2
.global \name
\name:
1:
    cbz     x0, 2f
    sub     x0, x0, #16

    \mnem   \dst0, \src1, \src2
    \mnem   \dst1, \src1, \src2
    \mnem   \dst2, \src1, \src2
    \mnem   \dst3, \src1, \src2
    \mnem   \dst4, \src1, \src2
    \mnem   \dst5, \src1, \src2
    \mnem   \dst6, \src1, \src2
    \mnem   \dst7, \src1, \src2

    \mnem   \dst0, \src1, \src2
    \mnem   \dst1, \src1, \src2
    \mnem   \dst2, \src1, \src2
    \mnem   \dst3, \src1, \src2
    \mnem   \dst4, \src1, \src2
    \mnem   \dst5, \src1, \src2
    \mnem   \dst6, \src1, \src2
    \mnem   \dst7, \src1, \src2

    b       1b
2:
    ret
.endm

// Latency loop for two operand instruction:
//   mnem dst, src
//
// Again, you choose dst and src so it creates a chain if that is valid.
// For many of the GC* instructions a strict latency chain is questionable,
// so you may just never use this macro for them.

// Latency loop for 2 operand instructions: mnem dst, src
.macro GEN_2OP_LAT name, mnem, dst, src
    .global \name
\name:
1:
    cbz     x0, 2f
    sub     x0, x0, #16
    .rept   16
        \mnem   \dst, \src
    .endr
    cbnz    x0, 1b
2:
    ret
.endm

// Throughput loop for 2 operand instructions: mnem dst, src
.macro GEN_2OP_TP name, mnem, dst0, dst1, dst2, dst3, dst4, dst5, dst6, dst7, src
    .global \name
\name:
1:
    cbz     x0, 2f
    sub     x0, x0, #16

    \mnem   \dst0, \src
    \mnem   \dst1, \src
    \mnem   \dst2, \src
    \mnem   \dst3, \src
    \mnem   \dst4, \src
    \mnem   \dst5, \src
    \mnem   \dst6, \src
    \mnem   \dst7, \src

    \mnem   \dst0, \src
    \mnem   \dst1, \src
    \mnem   \dst2, \src
    \mnem   \dst3, \src
    \mnem   \dst4, \src
    \mnem   \dst5, \src
    \mnem   \dst6, \src
    \mnem   \dst7, \src

    b       1b
2:
    ret
.endm

// Throughput loop for 1 operand instructions: mnem op
.macro GEN_1OP_TP name, mnem, op0, op1, op2, op3, op4, op5, op6, op7
    .global \name
\name:
1:
    cbz     x0, 2f
    sub     x0, x0, #16

    \mnem   \op0
    \mnem   \op1
    \mnem   \op2
    \mnem   \op3
    \mnem   \op4
    \mnem   \op5
    \mnem   \op6
    \mnem   \op7

    \mnem   \op0
    \mnem   \op1
    \mnem   \op2
    \mnem   \op3
    \mnem   \op4
    \mnem   \op5
    \mnem   \op6
    \mnem   \op7

    b       1b
2:
    ret
.endm

// =========================================
// Z conversions: CVTDZ, CVTPZ, CVTZ
// =========================================
// Forms assumed:
//   cvtdz  Cd, Xn
//   cvtpz  Cd, Xn
//   cvtz   Cd, Xn

// CVTDZ pointer -> capability (DDC based)
GEN_2OP_LAT cvtdz_tocap_latency_loop, cvtdz, c2, x1
GEN_2OP_TP  cvtdz_tocap_throughput_loop, cvtdz, c9, c10, c11, c12, c13, c14, c15, c16, x1

GEN_2OP_LAT cvtpz_tocap_latency_loop, cvtpz, c2, x1
GEN_2OP_TP  cvtpz_tocap_throughput_loop, cvtpz, c9, c10, c11, c12, c13, c14, c15, c16, x1

GEN_3OP_LAT cvtz_tocap_latency_loop, cvtz, c2, c1, x1
GEN_3OP_TP  cvtz_tocap_throughput_loop, cvtz, c9, c10, c11, c12, c13, c14, c15, c16, c1, x1


// =========================================
// Capability getters: GC*
// =========================================
// Forms assumed:
//   gcbase  Xd, Cn
//   gclen   Xd, Cn
//   gclim   Xd, Cn
//   gcoff   Xd, Cn
//   gcperm  Xd, Cn
//   gctype  Xd, Cn
//   gcvalue Xd, Cn
//   gcflgs  Xd, Cn
//   gcseal  Xd, Cn
//   gctag   Xd, Cn
//
// These are simple ALU like getters, so throughput is the main thing.
// Latency hardly matters in real code and would need more careful
// dependency design, so skip it for now.

GEN_2OP_TP gcbase_throughput_loop, gcbase, x9, x10, x11, x12, x13, x14, x15, x16, c1
GEN_2OP_TP gclen_throughput_loop, gclen, x9, x10, x11, x12, x13, x14, x15, x16, c1
GEN_2OP_TP gclim_throughput_loop, gclim, x9, x10, x11, x12, x13, x14, x15, x16, c1
GEN_2OP_TP gcoff_throughput_loop, gcoff, x9, x10, x11, x12, x13, x14, x15, x16, c1
GEN_2OP_TP gcperm_throughput_loop, gcperm, x9, x10, x11, x12, x13, x14, x15, x16, c1
GEN_2OP_TP gctype_throughput_loop, gctype, x9, x10, x11, x12, x13, x14, x15, x16, c1
GEN_2OP_TP gcvalue_throughput_loop, gcvalue, x9, x10, x11, x12, x13, x14, x15, x16, c1
GEN_2OP_TP gcflgs_throughput_loop, gcflgs, x9, x10, x11, x12, x13, x14, x15, x16, c1
GEN_2OP_TP gcseal_throughput_loop, gcseal, x9, x10, x11, x12, x13, x14, x15, x16, c1
GEN_2OP_TP gctag_throughput_loop, gctag, x9, x10, x11, x12, x13, x14, x15, x16, c1

// =========================================
// Capability copies and type/value copies
// =========================================
// Forms assumed:
//   cpy      Cd, Cs
//   cpytype  Cd, Cs
//   cpyvalue Cd, Cs

GEN_2OP_LAT cpy_latency_loop, cpy, c3, c2
GEN_2OP_TP  cpy_throughput_loop, cpy, c9, c10, c11, c12, c13, c14, c15, c16, c1

GEN_3OP_LAT cpytype_latency_loop, cpytype, c3, c2, c1
GEN_3OP_TP  cpytype_throughput_loop, cpytype, c9, c10, c11, c12, c13, c14, c15, c16, c1, c2

GEN_3OP_LAT cpyvalue_latency_loop, cpyvalue, c3, c2, c1
GEN_3OP_TP  cpyvalue_throughput_loop, cpyvalue, c9, c10, c11, c12, c13, c14, c15, c16, c1, c2


// =========================================
// Rounding and alignment: RRLEN, RRMASK, ALIGND, ALIGNU
// =========================================
// Forms assumed:
//   rrlen  Cd, Cs
//   rrmask Cd, Cs
//   alignd Cd, Cs
//   alignu Cd, Cs

GEN_2OP_LAT rrlen_latency_loop, rrlen, x2, x1
GEN_2OP_TP  rrlen_throughput_loop, rrlen, x9, x10, x11, x12, x13, x14, x15, x16, x1

GEN_2OP_LAT rrmask_latency_loop, rrmask, x2, x1
GEN_2OP_TP  rrmask_throughput_loop, rrmask, x9, x10, x11, x12, x13, x14, x15, x16, x1

GEN_3OP_LAT alignd_latency_loop, alignd, c2, c1, #0
GEN_3OP_TP  alignd_throughput_loop, alignd, c9, c10, c11, c12, c13, c14, c15, c16, c1, #0

GEN_3OP_LAT alignu_latency_loop, alignu, c2, c1, #0
GEN_3OP_TP  alignu_throughput_loop, alignu, c9, c10, c11, c12, c13, c14, c15, c16, c1, #0


// =========================================
// Permission and tag setters: CLRPERM, SCTAG
// =========================================
// Here I only cover the register form of CLRPERM, not the immediate one.
//
// Forms assumed:
//   clrperm Cd, Cs

GEN_3OP_TP clrperm_throughput_loop, clrperm, c9, c10, c11, c12, c13, c14, c15, c16, c1, x2
// GEN_3OP_TP sctag_throughput_loop, sctag, c9, c10, c11, c12, c13, c14, c15, c16, c1, x2


// =========================================
// Offset, flags, and value setters: SCOFF, SCFLGS, SCVALUE
// =========================================
// The register forms have an extra integer operand for the new
// offset or flags or value. That is a three operand pattern.
//
// Forms assumed:
//   scoff   Cd, Cs, Xm
//   scflgs  Cd, Cs, Xm
//   scvalue Cd, Cs, Xm
//   scbnds  Cd, Cs, Xm
//   scbndse Cd, Cs, Xm
//
// For latency chains this would need Xm tied to something or fed
// from a previous result, which is ugly. So only throughput here.
// Bounds tightening repeatedly can eventually fail if Xm is not zero,
// so again just do throughput with an Xm provided by the harness.

GEN_3OP_TP scoff_throughput_loop, scoff, c9, c10, c11, c12, c13, c14, c15, c16, c1, x1
GEN_3OP_TP scflgs_throughput_loop, scflgs, c9, c10, c11, c12, c13, c14, c15, c16, c1, x1
GEN_3OP_TP scvalue_throughput_loop, scvalue, c9, c10, c11, c12, c13, c14, c15, c16, c1, x1
GEN_3OP_TP scbnds_throughput_loop, scbnds, c9, c10, c11, c12, c13, c14, c15, c16, c1, x1
GEN_3OP_TP scbndse_throughput_loop, scbndse, c9, c10, c11, c12, c13, c14, c15, c16, c1, x1


// =========================================
// Sealing and unsealing: SEAL, CSEAL, UNSEAL
// =========================================
// Forms assumed (register versions):
//   seal   Cd, Cs
//   cseal  Cd, Cs
//   unseal Cd, Cs
//
// Repeated sealing on already sealed caps and repeated unseal
// are semantically odd but should be fine for throughput.

GEN_3OP_TP seal_throughput_loop, seal, c9, c10, c11, c12, c13, c14, c15, c16, c1, c2
GEN_3OP_TP cseal_throughput_loop, cseal, c9, c10, c11, c12, c13, c14, c15, c16, c1, c2
GEN_3OP_TP unseal_throughput_loop, unseal, c9, c10, c11, c12, c13, c14, c15, c16, c1, c2



// =========================================
// Checks: CHKSS, CHKTGD (flags only)
// =========================================
// These only set PSTATE flags and do not write a destination
// register, so a pure register latency chain is not meaningful.
// Still, you can time throughput on flag setting alone.
//
// Forms assumed:
//   chkss  Cd, Cs
//   chktgd Cs
// For chktgd, ignore the dst argument in the macro and just
// repeat the source capability. The assembler will drop the
// extra operand if the real encoding is one operand. If it does
// not, you will need a dedicated one operand macro.

GEN_2OP_TP chkss_throughput_loop, chkss, c9, c10, c11, c12, c13, c14, c15, c16, c1
GEN_3OP_TP chkssu_throughput_loop, chkssu, c9, c10, c11, c12, c13, c14, c15, c16, c1, c2
GEN_1OP_TP chktgd_throughput_loop, chktgd, c9, c10, c11, c12, c13, c14, c15, c16

// =========================================
// Pointer Arithmetic: ADD, SUB (on capabilities)
// =========================================
GEN_3OP_TP add_throughput_loop, add, c9, c10, c11, c12, c13, c14, c15, c16, c1, #0
GEN_3OP_TP sub_throughput_loop, sub, c9, c10, c11, c12, c13, c14, c15, c16, c1, #0

// =========================================
// Flag Bitwise: ORRFLGS, BICFLGS
// =========================================
GEN_3OP_TP orrflgs_throughput_loop, orrflgs, c9, c10, c11, c12, c13, c14, c15, c16, c1, x2
GEN_3OP_TP bicflgs_throughput_loop, bicflgs, c9, c10, c11, c12, c13, c14, c15, c16, c1, x2

// =========================================
// Equality: CHKEQ
// =========================================
// Syntax: chkeq cN, cM
GEN_2OP_TP chkeq_throughput_loop, chkeq, c9, c10, c11, c12, c13, c14, c15, c16, c1

// =========================================
// Load Exclusive: LDXR
// Store Exclusive: STXR
// =========================================
// Syntax: ldxr cD, [xN]
//         stxr xS, cT, [xN]
GEN_2OP_TP ldxr_throughput_loop, ldxr, x9, x10, x11, x12, x13, x14, x15, x16, [x1]
GEN_2OP_TP ldxr_cap_throughput_loop, ldxr, c9, c10, c11, c12, c13, c14, c15, c16, [x1]

.global stxr_throughput_loop
stxr_throughput_loop:
    cbz x0, stxr_end
    sub x0, x0, #16
    stxr w9, x2, [x1]
    stxr w9, x2, [x1]
    stxr w9, x2, [x1]
    stxr w9, x2, [x1]
    stxr w9, x2, [x1]
    stxr w9, x2, [x1]
    stxr w9, x2, [x1]
    stxr w9, x2, [x1]
    stxr w9, x2, [x1]
    stxr w9, x2, [x1]
    stxr w9, x2, [x1]
    stxr w9, x2, [x1]
    stxr w9, x2, [x1]
    stxr w9, x2, [x1]
    stxr w9, x2, [x1]
    stxr w9, x2, [x1]
    b stxr_throughput_loop
stxr_end:
    ret

.global stxr_cap_throughput_loop
stxr_cap_throughput_loop:
    cbz x0, stxr_cap_end
    sub x0, x0, #16
    stxr w9, c2, [x1]
    stxr w9, c2, [x1]
    stxr w9, c2, [x1]
    stxr w9, c2, [x1]
    stxr w9, c2, [x1]
    stxr w9, c2, [x1]
    stxr w9, c2, [x1]
    stxr w9, c2, [x1]
    stxr w9, c2, [x1]
    stxr w9, c2, [x1]
    stxr w9, c2, [x1]
    stxr w9, c2, [x1]
    stxr w9, c2, [x1]
    stxr w9, c2, [x1]
    stxr w9, c2, [x1]
    stxr w9, c2, [x1]
    b stxr_cap_throughput_loop
stxr_cap_end:
    ret

// =========================================
// Atomics: CAS, SWP
// =========================================

// CAS: cas cS, cT, [xN]
// Compare cS with [xN], if eq store cT, else load [xN] into cS.
.global cas_throughput_loop
cas_throughput_loop:
    cbz x0, cast_end
    sub x0, x0, #16
    cas c2, c3, [x1]
    cas c2, c3, [x1]
    cas c2, c3, [x1]
    cas c2, c3, [x1]
    cas c2, c3, [x1]
    cas c2, c3, [x1]
    cas c2, c3, [x1]
    cas c2, c3, [x1]
    cas c2, c3, [x1]
    cas c2, c3, [x1]
    cas c2, c3, [x1]
    cas c2, c3, [x1]
    cas c2, c3, [x1]
    cas c2, c3, [x1]
    cas c2, c3, [x1]
    cas c2, c3, [x1]
    b cas_throughput_loop
cast_end:
    ret

// SWP: swp cS, cT, [xN]
// Store cS to [xN], return old value in cT
.global swp_throughput_loop
swp_throughput_loop:
    cbz x0, swpt_end
    sub x0, x0, #16
    swp c2, c3, [x1]
    swp c2, c3, [x1]
    swp c2, c3, [x1]
    swp c2, c3, [x1]
    swp c2, c3, [x1]
    swp c2, c3, [x1]
    swp c2, c3, [x1]
    swp c2, c3, [x1]
    swp c2, c3, [x1]
    swp c2, c3, [x1]
    swp c2, c3, [x1]
    swp c2, c3, [x1]
    swp c2, c3, [x1]
    swp c2, c3, [x1]
    swp c2, c3, [x1]
    swp c2, c3, [x1]
    b swp_throughput_loop
swpt_end:
    ret
