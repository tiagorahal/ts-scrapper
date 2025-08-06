import asyncio
import pandas as pd
from pathlib import Path
from random import randint
from playwright.async_api import async_playwright
import os
import sys

# Adaptado para salvar na pasta dados
SCRIPT_DIR = Path(__file__).parent
DADOS_DIR = SCRIPT_DIR / "dados"
DADOS_DIR.mkdir(exist_ok=True)
EXCEL_PATH = DADOS_DIR / "primeira_instancia_tjsp.xlsx"

CAMPOS_PADRAO = [
    "instancia", "numero", "link", "classe", "assunto", "relator", "outros_numeros", "origem",
    "volume_apenso", "ultima_carga", "foro", "vara", "juiz", "requerente", "requerido", "polo_terceiro",
    "audiencia", "julgamento", "distribuicao", "controle", "area", "valor_acao", "movimentacoes", "movimentacoes_detalhe"
]

def salvar_incremental_excel(dados):
    try:
        df_novo = pd.DataFrame(dados)
        for col in CAMPOS_PADRAO:
            if col not in df_novo.columns:
                df_novo[col] = ""
        df_novo = df_novo[CAMPOS_PADRAO]
        if EXCEL_PATH.exists():
            antigo = pd.read_excel(EXCEL_PATH)
            for col in CAMPOS_PADRAO:
                if col not in antigo.columns:
                    antigo[col] = ""
            antigo = antigo[CAMPOS_PADRAO]
            df_final = pd.concat([antigo, df_novo], ignore_index=True)
            df_final.drop_duplicates(subset=["numero", "instancia"], keep="last", inplace=True)
        else:
            df_final = df_novo
        temp_path = EXCEL_PATH.with_suffix(".temp.xlsx")
        df_final.to_excel(temp_path, index=False)
        os.replace(temp_path, EXCEL_PATH)
        print(f"\n✅ Resultado salvo: {dados[0]['numero']} ({dados[0]['instancia']}) → {EXCEL_PATH}")
    except Exception as e:
        print(f"❌ Erro ao salvar Excel: {e}")

async def digitar_com_humanidade(page, selector, texto):
    await page.click(selector)
    await page.wait_for_timeout(randint(300, 800))  # Pausa após click
    await page.fill(selector, "")
    await page.wait_for_timeout(randint(200, 500))  # Pausa após limpar
    
    for i, caractere in enumerate(texto):
        await page.type(selector, caractere)
        # Varia o tempo entre caracteres de forma mais humana
        if i % 3 == 0:  # A cada 3 caracteres, pausa maior
            await page.wait_for_timeout(randint(150, 400))
        else:
            await page.wait_for_timeout(randint(80, 200))
    
    # Pausa final após digitar tudo
    await page.wait_for_timeout(randint(500, 1200))

async def aguardar_sem_erro(page, selector, timeout=10000):
    """Aguarda elemento sem dar erro se não encontrar"""
    try:
        await page.wait_for_selector(selector, timeout=timeout)
        return True
    except:
        return False

