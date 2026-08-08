SHELL := /bin/bash

# ----------------------------------------------------------------------
# Normal test and program-run configuration
# ----------------------------------------------------------------------

TEST_PATTERN ?= $(shell cat ./config/test_pattern.txt)
RUN_PATH ?= $(shell cat ./config/run_path.txt)
OS_TEST_PATTERN ?= $(shell cat ./config/os_test_pattern.txt)
OS_RUN_PATH ?= $(shell cat ./config/os_run_path.txt)
OS_TEST_CPL_OPTS ?= $(shell cat ./config/os_test_cpl_opts.txt)
OS_TEST_EMU_OPTS ?= $(shell cat ./config/os_test_emu_opts.txt)
OS_RUN_CPL_OPTS ?= $(shell cat ./config/os_run_cpl_opts.txt)
OS_RUN_EMU_OPTS ?= $(shell cat ./config/os_run_emu_opts.txt)
SRAM_SIZE ?= 262144 # 2^18
KERNEL_STACK_START ?= 40000

EXTRA_CPL_ARGS ?=
EXTRA_EMU_ARGS ?=
TEST_BUILD_MODE ?= staged

VALID_TEST_BUILD_MODES := staged direct
ifeq ($(filter $(TEST_BUILD_MODE),$(VALID_TEST_BUILD_MODES)),)
$(error TEST_BUILD_MODE must be 'staged' or 'direct')
endif
TEST_BUILD_OPTION := $(if $(filter direct,$(TEST_BUILD_MODE)),--direct,)
TEST_JOB_OPTION := $(if $(strip $(TEST_JOBS)),--jobs $(TEST_JOBS),)

USER_STARTUP_SOURCE := library/start/libstart.picoc
USER_STARTUP_LIBRARY_SOURCES := library/stdlib/libstdlib.picoc
USER_STARTUP_DEPENDENCIES := \
	$(USER_STARTUP_SOURCE) \
	library/start/start.picoc \
	library/stdlib/libstdlib.picoc \
	library/stdlib/malloc.picoc \
	library/stdlib/atoi.picoc \
	library/stdlib/env.picoc \
	library/stdlib/exit.picoc \
	library/stdlib/stdlib.header \
	common/heap.picoc \
	common/heap.header
USER_RUNTIME_SOURCES := \
	library/unistd/libunistd.picoc \
	library/fcntl/libfcntl.picoc \
	library/sys/wait/libwait.picoc \
	library/signal/libsignal.picoc \
	library/sys/prctl/libprctl.picoc
USER_RUNTIME_DEPENDENCIES := \
	$(USER_RUNTIME_SOURCES) \
	library/unistd/process.picoc \
	library/unistd/io.picoc \
	library/unistd/blocking.picoc \
	library/unistd/unistd.header \
	library/fcntl/fcntl.picoc \
	library/fcntl/fcntl.header \
	library/sys/wait/wait.picoc \
	library/sys/wait/wait.header \
	library/signal/signal.picoc \
	library/signal/signal.header \
	library/sys/prctl/prctl.picoc \
	library/sys/prctl/prctl.header \
	common/syscall.header \
	common/signal.header \
	common/prctl.header \
	common/file.header \
	common/loading_bar.header \
	common/stddef.header \
	common/wait_queue.header
PICOC_BUILD := picoc_compiler --show-input-files
PICOC_BUILD_DIRECT := $(PICOC_BUILD) --direct-source-link
PICOC_TEST_BUILD := $(if $(filter direct,$(TEST_BUILD_MODE)),$(PICOC_BUILD_DIRECT),$(PICOC_BUILD))
TEST_BUILD_FORCE := $(if $(filter direct,$(TEST_BUILD_MODE)),FORCE,)

