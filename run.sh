picoc_compiler --show-input-files $(cat ./config/run_cpl_opts.txt) $2 "$1" -o "${1%.picoc}.reti" || exit 1
./run_reti_emulator_isolated.sh $(cat ./config/run_emu_opts.txt) $3 "${1%.picoc}.reti"
