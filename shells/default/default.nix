{ mkShell
, pkgs
, ...
}:

mkShell {
  name = "pycord";
  
  packages = with pkgs; [
    inotify-tools
    
    poetry
    python3Full
  ];
  
  LD_LIBRARY_PATH = "${pkgs.stdenv.cc.cc.lib}/lib";

  POETRY_VIRTUALENVS_IN_PROJECT = true;
  shellHook = ''
    poetry env use $(which python)
    poetry install --no-root
  '';
}