{ pkgs ? import <nixpkgs> { } }:

let
  copyPathsToStore = pkgs.copyPathsToStore;
in
with pkgs.python36Packages;
buildPythonPackage rec {
  pname="zulip";
  version="0.3.4";
  name="${pname}-${version}";
  src = fetchPypi {
    inherit pname version;
    sha256 = "c7620c77720ecfd3b678b6d8dca55e8086abb6c2b94feca8c387e2e84ef1fc81";
    };
  patches = copyPathsToStore [(./Make-encoding-explicit.patch)];
  propagatedBuildInputs = [ requests six typing simplejson ];
}