picoc_dependency_specs = $(strip $(shell sed -nE 's@^[[:space:]]*//[[:space:]]*dependencies[[:space:]]*:[[:space:]]*(.*)$$@\1@p' "$(1)"))
picoc_dependency_source = $(patsubst %.reti_blocks,%.picoc,$(1))
picoc_resolved_dependency_source = $(firstword $(realpath $(call picoc_dependency_source,$(1))) $(realpath $(dir $(2))$(call picoc_dependency_source,$(1))))
picoc_dependency_sources = $(foreach dependency,$(call picoc_dependency_specs,$(1)),$(call picoc_resolved_dependency_source,$(dependency),$(1)))
picoc_blocks = $(patsubst %.picoc,%.reti_blocks,$(1))
compile_picoc_sources = set -e; $(foreach source,$(1),$(PICOC_BUILD) "$(source)" -O1 -s -g -c;)
prepare_test_picoc_sources = $(if $(filter staged,$(TEST_BUILD_MODE)),$(call compile_picoc_sources,$(1)),:)
test_picoc_inputs = $(if $(filter direct,$(TEST_BUILD_MODE)),$(1),$(call picoc_blocks,$(1)))


# ----------------------------------------------------------------------
# Phony targets
# ----------------------------------------------------------------------

.PHONY: help code-index FORCE
.PHONY: run run_send_keypresses run-os
.PHONY: test test-fast test-lib test-all test_not_passed
.PHONY: test-sys test-sys-fast
.PHONY: test-os test-os-fast test-shell test-shell-fast
.PHONY: bootload bootload-debug run-kernel firmware eprom kernel isrs system user shell.bin shell.reti cat.bin cat.reti echo.bin echo.reti kill.bin kill.reti poweroff.bin poweroff.reti clean-firmware rebuild-firmware
.PHONY: clean

FORCE:


# ----------------------------------------------------------------------
# Help
# ----------------------------------------------------------------------

help:
	@echo "Targets:"
	@echo "  make run                        Run configured program using RUN_PATH"
	@echo "  make run_send_keypresses        Run configured program and send keypresses"
	@echo "  make run-os                     Run configured OS test using OS_RUN_PATH"
	@echo "  make test                       Run library, OS feature, and shell tests normally"
	@echo "  make test-fast                  Run library tests, then fast OS feature and shell test groups"
	@echo "  make test-lib                   Run library tests using TEST_PATTERN"
	@echo "  make test-all                   Alias for make test"
	@echo "  make test_not_passed            Run library paths from ./config/not_passed_tests.txt"
	@echo "  make test-sys                   Run OS feature and shell tests normally"
	@echo "  make test-sys-fast              Run OS feature and shell tests with one boot per group"
	@echo "  make test-os                    Run OS feature tests normally"
	@echo "  make test-os-fast               Run OS feature tests with one OS boot"
	@echo "  make test-shell                 Run shell tests normally"
	@echo "  make test-shell-fast            Run shell tests with one OS boot"
	@echo "  make firmware                   Build bootloader and kernel artifacts"
	@echo "  make bootload                   Build firmware and boot through startprogram.reti"
	@echo "  make bootload-debug             Rebuild PicoC files with -g and bootload"
	@echo "  make run-kernel                 Build and run kernel.reti directly"
	@echo "  make eprom                      Build boot/startprogram.reti"
	@echo "  make kernel                     Build kernel/kernel.bin"
	@echo "  make isrs                       Build the UART-only test ISR table"
	@echo "  make system                     Build system programs"
	@echo "  make user                       Build user programs"
	@echo "  make shell.bin                  Build the shell user program binary"
	@echo "  make cat.bin                    Build the cat user program binary"
	@echo "  make echo.bin                   Build the echo user program binary"
	@echo "  make kill.bin                   Build the kill user program binary"
	@echo "  make poweroff.bin               Build the poweroff user program binary"
	@echo "  make rebuild-firmware           Remove and rebuild firmware files"
	@echo "  make clean-firmware             Remove generated firmware files only"
	@echo "  make clean                      Remove generated test and firmware files"
	@echo "  make code-index                 Refresh VS Code navigation for PicoC files"
	@echo ""
	@echo "Variables:"
	@echo "  TEST_PATTERN=<pattern>          Override the configured test pattern"
	@echo "  RUN_PATH=<path>                 Override configured run path"
	@echo "  OS_TEST_PATTERN=<pattern>       Override the configured OS test pattern"
	@echo "  OS_RUN_PATH=<path>              Override configured OS run path"
	@echo "  OS_TEST_CPL_OPTS='<arguments>'  Override ./config/os_test_cpl_opts.txt"
	@echo "  OS_TEST_EMU_OPTS='<arguments>'  Override ./config/os_test_emu_opts.txt"
	@echo "  OS_RUN_CPL_OPTS='<arguments>'   Override ./config/os_run_cpl_opts.txt"
	@echo "  OS_RUN_EMU_OPTS='<arguments>'   Override ./config/os_run_emu_opts.txt"
	@echo "  EXTRA_CPL_ARGS='<arguments>'    Additional compiler arguments for normal runs/tests"
	@echo "  EXTRA_EMU_ARGS='<arguments>'    Additional emulator arguments for normal runs/tests"
	@echo "  TEST_BUILD_MODE=staged|direct   Select staged or direct test compilation (default: staged)"
	@echo "  TEST_JOBS=<count>               Set parallel normal-test jobs without prompting"
	@echo ""
	@echo "Each sys test is stopped automatically if the emulator exceeds"
	@echo "the timeout configured in ./run_sys_tests.sh."


