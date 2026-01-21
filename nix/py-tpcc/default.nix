{ lib, python3Packages, fetchFromGitHub }:

python3Packages.buildPythonApplication rec {
  pname = "py-tpcc";
  version = "unstable-2024-01-15";

  src = fetchGit {
    url = "https://github.com/mongodb-labs/py-tpcc.git";
    rev = "0c5a236d87efaeadfe2a112542ea14f0ca4a7b02";
  };

  format = "other";
  dontBuild = true;

  propagatedBuildInputs = with python3Packages; [
    python
  ];
  
  patches = [
    ./python3.patch
  ];
  patchFlags = [ "-p1" "-l" ];

  installPhase = ''
    mkdir -p $out/bin $out/lib/py-tpcc
    cp -r pytpcc/* $out/lib/py-tpcc/

    cat > $out/bin/py-tpcc <<EOF
#!/usr/bin/env bash
exec ${python3Packages.python}/bin/python $out/lib/py-tpcc/tpcc.py "\$@"
EOF
    chmod +x $out/bin/py-tpcc
  '';

  meta = with lib; {
    description = "Python implementation of the TPC-C benchmark";
    homepage = "https://github.com/apavlo/py-tpcc";
    license = licenses.asl20;
    platforms = platforms.linux;
  };
}
