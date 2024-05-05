{
  inputs = {
    snowfall-lib = {
      url = "github:snowfallorg/lib";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    nixpkgs = {
      url = "github:NixOS/nixpkgs/nixos-23.11";
    };
  };

  outputs = inputs: inputs.snowfall-lib.mkFlake {
    inherit inputs;
    src = ./.;
  };
}