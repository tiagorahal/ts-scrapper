IMAGE_NAME := ts-scrapper
CONTAINER_NAME := ts-scrapper-run
SHM ?= 1g                 # memória compartilhada pro Chromium
PW_PARALLEL ?= 1          # usado se o orquestrador ler PW_PARALLEL

DOCKER_RUN := docker run --rm -it \
	--name $(CONTAINER_NAME) \
	--shm-size=$(SHM) \
	-e DISABLE_DESKTOP_NOTIFY=1 \
	-e PW_PARALLEL=$(PW_PARALLEL) \
	-v "$$PWD:/app" \
	$(IMAGE_NAME)

.PHONY: montar_ts montar_limpo shell_ts tjsp tjsp_seq tjsp_1 tjsp_2 tjsp_c limpar_ts

montar_ts:
	@echo "🔨 Construindo imagem..."
	docker build -t $(IMAGE_NAME) .

montar_limpo:
	@echo "🧼 Build sem cache..."
	docker build --no-cache -t $(IMAGE_NAME) .

# abre um bash dentro do container com o repo montado
shell_ts: montar_ts
	@echo "🐚 Abrindo shell no container..."
	$(DOCKER_RUN) /bin/bash

# roda o executor do TJSP (modo padrão - pode abrir 3 em paralelo dependendo do código)
# uso: make tjsp ARG="18.188.384/0001-83"
tjsp: montar_ts
	@if [ -z "$$ARG" ]; then echo "Use: make tjsp ARG='<CNPJ/param>'"; exit 1; fi
	$(DOCKER_RUN) run-tjsp "$$ARG"

# roda SEQUENCIALMENTE: 1ª, 2ª e Colégio (evita 3 Playwright simultâneos)
# uso: make tjsp_seq ARG="18.188.384/0001-83"
tjsp_seq: montar_ts
	@if [ -z "$$ARG" ]; then echo "Use: make tjsp_seq ARG='<CNPJ/param>'"; exit 1; fi
	$(DOCKER_RUN) run-tjsp -1 "$$ARG"
	$(DOCKER_RUN) run-tjsp -2 "$$ARG"
	$(DOCKER_RUN) run-tjsp -c "$$ARG"

# targets por instância (úteis pra depurar)
tjsp_1: montar_ts
	@if [ -z "$$ARG" ]; then echo "Use: make tjsp_1 ARG='<CNPJ/param>'"; exit 1; fi
	$(DOCKER_RUN) run-tjsp -1 "$$ARG"

tjsp_2: montar_ts
	@if [ -z "$$ARG" ]; then echo "Use: make tjsp_2 ARG='<CNPJ/param>'"; exit 1; fi
	$(DOCKER_RUN) run-tjsp -2 "$$ARG"

tjsp_c: montar_ts
	@if [ -z "$$ARG" ]; then echo "Use: make tjsp_c ARG='<CNPJ/param>'"; exit 1; fi
	$(DOCKER_RUN) run-tjsp -c "$$ARG"

limpar_ts:
	- docker rm -f $(CONTAINER_NAME) 2>/dev/null || true
	- docker rmi -f $(IMAGE_NAME) 2>/dev/null || true