# ----------------------------------------------------------------------
# Editor tooling
# ----------------------------------------------------------------------

code-index:
	./update_code_index.py


# ----------------------------------------------------------------------
# Normal program running
# ----------------------------------------------------------------------

run:
	./run.sh "$(RUN_PATH)" "$(EXTRA_CPL_ARGS)" "$(EXTRA_EMU_ARGS)"

run-os: kernel.reti system/init.bin user/shell.bin user/cat.bin user/kill.bin user/poweroff.bin
	./export_environment_vars_for_makefile.sh;\
	./run_os_tests.py --run "$(OS_RUN_PATH)" "$${COLUMNS:-120}" "" "$(OS_RUN_CPL_OPTS) $(EXTRA_CPL_ARGS) -C $(USER_STARTUP_SOURCE)" "$(OS_RUN_EMU_OPTS) -O $(EXTRA_EMU_ARGS)"

run_send_keypresses:
	@set -e; \
	run_path="$(RUN_PATH)"; \
	if [[ "$$run_path" == *.picoc ]]; then \
		compiled_path="$${run_path%.picoc}.reti"; \
		$(PICOC_BUILD) $$(cat ./config/run_cpl_opts.txt) $(EXTRA_CPL_ARGS) "$$run_path" -o "$$compiled_path"; \
		run_path="$$compiled_path"; \
	fi; \
	./send_keypresses.py --input ./config/input.txt ./run_reti_emulator_isolated.sh $$(cat ./config/run_emu_opts.txt) $(EXTRA_EMU_ARGS) "$$run_path"


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------

test:
	@test_jobs="$$(./select_test_jobs.sh)" || exit $$?; \
	summary_file=$$(mktemp); \
	status=0; \
	print_summary() { \
		echo; \
		./heading_subheadings.py heading "Final test summary" "$${COLUMNS:-120}" "="; \
		cat "$$summary_file"; \
		rm -f "$$summary_file"; \
	}; \
	trap print_summary EXIT; \
	echo "===== Library tests (make test-lib) ====="; \
	TEST_SUMMARY_FILE="$$summary_file" \
	TEST_SUMMARY_HEADING="Library tests (make test-lib)" \
	$(MAKE) test-lib TEST_JOBS="$$test_jobs" || status=$$?; \
	echo "===== System tests (make test-sys) ====="; \
	TEST_SUMMARY_FILE="$$summary_file" $(MAKE) test-sys TEST_JOBS="$$test_jobs" || status=$$?; \
	exit "$$status"

