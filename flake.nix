{
  description = "Flake for the memsafeDB project";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-25.05";
    oldnixpkgs.url = "github:nixos/nixpkgs?ref=nixos-23.05";
    flake-utils.url = "github:numtide/flake-utils";
    doctor-cluster-repo.url = "github:TUM-DSE/doctor-cluster-config";
    nur-kapack = {
      url = "github:oar-team/nur-kapack";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { 
    self
    , nixpkgs 
    , oldnixpkgs
    , flake-utils
    , doctor-cluster-repo
    , nur-kapack
  }@inputs: flake-utils.lib.eachDefaultSystem (system:
  let
    pkgs = import nixpkgs { inherit system; };
    oldpkgs = import oldnixpkgs { inherit system; };
    doctor-pkgs = doctor-cluster-repo.packages.${system};
    execo = nur-kapack.packages.${system}.execo;
    glibc-mte = pkgs.glibc.overrideAttrs (
    final: prev_:
      {
        configureFlags = prev_.configureFlags ++ [ "--enable-memory-tagging" ];
      }
    );
    malloc-mte = pkgs.graphene-hardened-malloc.overrideAttrs (
      final: prev_:
      {
        preBuild = ''
          substituteInPlace Makefile --replace 'CPPFLAGS := $(CPPFLAGS) -D_GNU_SOURCE -I include' 'CPPFLAGS := $(CPPFLAGS) -D_GNU_SOURCE -DHAS_ARM_MTE -I include' --replace 'SHARED_FLAGS += -march=native' 'SHARED_FLAGS += -march=armv8.5-a+memtag'
          '';
      }
    );
    ycsb-bin = pkgs.callPackage ./nix/ycsb.nix {};
    python-pkgs = with pkgs.python3Packages; [
      execo
      requests
      matplotlib
      seaborn
      scipy
      pyyaml
      tqdm
    ];
    sharedPkgs = with pkgs; [
      gnumake 
      pax-utils 
      pkg-config 
      gdb 
      just
      cmake 
      boost
      gperftools
      triton-llvm
      jemalloc
      tbb
      automake
      scons
      bison
      flex
      python3
      python-pkgs 
      zlib
      maven
      ycsb-bin
    ];
  in
  {
    packages = {
        morello-glibc = oldpkgs.glibc.override { src=pkgs.fetchurl; };
        hardened-malloc = pkgs.graphene-hardened-malloc;
        malloc-mte = malloc-mte;
        glibc-mte = glibc-mte;
        ycsb-bin = pkgs.callPackage ./nix/ycsb.nix {};
      };
      devShells = {
        "eliza" = pkgs.mkShell {
          name="memsafedb-devshell-eliza";
          buildInputs = with pkgs; [
            clang
            glibc-mte.out
            #malloc-mte
          ] ++ sharedPkgs;
          MTE_MALLOC= "${malloc-mte}/lib/libhardened_malloc.so";
          NIX_ENFORCE_NO_NATIVE="0";
        };
        "ace-aarch64" = pkgs.mkShell {
          name="memsafedb-devshell-ace-hybrid";
          buildInputs = with pkgs; [
            pkgsStatic.clang
          ] ++ sharedPkgs;
          CLANG_HYBRID_PATH = "${doctor-pkgs.clang-morello}";
          NIX_ENFORCE_NO_NATIVE="0";

          # Needed to fix https://github.com/NixOS/nixpkgs/issues/177129
          shellHook = ''
            touch /tmp/libgcc_eh.a
          '';
        };
        "ace-cheri" = pkgs.mkShell {
          name="memsafedb-devshell-ace-pure";
          buildInputs = with pkgs; [
            #doctor-pkgs.llvm-morello-purecap
            #doctor-pkgs.musl-morello-purecap
          ] ++ sharedPkgs;
          #CLANG_PURECAP_PATH = "${doctor-pkgs.llvm-morello-purecap}";
          #PURECAP_LIBC = "${doctor-pkgs.musl-morello-purecap}";
          #LLVM_PATH = "${doctor-pkgs.llvm-morello-purecap}";
          #GCC_PATH = "${pkgs.gcc-unwrapped}";
          #GCC_INCLUDES = "-I${pkgs.gcc-unwrapped}/include/c++/14.3.0 -I${pkgs.gcc-unwrapped}/include/c++/14.3.0/aarch64-unknown-linux-gnu -I${pkgs.gcc-unwrapped}/include/c++/14.3.0/backward -I${pkgs.gcc-unwrapped}/lib/gcc/aarch64-unknown-linux-gnu/14.3.0/include -I${pkgs.gcc-unwrapped}/include -I${pkgs.gcc-unwrapped}/lib/gcc/aarch64-unknown-linux-gnu/14.3.0/include-fixed";

          shellHook = ''
            source /morello/env/morello-sdk
          '';
        };
      };
    });
  }
