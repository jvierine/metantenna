#!/bin/sh
set -eu
build_dir=${1:-/tmp/metantenna-nec2c}
if [ ! -d "$build_dir/.git" ]; then
    git clone https://github.com/KJ7LNW/nec2c.git "$build_dir"
fi
git -C "$build_dir" checkout 55be1e0e3fe5ee9dad4ce6050711450d19c562fd
cd "$build_dir"
cc -O3 '-DPACKAGE_STRING="nec2c"' -o nec2c calculations.c geometry.c input.c matrix.c network.c shared.c fields.c ground.c main.c misc.c radiation.c somnec.c -lm
./nec2c -v
