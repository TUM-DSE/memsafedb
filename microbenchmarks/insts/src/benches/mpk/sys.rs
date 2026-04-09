const SYS_PKEY_ALLOC: libc::c_long = 330;
const SYS_PKEY_FREE: libc::c_long = 331;
const SYS_PKEY_MPROTECT: libc::c_long = 329;

pub unsafe fn pkey_alloc(flags: i32, access: i32) -> i32 {
    unsafe {
        libc::syscall(
            SYS_PKEY_ALLOC,
            flags as libc::c_long,
            access as libc::c_long,
        ) as i32
    }
}

pub unsafe fn pkey_free(pkey: i32) -> i32 {
    unsafe { libc::syscall(SYS_PKEY_FREE, pkey as libc::c_long) as i32 }
}

pub unsafe fn pkey_mprotect(addr: *mut libc::c_void, len: usize, prot: i32, pkey: i32) -> i32 {
    unsafe {
        libc::syscall(
            SYS_PKEY_MPROTECT,
            addr,
            len as libc::c_long,
            prot as libc::c_long,
            pkey as libc::c_long,
        ) as i32
    }
}
