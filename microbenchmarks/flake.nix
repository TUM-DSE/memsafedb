{
  description = "A devShell example";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.05";
    nixpkgs-unstable.url = "github:NixOS/nixpkgs/nixos-unstable";
    rust-overlay.url = "github:oxalica/rust-overlay";
    flake-utils.url = "github:numtide/flake-utils";
    doctor-cluster.url = "github:TUM-DSE/doctor-cluster-config";
    doctor-cluster.inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs =
    {
      self,
      nixpkgs,
      rust-overlay,
      flake-utils,
      doctor-cluster,
      nixpkgs-unstable,
      ...
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        overlays = [ (import rust-overlay) ];
        pkgs = import nixpkgs {
          inherit system overlays;
        };
        doctorPackages = doctor-cluster.packages.${system};
        rustVersion = "1.91.1";
        myRust = pkgs.rust-bin.stable."${rustVersion}".default.override {
          extensions = [ "rust" ];
          targets = [
            "aarch64-unknown-linux-musl"
            "x86_64-unknown-linux-gnu"
          ];
        };
        unstablePkgs = import nixpkgs-unstable {
          inherit system;
        };
        # HACK: work around https://github.com/NixOS/nixpkgs/issues/177129
        # Though this is an issue between Clang and GCC,
        # so it may not get fixed anytime soon...
        empty-libgcc_eh = pkgs.stdenv.mkDerivation {
          pname = "empty-libgcc_eh";
          version = "0";
          dontUnpack = true;
          installPhase = ''
            mkdir -p "$out"/lib
            "${pkgs.binutils}"/bin/ar r "$out"/lib/libgcc_eh.a
          '';
        };
        glibc-mte = pkgs.glibc.overrideAttrs (
          final: prev_: {
            configureFlags = prev_.configureFlags ++ [ "--enable-memory-tagging" ];
          }
        );

        # bintools-mte = pkgs.wrapBintoolsWith {
        #   bintools = pkgs.binutils-unwrapped;
        #   libc = glibc-mte;
        # };

        # clang-mte = pkgs.wrapCCWith {
        #   cc = pkgs.llvmPackages.clang-unwrapped;
        #   bintools = bintools-mte;
        #   libc = glibc-mte;
        # };
        myPython = (
          pkgs.python311.withPackages (p: [
            p.numpy
            p.matplotlib
            p.seaborn
            p.scipy
            p.natsort
            p.pandas
          ])
        );
      in
      with pkgs;
      {
        devShells.default = mkShell {
          nativeBuildInputs = [
            doctorPackages.llvm-morello-purecap
            myRust
          ];
          buildInputs = [
            # crossRust
            mold
            unstablePkgs.just
            cargo-sort
            pkgsStatic.clang

            myPython
            texliveFull
            empty-libgcc_eh
          ];
          env = {
            CLANG = "${pkgs.pkgsStatic.clang}/bin/clang";
            CLANG_HYBRID = "${doctorPackages.clang-morello}/bin/clang";
            CLANG_PURECAP = "${doctorPackages.llvm-morello-purecap}/bin/clang";
            MUSL_PATH = "${doctorPackages.musl-morello-purecap}";
            LLVM_PATH = "${doctorPackages.llvm-morello-purecap}";

            CLANG_X86_64 = "${pkgs.pkgsCross.gnu64.buildPackages.clang}/bin/x86_64-unknown-linux-gnu-clang";
            CARGO_TARGET_X86_64_UNKNOWN_LINUX_GNU_LINKER = "${pkgs.pkgsCross.gnu64.buildPackages.clang}/bin/x86_64-unknown-linux-gnu-clang";

            RUST_BACKTRACE = "full";
          };
        };
        devShells.glibc-mte = mkShell {
          buildInputs = [
            glibc-mte
            pkgs.clang
            empty-libgcc_eh
          ];
          env = {
            CLANG = "${pkgs.clang}/bin/clang";
          };
        };
        devShells.plot = mkShell {
          buildInputs = [
            myPython
            texliveFull
          ];
        };
      }
    );
}