test-fast:
	@test_jobs="$$(./select_test_jobs.sh)" || exit $$?; \
	summary_file=$$(mktemp); \
	status=0; \
	print_summary() { \
		echo; \
		./heading_subheadings.py heading "Final test summary" "$${COLUMNS:-120}" "="; \
		cat "$$summary_file"; \
		rm -f "$$summary_file"; \
	}; \
	trap print_summary EXIT; \
	echo "===== Library tests (make test-lib) ====="; \
	TEST_SUMMARY_FILE="$$summary_file" \
	TEST_SUMMARY_HEADING="Library tests (make test-lib)" \
	$(MAKE) test-lib TEST_JOBS="$$test_jobs" || status=$$?; \
	echo "===== System tests (make test-sys-fast) ====="; \
	TEST_SUMMARY_FILE="$$summary_file" $(MAKE) test-sys-fast TEST_JOBS="$$test_jobs" || status=$$?; \
	exit "$$status"

test-lib: config/isrs.reti
	./export_environment_vars_for_makefile.sh;\
	TEST_JOBS="$(TEST_JOBS)" ./run_sys_tests.sh $(TEST_BUILD_OPTION) "$${COLUMNS:-120}" "$(TEST_PATTERN)" "$(EXTRA_CPL_ARGS)" "$(EXTRA_EMU_ARGS)"

test-all: test

test_not_passed:
	./export_environment_vars_for_makefile.sh;\
	TEST_JOBS="$(TEST_JOBS)" ./run_sys_tests.sh --not-passed $(TEST_BUILD_OPTION) "$${COLUMNS:-120}" "" "$(EXTRA_CPL_ARGS)" "$(EXTRA_EMU_ARGS)"

test-sys:
	@test_jobs="$$(./select_test_jobs.sh)" || exit $$?; \
	start=$$SECONDS; status=0; \
	TEST_SUMMARY_HEADING="OS feature tests (make test-os)" \
	$(MAKE) test-os TEST_JOBS="$$test_jobs" || status=$$?; \
	TEST_SUMMARY_HEADING="Shell tests (make test-shell)" \
	$(MAKE) test-shell TEST_JOBS="$$test_jobs" || status=$$?; \
	duration=$$(($$SECONDS - $$start)); \
	printf 'make test-sys completed in %02d:%02d\n' \
		"$$((duration / 60))" "$$((duration % 60))"; \
	exit "$$status"

test-os: kernel.reti system/init.bin user/shell.bin user/cat.bin user/echo.bin user/kill.bin user/poweroff.bin
	@start=$$SECONDS; \
	./export_environment_vars_for_makefile.sh; \
	./run_os_tests.py $(TEST_BUILD_OPTION) $(TEST_JOB_OPTION) --kind os "$${COLUMNS:-120}" "$(OS_TEST_PATTERN)" "$(OS_TEST_CPL_OPTS) $(EXTRA_CPL_ARGS) -C $(USER_STARTUP_SOURCE)" "$(OS_TEST_EMU_OPTS) -O $(EXTRA_EMU_ARGS)"; \
	status=$$?; duration=$$(($$SECONDS - $$start)); \
	printf 'make test-os completed in %02d:%02d\n' \
		"$$((duration / 60))" "$$((duration % 60))"; \
	exit "$$status"

