SHELL := /bin/bash

TEST_PATTERN ?= $(shell cat ./opts/test_pattern.txt)
RUN_PATH ?= $(shell cat ./opts/run_path.txt)
EXTRA_CPL_ARGS ?=
EXTRA_EMU_ARGS ?=

.PHONY: help run run_send_keypresses test test-all clean

help:
	@echo "Targets:"
	@echo "  make test                       Run sys tests using TEST_PATTERN"
	@echo "  make test-all                   Run all sys tests"
	@echo "  make clean                      Remove generated sys-test files"

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

test:
	./export_environment_vars_for_makefile.sh;\
	./run_sys_tests.sh $${COLUMNS} "$(TEST_PATTERN)" "$(EXTRA_CPL_ARGS)" "$(EXTRA_EMU_ARGS)"

test-all:
	./export_environment_vars_for_makefile.sh;\
	./run_sys_tests.sh $${COLUMNS} "all" "$(EXTRA_CPL_ARGS)" "$(EXTRA_EMU_ARGS)"

clean:
	find . -type f \
		! -path './interrupt_service_routines/*.reti' \
		\( -name '*.tokens' \
		-o -name '*.rtokens' \
		-o -name '*.dt' \
		-o -name '*.rdt' \
		-o -name '*.dt_simple' \
		-o -name '*.ast' \
		-o -name '*.rast' \
		-o -name '*.json' \
		-o -name '*.picoc_shrink' \
		-o -name '*.picoc_blocks' \
		-o -name '*.picoc_patch' \
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
		\) -delete
