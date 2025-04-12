{pkgs}: {
  deps = [
    pkgs.unzip
    pkgs.rustc
    pkgs.pkg-config
    pkgs.libxcrypt
    pkgs.libiconv
    pkgs.cargo
    pkgs.postgresql
    pkgs.openssl
  ];
}
