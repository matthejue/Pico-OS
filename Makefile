SHELL := /bin/bash

# ----------------------------------------------------------------------
# Normal test and program-run configuration
# ----------------------------------------------------------------------

TEST_PATTERN ?= $(shell cat ./opts/test_pattern.txt)
RUN_PATH ?= $(shell cat ./opts/run_path.txt)
OS_TEST_PATTERN ?= $(shell cat ./opts/os_test_pattern.txt)
OS_RUN_PATH ?= $(shell cat ./opts/os_run_path.txt)
OS_TEST_CPL_OPTS ?= $(shell cat ./opts/os_test_cpl_opts.txt)
OS_TEST_EMU_OPTS ?= $(shell cat ./opts/os_test_emu_opts.txt)
OS_RUN_CPL_OPTS ?= $(shell cat ./opts/os_run_cpl_opts.txt)
OS_RUN_EMU_OPTS ?= $(shell cat ./opts/os_run_emu_opts.txt)
SRAM_SIZE ?= 262144 # 2^18
KERNEL_STACK_START ?= 15000
START_EXIT_SYSCALL ?= 10

EXTRA_CPL_ARGS ?=
EXTRA_EMU_ARGS ?=


# ----------------------------------------------------------------------
# Phony targets
# ----------------------------------------------------------------------

.PHONY: help
.PHONY: run run_send_keypresses run-os
.PHONY: test test-all test_not_passed test-os
.PHONY: bootload bootload-debug run-kernel firmware eprom kernel isrs system clean-firmware rebuild-firmware
.PHONY: clean


# ----------------------------------------------------------------------
# Help
# ----------------------------------------------------------------------

help:
	@echo "Targets:"
	@echo "  make run                        Run configured program using RUN_PATH"
	@echo "  make run_send_keypresses        Run configured program and send keypresses"
	@echo "  make run-os                     Run configured OS test using OS_RUN_PATH"
	@echo "  make test                       Run sys tests using TEST_PATTERN"
	@echo "  make test-all                   Run all sys tests"
	@echo "  make test_not_passed            Run paths from ./opts/not_passed_tests.txt"
	@echo "  make test-os                    Run OS integration tests from sys_tests/*/"
	@echo "  make firmware                   Build bootloader and kernel artifacts"
	@echo "  make bootload                   Build firmware and boot through startprogram.reti"
	@echo "  make bootload-debug             Rebuild PicoC files with -g and bootload"
	@echo "  make run-kernel                 Build and run kernel.reti directly"
	@echo "  make eprom                      Build eprom_startprogram/startprogram.reti"
	@echo "  make kernel                     Build kernel.bin"
	@echo "  make isrs                       Build the UART-only test ISR table"
	@echo "  make system                     Build system programs"
	@echo "  make rebuild-firmware           Remove and rebuild firmware files"
	@echo "  make clean-firmware             Remove generated firmware files only"
	@echo "  make clean                      Remove generated test and firmware files"
	@echo ""
	@echo "Variables:"
	@echo "  TEST_PATTERN=<pattern>          Override the configured test pattern"
	@echo "  RUN_PATH=<path>                 Override configured run path"
	@echo "  OS_TEST_PATTERN=<pattern>       Override the configured OS test pattern"
	@echo "  OS_RUN_PATH=<path>              Override configured OS run path"
	@echo "  OS_TEST_CPL_OPTS='<arguments>'  Override ./opts/os_test_cpl_opts.txt"
	@echo "  OS_TEST_EMU_OPTS='<arguments>'  Override ./opts/os_test_emu_opts.txt"
	@echo "  OS_RUN_CPL_OPTS='<arguments>'   Override ./opts/os_run_cpl_opts.txt"
	@echo "  OS_RUN_EMU_OPTS='<arguments>'   Override ./opts/os_run_emu_opts.txt"
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

run-os: kernel.reti system/init.bin
	./export_environment_vars_for_makefile.sh;\
	./run_os_tests.py --run "$(OS_RUN_PATH)" "$${COLUMNS}" "" "$(OS_RUN_CPL_OPTS) $(EXTRA_CPL_ARGS)" "$(OS_RUN_EMU_OPTS) $(EXTRA_EMU_ARGS)"

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

test-os: kernel.reti system/init.bin
	./export_environment_vars_for_makefile.sh;\
	./run_os_tests.py "$${COLUMNS}" "$(OS_TEST_PATTERN)" "$(OS_TEST_CPL_OPTS) $(EXTRA_CPL_ARGS)" "$(OS_TEST_EMU_OPTS) $(EXTRA_EMU_ARGS)"


# ----------------------------------------------------------------------
# Firmware build
# ----------------------------------------------------------------------

firmware: eprom_startprogram/startprogram.reti kernel.bin system/init.bin

eprom: eprom_startprogram/startprogram.reti

kernel: kernel.bin

isrs: opts/isrs.reti

system: system/init.bin

ISRS_PICOC_SOURCES := \
	interrupt_service_routines/isrs.picoc \
	kernel/uart_hardware.picoc

opts/isrs.reti: $(ISRS_PICOC_SOURCES)
	picoc_compiler \
		$(ISRS_PICOC_SOURCES) \
		-O1 -i -w -s -v \
		-o opts/isrs.reti

EPROM_PICOC_SOURCES := \
	eprom_startprogram/startprogram.picoc \
	common/sram_loader.picoc \
	kernel/uart_hardware.picoc \
	common/uart_protocol.picoc

