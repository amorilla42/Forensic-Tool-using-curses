# Makefile

# 1) Buscar el proyecto
PROJECT_DIR := $(shell find /home -type d -name "Forensic-Tool-using-curses" 2>/dev/null | head -n 1)
SRC_DIR     := $(PROJECT_DIR)/src

# 2) Rutas del entorno virtual en Linux
VENV_DIR    := $(PROJECT_DIR)/forensic_env
VENV_PYTHON := $(VENV_DIR)/bin/python

# 3) URL de rockyou.txt.gz (mirror confiable en GitHub)
ROCKYOU_URL := https://github.com/praetorian-inc/Hob0Rules/raw/master/wordlists/rockyou.txt.gz
ROCKYOU_TXT := $(SRC_DIR)/rockyou.txt
ROCKYOU_GZ  := $(SRC_DIR)/rockyou.txt.gz

.PHONY: run venv install-deps rockyou all clean clean-venv clean-rockyou

all: run

# Crear venv solo la primera vez
venv:
	@if [ -z "$(PROJECT_DIR)" ] || [ ! -d "$(SRC_DIR)" ]; then \
		echo "❌ No se encontró Forensic-Tool-using-curses/src en /home"; exit 1; \
	fi
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "🆕 Creando entorno virtual en $(VENV_DIR) ..."; \
		python3 -m venv "$(VENV_DIR)"; \
		"$(VENV_PYTHON)" -m pip install --upgrade pip; \
		"$(VENV_PYTHON)" -m pip install -r "$(SRC_DIR)/requirements.txt"; \
		echo "✅ Entorno creado e instalaciones completadas."; \
	else \
		echo "ℹ️ Entorno ya existe: $(VENV_DIR)"; \
	fi

# Descargar rockyou.txt si no está
rockyou:
	@if [ ! -f "$(ROCKYOU_TXT)" ]; then \
		echo "⬇️  Descargando rockyou.txt ..."; \
		wget -q -O "$(ROCKYOU_GZ)" "$(ROCKYOU_URL)" || (echo "❌ Error al descargar rockyou"; exit 1); \
		gunzip -f "$(ROCKYOU_GZ)"; \
		echo "✅ rockyou.txt disponible en $(ROCKYOU_TXT)"; \
	else \
		echo "ℹ️ rockyou.txt ya existe en $(ROCKYOU_TXT)"; \
	fi

# Ejecutar la app desde el venv (asegurando que rockyou.txt exista)
run: venv rockyou
	@cd "$(SRC_DIR)" && "$(VENV_PYTHON)" main.py

# Reinstalar dependencias manualmente
install-deps: venv
	@"$(VENV_PYTHON)" -m pip install -r "$(SRC_DIR)/requirements.txt"


# Borrar el entorno virtual si existe
clean-venv:
	@if [ -d "$(VENV_DIR)" ]; then \
		echo "🗑️  Eliminando entorno virtual $(VENV_DIR)"; \
		rm -rf "$(VENV_DIR)"; \
	else \
		echo "ℹ️ No existe entorno virtual en $(VENV_DIR)"; \
	fi

# Borrar rockyou.txt y su .gz si existen
clean-rockyou:
	@if [ -f "$(ROCKYOU_TXT)" ]; then \
		echo "🗑️  Eliminando $(ROCKYOU_TXT)"; \
		rm -f "$(ROCKYOU_TXT)"; \
	else \
		echo "ℹ️ No existe $(ROCKYOU_TXT)"; \
	fi

# Borrar todo (venv + rockyou)
clean: clean-venv clean-rockyou
	@echo "✅ Limpieza completa."
