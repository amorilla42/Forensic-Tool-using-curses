# Makefile

# Buscar la carpeta automáticamente
PROJECT_DIR := $(shell find /home -type d -name "Forensic-Tool-using-curses" 2>/dev/null | head -n 1)

# Directorio src dentro del proyecto
SRC_DIR := $(PROJECT_DIR)/src

run:
	@if [ -d "$(SRC_DIR)" ]; then \
		cd $(SRC_DIR) && python3 main.py; \
	else \
		echo "No se encontró el directorio Forensic-Tool-using-curses/src"; \
	fi

install-deps:
	@if [ -d "$(SRC_DIR)" ]; then \
		pip install -r $(SRC_DIR)/requirements.txt; \
	else \
		echo "No se encontró el directorio Forensic-Tool-using-curses/src"; \
	fi

.PHONY: run install-deps