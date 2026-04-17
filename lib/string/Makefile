# based on source: https://stackoverflow.com/a/30602701

SRC_DIR      := .
OBJ_DIR      := .
BIN_DIR      := .
TEST_DIR     := .
OBJ_TEST_DIR := .

BIN_SRC  := $(addsuffix .reti,$(BIN_DIR)/$(basename $(notdir $(wildcard $(SRC_DIR)/*_main.picoc))))
BIN_TEST := $(patsubst $(TEST_DIR)/%.picoc,$(BIN_DIR)/%.reti,$(wildcard $(TEST_DIR)/*_test.picoc))
SRC      := $(filter-out %_main.picoc %_test.picoc, $(wildcard $(SRC_DIR)/*.picoc))
OBJ_SRC  := $(SRC:$(SRC_DIR)/%.picoc=$(OBJ_DIR)/%.reti_blocks)
OBJ_TEST := $(patsubst $(TEST_DIR)/%.picoc,$(OBJ_TEST_DIR)/%.reti_blocks,$(wildcard $(TEST_DIR)/*_test.picoc))

CC			 := picoc_compiler
CFLAGS   := -s

.PRECIOUS: $(OBJ_DIR)/%.reti_blocks $(OBJ_TEST_DIR)/%.reti_blocks
.PHONY: all sys-test unit-test run clean clean-files debug

all: $(BIN_SRC)

SHELL := /bin/bash -x
unit-test: $(BIN_TEST)
		@bash -c 'for T in $(BIN_TEST); do \
			echo "Running $$T"; \
			./$$T || echo "$$T failed with exit code $$?"; \
		done'

$(BIN_DIR)/%_main.reti: $(OBJ_DIR)/%_main.reti_blocks $(OBJ_SRC)
	$(CC) $(CFLAGS) $^ -o $@

$(BIN_DIR)/%_test.reti: $(OBJ_TEST_DIR)/%_test.reti_blocks $(OBJ_SRC)
	$(CC) $(CFLAGS) $^ -o $@

$(OBJ_DIR)/%.reti_blocks: $(SRC_DIR)/%.picoc
	$(CC) $(CFLAGS) -c $< -o $@

$(OBJ_TEST_DIR)/%.reti_blocks: $(TEST_DIR)/%.picoc
	$(CC) $(CFLAGS) -c $< -o $@

sys-test: $(BIN_SRC)
	./export_environment_vars_for_makefile.sh;\
	./run_sys_tests.sh $${COLUMNS} $(shell cat ./opts/test_pattern.txt) $(EXTRA_ARGS);

run: $(BIN_SRC)
	./reti_emulator_main $(shell cat ./opts/run_opts.txt) $(EXTRA_ARGS) $(shell cat ./opts/run_path.txt)

clean: clean-files
	@$(RM) -v ./*.reti_blocks ./*.json ./*.reti

clean-files:
	find . -type f -wholename "./sys_test/*.output" -delete
	find . -type f -wholename "./sys_test/*.expected_output" -delete
	find . -type f -wholename "./sys_test/*.error" -delete
	find . -type f -name "sram.bin" -delete
	find . -type f -name "test_results" -delete

DEB_BIN := reti_emulator_main
run_send_keypresses:
	./send_keypresses.py --input ./opts/input.txt ./$(DEB_BIN) $(shell cat ./opts/run_opts.txt) $(EXTRA_ARGS) $(shell cat ./opts/run_path.txt)

debug: $(BIN_SRC) $(BIN_TEST)
	gdb --tui -n -x ./.gdbinit --args ./$(DEB_BIN) $(shell cat ./opts/deb_opts.txt) $(EXTRA_ARGS) $(shell cat ./opts/debug_path.txt)

debug_send_keypresses:
	./send_keypresses.py --input ./opts/debug_input.txt make debug DEB_BIN=$(DEB_BIN) EXTRA_ARGS=$(EXTRA_ARGS)

-include $(OBJ_SRC:.reti_blocks=.d) $(OBJ_TEST:.reti_blocks=.d)
