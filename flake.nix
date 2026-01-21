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
    selfpkgs = self.packages.${system};
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
    py-tpcc = pkgs.callPackage ./nix/py-tpcc {};
    python-pkgs = with pkgs.python3Packages; [
      execo
      requests
      matplotlib
      seaborn
      scipy
      pyyaml
      tqdm
      natsort
      psutil
    ];
    mysql_jdbc_jar = "${pkgs.mysql_jdbc}/share/java/mysql-connector-j.jar";
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
      py-tpcc
      lldb
      openssl
      libtirpc
      rpcsvc-proto
      mysql_jdbc
      unixtools.netstat
      sysbench
    ];
  in
  {
    packages = rec {
        morello-glibc = oldpkgs.glibc.override { src=pkgs.fetchurl; };
        hardened-malloc = pkgs.graphene-hardened-malloc;
        malloc-mte = malloc-mte;
        glibc-mte = glibc-mte;
        binutils-morello = pkgs.callPackage ./nix/binutils.nix {};
        gcc-morello = pkgs.callPackage ./nix/gcc.nix { inherit binutils-morello; };
        ycsb-bin = pkgs.callPackage ./nix/ycsb.nix {};
        py-tpcc = pkgs.callPackage ./nix/py-tpcc {};
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
          MYSQL_JDBC_JAR = mysql_jdbc_jar;
          NIX_ENFORCE_NO_NATIVE="0";
          SYSBENCH_PATH="${pkgs.sysbench}";
        };
        "cross-compiler" = pkgs.mkShell {
          name="memsafedb-devshell-eliza-crosscompiler";
          buildInputs = with pkgs; [
            doctor-pkgs.clang-morello
            doctor-pkgs.musl-morello-purecap
            doctor-pkgs.llvm-morello-purecap
          ] ++ sharedPkgs;
          MORELLO_CLANG_DIR = "${doctor-pkgs.clang-morello}";
          MORELLO_LLVM_DIR = "${doctor-pkgs.llvm-morello-purecap}";
          MORELLO_SYSROOT = "${doctor-pkgs.musl-morello-purecap}";
          MYSQL_JDBC_JAR = mysql_jdbc_jar;
        };
        "ace-aarch64" = pkgs.mkShell {
          name="memsafedb-devshell-ace-hybrid";
          buildInputs = with pkgs; [
            pkgsStatic.clang
            pkgsStatic.musl
            pkgsStatic.libcxx
            pkgsStatic.libcxx.dev
            pkgsStatic.boost
          ] ++ sharedPkgs;
          CLANG_PATH = "${pkgs.pkgsStatic.clang}";
          MUSL_PATH = "${pkgs.pkgsStatic.musl}";
          LIBCXX_PATH = "${pkgs.pkgsStatic.libcxx}";
          LIBCXX_HDR = "${pkgs.pkgsStatic.libcxx.dev}";
          MYSQL_JDBC_JAR = mysql_jdbc_jar;
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

          MYSQL_JDBC_JAR = mysql_jdbc_jar;
          shellHook = ''
            source /morello/env/morello-sdk
          '';
        };
      };
    });
  }
