{ stdenv, lib, fetchurl, jre }:

stdenv.mkDerivation rec {
  pname = "ycsb";
  version = "0.17.0";

  src = fetchurl {
    url = "https://github.com/brianfrankcooper/YCSB/releases/download/${version}/ycsb-${version}.tar.gz";
    sha256 = "sha256-2A2LZ8Sx2px9ncDUDN2aZR8MD0TlgK6gD7P4bP+29cw=";
  };

  propagatedBuildInputs = [ jre ];

  dontBuild = true;

  installPhase = ''
    #cd ycsb-${version}
    cp -R . $out
    chmod +x $out/bin/ycsb
  '';

  meta = with lib; {
    description = "The Yahoo! Cloud Serving Benchmark (YCSB) framework";
    homepage = "https://github.com/brianfrankcooper/YCSB";
    license = licenses.asl20;
    platforms = platforms.linux;
  };
}