async def extrair_processos_da_pagina_primeira(page):
    rows = await page.query_selector_all("ul.unj-list-row > li .home__lista-de-processos")
    for row in rows:
        try:
            numero_el = await row.query_selector(".nuProcesso a")
            if not numero_el:
                continue
                
            link = await numero_el.get_attribute("href")
            detalhe_url = f"https://esaj.tjsp.jus.br{link}" if link else ""
            
            detalhe = await page.context.new_page()
            await detalhe.goto(detalhe_url)
            await detalhe.wait_for_load_state("networkidle")
            
            # Tenta expandir detalhes se houver botão "mais"
            mais_btn = await detalhe.query_selector("a.unj-link-collapse")
            if mais_btn:
                await mais_btn.click()
                await detalhe.wait_for_timeout(1000)

            # Função helper para extrair texto
            async def extrair_texto(selector):
                try:
                    el = await detalhe.query_selector(selector)
                    return await el.inner_text() if el else ""
                except:
                    return ""

            numero = await extrair_texto("#numeroProcesso")
            classe = await extrair_texto("#classeProcesso")
            assunto = await extrair_texto("#assuntoProcesso")
            foro = await extrair_texto("#foroProcesso")
            vara = await extrair_texto("#varaProcesso")
            juiz = await extrair_texto("#juizProcesso")
            
            # Extrai partes
            requerente = ""
            requerido = ""
            try:
                partes_raw = await detalhe.query_selector_all("#tablePartesPrincipais tr")
                for parte in partes_raw:
                    tipo_el = await parte.query_selector(".tipoDeParticipacao")
                    nome_el = await parte.query_selector(".nomeParteEAdvogado")
                    if tipo_el and nome_el:
                        tipo = await tipo_el.inner_text()
                        nome = await nome_el.inner_text()
                        if "Reqte" in tipo or "Apelante" in tipo:
                            requerente = nome.strip()
                        elif "Reqdo" in tipo or "Apelado" in tipo:
                            requerido = nome.strip()
            except:
                pass

            audiencia = await extrair_texto("#processoSemAudiencias")
            julgamento = await extrair_texto("#processoSemJulgamentos")
            
            # Extrai movimentações
            movimentacoes = []
            movimentacoes_detalhe = []
            try:
                mov_rows = await detalhe.query_selector_all("#tabelaUltimasMovimentacoes tr")
                for mov in mov_rows:
                    data_el = await mov.query_selector("td.data")
                    desc_el = await mov.query_selector("td.movimentacao")
                    if data_el and desc_el:
                        data = (await data_el.inner_text()).strip()
                        desc = (await desc_el.inner_text()).strip()
                        movimentacoes.append(f"{data} - {desc}")
                        
                        # Verifica se há detalhes
                        detalhe_el = await mov.query_selector("td.movimentacao span span")
                        if detalhe_el:
                            detalhe_txt = (await detalhe_el.inner_text()).strip()
                            movimentacoes_detalhe.append(f"{data} - {desc} => {detalhe_txt}")
                        else:
                            movimentacoes_detalhe.append(f"{data} - {desc}")
            except:
                pass

            distribuicao = await extrair_texto("#dataHoraDistribuicaoProcesso")
            controle = await extrair_texto("#numeroControleProcesso")
            area = await extrair_texto("#areaProcesso span")
            valor = await extrair_texto("#valorAcaoProcesso")

            processo_info = {campo: "" for campo in CAMPOS_PADRAO}
            processo_info.update({
                "instancia": "1ª Instância",
                "numero": numero.strip(),
                "link": detalhe_url,
                "classe": classe.strip(),
                "assunto": assunto.strip(),
                "foro": foro.strip(),
                "vara": vara.strip(),
                "juiz": juiz.strip(),
                "requerente": requerente,
                "requerido": requerido,
                "audiencia": audiencia.strip(),
                "julgamento": julgamento.strip(),
                "distribuicao": distribuicao.strip(),
                "controle": controle.strip(),
                "area": area.strip(),
                "valor_acao": valor.strip(),
                "movimentacoes": " | ".join(movimentacoes),
                "movimentacoes_detalhe": " | ".join(movimentacoes_detalhe)
            })

            salvar_incremental_excel([processo_info])
            await detalhe.close()
            
        except Exception as e:
            print(f"❌ Erro ao processar processo: {e}")
            try: 
                await detalhe.close()
            except: 
                pass

