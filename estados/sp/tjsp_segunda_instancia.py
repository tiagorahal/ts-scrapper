import asyncio
import pandas as pd
from pathlib import Path
from random import randint
from playwright.async_api import async_playwright
import os
import sys

SCRIPT_DIR = Path(__file__).parent
DADOS_DIR = SCRIPT_DIR / "dados"
DADOS_DIR.mkdir(exist_ok=True)
EXCEL_PATH = DADOS_DIR / "segunda_instancia_tjsp.xlsx"

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
    await page.wait_for_timeout(randint(300, 800))
    await page.fill(selector, "")
    await page.wait_for_timeout(randint(200, 500))
    
    for i, caractere in enumerate(texto):
        await page.type(selector, caractere)
        if i % 3 == 0:
            await page.wait_for_timeout(randint(150, 400))
        else:
            await page.wait_for_timeout(randint(80, 200))
    
    await page.wait_for_timeout(randint(500, 1200))

async def aguardar_sem_erro(page, selector, timeout=10000):
    try:
        await page.wait_for_selector(selector, timeout=timeout)
        return True
    except:
        return False

async def extrair_processos_da_pagina_segunda(page):
    rows = await page.query_selector_all("ul.unj-list-row > li")
    for row in rows:
        try:
            numero_el = await row.query_selector("div.nuProcesso a.linkProcesso")
            if not numero_el:
                continue
                
            numero = (await numero_el.inner_text()).strip()
            link = await numero_el.get_attribute("href")
            detalhe_url = f"https://esaj.tjsp.jus.br{link}" if link else ""
            
            detalhe = await page.context.new_page()
            await detalhe.goto(detalhe_url)
            await detalhe.wait_for_load_state("networkidle")

            async def txt(sel):
                try:
                    el = await detalhe.query_selector(sel)
                    return (await el.inner_text()).strip() if el else ""
                except:
                    return ""

            numero_proc = await txt("#numeroProcesso")
            classe = await txt("#classeProcesso span")
            assunto = await txt("#assuntoProcesso span")
            relator = await txt("#relatorProcesso span")
            valor_acao = await txt("#valorAcaoProcesso span")
            volume_apenso = await txt("#volumeApensoProcesso span")
            area = await txt("#areaProcesso span")
            
            # Origem
            origem = ""
            try:
                origem_el = await detalhe.query_selector("div.line-clamp__2 span[title]")
                origem = await origem_el.get_attribute("title") if origem_el else ""
            except:
                pass
            
            # Números de 1ª instância
            numeros_1inst = []
            try:
                rows_1inst = await detalhe.query_selector_all("table[align='center'] tr.fundoClaro")
                for r1 in rows_1inst:
                    cols = await r1.query_selector_all("td")
                    if cols and len(cols) >= 1:
                        ninst = (await cols[0].inner_text()).strip()
                        numeros_1inst.append(ninst)
            except:
                pass

            # Partes do processo
            requerente, requerido, polo_terceiro = "", "", ""
            try:
                partes_trs = await detalhe.query_selector_all("#tablePartesPrincipais tr")
                for tr in partes_trs:
                    tipo_el = await tr.query_selector(".tipoDeParticipacao")
                    nome_el = await tr.query_selector(".nomeParteEAdvogado")
                    if tipo_el and nome_el:
                        tipo = (await tipo_el.inner_text()).strip()
                        nome = (await nome_el.inner_text()).strip()
                        if "Apelante" in tipo:
                            requerente = nome
                        elif "Apelado" in tipo:
                            requerido = nome
                        elif "Interessado" in tipo:
                            polo_terceiro = nome
            except:
                pass

            julgamento = await txt("#processoSemJulgamentos")

            # Movimentações
            movimentacoes = []
            movimentacoes_detalhe = []
            try:
                mov_rows = await detalhe.query_selector_all("#tabelaUltimasMovimentacoes tr")
                for mov in mov_rows:
                    tds = await mov.query_selector_all("td")
                    if len(tds) >= 3:
                        data = (await tds[0].inner_text()).strip()
                        desc = (await tds[2].inner_text()).strip()
                        movimentacoes.append(f"{data} - {desc}")
                        
                        detalhe_span = await tds[2].query_selector("span")
                        detalhe_txt = (await detalhe_span.inner_text()).strip() if detalhe_span else ""
                        movimentacoes_detalhe.append(f"{data} - {desc} => {detalhe_txt}" if detalhe_txt else f"{data} - {desc}")
            except:
                pass

            processo_info = {campo: "" for campo in CAMPOS_PADRAO}
            processo_info.update({
                "instancia": "2ª Instância",
                "numero": numero_proc or numero,
                "link": detalhe_url,
                "classe": classe,
                "assunto": assunto,
                "relator": relator,
                "outros_numeros": " | ".join(numeros_1inst),
                "origem": origem,
                "volume_apenso": volume_apenso,
                "requerente": requerente,
                "requerido": requerido,
                "polo_terceiro": polo_terceiro,
                "julgamento": julgamento,
                "area": area,
                "valor_acao": valor_acao,
                "movimentacoes": " | ".join(movimentacoes),
                "movimentacoes_detalhe": " | ".join(movimentacoes_detalhe)
            })

            salvar_incremental_excel([processo_info])
            await detalhe.close()
            
        except Exception as e:
            print(f"❌ Erro ao processar processo 2ª instância: {e}")
            try: 
                await detalhe.close()
            except: 
                pass

