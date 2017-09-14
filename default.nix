{ pkgs ? import <nixpkgs> { }, local ? true}:

with pkgs.python36Packages;
let
  
  optionalString = cond: str: if cond then str else "";
  zulip = buildPythonPackage rec {
    pname = "zulip";
    version = "0.3.4";
    name = "${pname}-${version}";
    src = fetchPypi {
      inherit pname version;
      sha256 = "c7620c77720ecfd3b678b6d8dca55e8086abb6c2b94feca8c387e2e84ef1fc81";
    };
    patches = pkgs.copyPathsToStore [(./. + "${optionalString local "/dist"}/zulip-make-encoding-explicit-${version}.patch")];
    propagatedBuildInputs = [ requests six typing simplejson ];
  };
in buildPythonPackage rec {
  pname = "zulip-coffeebot";
  version = "0.1.1";
  name = "${pname}-${version}";
  src = ./. + "${optionalString local "/dist"}/${name}.tar.gz";
  propagatedBuildInputs = [ zulip ];  # pytest?
}
  

  