test-shell: kernel.reti system/init.bin user/shell.bin user/cat.bin user/echo.bin user/kill.bin user/poweroff.bin
	@start=$$SECONDS; \
	./export_environment_vars_for_makefile.sh; \
	./run_os_tests.py $(TEST_BUILD_OPTION) $(TEST_JOB_OPTION) --kind shell "$${COLUMNS:-120}" "$(OS_TEST_PATTERN)" "$(OS_TEST_CPL_OPTS) $(EXTRA_CPL_ARGS) -C $(USER_STARTUP_SOURCE)" "$(OS_TEST_EMU_OPTS) -O $(EXTRA_EMU_ARGS)"; \
	status=$$?; duration=$$(($$SECONDS - $$start)); \
	printf 'make test-shell completed in %02d:%02d\n' \
		"$$((duration / 60))" "$$((duration % 60))"; \
	exit "$$status"

test-sys-fast:
	@test_jobs="$$(./select_test_jobs.sh)" || exit $$?; \
	start=$$SECONDS; status=0; \
	TEST_SUMMARY_HEADING="OS feature tests (make test-os-fast)" \
	$(MAKE) test-os-fast TEST_JOBS="$$test_jobs" || status=$$?; \
	TEST_SUMMARY_HEADING="Shell tests (make test-shell-fast)" \
	$(MAKE) test-shell-fast TEST_JOBS="$$test_jobs" || status=$$?; \
	duration=$$(($$SECONDS - $$start)); \
	printf 'make test-sys-fast completed in %02d:%02d\n' \
		"$$((duration / 60))" "$$((duration % 60))"; \
	exit "$$status"

test-os-fast: kernel.reti system/init.bin user/shell.bin system/fast_os_test_launcher.bin user/cat.bin user/echo.bin user/kill.bin user/poweroff.bin
	@start=$$SECONDS; \
	./export_environment_vars_for_makefile.sh; \
	./run_os_tests_fast.py $(TEST_BUILD_OPTION) --kind os "$${COLUMNS:-120}" "$(OS_TEST_PATTERN)" "$(OS_TEST_CPL_OPTS) $(EXTRA_CPL_ARGS) -C $(USER_STARTUP_SOURCE)" "$(OS_TEST_EMU_OPTS) -O $(EXTRA_EMU_ARGS)"; \
	status=$$?; duration=$$(($$SECONDS - $$start)); \
	printf 'make test-os-fast completed in %02d:%02d\n' \
		"$$((duration / 60))" "$$((duration % 60))"; \
	exit "$$status"

test-shell-fast: kernel.reti system/init.bin user/shell.bin system/fast_os_test_launcher.bin user/cat.bin user/echo.bin user/kill.bin user/poweroff.bin
	@start=$$SECONDS; \
	./export_environment_vars_for_makefile.sh; \
	./run_os_tests_fast.py $(TEST_BUILD_OPTION) --kind shell "$${COLUMNS:-120}" "$(OS_TEST_PATTERN)" "$(OS_TEST_CPL_OPTS) $(EXTRA_CPL_ARGS) -C $(USER_STARTUP_SOURCE)" "$(OS_TEST_EMU_OPTS) -O $(EXTRA_EMU_ARGS)"; \
	status=$$?; duration=$$(($$SECONDS - $$start)); \
	printf 'make test-shell-fast completed in %02d:%02d\n' \
		"$$((duration / 60))" "$$((duration % 60))"; \
	exit "$$status"


# ----------------------------------------------------------------------
# Firmware build
# ----------------------------------------------------------------------

firmware: boot/startprogram.reti kernel/kernel.bin system/init.bin user/shell.bin user/poweroff.bin

eprom: boot/startprogram.reti

kernel: kernel/kernel.bin

isrs: config/isrs.reti

