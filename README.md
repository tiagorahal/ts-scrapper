

# 🏛️ TJSP Scraper

Sistema automatizado para extração de processos judiciais do Tribunal de Justiça de São Paulo (TJSP). Realiza consultas em **1ª Instância**, **2ª Instância** e **Colégio Recursal**, exportando os dados para planilhas Excel.

> **Recomendado:** rodar via **Docker** (imagem Playwright com navegadores pré-instalados) usando os alvos do **Makefile**.

## 📋 Índice

* [Características](#-características)
* [Pré-requisitos](#-pré-requisitos)
* [Como rodar (Docker)](#-como-rodar-docker)
* [Comandos do Makefile](#-comandos-do-makefile)
* [Execução local (opcional)](#-execução-local-opcional)
* [Estrutura do Projeto](#-estrutura-do-projeto)
* [Configuração](#-configuração)
* [Logs e Saída](#-logs-e-saída)
* [Troubleshooting](#-troubleshooting)
* [Contribuição](#-contribuição)
* [Licença](#-licença)

## ✨ Características

* **🐳 Docker-first**: imagem baseada em `mcr.microsoft.com/playwright/python:v1.44.0-jammy`
* **🧠 Anti-detecção**: Playwright + stealth + delays humanizados
* **📊 Export Excel**: planilhas por instância
* **🔁 Execução Sequencial/Paralela**: escolha rodar 1, 2 ou 3 instâncias
* **🔧 Makefile**: comandos prontos (`montar`, `tjsp_seq`, `tjsp_1`, `tjsp_2`, `tjsp_c`, `shell`, `limpar`)
* **🧱 Resiliência**: patches automáticos de dependências Linux (sem libs só-Windows)
* **🧪 Diagnóstico**: scripts de debug/relatórios

## ✅ Pré-requisitos

* **Docker** 20+
* **Make** (GNU make)

> Se não quiser usar `make`, há exemplos com `docker run` mais abaixo.

## 🚀 Como rodar (Docker)

```bash
# 1) Clonar e entrar no projeto
git clone https://github.com/tiagorahal/ts-scrapper.git
cd ts-scrapper

# 2) Montar a imagem (sem cache, do zero)
make montar_limpo

# 3) Executar SEQUENCIAL (recomendado: evita 3 Chromiums simultâneos)
make tjsp_seq ARG="18.188.384/0001-83"

# (ou rodar cada instância separada)
make tjsp_1 ARG="18.188.384/0001-83"
make tjsp_2 ARG="18.188.384/0001-83"
make tjsp_c ARG="18.188.384/0001-83"

# abrir um shell dentro do container
make shell_ts
```

### Sem Makefile (só Docker)

```bash
docker pull mcr.microsoft.com/playwright/python:v1.44.0-jammy
docker build --no-cache -t ts-scrapper .

# Sequencial:
docker run --rm -it --name ts-scrapper-run --shm-size=1g \
  -e DISABLE_DESKTOP_NOTIFY=1 \
  -v "$PWD:/app" ts-scrapper run-tjsp -1 "18.188.384/0001-83"

docker run --rm -it --name ts-scrapper-run --shm-size=1g \
  -e DISABLE_DESKTOP_NOTIFY=1 \
  -v "$PWD:/app" ts-scrapper run-tjsp -2 "18.188.384/0001-83"

docker run --rm -it --name ts-scrapper-run --shm-size=1g \
  -e DISABLE_DESKTOP_NOTIFY=1 \
  -v "$PWD:/app" ts-scrapper run-tjsp -c "18.188.384/0001-83"
```

> **Dicas**
>
> * `--shm-size=1g` evita crash do Chromium em scraping pesado.
> * `DISABLE_DESKTOP_NOTIFY=1` silencia notificações no container.

## 🧰 Comandos do Makefile

| Alvo           | O que faz                                                                      | Exemplo                    |
| -------------- | ------------------------------------------------------------------------------ | -------------------------- |
| `montar_ts`    | Build da imagem com cache                                                      | `make montar_ts`           |
| `montar_limpo` | Build **sem cache** (reconstrói tudo)                                          | `make montar_limpo`        |
| `tjsp`         | Executa o orquestrador padrão (pode abrir 3 ao mesmo tempo, depende do código) | `make tjsp ARG="CNPJ"`     |
| `tjsp_seq`     | **Executa sequencialmente**: 1ª ➜ 2ª ➜ Colégio                                 | `make tjsp_seq ARG="CNPJ"` |
| `tjsp_1`       | Só 1ª instância                                                                | `make tjsp_1 ARG="CNPJ"`   |
| `tjsp_2`       | Só 2ª instância                                                                | `make tjsp_2 ARG="CNPJ"`   |
| `tjsp_c`       | Só Colégio Recursal                                                            | `make tjsp_c ARG="CNPJ"`   |
| `shell_ts`     | Abre um bash no container com o repo montado                                   | `make shell_ts`            |
| `limpar_ts`    | Remove container/imagem                                                        | `make limpar_ts`           |

**Variáveis úteis:**

* `PW_PARALLEL` — se o orquestrador suportar, controla concorrência interna (default `1` no Makefile):

  ```bash
  make PW_PARALLEL=2 tjsp ARG="CNPJ"
  ```
* `SHM` — memória compartilhada do container (default `1g`):

  ```bash
  make SHM=2g tjsp_seq ARG="CNPJ"
  ```

## 🐍 Execução local (opcional)

> Só se você preferir rodar sem Docker.

```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -r requirements.txt

# baixar navegadores do Playwright
python -m pip install playwright==1.44.0
playwright install chromium

# rodar
cd estados/sp
python tjsp_executor.py "18.188.384/0001-83"
# ou:
python tjsp_executor.py -1 "CNPJ"    # 1ª
python tjsp_executor.py -2 "CNPJ"    # 2ª
python tjsp_executor.py -c "CNPJ"    # Colégio
```

## 📁 Estrutura do Projeto

```
ts-scrapper/
├── estados/sp/
│   ├── dados/                        # 📊 Planilhas geradas (.xlsx)
│   ├── logs/                         # 📝 Logs de execução
│   ├── relatorios/                   # 📄 Relatórios HTML (se habilitado)
│   ├── prints/                       # 📸 Screenshots/HTML de debug
│   ├── tjsp_executor.py              # 🎮 Orquestrador
│   ├── scrappers_implementados.py    # 🧩 Scrapers por instância
│   ├── analisador.py                 # 📈 Análise agregada
│   └── ... (outros utilitários)
├── Dockerfile                        # 🐳 Build usando Playwright + browsers
├── Makefile                          # 🔧 Comandos prontos
├── requirements.txt                  # 📦 Dependências (Linux-patched no build)
└── README.md                         # 📖 Este arquivo
```

## ⚙️ Configuração

Principais variáveis (lidas por CLI/env/código):

| Variável/Flag                  | Descrição                                        | Exemplo              |
| ------------------------------ | ------------------------------------------------ | -------------------- |
| `-1`, `-2`, `-c`               | Seleciona instâncias (1ª, 2ª, Colégio)           | `run-tjsp -1 "CNPJ"` |
| `PW_PARALLEL` (env)            | Limita concorrência de Playwright (se suportado) | `PW_PARALLEL=1`      |
| `DISABLE_DESKTOP_NOTIFY` (env) | Desliga notificações no container                | `1`                  |
| Timeouts/Delays                | Ajuste no código (delays humanizados, timeouts)  | —                    |

## 🗂️ Logs e Saída

* **Planilhas**: `estados/sp/dados/`

  * `primeira_instancia_tjsp.xlsx`
  * `segunda_instancia_tjsp.xlsx`
  * `colegio_recursal_tjsp.xlsx`
* **Logs**: `estados/sp/logs/`
* **Debug** (se habilitado): `estados/sp/prints/`

## 🛠️ Troubleshooting

### ❌ “Abriu 3 Playwright ao mesmo tempo”

* Use execução **sequencial**:

  ```bash
  make tjsp_seq ARG="CNPJ"
  ```
* Ou, se o orquestrador suportar, limite:

  ```bash
  make PW_PARALLEL=1 tjsp ARG="CNPJ"
  ```

### ❌ “No such file or directory: 'gdbus'” / DBus / notificação

* No Docker, desabilite notificações:

  ```bash
  make tjsp_seq ARG="CNPJ" PW_PARALLEL=1
  ```

  (o Makefile já exporta `DISABLE_DESKTOP_NOTIFY=1`).
* Alternativamente, instale `libglib2.0-bin libnotify-bin dbus` (já incluso na imagem base Playwright Jammy).

### ❌ Playwright “Executable doesn’t exist…”

* Na imagem Playwright **não** precisa `playwright install`. Se estiver rodando **local**, rode:

  ```bash
  playwright install chromium
  ```

### ❌ `' margin'`

* Chave de layout com espaço (Plotly/Matplotlib). Patch rápido:

  ```bash
  sed -i "s/' margin'/'margin'/g; s/\" margin\"/\"margin\"/g" estados/sp/analisador.py
  ```

### ❌ `'datetime.datetime' object has no attribute 'get'`

* Algum ponto espera `dict` e recebe `datetime`. Adicione um guard no local apontado pelo stack:

  ```python
  from datetime import datetime
  if isinstance(obj, datetime):
      # converter para string/data ou pular
  ```

### ❌ Falhas de dependência no Linux

* O Docker já **remove** libs só-Windows (`pywin32`, `pypiwin32`, `win10toast`) e corrige pins problemáticos (`numpy==1.26.4`, `scikit-learn==1.4.2`, `proxy-requests==0.5.2`).

## 🤝 Contribuição

1. Faça um **fork**
2. Crie uma branch: `git checkout -b feature/minha-feature`
3. Commit: `git commit -m "feat: minha feature"`
4. Push: `git push origin feature/minha-feature`
5. Abra um **PR**

## 📄 Licença

Licença **MIT**. Veja `LICENSE`.

---

**Autor:** [@tiagorahal](https://github.com/tiagorahal)
**Versão atual:** 1.0.0
**Status:** ✅ Ativo
**Última atualização:** **Agosto/2025**

> ⭐ Curtiu? Deixa uma estrela no GitHub!
