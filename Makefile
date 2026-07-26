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

EXTRA_CPL_ARGS ?=
EXTRA_EMU_ARGS ?=

USER_STARTUP_SOURCE := lib/start/libstart.picoc
USER_STARTUP_DEPENDENCIES := \
	$(USER_STARTUP_SOURCE) \
	lib/start/start.picoc \
	lib/stdlib/libstdlib.picoc \
	lib/stdlib/malloc.picoc \
	lib/stdlib/atoi.picoc \
	lib/stdlib/env.picoc \
	lib/stdlib/exit.picoc \
	lib/stdlib/stdlib.header \
	common/heap.picoc \
	common/heap.header
USER_RUNTIME_SOURCES := \
	lib/unistd/libunistd.picoc \
	lib/sys/wait/libwait.picoc
USER_RUNTIME_DEPENDENCIES := \
	$(USER_RUNTIME_SOURCES) \
	lib/unistd/process.picoc \
	lib/unistd/blocking.picoc \
	lib/unistd/unistd.header \
	lib/sys/wait/wait.picoc \
	lib/sys/wait/wait.header \
	common/syscall.header \
	common/stddef.header \
	common/wait_queue.header
USER_PROGRAM_CPL_ARGS := $(USER_RUNTIME_SOURCES) -C $(USER_STARTUP_SOURCE)


# ----------------------------------------------------------------------
# Phony targets
# ----------------------------------------------------------------------

.PHONY: help
.PHONY: run run_send_keypresses run-os
.PHONY: test test-all test_not_passed test-os
.PHONY: bootload bootload-debug run-kernel firmware eprom kernel isrs system user shell.bin shell.reti echo.bin echo.reti clean-firmware rebuild-firmware
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
	@echo "  make user                       Build user programs"
	@echo "  make shell.bin                  Build the shell system program binary"
	@echo "  make echo.bin                   Build the echo user program binary"
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

run-os: kernel.reti system/init.bin system/shell.bin
	./export_environment_vars_for_makefile.sh;\
	./run_os_tests.py --run "$(OS_RUN_PATH)" "$${COLUMNS}" "" "$(USER_RUNTIME_SOURCES) $(OS_RUN_CPL_OPTS) $(EXTRA_CPL_ARGS) -C $(USER_STARTUP_SOURCE)" "$(OS_RUN_EMU_OPTS) -O $(EXTRA_EMU_ARGS)"

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

test: opts/isrs.reti
	./export_environment_vars_for_makefile.sh;\
	./run_sys_tests.sh "$${COLUMNS}" "$(TEST_PATTERN)" "$(EXTRA_CPL_ARGS)" "$(EXTRA_EMU_ARGS)"

test-all: opts/isrs.reti
	./export_environment_vars_for_makefile.sh;\
	./run_sys_tests.sh "$${COLUMNS}" "all" "$(EXTRA_CPL_ARGS)" "$(EXTRA_EMU_ARGS)"

test_not_passed:
	./export_environment_vars_for_makefile.sh;\
	./run_sys_tests.sh --not-passed "$${COLUMNS}" "" "$(EXTRA_CPL_ARGS)" "$(EXTRA_EMU_ARGS)"

test-os: kernel.reti system/init.bin system/shell.bin user/echo.bin
	./export_environment_vars_for_makefile.sh;\
	./run_os_tests.py "$${COLUMNS}" "$(OS_TEST_PATTERN)" "$(USER_RUNTIME_SOURCES) $(OS_TEST_CPL_OPTS) $(EXTRA_CPL_ARGS) -C $(USER_STARTUP_SOURCE)" "$(OS_TEST_EMU_OPTS) -O $(EXTRA_EMU_ARGS)"


# ----------------------------------------------------------------------
# Firmware build
# ----------------------------------------------------------------------

firmware: eprom_startprogram/startprogram.reti kernel.bin system/init.bin system/shell.bin

