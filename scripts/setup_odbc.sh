#!/usr/bin/env bash
# Local WSL runtime only: no sudo, system registration or maintainer scripts.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
test "$(uname -m)" = x86_64
source /etc/os-release
test "$ID:$VERSION_ID" = ubuntu:26.04
odbc_root="$PWD/.local/odbc"
package_dir="$(mktemp -d /tmp/ecommerce-odbc.XXXXXX)"
(
  cd "$package_dir"
  apt-get download libodbc2=2.3.14-1 libodbcinst2=2.3.14-1 libltdl7=2.5.4-9
  curl --fail --location --max-time 60 \
    https://packages.microsoft.com/ubuntu/26.04/prod/pool/main/m/msodbcsql18/msodbcsql18_18.7.1.1-1_amd64.deb \
    --output msodbcsql18.deb
  echo 'be20dcf224e0adc8865288e6c1d3eef4e00b2e267db363a28adccbc8c3ebb462  msodbcsql18.deb' | sha256sum --check
)
mkdir -p "$odbc_root"
for package in "$package_dir"/*.deb; do
  dpkg-deb --extract "$package" "$odbc_root"
done
mkdir -p "$odbc_root/etc"
driver_path="$(find "$odbc_root/opt/microsoft/msodbcsql18/lib64" -name 'libmsodbcsql-*.so.*' -print -quit)"
printf '[ODBC Driver 18 for SQL Server]\nDescription=Project-local Microsoft ODBC Driver 18\nDriver=%s\nUsageCount=1\n' "$driver_path" > "$odbc_root/etc/odbcinst.ini"
echo 'Local runtime extracted. Review bundled Microsoft license before use.'
echo 'Install requirements-sqlserver.txt inside the activated venv next.'
