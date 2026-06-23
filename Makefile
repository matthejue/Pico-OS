SHELL := /bin/bash

# ----------------------------------------------------------------------
# Normal test and program-run configuration
# ----------------------------------------------------------------------

TEST_PATTERN ?= $(shell cat ./opts/test_pattern.txt)
RUN_PATH ?= $(shell cat ./opts/run_path.txt)

EXTRA_CPL_ARGS ?=
EXTRA_EMU_ARGS ?=


# ----------------------------------------------------------------------
# Phony targets
# ----------------------------------------------------------------------

.PHONY: help
.PHONY: run run_send_keypresses
.PHONY: test test-all test_not_passed
.PHONY: bootload run-kernel firmware eprom kernel isrs clean-firmware rebuild-firmware
.PHONY: clean


# ----------------------------------------------------------------------
# Help
# ----------------------------------------------------------------------

help:
	@echo "Targets:"
	@echo "  make run                        Run configured program using RUN_PATH"
	@echo "  make run_send_keypresses        Run configured program and send keypresses"
	@echo "  make test                       Run sys tests using TEST_PATTERN"
	@echo "  make test-all                   Run all sys tests"
	@echo "  make test_not_passed            Run paths from ./opts/not_passed_tests.txt"
	@echo "  make firmware                   Build bootloader and kernel artifacts"
	@echo "  make bootload                   Build firmware and boot through startprogram.reti"
	@echo "  make run-kernel                 Build and run kernel.reti directly"
	@echo "  make eprom                      Build eprom_startprogram/startprogram.reti"
	@echo "  make kernel                     Build kernel.bin"
	@echo "  make isrs                       Build interrupt_service_routines/isrs.reti"
	@echo "  make rebuild-firmware           Remove and rebuild firmware files"
	@echo "  make clean-firmware             Remove generated firmware files only"
	@echo "  make clean                      Remove generated test and firmware files"
	@echo ""
	@echo "Variables:"
	@echo "  TEST_PATTERN=<pattern>          Override the configured test pattern"
	@echo "  RUN_PATH=<path>                 Override configured run path"
	@echo "  EXTRA_CPL_ARGS='<arguments>'    Additional compiler arguments for normal runs/tests"
	@echo "  EXTRA_EMU_ARGS='<arguments>'    Additional emulator arguments for normal runs/tests"
	@echo ""
	@echo "Each sys test is stopped automatically if the emulator exceeds"
	@echo "the timeout configured in ./run_sys_tests.sh."


# ----------------------------------------------------------------------
# Normal program running
# ----------------------------------------------------------------------

run:
	./run.sh "$(RUN_PATH)" "$(EXTRA_CPL_ARGS)" "$(EXTRA_EMU_ARGS)"

run_send_keypresses:
	@set -e; \
	run_path="$(RUN_PATH)"; \
	if [[ "$$run_path" == *.picoc ]]; then \
		compiled_path="$${run_path%.picoc}.reti"; \
		./run.py $$(cat ./opts/run_cpl_opts.txt) $(EXTRA_CPL_ARGS) "$$run_path" -o "$$compiled_path"; \
		run_path="$$compiled_path"; \
	fi; \
	./send_keypresses.py --input ./opts/input.txt reti_emulator $$(cat ./opts/run_emu_opts.txt) $(EXTRA_EMU_ARGS) "$$run_path"


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------

test:
	./export_environment_vars_for_makefile.sh;\
	./run_sys_tests.sh "$${COLUMNS}" "$(TEST_PATTERN)" "$(EXTRA_CPL_ARGS)" "$(EXTRA_EMU_ARGS)"

test-all:
	./export_environment_vars_for_makefile.sh;\
	./run_sys_tests.sh "$${COLUMNS}" "all" "$(EXTRA_CPL_ARGS)" "$(EXTRA_EMU_ARGS)"

test_not_passed:
	./export_environment_vars_for_makefile.sh;\
	./run_sys_tests.sh --not-passed "$${COLUMNS}" "" "$(EXTRA_CPL_ARGS)" "$(EXTRA_EMU_ARGS)"


# ----------------------------------------------------------------------
# Firmware build
# ----------------------------------------------------------------------

firmware: eprom_startprogram/startprogram.reti kernel.bin

eprom: eprom_startprogram/startprogram.reti

kernel: kernel.bin

isrs: interrupt_service_routines/isrs.reti

interrupt_service_routines/isrs.reti: interrupt_service_routines/isrs.picoc
	cd interrupt_service_routines && picoc_compiler isrs.picoc -O1 -i -w -s -o isrs.reti

eprom_startprogram/startprogram.reti: eprom_startprogram/startprogram.picoc
	cd eprom_startprogram && picoc_compiler startprogram.picoc -O1 -i -w -s -o startprogram.reti

kernel.reti: interrupt_service_routines/isrs.picoc kernel/kernel.picoc kernel/interrupt_controller.picoc
	picoc_compiler \
		interrupt_service_routines/isrs.picoc \
		kernel/kernel.picoc \
		kernel/interrupt_controller.picoc \
		-O1 -i -w -s -g -v \
		-o kernel.reti

kernel.bin: kernel.reti eprom_startprogram/startprogram.reti
	reti_emulator -a kernel.reti
	hexyl kernel.bin


# ----------------------------------------------------------------------
# Firmware bootload and direct kernel run
# ----------------------------------------------------------------------

run-kernel: kernel.reti
	reti_emulator kernel.reti -c -d

bootload: firmware
	reti_emulator -e ./eprom_startprogram/startprogram.reti -d -f /tmp -r 262144 -S kernel.sections -D kernel.debuginfo


# ----------------------------------------------------------------------
# Cleaning
# ----------------------------------------------------------------------

rebuild-firmware: clean-firmware firmware

clean-firmware:
	find eprom_startprogram interrupt_service_routines kernel -type f \
		! -name '*.picoc' \
		! -name '*.header' \
		-delete
	rm -f kernel.reti kernel.bin kernel.sections kernel.debuginfo

clean: clean-firmware
	find . -type f \
		! -path './eprom_startprogram/*' \
		! -path './interrupt_service_routines/*' \
		! -path './kernel/*' \
		\( -name '*.tokens' \
		-o -name '*.rtokens' \
		-o -name '*.dt' \
		-o -name '*.pre' \
		-o -name '*.ps' \
		-o -name '*.st' \
		-o -name '*.sections' \
		-o -name '*.rdt' \
		-o -name '*.dt_simple' \
		-o -name '*.ast' \
		-o -name '*.rast' \
		-o -name '*.json' \
		-o -name '*.picoc_shrink' \
		-o -name '*.picoc_blocks' \
		-o -name '*.picoc_symbol' \
		-o -name '*.picoc_typing' \
		-o -name '*.picoc_anf' \
		-o -name '*.reti_blocks' \
		-o -name '*.reti_patch' \
		-o -name '*.reti' \
		-o -name '*.error' \
		-o -name '*.c' \
		-o -name '*.c_output' \
		-o -name '*.reti_tokens' \
		-o -name '*.reti_ast' \
		-o -name '*.input' \
		-o -name '*.output' \
		-o -name '*.expected_output' \
		-o -name '*.datasegment_size' \
		-o -name '*.reti_states' \
		-o -name '*.eprom' \
		-o -name '*.res' \
		-o -name 'sram.bin' \
		-o -name 'kernel.bin' \
		\) -delete
