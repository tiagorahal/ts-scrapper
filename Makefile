IMAGE_NAME := ts-scrapper
CONTAINER_NAME := ts-scrapper-run

.PHONY: montar_ts shell_ts tjsp limpar_ts

montar_ts:
	@echo "🔨 Construindo imagem..."
	docker build -t $(IMAGE_NAME) .

# abre um bash dentro do container com o repo montado
shell_ts: montar_ts
	@echo "🐚 Abrindo shell no container..."
	docker run --rm -it \
		--name $(CONTAINER_NAME) \
		-v "$$PWD:/app" \
		$(IMAGE_NAME) /bin/bash

# roda o executor do TJSP a partir de /estados/sp
# uso: make tjsp ARG="18.188.384/0001-83"
tjsp: montar_ts
	@if [ -z "$$ARG" ]; then echo "Use: make tjsp ARG='<CNPJ/param>'"; exit 1; fi
	docker run --rm -it \
		--name $(CONTAINER_NAME) \
		-v "$$PWD:/app" \
		$(IMAGE_NAME) run-tjsp "$$ARG"

limpar_ts:
	- docker rm -f $(CONTAINER_NAME) 2>/dev/null || true
	- docker rmi -f $(IMAGE_NAME) 2>/dev/null || true
