{ pkgs ? import <nixpkgs> {} }:
pkgs.stdenv.mkDerivation rec {
	name="ycsb-cpp-dev-env";
        nativeBuildInputs = with pkgs.buildPackages; [go lcov gnumake unzip readline docker pax-utils pkg-config qemu_full gdb ack bash python3 flamegraph python311Packages.requests zlib cmake boost175.all gperftools];
        ZLIB = pkgs.zlib;
	#TBB_ROOT = tbb-hot;
	BOOST175 = pkgs.boost175.all;
	LIB_TCMALLOC = pkgs.gperftools;
}