async def buscar_segunda_instancia(cnpj):
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
        
        print("\n====== SEGUNDA INSTÂNCIA ======\n")
        sys.stdout.flush()
        
        try:
            await page.goto("https://esaj.tjsp.jus.br/cposg/open.do")
            print("🌐 Página carregada, aguardando estabilizar...")
            sys.stdout.flush()
            await page.wait_for_timeout(randint(3000, 5000))
            
            print("🔍 Aguardando seletor de pesquisa...")
            sys.stdout.flush()
            if not await aguardar_sem_erro(page, "select#cbPesquisa", 15000):
                print("❌ Seletor não encontrado")
                await browser.close()
                return
            
            print("🤔 Analisando opções de consulta...")
            sys.stdout.flush()
            await page.wait_for_timeout(randint(2000, 4000))
            
            print("📋 Selecionando 'Documento da Parte'...")
            sys.stdout.flush()
            await page.select_option("select#cbPesquisa", value="DOCPARTE")
            await page.wait_for_timeout(randint(1500, 3000))
            
            print(f"⌨️  Digitando CNPJ: {cnpj_mascarado}")
            sys.stdout.flush()
            await digitar_com_humanidade(page, "input#campo_DOCPARTE", cnpj_mascarado)
            
            print("🔍 Verificando dados digitados...")
            sys.stdout.flush()
            await page.wait_for_timeout(randint(2000, 4000))
            
            print("🎯 Aguardando botão de consulta...")
            sys.stdout.flush()
            await page.wait_for_selector("#pbConsultar", state="visible")
            await page.wait_for_timeout(randint(1000, 2000))
            
            is_disabled = await page.is_disabled("#pbConsultar")
            if is_disabled:
                print("⚠️ Botão desabilitado, aguardando...")
                sys.stdout.flush()
                await page.wait_for_timeout(randint(3000, 5000))
            
            print("🖱️  Posicionando para clicar...")
            sys.stdout.flush()
            await page.hover("#pbConsultar")
            await page.wait_for_timeout(randint(800, 1500))
            
            print("🚀 Clicando no botão consultar...")
            sys.stdout.flush()
            
            try:
                async with page.expect_navigation(timeout=60000):
                    await page.click("#pbConsultar")
                    print("⏳ Aguardando resposta do servidor...")
                    sys.stdout.flush()
            except Exception as e:
                print(f"⚠️ Navegação demorou: {e}")
                sys.stdout.flush()
                await page.wait_for_timeout(30000)
            
            current_url = page.url
            print(f"📍 URL atual: {current_url}")
            
            if "search.do" not in current_url:
                print("❌ Não chegou na página de resultados")
                await browser.close()
                return
                
            print("✅ Página de resultados carregada!")
            
            pagina = 1
            while True:
                print(f"🔍 Extraindo dados da página {pagina} (2ª instância)...")
                await extrair_processos_da_pagina_segunda(page)
                
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
        print("Uso: python tjsp_segunda_instancia.py <CNPJ>")
        sys.exit(1)
    cnpj_input = sys.argv[1]
    asyncio.run(buscar_segunda_instancia(cnpj_input))