SYSTEM_PROGRAM_SOURCES := $(wildcard system/*.picoc)
SYSTEM_PROGRAM_BINARIES := $(SYSTEM_PROGRAM_SOURCES:.picoc=.bin)
USER_PROGRAM_SOURCES := $(wildcard user/*.picoc)
USER_PROGRAM_BINARIES := $(USER_PROGRAM_SOURCES:.picoc=.bin)

system: $(SYSTEM_PROGRAM_BINARIES)

user: $(USER_PROGRAM_BINARIES)

user/echo.reti: library/stdio/libstdio.picoc library/stdio/stdio.picoc library/stdio/scanf.picoc library/stdio/stdio.header common/decimal.picoc common/decimal.header

cat.reti: user/cat.reti

cat.bin: user/cat.bin

echo.reti: user/echo.reti

echo.bin: user/echo.bin

kill.reti: user/kill.reti

kill.bin: user/kill.bin

poweroff.reti: user/poweroff.reti

poweroff.bin: user/poweroff.bin

shell.reti: user/shell.reti

shell.bin: user/shell.bin

ISRS_PICOC_SOURCES := \
	interrupt_service_routines/isrs.picoc \
	kernel/uart_hardware.picoc

config/isrs.reti: $(ISRS_PICOC_SOURCES)
	$(PICOC_BUILD_DIRECT) \
		$(ISRS_PICOC_SOURCES) \
		-O1 -i -w -s -v \
		-o config/isrs.reti

EPROM_PICOC_SOURCES := \
	boot/bootloader.picoc \
	common/loading_bar.picoc \
	common/sram_loader.picoc \
	kernel/uart_hardware.picoc \
	common/uart_protocol.picoc

EPROM_HEADERS := \
	config/config.header \
	common/loading_bar.header

boot/memory_constants.header: $(EPROM_PICOC_SOURCES) $(EPROM_HEADERS) kernel/memory_constants.header
	# The -k build creates memory_constants.header if none exists.
	# This earlier placeholder is only needed because preprocessing
	# bootloader.picoc requires the include before -k can compute addresses.
	@if [ ! -f boot/memory_constants.header ]; then \
		printf '%s\n' \
			'#define SRAM_MAX_ADDRESS 0' \
			'#define EPROM_DS_START_ASM "LOADI32 DS 0"' \
			'#define EPROM_STACK_START_ASM "LOADI32 SP 0"' \
			> boot/memory_constants.header; \
	fi
	$(PICOC_BUILD_DIRECT) \
		$(EPROM_PICOC_SOURCES) \
		-O1 -s -k eprom \
		-o boot/memory_constants.header

boot/startprogram.reti: $(EPROM_PICOC_SOURCES) $(EPROM_HEADERS) boot/memory_constants.header kernel/memory_constants.header
	$(PICOC_BUILD_DIRECT) \
		$(EPROM_PICOC_SOURCES) \
		-O1 -i -w -s -v \
		-o boot/startprogram.reti

SYSTEM_LIBRARY_SOURCES := \
	$(USER_STARTUP_LIBRARY_SOURCES) \
	$(USER_RUNTIME_SOURCES) \
	library/string/libstring.picoc
SHELL_LIBRARY_SOURCES := \
	$(SYSTEM_LIBRARY_SOURCES) \
	common/decimal.picoc
SYSTEM_INIT_SOURCES := system/init.picoc $(SYSTEM_LIBRARY_SOURCES)
SHELL_SOURCES := user/shell.picoc $(SHELL_LIBRARY_SOURCES)

system/init.reti: system/init.picoc config/config.header common/loading_bar.header $(SYSTEM_LIBRARY_SOURCES) $(USER_RUNTIME_DEPENDENCIES) $(USER_STARTUP_DEPENDENCIES) library/stdio/stdio.header library/string/string.picoc library/string/string.header $(TEST_BUILD_FORCE)
	@$(call prepare_test_picoc_sources,$(SYSTEM_INIT_SOURCES) $(USER_STARTUP_SOURCE))
	$(PICOC_TEST_BUILD) \
		$(call test_picoc_inputs,$(SYSTEM_INIT_SOURCES)) \
		-C $(call test_picoc_inputs,$(USER_STARTUP_SOURCE)) \
		-O1 -s -g \
		-o system/init.reti

system/init.bin: system/init.reti
	./run_reti_emulator_isolated.sh -a system/init.reti

user/shell.reti: user/shell.picoc $(SHELL_LIBRARY_SOURCES) $(USER_RUNTIME_DEPENDENCIES) $(USER_STARTUP_DEPENDENCIES) common/decimal.header library/string/string.picoc library/string/string.header $(TEST_BUILD_FORCE)
	@$(call prepare_test_picoc_sources,$(SHELL_SOURCES) $(USER_STARTUP_SOURCE))
	$(PICOC_TEST_BUILD) \
		$(call test_picoc_inputs,$(SHELL_SOURCES)) \
		-C $(call test_picoc_inputs,$(USER_STARTUP_SOURCE)) \
		-O1 -s -g \
		-o user/shell.reti

system/%.reti: system/%.picoc $(USER_STARTUP_DEPENDENCIES) $(USER_RUNTIME_DEPENDENCIES) $(TEST_BUILD_FORCE)
	@$(call prepare_test_picoc_sources,$< $(call picoc_dependency_sources,$<) $(USER_STARTUP_LIBRARY_SOURCES) $(USER_STARTUP_SOURCE))
	$(PICOC_TEST_BUILD) \
		$(call test_picoc_inputs,$< $(call picoc_dependency_sources,$<) $(USER_STARTUP_LIBRARY_SOURCES)) \
		-C $(call test_picoc_inputs,$(USER_STARTUP_SOURCE)) \
		-O1 -s -g \
		-o $@

system/%.bin: system/%.reti
	./run_reti_emulator_isolated.sh -a $<

user/%.reti: user/%.picoc $(USER_STARTUP_DEPENDENCIES) $(USER_RUNTIME_DEPENDENCIES) $(TEST_BUILD_FORCE)
	@$(call prepare_test_picoc_sources,$< $(call picoc_dependency_sources,$<) $(USER_STARTUP_LIBRARY_SOURCES) $(USER_STARTUP_SOURCE))
	$(PICOC_TEST_BUILD) \
		$(call test_picoc_inputs,$< $(call picoc_dependency_sources,$<) $(USER_STARTUP_LIBRARY_SOURCES)) \
		-C $(call test_picoc_inputs,$(USER_STARTUP_SOURCE)) \
		-O1 -s -g \
		-o $@

user/%.bin: user/%.reti
	./run_reti_emulator_isolated.sh -a $<

KERNEL_PICOC_SOURCES := \
	interrupt_service_routines/os_isrs.picoc \
	common/loading_bar.picoc \
	common/sram_loader.picoc \
	kernel/uart_hardware.picoc \
	common/uart_protocol.picoc \
	kernel/kernel.picoc \
	kernel/exception.picoc \
	kernel/interrupt_controller.picoc \
	kernel/periphery.picoc \
	common/heap.picoc \
	kernel/kmalloc.picoc \
	kernel/pmalloc.picoc \
	kernel/shared_memory.picoc \
	kernel/process/process.picoc \
	kernel/signal.picoc \
	kernel/filesystem/file_descriptor.picoc \
	kernel/filesystem/filesystem.picoc \
	kernel/filesystem/standard_input.picoc \
	kernel/process/process_arguments.picoc \
	kernel/scheduler.picoc \
	kernel/dispatcher.picoc \
	kernel/process/process_loader.picoc \
	kernel/syscall.picoc

KERNEL_HEADERS := \
	$(filter-out kernel/memory_constants.header,$(wildcard kernel/*.header)) \
	$(wildcard kernel/filesystem/*.header) \
	$(wildcard common/*.header)

kernel/memory_constants.header: $(KERNEL_PICOC_SOURCES) $(KERNEL_HEADERS) Makefile
	$(PICOC_BUILD_DIRECT) \
		$(KERNEL_PICOC_SOURCES) \
		-O1 -s -k sram \
		-o kernel/memory_constants.header
	@stack_address=$$((-2147483648 + $(KERNEL_STACK_START))); \
	process_memory_start=$$((stack_address + 1)); \
	sed -i -E \
		"s/^#define PROCESS_MEMORY_START .*/#define PROCESS_MEMORY_START $$process_memory_start \\/\\/ -2^31 + stack_start + 1/" \
		kernel/memory_constants.header; \
	sed -i -E \
		"s/^#define KERNEL_SP_START_ASM .*/#define KERNEL_SP_START_ASM \\\"LOADI32 SP $$stack_address\\\" \\/\\/ -2^31 + stack_start/" \
		kernel/memory_constants.header

kernel.reti: $(KERNEL_PICOC_SOURCES) $(KERNEL_HEADERS) kernel/memory_constants.header Makefile
	$(PICOC_BUILD_DIRECT) \
		$(KERNEL_PICOC_SOURCES) \
		-O1 -i -w -s -g -v \
		-o kernel.reti
	sed -i -E 's/"stack_start": *-?[0-9]+/"stack_start": $(KERNEL_STACK_START)/' kernel.sections

kernel/kernel.bin: kernel.reti boot/startprogram.reti
	@set -e; \
	temporary_reti=kernel/.kernel.reti; \
	ln -sf ../kernel.reti "$$temporary_reti"; \
	trap 'rm -f "$$temporary_reti" kernel/.kernel.bin' EXIT; \
	./run_reti_emulator_isolated.sh -S kernel.sections -a "$$temporary_reti"; \
	mv kernel/.kernel.bin $@


# ----------------------------------------------------------------------
# Firmware bootload and direct kernel run
# ----------------------------------------------------------------------

run-firmware: kernel.reti system/init.bin user/shell.bin user/poweroff.bin
	./run_reti_emulator_isolated.sh kernel.reti -d -c -O -r $(SRAM_SIZE)

bootload: firmware
	./run_reti_emulator_isolated.sh -n 4 -e ./boot/startprogram.reti -d -c -O -r $(SRAM_SIZE) -S kernel.sections -D kernel.debuginfo

bootload-debug:
	$(MAKE) kernel/memory_constants.header
	$(MAKE) boot/memory_constants.header
	$(PICOC_BUILD_DIRECT) \
		$(EPROM_PICOC_SOURCES) \
		-O1 -i -w -s -g -v \
		-o boot/startprogram.reti
	$(PICOC_BUILD_DIRECT) \
		$(KERNEL_PICOC_SOURCES) \
		-O1 -i -w -s -g -v \
		-o kernel.reti
	sed -i -E 's/"stack_start": *-?[0-9]+/"stack_start": $(KERNEL_STACK_START)/' kernel.sections
	@set -e; \
	temporary_reti=kernel/.kernel.reti; \
	ln -sf ../kernel.reti "$$temporary_reti"; \
	trap 'rm -f "$$temporary_reti" kernel/.kernel.bin' EXIT; \
	./run_reti_emulator_isolated.sh -S kernel.sections -a "$$temporary_reti"; \
	mv kernel/.kernel.bin kernel/kernel.bin
	./run_reti_emulator_isolated.sh -n 4 -e ./boot/startprogram.reti -d -c -O -r $(SRAM_SIZE) -S kernel.sections -D kernel.debuginfo


# ----------------------------------------------------------------------
# Cleaning
# ----------------------------------------------------------------------

rebuild-firmware: clean-firmware firmware

clean-firmware:
	find common boot interrupt_service_routines kernel system -type f \
		! -name '*.picoc' \
		! -name '*.header' \
		! -name '.gitkeep' \
		-delete
	rm -f kernel.reti kernel/kernel.bin kernel.sections kernel.debuginfo

clean: clean-firmware
	find . -type f \
		! -path './.vscode/*' \
		! -path './boot/*' \
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
	find . -type f -path './.test_dependencies/*.d' -delete
	find . -type d -path './.test_dependencies' -empty -delete
