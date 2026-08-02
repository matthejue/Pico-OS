SHELL := /bin/bash

TEST_BUILD_MODE ?= staged
RESULT_DIR ?= /tmp/pico-os-library-tests
DEPENDENCY_DIR ?= .test_dependencies
TEST_SOURCES ?=
TEST_CPL_OPTIONS ?=
EXTRA_CPL_ARGS ?=
EXTRA_EMU_ARGS ?=

VALID_TEST_BUILD_MODES := staged direct
ifeq ($(filter $(TEST_BUILD_MODE),$(VALID_TEST_BUILD_MODES)),)
$(error TEST_BUILD_MODE must be 'staged' or 'direct')
endif

.PHONY: all FORCE

FORCE:

dependency_specs = $(strip $(shell sed -nE 's@^[[:space:]]*//[[:space:]]*dependencies[[:space:]]*:[[:space:]]*(.*)$$@\1@p' "$(1)"))
dependency_source = $(patsubst %.reti_blocks,%.picoc,$(1))
resolved_dependency_source = $(firstword $(realpath $(call dependency_source,$(1))) $(realpath $(dir $(2))$(call dependency_source,$(1))))
resolved_dependency = $(patsubst %.picoc,%.reti_blocks,$(call resolved_dependency_source,$(1),$(2)))
checked_dependency = \
  $(if $(filter %.reti_blocks,$(1)), \
    $(if $(call resolved_dependency_source,$(1),$(2)), \
      $(call resolved_dependency,$(1),$(2)), \
      $(error Dependency '$(1)' from '$(2)' was not found)), \
    $(error Dependency '$(1)' from '$(2)' must be a .reti_blocks file))
test_dependencies = $(foreach dependency,$(call dependency_specs,$(1)),$(call checked_dependency,$(dependency),$(1)))
dependency_sources = $(patsubst %.reti_blocks,%.picoc,$(1))
dependency_file = $(DEPENDENCY_DIR)/$(subst /,_,$(abspath $(1))).d
test_status = $(RESULT_DIR)/$(notdir $(basename $(1))).status

TEST_DEPENDENCIES := $(sort $(foreach test,$(TEST_SOURCES),$(call test_dependencies,$(test))))
TEST_BLOCKS := $(patsubst %.picoc,%.reti_blocks,$(TEST_SOURCES))
ALL_BLOCKS := $(TEST_BLOCKS) $(TEST_DEPENDENCIES)
DEPENDENCY_FILES := $(foreach block,$(ALL_BLOCKS),$(call dependency_file,$(block)))
ARTIFACT_FORCE := $(if $(strip $(EXTRA_CPL_ARGS)),FORCE,)
TEST_STATUSES := $(foreach test,$(TEST_SOURCES),$(call test_status,$(test)))

ifeq ($(TEST_BUILD_MODE),staged)
-include $(DEPENDENCY_FILES)
endif

all: $(TEST_STATUSES)

$(RESULT_DIR) $(DEPENDENCY_DIR):
	@mkdir -p "$@"

define artifact_template
$(1) $(patsubst %.reti_blocks,%.st,$(1)) $(call dependency_file,$(1)) &: $(patsubst %.reti_blocks,%.picoc,$(1)) ./opts/test_cpl_opts.txt $(ARTIFACT_FORCE) | $(DEPENDENCY_DIR)
	@picoc_compiler $(TEST_CPL_OPTIONS) $(EXTRA_CPL_ARGS) --show-input-files --dependency-file "$(call dependency_file,$(1))" -c "$(patsubst %.reti_blocks,%.picoc,$(1))"
endef

ifeq ($(TEST_BUILD_MODE),staged)
$(foreach block,$(ALL_BLOCKS),$(eval $(call artifact_template,$(block))))
endif

define test_template
TEST_DEPENDENCIES_$(notdir $(basename $(1))) := $(call test_dependencies,$(1))

ifeq ($(TEST_BUILD_MODE),staged)
$(call test_status,$(1)): $(basename $(1)).reti_blocks $(basename $(1)).st $$(TEST_DEPENDENCIES_$(notdir $(basename $(1)))) $$(patsubst %.reti_blocks,%.st,$$(TEST_DEPENDENCIES_$(notdir $(basename $(1))))) FORCE | $(RESULT_DIR)
	@./run_lib_test_case.sh staged "$$@" "$(1)" \
		"$(basename $(1)).reti_blocks" $(foreach dependency,$(call test_dependencies,$(1)),"$(dependency)")
else
$(call test_status,$(1)): FORCE | $(RESULT_DIR)
	@./run_lib_test_case.sh direct "$$@" "$(1)" \
		$(foreach dependency,$(call dependency_sources,$(call test_dependencies,$(1))),"$(dependency)")
endif
endef

$(foreach test,$(TEST_SOURCES),$(eval $(call test_template,$(test))))
