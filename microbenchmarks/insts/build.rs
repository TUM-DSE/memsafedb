fn main() {
    let arch = std::env::var("CARGO_CFG_TARGET_ARCH").unwrap();

    let mut b = cc::Build::new();
    match arch.as_str() {
        "aarch64" => {
            b.compiler("clang");
            b.file("src/benches/mte/insts.s");
            b.flag("-march=armv8.5-a+memtag");
            b.compile("mte_insts");
            let mut b = cc::Build::new();
            b.compiler("clang");
            b.file("src/benches/pac/insts.s");
            b.flag("-march=armv8.3-a");
            b.compile("pac_insts");

            let morello_clang = std::env::var("CLANG_HYBRID").expect("CLANG_HYBRID to be set");
            b.compiler(&morello_clang);
            b.file("src/benches/cheri/insts.s");
            b.flag("-march=morello");
            b.compile("cheri_insts");
        }
        "x86_64" => {
            let x86_clang = std::env::var("CLANG_X86_64").expect("CLANG_X86_64 to be set");
            b.compiler(&x86_clang);
            b.file("src/benches/mpk/insts.s");
            b.compile("mpk_insts");
        }
        _ => panic!("unsupported architecture {arch}"),
    }

    println!("cargo::rerun-if-changed=build.rs");
    println!("cargo::rerun-if-changed=src/benches/mte/insts.s");
    println!("cargo::rerun-if-changed=src/benches/pac/insts.s");
    println!("cargo::rerun-if-changed=src/benches/cheri/insts.s");
    println!("cargo::rerun-if-changed=src/benches/mpk/insts.s");
}
