# 🏛️ TJSP Scraper

Sistema automatizado para extração de processos judiciais do Tribunal de Justiça de São Paulo (TJSP). Realiza consultas simultâneas em **1ª Instância**, **2ª Instância** e **Colégio Recursal**, exportando os dados para planilhas Excel organizadas.

## 📋 Índice

- [Características](#-características)
- [Instalação](#-instalação)
- [Uso](#-uso)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Configuração](#-configuração)
- [Logs e Monitoramento](#-logs-e-monitoramento)
- [Troubleshooting](#-troubleshooting)
- [Contribuição](#-contribuição)

## ✨ Características

- **🔄 Execução Paralela**: Consulta as 3 instâncias simultaneamente
- **📊 Export Excel**: Dados organizados em planilhas estruturadas
- **🔍 Logs em Tempo Real**: Monitoramento detalhado da execução
- **🤖 Comportamento Humano**: Delays inteligentes para evitar detecção
- **📄 Extração Completa**: Movimentações, partes, valores e detalhes processuais
- **🛡️ Anti-Detecção**: User-agents realistas e timing humanizado
- **💾 Dados Incrementais**: Evita duplicatas e permite execuções múltiplas

## 🚀 Instalação

### Pré-requisitos

- Python 3.8+
- pip (gerenciador de pacotes Python)

### 1. Clone o Repositório

```bash
git clone https://github.com/tiagorahal/ts-scrapper.git
cd ts-scrapper
```

### 2. Configure o Ambiente Virtual

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

### 3. Instale as Dependências

```bash
pip install -r requirements.txt
```

### 4. Instale o Playwright

```bash
playwright install chromium
```

## 🎯 Uso

### Execução Completa (Recomendada)

```bash
cd estados/sp/
python tjsp_rodar.py
```

O sistema irá:
1. ✅ Solicitar o CNPJ da empresa
2. ✅ Executar os 3 scripts em paralelo
3. ✅ Mostrar logs em tempo real
4. ✅ Gerar planilhas na pasta `dados/`

### Execução Individual

Para testar uma instância específica:

```bash
# 1ª Instância
python tjsp_primeira_instancia.py "00.000.000/0001-91"

# 2ª Instância  
python tjsp_segunda_instancia.py "00.000.000/0001-91"

# Colégio Recursal
python tjsp_colegio_recursal.py "00.000.000/0001-91"
```

### Diagnóstico do Sistema

Para verificar se tudo está funcionando:

```bash
python diagnostic_tjsp.py
```

## 📁 Estrutura do Projeto

```
ts-scrapper/
├── estados/sp/
│   ├── dados/                          # 📊 Planilhas geradas
│   │   ├── primeira_instancia_tjsp.xlsx
│   │   ├── segunda_instancia_tjsp.xlsx
│   │   └── colegio_recursal_tjsp.xlsx
│   ├── prints/                         # 📸 Screenshots de debug
│   ├── tjsp_rodar.py                   # 🎮 Executor principal
│   ├── tjsp_primeira_instancia.py      # 🏛️ Script 1ª instância
│   ├── tjsp_segunda_instancia.py       # ⚖️ Script 2ª instância
│   ├── tjsp_colegio_recursal.py        # 🎓 Script colégio recursal
│   ├── diagnostic_tjsp.py              # 🔍 Diagnóstico do sistema
│   ├── debug_offline.py                # 🛠️ Debug offline
│   └── analise_seletores.py            # 🔧 Análise de seletores
├── venv/                               # 🐍 Ambiente virtual
├── requirements.txt                    # 📦 Dependências
└── README.md                           # 📖 Este arquivo
```

## ⚙️ Configuração

### Campos Extraídos

Cada planilha contém os seguintes campos:

| Campo | Descrição |
|-------|-----------|
| `instancia` | 1ª Instância / 2ª Instância / Colégio Recursal |
| `numero` | Número do processo |
| `link` | URL do processo no TJSP |
| `classe` | Classe processual |
| `assunto` | Assunto do processo |
| `relator` | Relator (2ª instância/Colégio) |
| `foro` | Foro de origem |
| `vara` | Vara responsável |
| `juiz` | Juiz responsável |
| `requerente` | Parte requerente |
| `requerido` | Parte requerida |
| `valor_acao` | Valor da ação |
| `movimentacoes` | Últimas movimentações |
| `distribuicao` | Data de distribuição |
| `area` | Área do direito |

### Personalização

Para modificar campos ou comportamento, edite as constantes nos scripts:

```python
# Timeout para aguardar elementos (ms)
TIMEOUT_PADRAO = 15000

# Campos extraídos
CAMPOS_PADRAO = [
    "instancia", "numero", "link", 
    # ... adicione campos personalizados
]
```

## 📊 Logs e Monitoramento

### Logs em Tempo Real

Durante a execução, você verá logs detalhados:

```
[22:15:30] [primeira_instancia] 🌐 Página carregada, aguardando estabilizar...
[22:15:33] [primeira_instancia] 🔍 Aguardando seletor de pesquisa...
[22:15:35] [segunda_instancia] 📋 Selecionando 'Documento da Parte'...
[22:15:37] [colegio_recursal] ⌨️ Digitando CNPJ: 00.000.000/0001-91
[22:15:42] [primeira_instancia] 🚀 Clicando no botão consultar...
[22:15:45] [segunda_instancia] ✅ Página de resultados carregada!
```

### Relatórios de Debug

O sistema gera relatórios automáticos na pasta `prints/`:

- `dependencias_*.txt` - Status das dependências
- `analise_arquivos_*.txt` - Verificação dos scripts
- `debug_*.png` - Screenshots das páginas
- `debug_*.html` - HTML das páginas para análise

## 🔧 Troubleshooting

### Problemas Comuns

#### ❌ "Seletor não encontrado"
```bash
# Execute o diagnóstico
python diagnostic_tjsp.py

# Verifique se o site está online
# Screenshots serão salvas em prints/
```

#### ❌ "Timeout ao clicar no botão"
```bash
# Teste individual para debug
python tjsp_primeira_instancia.py "00.000.000/0001-91"

# Verifique logs detalhados para identificar onde para
```

#### ❌ "Playwright não instalado"
```bash
pip install playwright
playwright install chromium
```

#### ❌ "Arquivo Excel corrompido"
```bash
# Remove arquivos corrompidos
rm dados/*.xlsx

# Executa novamente
python tjsp_rodar.py
```

### Debug Avançado

Para análise detalhada dos problemas:

```bash
# Debug offline completo
python debug_offline.py

# Análise de seletores CSS
python analise_seletores.py

# Diagnóstico com screenshots
python diagnostic_tjsp.py
```

### Limitações Conhecidas

- ⚠️ **Rate limiting**: Evite execuções muito frequentes
- ⚠️ **Captchas**: Podem aparecer em consultas excessivas
- ⚠️ **Mudanças no site**: Seletores podem mudar

## 🛡️ Considerações Legais

- ✅ **Uso Responsável**: Respeite os termos de uso do TJSP
- ✅ **Rate Limiting**: Sistema inclui delays para evitar sobrecarga
- ✅ **Dados Públicos**: Apenas consulta informações públicas
- ✅ **Compliance**: Adequado para uso advocatício e empresarial

## 🤝 Contribuição

### Como Contribuir

1. **Fork** o projeto
2. **Crie** uma branch para sua feature (`git checkout -b feature/nova-funcionalidade`)
3. **Commit** suas mudanças (`git commit -am 'Adiciona nova funcionalidade'`)
4. **Push** para a branch (`git push origin feature/nova-funcionalidade`)
5. **Abra** um Pull Request

### Reportar Bugs

Use as [Issues do GitHub](https://github.com/tiagorahal/ts-scrapper/issues) para reportar bugs, incluindo:

- 🐛 Descrição do problema
- 📱 Sistema operacional
- 🐍 Versão do Python
- 📄 Logs de erro completos
- 📸 Screenshots se relevante

### Roadmap

- [ ] 🔐 Suporte a autenticação com certificado digital
- [ ] 📊 Dashboard web para visualização dos dados
- [ ] 🤖 Integração com APIs
- [ ] 📱 Versão mobile/responsiva
- [ ] 🔔 Notificações automáticas de movimentações
- [ ] 📈 Análises estatísticas automáticas

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.

## 👥 Autores

- **Tiago Rahal** - *Desenvolvimento inicial* - [@tiagorahal](https://github.com/tiagorahal)

## 📞 Suporte

- 📧 **Email**: [rahal.aires@gmail.com]
- 🐛 **Issues**: [GitHub Issues](https://github.com/tiagorahal/ts-scrapper/issues)
- 💬 **Discussões**: [GitHub Discussions](https://github.com/tiagorahal/ts-scrapper/discussions)

---

⭐ **Se este projeto te ajudou, considere dar uma estrela no GitHub!**

**Versão atual**: 1.0.0  
**Status**: ✅ Ativo e Funcional  
**Última atualização**: Agosto 2025