eprom_startprogram/memory_constants.header: $(EPROM_PICOC_SOURCES) kernel/memory_constants.header
	# The -k build creates memory_constants.header if none exists.
	# This earlier placeholder is only needed because preprocessing
	# startprogram.picoc requires the include before -k can compute addresses.
	@if [ ! -f eprom_startprogram/memory_constants.header ]; then \
		printf '%s\n' \
			'#define SRAM_MAX_ADDRESS 0' \
			'#define EPROM_DS_START_ASM "LOADI32 DS 0"' \
			'#define EPROM_STACK_START_ASM "LOADI32 SP 0"' \
			> eprom_startprogram/memory_constants.header; \
	fi
	picoc_compiler \
		$(EPROM_PICOC_SOURCES) \
		-O1 -s -k eprom \
		-o eprom_startprogram/memory_constants.header

eprom_startprogram/startprogram.reti: $(EPROM_PICOC_SOURCES) eprom_startprogram/memory_constants.header kernel/memory_constants.header
	picoc_compiler \
		$(EPROM_PICOC_SOURCES) \
		-O1 -i -w -s -v \
		-o eprom_startprogram/startprogram.reti

SYSTEM_PICOC_SOURCES := \
	system/init.picoc \
	lib/process/libprocess.picoc \
	lib/stdio/stdio.picoc \
	lib/string/libstring.picoc \
	common/uart_protocol.picoc

system/init.reti: $(SYSTEM_PICOC_SOURCES) lib/process/process.picoc lib/process/process.header lib/stdio/stdio.header lib/string/string.picoc lib/string/string.header common/syscall.header patch_start_exit_syscall.py
	picoc_compiler \
		$(SYSTEM_PICOC_SOURCES) \
		-O1 -i -w -s -g -v \
		-o system/init.reti
	python3 patch_start_exit_syscall.py $(START_EXIT_SYSCALL) system/init.reti
	sed -i -E 's/"stack_start": *-?[0-9]+/"stack_start": 8000/' system/init.sections

system/init.bin: system/init.reti
	reti_emulator -f /tmp -a system/init.reti
	hexyl system/init.bin

KERNEL_PICOC_SOURCES := \
	interrupt_service_routines/os_isrs.picoc \
	common/sram_loader.picoc \
	kernel/uart_hardware.picoc \
	common/uart_protocol.picoc \
	kernel/kernel.picoc \
	kernel/interrupt_controller.picoc \
	kernel/periphery.picoc \
	common/heap.picoc \
	kernel/kmalloc.picoc \
	kernel/pmalloc.picoc \
	kernel/process.picoc \
	kernel/process_arguments.picoc \
	kernel/scheduler.picoc \
	kernel/dispatcher.picoc \
	kernel/process_loader.picoc \
	kernel/syscall.picoc

kernel/memory_constants.header: $(KERNEL_PICOC_SOURCES) common/syscall.header
	picoc_compiler \
		$(KERNEL_PICOC_SOURCES) \
		-O1 -s -k sram \
		-o kernel/memory_constants.header

kernel.reti: $(KERNEL_PICOC_SOURCES) common/syscall.header kernel/memory_constants.header
	picoc_compiler \
		$(KERNEL_PICOC_SOURCES) \
		-O1 -i -w -s -g -v \
		-o kernel.reti
	sed -i -E 's/"stack_start": *-?[0-9]+/"stack_start": $(KERNEL_STACK_START)/' kernel.sections

kernel.bin: kernel.reti eprom_startprogram/startprogram.reti
	reti_emulator -f /tmp -a kernel.reti
	hexyl kernel.bin


# ----------------------------------------------------------------------
# Firmware bootload and direct kernel run
# ----------------------------------------------------------------------

run-firmware: kernel.reti system/init.bin
	reti_emulator kernel.reti -d -c -r $(SRAM_SIZE) -f /tmp

bootload: firmware
	reti_emulator -e ./eprom_startprogram/startprogram.reti -d -c -f /tmp -r $(SRAM_SIZE) -S kernel.sections -D kernel.debuginfo

bootload-debug:
	$(MAKE) kernel/memory_constants.header
	$(MAKE) eprom_startprogram/memory_constants.header
	picoc_compiler \
		$(EPROM_PICOC_SOURCES) \
		-O1 -i -w -s -g -v \
		-o eprom_startprogram/startprogram.reti
	picoc_compiler \
		$(KERNEL_PICOC_SOURCES) \
		-O1 -i -w -s -g -v \
		-o kernel.reti
	sed -i -E 's/"stack_start": *-?[0-9]+/"stack_start": $(KERNEL_STACK_START)/' kernel.sections
	reti_emulator -f /tmp -a kernel.reti
	hexyl kernel.bin
	reti_emulator -e ./eprom_startprogram/startprogram.reti -d -c -f /tmp -r $(SRAM_SIZE) -S kernel.sections -D kernel.debuginfo


# ----------------------------------------------------------------------
# Cleaning
# ----------------------------------------------------------------------

rebuild-firmware: clean-firmware firmware

clean-firmware:
	find common eprom_startprogram interrupt_service_routines kernel system -type f \
		! -name '*.picoc' \
		! -name '*.header' \
		! -name '.gitkeep' \
		-delete
	rm -f kernel.reti kernel.bin kernel.sections kernel.debuginfo

clean: clean-firmware
	find . -type f \
		! -path './.vscode/*' \
		! -path './eprom_startprogram/*' \
		! -path './interrupt_service_routines/*' \
		! -path './kernel/*' \
		! -name 'compile_commands.json' \
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
		-o -name '*.bin' \
		-o -name '*.res' \
		-o -name 'sram.bin' \
		-o -name 'kernel.bin' \
		\) -delete
