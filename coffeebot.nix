{ pkgs, ... }:

let
coffeebot = pkgs.callPackages ./default.nix {
  inherit pkgs;
  local = false;
};
in
{
  environment.systemPackages = [ coffeebot ];
  systemd.services.coffeebot = {
    description = "Coffee for all";
    wantedBy = [ "multi-user.target" ];
    serviceConfig.ExecStart =
      "sh -c '${coffeebot}/bin/coffeebot'";
    };
  }
