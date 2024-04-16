{ pkgs ? import <nixpkgs> {} }:
let
	tbb-hot = pkgs.stdenv.mkDerivation{
		pname = "tbb";
		version = "2018_20171205";

		src = pkgs.fetchurl {
			url="https://github.com/oneapi-src/oneTBB/archive/refs/tags/2018_U2.tar.gz";
			hash="";
		};
		
	};
  pkgs.stdenv.mkDerivation {
        name="ycsb-cpp-dev-env";
        nativeBuildInputs = with pkgs.buildPackages; [lcov gnumake unzip readline docker pax-utils pkg-config qemu_full gdb ack bash python3 flamegraph python311Packages.requests zlib cmake tbb-hot];
        ZLIB = pkgs.zlib;
	TBB_ROOT = tbb-hot;
}
