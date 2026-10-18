# Safe Multi-Embodied Agents: Coordinating Connected Vehicles at an Intersection (ASU CSE 494/598, Fall 2026)
# Thin wrapper over the Python entry points. Run `make help` for the list.
# On Sol, run the same targets inside the container with:
#   make PY="bash scripts/sol_exec.sh python" <target>

SHELL := /bin/bash
ROOT := $(patsubst %/,%,$(dir $(abspath $(lastword $(MAKEFILE_LIST)))))
PY ?= $(if $(wildcard $(ROOT)/.venv/bin/python),$(ROOT)/.venv/bin/python,python3)
SCENARIO ?= nominal
MODE ?= robust
OUT ?= results/$(SCENARIO)-$(MODE)
GROUPID ?=
REQUIRE_GRAD ?= 0

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show the command surface
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z0-9_-]+:.*?## / {printf "  %-18s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.PHONY: check
check: ## Infrastructure check: Python, pinned SUMO packages, executables, one TraCI launch
	@$(PY) check_environment.py

.PHONY: baseline
baseline: ## Part 1: supplied nominal independent baseline into results/baseline
	@$(PY) run_lab.py --scenario nominal --mode independent --out results/baseline

.PHONY: run
run: ## One run: make run SCENARIO=slow_car MODE=lease [OUT=results/name]
	@$(PY) run_lab.py --scenario $(SCENARIO) --mode $(MODE) --out $(OUT)

.PHONY: matrix
matrix: ## Part 3: the 12 required scenario/policy runs into results/comparison
	@$(PY) run_matrix.py --out results/comparison

.PHONY: grad
grad: ## CSE 598: start-window sweep (0.5, 1, 2, 4 s) with a 0.8 s delay and no loss
	@for w in 05:0.5 1:1 2:2 4:4; do \
	  $(PY) run_lab.py --scenario nominal --mode robust --seed 2026 --delay 0.8 --loss 0 \
	    --lease-seconds $${w#*:} --out results/graduate-window-$${w%%:*} || exit $$?; \
	done

.PHONY: replay-planner
replay-planner: ## Replace the planner with the synthetic replay component
	@$(PY) run_lab.py --mode robust --planner replay --planner-file scenarios/replay_example.json --out results/replay-planner

.PHONY: submission
submission: ## Package one group ZIP: make submission GROUPID=<id> [REQUIRE_GRAD=1]
	@test -n "$(GROUPID)" || { echo "usage: make submission GROUPID=<id> [REQUIRE_GRAD=1]" >&2; exit 2; }
	@$(PY) package_submission.py --groupid "$(GROUPID)" $(if $(filter 1,$(REQUIRE_GRAD)),--require-grad,)

