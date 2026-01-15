{ pkgs, binutils-morello, ... }:

pkgs.stdenv.mkDerivation rec {
  pname = "gcc-morello-stage1";
  version = "10.1.0";
  
  src = pkgs.fetchgit {
    url = "https://git.morello-project.org/morello/gnu-toolchain/gcc.git";
    rev = "5d3776f5063baa2ddea94c595a4a8bf538016aea";
    hash = "sha256-YGewu1MdhZNtOv5gjFPk6R39B6G+IKFx8uy29MQ9/qY=";
  };

  nativeBuildInputs = with pkgs; [ flex bison texinfo perl gawk binutils-morello ];
  buildInputs = with pkgs; [ gmp mpfr libmpc zlib ];

  hardeningDisable = [ "format" "fortify" "pie" "stackprotector" ]; 
  
  preConfigure = ''
    mkdir build
    cd build
    export PATH="${binutils-morello}/bin:$PATH"
    export AS_FOR_TARGET="${binutils-morello}/bin/aarch64-none-elf-as"
    export LD_FOR_TARGET="${binutils-morello}/bin/aarch64-none-elf-ld"
    export CFLAGS_FOR_TARGET="-O2 -Dinhibit_libc -mno-lse"
    export CXXFLAGS_FOR_TARGET="-O2 -Dinhibit_libc -mno-lse"
  '';

  configureScript = "../configure";
  configureFlags = [ 
    "--target=aarch64-none-elf"
    "--with-arch=morello+c64"
    "--with-abi=purecap"
    "--enable-languages=c,c++"
    "--disable-bootstrap"
    "--disable-shared"
    "--disable-threads"
    "--disable-libsanitizer"
    "--disable-libssp"
    "--disable-lse"
    "--disable-libquadmath"
    "--disable-libgomp"
    "--disable-libatomic"
    "--without-headers"
    "--with-newlib"
    "--disable-multilib"
    "--with-gmp=${pkgs.gmp.dev}"
    "--with-mpfr=${pkgs.mpfr.dev}"
    "--with-mpc=${pkgs.libmpc}"
    "--with-as=${binutils-morello}/bin/aarch64-none-elf-as"
    "--with-ld=${binutils-morello}/bin/aarch64-none-elf-ld"
  ];
  enableParallelBuilding = true;

  buildPhase = ''
    make $makeFlags all-gcc
    make $makeFlags all-target-libgcc
  '';
  installPhase = ''
    make $makeFlags install-gcc
    make $makeFlags install-target-libgcc
  '';
  
  meta = with pkgs.lib; {
    description = "CHERI Morello GCC Stage 1 (Purecap)";
    homepage = "https://www.morello-project.org/";
    license = licenses.gpl3Plus;
    platforms = platforms.linux;
  };
}
