# C³ Makefile — light wrappers for the stubs (safe anywhere)
.PHONY: demo run stop analyze

demo:
	chmod +x demo.sh
	./demo.sh --preset low --duration 10

run:
	chmod +x run_local.sh
	./run_local.sh

stop:
	chmod +x stop_local.sh
	./stop_local.sh

analyze:
	python3 analyzer.py || true