async def buscar_primeira_instancia(cnpj):
    cnpj_formatado = ''.join(filter(str.isdigit, cnpj))
    if len(cnpj_formatado) != 14:
        print("❌ CNPJ inválido")
        return

    cnpj_mascarado = f"{cnpj_formatado[:2]}.{cnpj_formatado[2:5]}.{cnpj_formatado[5:8]}/{cnpj_formatado[8:12]}-{cnpj_formatado[12:]}"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox'
            ]
        )
        
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        page = await context.new_page()
        
        print("\n====== PRIMEIRA INSTÂNCIA ======\n")
        sys.stdout.flush()  # Força mostrar o print imediatamente
        
        try:
            await page.goto("https://esaj.tjsp.jus.br/cpopg/open.do")
            print("🌐 Página carregada, aguardando estabilizar...")
            sys.stdout.flush()
            # Simula tempo de leitura da página
            await page.wait_for_timeout(randint(3000, 5000))
            
            # Aguarda o seletor aparecer
            print("🔍 Aguardando seletor de pesquisa...")
            sys.stdout.flush()
            if not await aguardar_sem_erro(page, "select#cbPesquisa", 15000):
                print("❌ Seletor não encontrado - possível problema no site")
                await browser.close()
                return
            
            # Simula usuário pensando antes de selecionar
            print("🤔 Analisando opções de consulta...")
            sys.stdout.flush()
            await page.wait_for_timeout(randint(2000, 4000))
            
            # Seleciona tipo de consulta
            print("📋 Selecionando 'Documento da Parte'...")
            sys.stdout.flush()
            await page.select_option("select#cbPesquisa", value="DOCPARTE")
            
            # Aguarda campo aparecer e simula tempo de leitura
            await page.wait_for_timeout(randint(1500, 3000))
            print("📝 Campo de documento carregado...")
            sys.stdout.flush()
            
            # Digita o CNPJ
            print(f"⌨️  Digitando CNPJ: {cnpj_mascarado}")
            sys.stdout.flush()
            await digitar_com_humanidade(page, "input#campo_DOCPARTE", cnpj_mascarado)
            
            # Simula usuário verificando se digitou certo
            print("🔍 Verificando dados digitados...")
            sys.stdout.flush()
            await page.wait_for_timeout(randint(2000, 4000))
            
            # NOVA ESTRATÉGIA: Aguarda o botão ficar clicável
            print("🎯 Aguardando botão de consulta...")
            sys.stdout.flush()
            
            # Aguarda o botão aparecer e ficar habilitado
            await page.wait_for_selector("#botaoConsultarProcessos", state="visible")
            await page.wait_for_timeout(randint(1000, 2000))
            
            # Verifica se o botão está habilitado
            is_disabled = await page.is_disabled("#botaoConsultarProcessos")
            if is_disabled:
                print("⚠️ Botão está desabilitado, aguardando...")
                await page.wait_for_timeout(randint(3000, 5000))
            
            # Simula usuário posicionando mouse sobre o botão
            print("🖱️  Posicionando para clicar...")
            await page.hover("#botaoConsultarProcessos")
            await page.wait_for_timeout(randint(800, 1500))
            
            print("🚀 Clicando no botão consultar...")
            
            # ESTRATÉGIA MELHORADA: Use Promise.race para lidar com timeouts
            try:
                # Clica e aguarda navegação OU timeout
                async with page.expect_navigation(timeout=60000):  # 60 segundos
                    await page.click("#botaoConsultarProcessos")
                    print("⏳ Aguardando resposta do servidor...")
                    
            except Exception as e:
                print(f"⚠️ Navegação demorou ou falhou: {e}")
                print("🔄 Tentando aguardar manualmente...")
                await page.wait_for_timeout(30000)
            
            # Verifica se chegou na página de resultados
            current_url = page.url
            print(f"📍 URL atual: {current_url}")
            
            if "search.do" not in current_url:
                print("❌ Não chegou na página de resultados")
                await browser.close()
                return
                
            print("✅ Página de resultados carregada!")
            
            # Agora processa as páginas normalmente
            pagina = 1
            while True:
                print(f"🔍 Extraindo dados da página {pagina} (1ª instância)...")
                await extrair_processos_da_pagina_primeira(page)
                
                # Verifica se há próxima página
                next_btn = await page.query_selector("a.unj-pagination__next")
                if next_btn:
                    await next_btn.scroll_into_view_if_needed()
                    await page.wait_for_timeout(randint(2000, 3000))
                    await next_btn.click()
                    await page.wait_for_timeout(randint(3000, 5000))
                    pagina += 1
                else:
                    break
                    
        except Exception as e:
            print(f"❌ Erro geral: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python tjsp_primeira_instancia.py <CNPJ>")
        sys.exit(1)
    cnpj_input = sys.argv[1]
    asyncio.run(buscar_primeira_instancia(cnpj_input))