eprom: eprom_startprogram/startprogram.reti

kernel: kernel.bin

isrs: opts/isrs.reti

SYSTEM_PROGRAM_SOURCES := $(wildcard system/*.picoc)
SYSTEM_PROGRAM_BINARIES := $(SYSTEM_PROGRAM_SOURCES:.picoc=.bin)
USER_PROGRAM_SOURCES := $(wildcard user/*.picoc)
USER_PROGRAM_BINARIES := $(USER_PROGRAM_SOURCES:.picoc=.bin)

system: $(SYSTEM_PROGRAM_BINARIES)

user: $(USER_PROGRAM_BINARIES)

user/echo.reti: lib/stdio/libstdio.picoc lib/stdio/stdio.picoc lib/stdio/stdio.header common/uart_protocol.picoc common/uart_protocol.header

echo.reti: user/echo.reti

echo.bin: user/echo.bin

shell.reti: system/shell.reti

shell.bin: system/shell.bin

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

SYSTEM_LIBRARY_SOURCES := \
	$(USER_RUNTIME_SOURCES) \
	lib/stdio/stdio.picoc \
	lib/string/libstring.picoc \
	common/uart_protocol.picoc

system/init.reti: system/init.picoc $(SYSTEM_LIBRARY_SOURCES) $(USER_RUNTIME_DEPENDENCIES) $(USER_STARTUP_DEPENDENCIES) lib/stdio/stdio.header lib/string/string.picoc lib/string/string.header
	picoc_compiler \
		system/init.picoc $(SYSTEM_LIBRARY_SOURCES) \
		-C $(USER_STARTUP_SOURCE) \
		-O1 -i -w -s -g -v \
		-o system/init.reti

system/init.bin: system/init.reti
	reti_emulator -f /tmp -a system/init.reti
	hexyl system/init.bin

system/shell.reti: system/shell.picoc $(SYSTEM_LIBRARY_SOURCES) $(USER_RUNTIME_DEPENDENCIES) $(USER_STARTUP_DEPENDENCIES) lib/stdio/stdio.header lib/string/string.picoc lib/string/string.header
	picoc_compiler \
		system/shell.picoc $(SYSTEM_LIBRARY_SOURCES) \
		-C $(USER_STARTUP_SOURCE) \
		-O1 -i -w -s -g -v \
		-o system/shell.reti

system/%.reti: system/%.picoc $(USER_STARTUP_DEPENDENCIES) $(USER_RUNTIME_DEPENDENCIES)
	picoc_compiler \
		$< $(USER_PROGRAM_CPL_ARGS) \
		-O1 -i -w -s -g -v \
		-o $@

system/%.bin: system/%.reti
	reti_emulator -f /tmp -a $<
	hexyl $@

user/%.reti: user/%.picoc $(USER_STARTUP_DEPENDENCIES) $(USER_RUNTIME_DEPENDENCIES)
	picoc_compiler \
		$< $(USER_PROGRAM_CPL_ARGS) \
		-O1 -i -w -s -g -v \
		-o $@

user/%.bin: user/%.reti
	reti_emulator -f /tmp -a $<
	hexyl $@

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

run-firmware: kernel.reti system/init.bin system/shell.bin
	reti_emulator kernel.reti -d -c -O -r $(SRAM_SIZE) -f /tmp

bootload: firmware
	reti_emulator -e ./eprom_startprogram/startprogram.reti -d -c -O -f /tmp -r $(SRAM_SIZE) -S kernel.sections -D kernel.debuginfo

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
	reti_emulator -e ./eprom_startprogram/startprogram.reti -d -c -O -f /tmp -r $(SRAM_SIZE) -S kernel.sections -D kernel.debuginfo


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
		-o -name 'output.txt' \
		-o -name 'raw_output.txt' \
		-o -name 'sram.bin' \
		-o -name 'kernel.bin' \
		\) -delete
