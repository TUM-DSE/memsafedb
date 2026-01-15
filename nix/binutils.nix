{ pkgs, ... }:

pkgs.stdenv.mkDerivation rec {
  pname = "binutils-morello";
    version = "2.35-morello";

    src = pkgs.fetchFromGitHub {
      owner = "CTSRD-CHERI";
      repo = "gdb";
      rev = "gdb-cheri-14.1.d20251105.1";
      hash = "sha256-HkWw35LfVlojrfQxX8MAwXDtlRWvdYkG+aKS8NHfFPc=";
    };
    #src = pkgs.fetchgit {
    #  url = "https://git.morello-project.org/morello/gnu-toolchain/binutils-gdb.git";
    #  rev = "21b9239b70d870b155284bf508cdf5401f37e2f5";
    #  hash = "sha256-jGeW7uPDTnReEM6Yw/PkoU2JXGncu2IgmABA+tqIMpA=";
    #};

    nativeBuildInputs = with pkgs; [ bison flex texinfo zlib ];
    enableParallelBuilding = true;

    configureFlags = [
      "--target=aarch64-none-elf"
      "--disable-nls"
      "--enable-deterministic-archives"
      "--enable-ld" 
      "--enable-multilib"
      "--with-gnu-as"
      "--with-gnu-ld"
      "--without-isl"
      "--with-system-zlib"
      "--disable-werror"
      "--disable-gdb"
    ];
}
