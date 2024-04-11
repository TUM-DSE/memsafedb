{ pkgs ? import <nixpkgs> {} }:
  pkgs.stdenv.mkDerivation {
        name="ycsb-cpp-dev-env";
        nativeBuildInputs = with pkgs.buildPackages; [gnumake unzip readline docker pax-utils pkg-config qemu_full gdb ack bash python3 flamegraph python311Packages.requests zlib cmake];
        ZLIB = pkgs.zlib;
}
