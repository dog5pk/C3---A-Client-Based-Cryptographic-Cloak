# D-Bridge Makefile
# Canonical ship flow: selftest -> pack -> verify

SHELL := /usr/bin/env bash
ROOT  := $(shell pwd)
VERSION ?= $(shell git describe --tags --abbrev=0 2>/dev/null || date +%Y%m%d)

.PHONY: health selftest pack verify clean restart demo_systemd demo_spawn

health:
	@./scripts/check_health.sh

selftest:
	@./scripts/selftest.sh

pack:
	@VERSION=$(VERSION) ./scripts/pack_release.sh

verify:
	@./scripts/verify_release.sh V01.01 || ./scripts/verify_release.sh

clean:
	@./scripts/clean_demo.sh || true

restart:
	@./scripts/restart_relays.sh || true

demo_systemd:
	@./scripts/demo_systemd.sh

demo_spawn:
	@./scripts/demo_spawn.sh
