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
DADOS_DIR.mkdir(exist_ok=True)  # Cria a pasta dados se não existir
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
    await page.fill(selector, "")
    for caractere in texto:
        await page.type(selector, caractere)
        await page.wait_for_timeout(randint(100, 250))

async def extrair_processos_da_pagina_primeira(page):
    rows = await page.query_selector_all("ul.unj-list-row > li .home__lista-de-processos")
    for row in rows:
        try:
            numero_el = await row.query_selector(".nuProcesso a")
            link = await numero_el.get_attribute("href") if numero_el else ""
            detalhe_url = f"https://esaj.tjsp.jus.br{link}" if link else ""
            detalhe = await page.context.new_page()
            await detalhe.goto(detalhe_url)
            await detalhe.wait_for_load_state("networkidle")
            mais_btn = await detalhe.query_selector("a.unj-link-collapse")
            if mais_btn:
                await mais_btn.click()
                await detalhe.wait_for_timeout(1000)
            numero = await (await detalhe.query_selector("#numeroProcesso")).inner_text()
            classe = await (await detalhe.query_selector("#classeProcesso")).inner_text()
            assunto = await (await detalhe.query_selector("#assuntoProcesso")).inner_text()
            foro = await (await detalhe.query_selector("#foroProcesso")).inner_text()
            vara = await (await detalhe.query_selector("#varaProcesso")).inner_text()
            juiz_el = await detalhe.query_selector("#juizProcesso")
            juiz = await juiz_el.inner_text() if juiz_el else ""
            partes_raw = await detalhe.query_selector_all("#tablePartesPrincipais tr")
            requerente = ""
            requerido = ""
            for parte in partes_raw:
                tipo_el = await parte.query_selector(".tipoDeParticipacao")
                nome_el = await parte.query_selector(".nomeParteEAdvogado")
                tipo = await tipo_el.inner_text() if tipo_el else ""
                nome = await nome_el.inner_text() if nome_el else ""
                if "Reqte" in tipo or "Apelante" in tipo:
                    requerente = nome.strip()
                elif "Reqdo" in tipo or "Apelado" in tipo:
                    requerido = nome.strip()
            audiencias_el = await detalhe.query_selector("#processoSemAudiencias")
            audiencia = await audiencias_el.inner_text() if audiencias_el else ""
            julgamentos_el = await detalhe.query_selector("#processoSemJulgamentos")
            julgamento = await julgamentos_el.inner_text() if julgamentos_el else ""
            movimentacoes = []
            movimentacoes_detalhe = []
            mov_rows = await detalhe.query_selector_all("#tabelaUltimasMovimentacoes tr")
            for mov in mov_rows:
                data_el = await mov.query_selector("td.data")
                desc_el = await mov.query_selector("td.movimentacao")
                detalhe_el = await mov.query_selector("td.movimentacao span span")
                if data_el and desc_el:
                    data = (await data_el.inner_text()).strip()
                    desc = (await desc_el.inner_text()).strip()
                    movimentacoes.append(f"{data} - {desc}")
                    if detalhe_el:
                        detalhe_txt = (await detalhe_el.inner_text()).strip()
                        movimentacoes_detalhe.append(f"{data} - {desc} => {detalhe_txt}")
                    else:
                        movimentacoes_detalhe.append(f"{data} - {desc}")
            try:
                dist = await (await detalhe.query_selector("#dataHoraDistribuicaoProcesso")).inner_text()
            except: dist = ""
            try:
                controle = await (await detalhe.query_selector("#numeroControleProcesso")).inner_text()
            except: controle = ""
            try:
                area = await (await detalhe.query_selector("#areaProcesso span")).inner_text()
            except: area = ""
            try:
                valor = await (await detalhe.query_selector("#valorAcaoProcesso")).inner_text()
            except: valor = ""
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
                "distribuicao": dist.strip(),
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
            try: await detalhe.close()
            except: pass
            continue

async def buscar_primeira_instancia(cnpj):
    cnpj_formatado = ''.join(filter(str.isdigit, cnpj))
    if len(cnpj_formatado) != 14:
        print("❌ CNPJ inválido")
        return
    cnpj_mascarado = f"{cnpj_formatado[:2]}.{cnpj_formatado[2:5]}.{cnpj_formatado[5:8]}/{cnpj_formatado[8:12]}-{cnpj_formatado[12:]}"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()
        print("\n====== PRIMEIRA INSTÂNCIA ======\n")
        await page.goto("https://esaj.tjsp.jus.br/cpopg/open.do")
        await page.wait_for_timeout(randint(1500, 2500))
        await page.wait_for_selector("select#cbPesquisa")
        await page.select_option("select#cbPesquisa", value="DOCPARTE")
        await page.wait_for_timeout(randint(1000, 2000))
        await digitar_com_humanidade(page, "input#campo_DOCPARTE", cnpj_mascarado)
        await page.wait_for_timeout(randint(800, 1200))
        await page.click("#botaoConsultarProcessos")
        print("⏳ Aguarde 30 segundos (1ª instância)...")
        await page.wait_for_timeout(30000)
        pagina = 1
        while True:
            print(f"🔍 Extraindo dados da página {pagina} (1ª instância)...")
            await extrair_processos_da_pagina_primeira(page)
            next_btn = await page.query_selector("a.unj-pagination__next")
            if next_btn:
                await next_btn.scroll_into_view_if_needed()
                await page.wait_for_timeout(randint(1500, 2500))
                await next_btn.click()
                await page.wait_for_timeout(randint(3000, 4000))
                pagina += 1
            else:
                break
        await browser.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python tjsp_primeira_instancia.py <CNPJ>")
        sys.exit(1)
    cnpj_input = sys.argv[1]
    asyncio.run(buscar_primeira_instancia(cnpj_input))