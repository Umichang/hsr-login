#!/bin/sh
set -eu

python_cmd="${PYTHON:-python3}"
app_name="hsr-login"
data_home="${XDG_DATA_HOME:-$HOME/.local/share}"
venv_dir="${HSR_LOGIN_VENV_DIR:-$data_home/$app_name/venv}"
bin_dir="${HSR_LOGIN_BIN_DIR:-$HOME/.local/bin}"

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
project_dir=$(CDPATH= cd -- "$script_dir/.." && pwd)

"$python_cmd" -m venv "$venv_dir"
"$venv_dir/bin/python" -m pip install --upgrade "$project_dir"

mkdir -p "$bin_dir"
cat > "$bin_dir/$app_name" <<EOF
#!/bin/sh
exec "$venv_dir/bin/$app_name" "\$@"
EOF
chmod 755 "$bin_dir/$app_name"

echo "Installed $app_name to $bin_dir/$app_name"
echo "If the command is not found, add $bin_dir to PATH."
