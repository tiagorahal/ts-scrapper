"""
Implementações específicas dos scrapers para cada instância do TJSP
Utilizando a classe base para eliminar duplicação
"""

import asyncio
from typing import Dict, List, Optional
from pathlib import Path
from playwright.async_api import Page
from base_scraper import TJSPBaseScraper
import re
from datetime import datetime

class ScraperPrimeiraInstancia(TJSPBaseScraper):
    """Scraper especializado para 1ª Instância do TJSP"""
    
    def __init__(self):
        super().__init__(
            instancia_nome="primeira_instancia",
            url_base="https://esaj.tjsp.jus.br/cpopg/open.do",
            arquivo_saida="primeira_instancia_tjsp.xlsx"
        )
    
    async def configurar_busca(self, page: Page, cnpj: str) -> bool:
        """Configura busca específica para 1ª instância"""
        try:
            self.logger.info("🔍 Configurando busca na 1ª Instância...")
            
            # Aguardar página carregar completamente
            await asyncio.sleep(3)
            
            # Aguardar e selecionar tipo de pesquisa
            if not await self.aguardar_elemento(page, "select#cbPesquisa"):
                self.logger.error("❌ Seletor de pesquisa não encontrado")
                return False
            
            await page.select_option("select#cbPesquisa", value="DOCPARTE")
            await asyncio.sleep(2)
            
            # Digitar CNPJ
            await self.digitar_humanizado(page, "input#campo_DOCPARTE", cnpj)
            
            # Clicar em consultar
            if not await self.aguardar_elemento(page, "#botaoConsultarProcessos"):
                self.logger.error("❌ Botão consultar não encontrado")
                return False
            
            # Verificar se botão está habilitado
            is_disabled = await page.is_disabled("#botaoConsultarProcessos")
            if is_disabled:
                self.logger.info("⏳ Aguardando botão ficar habilitado...")
                await asyncio.sleep(3)
            
            # Clicar e aguardar navegação
            try:
                async with page.expect_navigation(timeout=60000):
                    await page.click("#botaoConsultarProcessos")
                    self.logger.info("⏳ Aguardando resultados...")
            except:
                # Fallback se navegação falhar
                await page.click("#botaoConsultarProcessos")
                await asyncio.sleep(10)
            
            # Verificar se chegou na página de resultados
            current_url = page.url
            if "search.do" not in current_url:
                self.logger.error("❌ Não chegou na página de resultados")
                return False
            
            self.logger.info("✅ Busca configurada com sucesso")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao configurar busca: {e}")
            return False
    
    async def extrair_processos_pagina(self, page: Page) -> List[Dict]:
        """Extrai processos da página atual"""
        processos = []
        
        try:
            # Aguardar lista carregar
            await self.aguardar_elemento(page, "ul.unj-list-row", timeout=10000)
            
            # Buscar todos os processos da página
            rows = await page.query_selector_all("ul.unj-list-row > li .home__lista-de-processos")
            
            self.logger.info(f"📋 {len(rows)} processos encontrados na página")
            
            for i, row in enumerate(rows):
                try:
                    # Verificar cache antes de processar
                    numero_el = await row.query_selector(".nuProcesso a")
                    if not numero_el:
                        continue
                    
                    numero_preview = await numero_el.inner_text()
                    
                    if self.is_processo_cached(numero_preview.strip()):
                        self.logger.info(f"⏭️ Processo {numero_preview} já em cache")
                        continue
                    
                    # Extrair link e abrir detalhes
                    link = await numero_el.get_attribute("href")
                    if not link:
                        continue
                    
                    detalhe_url = f"https://esaj.tjsp.jus.br{link}"
                    
                    # Abrir página de detalhes em nova aba
                    detalhe_page = await page.context.new_page()
                    
                    try:
                        await detalhe_page.goto(detalhe_url, wait_until='networkidle')
                        await detalhe_page.wait_for_load_state("networkidle")
                        
                        # Expandir detalhes se houver
                        mais_btn = await detalhe_page.query_selector("a.unj-link-collapse")
                        if mais_btn:
                            await mais_btn.click()
                            await asyncio.sleep(1)
                        
                        # Extrair dados do processo
                        processo_info = await self.extrair_dados_processo_primeira(detalhe_page, detalhe_url)
                        
                        if processo_info:
                            processos.append(processo_info)
                            self.logger.info(f"✅ Processo {i+1}/{len(rows)}: {processo_info['numero']}")
                        
                    finally:
                        await detalhe_page.close()
                    
                    # Delay entre processos
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    self.logger.error(f"❌ Erro ao processar linha {i}: {e}")
                    self.stats["processos_erro"] += 1
                    continue
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao extrair processos da página: {e}")
        
        return processos
    
    async def extrair_dados_processo_primeira(self, page: Page, url: str) -> Optional[Dict]:
        """Extrai dados detalhados de um processo da 1ª instância"""
        try:
            # Helper para extrair texto seguro
            async def get_text(selector: str) -> str:
                try:
                    el = await page.query_selector(selector)
                    return (await el.inner_text()).strip() if el else ""
                except:
                    return ""
            
            # Dados básicos
            dados = {campo: "" for campo in self.CAMPOS_PADRAO}
            dados.update({
                "instancia": "1ª Instância",
                "link": url,
                "numero": await get_text("#numeroProcesso"),
                "classe": await get_text("#classeProcesso"),
                "assunto": await get_text("#assuntoProcesso"),
                "foro": await get_text("#foroProcesso"),
                "vara": await get_text("#varaProcesso"),
                "juiz": await get_text("#juizProcesso"),
                "distribuicao": await get_text("#dataHoraDistribuicaoProcesso"),
                "controle": await get_text("#numeroControleProcesso"),
                "area": await get_text("#areaProcesso span"),
                "valor_acao": await get_text("#valorAcaoProcesso"),
                "audiencia": await get_text("#processoSemAudiencias"),
                "julgamento": await get_text("#processoSemJulgamentos")
            })
            
            # Extrair partes
            partes = await self.extrair_partes_processo(page)
            dados.update(partes)
            
            # Extrair movimentações
            movimentacoes = await self.extrair_movimentacoes_processo(page)
            dados.update(movimentacoes)
            
            # Adicionar metadados
            dados["hash_processo"] = self.get_processo_hash(dados["numero"])
            dados["data_extracao"] = datetime.now().isoformat()
            dados["status_extracao"] = "sucesso"
            dados["tentativas"] = 1
            
            return dados
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao extrair dados do processo: {e}")
            return None
    
    async def extrair_partes_processo(self, page: Page) -> Dict:
        """Extrai informações das partes do processo"""
        partes = {
            "requerente": "",
            "requerido": "",
            "polo_terceiro": ""
        }
        
        try:
            partes_rows = await page.query_selector_all("#tablePartesPrincipais tr")
            
            for row in partes_rows:
                tipo_el = await row.query_selector(".tipoDeParticipacao")
                nome_el = await row.query_selector(".nomeParteEAdvogado")
                
                if tipo_el and nome_el:
                    tipo = (await tipo_el.inner_text()).strip()
                    nome = (await nome_el.inner_text()).strip()
                    
                    # Classificar tipo de parte
                    if any(t in tipo.lower() for t in ["reqte", "autor", "exequente", "impetrante"]):
                        partes["requerente"] = nome
                    elif any(t in tipo.lower() for t in ["reqdo", "réu", "executado", "impetrado"]):
                        partes["requerido"] = nome
                    elif any(t in tipo.lower() for t in ["terceiro", "interessado", "assistente"]):
                        partes["polo_terceiro"] = nome
        except:
            pass
        
        return partes
    
    async def extrair_movimentacoes_processo(self, page: Page) -> Dict:
        """Extrai movimentações do processo"""
        movimentacoes_data = {
            "movimentacoes": "",
            "movimentacoes_detalhe": ""
        }
        
        try:
            movs = []
            movs_detalhe = []
            
            mov_rows = await page.query_selector_all("#tabelaUltimasMovimentacoes tr")
            
            for row in mov_rows:
                data_el = await row.query_selector("td.data")
                desc_el = await row.query_selector("td.movimentacao")
                
                if data_el and desc_el:
                    data = (await data_el.inner_text()).strip()
                    desc = (await desc_el.inner_text()).strip()
                    
                    # Movimentação básica
                    movs.append(f"{data} - {desc}")
                    
                    # Tentar pegar detalhes
                    detalhe_el = await row.query_selector("td.movimentacao span span")
                    if detalhe_el:
                        detalhe = (await detalhe_el.inner_text()).strip()
                        movs_detalhe.append(f"{data} - {desc} => {detalhe}")
                    else:
                        movs_detalhe.append(f"{data} - {desc}")
            
            movimentacoes_data["movimentacoes"] = " | ".join(movs[:10])  # Limitar a 10 últimas
            movimentacoes_data["movimentacoes_detalhe"] = " | ".join(movs_detalhe[:10])
            
        except:
            pass
        
        return movimentacoes_data


class ScraperSegundaInstancia(TJSPBaseScraper):
    """Scraper especializado para 2ª Instância do TJSP"""
    
    def __init__(self):
        super().__init__(
            instancia_nome="segunda_instancia",
            url_base="https://esaj.tjsp.jus.br/cposg/open.do",
            arquivo_saida="segunda_instancia_tjsp.xlsx"
        )
    
    async def configurar_busca(self, page: Page, cnpj: str) -> bool:
        """Configura busca específica para 2ª instância"""
        try:
            self.logger.info("🔍 Configurando busca na 2ª Instância...")
            
            await asyncio.sleep(3)
            
            if not await self.aguardar_elemento(page, "select#cbPesquisa"):
                return False
            
            await page.select_option("select#cbPesquisa", value="DOCPARTE")
            await asyncio.sleep(2)
            
            await self.digitar_humanizado(page, "input#campo_DOCPARTE", cnpj)
            
            if not await self.aguardar_elemento(page, "#pbConsultar"):
                return False
            
            # Verificar estado do botão
            is_disabled = await page.is_disabled("#pbConsultar")
            if is_disabled:
                await asyncio.sleep(3)
            
            try:
                async with page.expect_navigation(timeout=60000):
                    await page.click("#pbConsultar")
            except:
                await page.click("#pbConsultar")
                await asyncio.sleep(10)
            
            return "search.do" in page.url
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao configurar busca: {e}")
            return False
    
    async def extrair_processos_pagina(self, page: Page) -> List[Dict]:
        """Extrai processos da página atual da 2ª instância"""
        processos = []
        
        try:
            await self.aguardar_elemento(page, "ul.unj-list-row", timeout=10000)
            rows = await page.query_selector_all("ul.unj-list-row > li")
            
            self.logger.info(f"📋 {len(rows)} processos encontrados")
            
            for i, row in enumerate(rows):
                try:
                    numero_el = await row.query_selector("div.nuProcesso a.linkProcesso")
                    if not numero_el:
                        continue
                    
                    numero = (await numero_el.inner_text()).strip()
                    
                    if self.is_processo_cached(numero):
                        continue
                    
                    link = await numero_el.get_attribute("href")
                    detalhe_url = f"https://esaj.tjsp.jus.br{link}" if link else ""
                    
                    detalhe_page = await page.context.new_page()
                    
                    try:
                        await detalhe_page.goto(detalhe_url, wait_until='networkidle')
                        
                        processo_info = await self.extrair_dados_processo_segunda(
                            detalhe_page, detalhe_url, numero
                        )
                        
                        if processo_info:
                            processos.append(processo_info)
                            self.logger.info(f"✅ Processo {i+1}/{len(rows)}: {processo_info['numero']}")
                        
                    finally:
                        await detalhe_page.close()
                    
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    self.logger.error(f"❌ Erro ao processar processo {i}: {e}")
                    self.stats["processos_erro"] += 1
            
        except Exception as e:
            self.logger.error(f"❌ Erro na extração: {e}")
        
        return processos
    
    async def extrair_dados_processo_segunda(self, page: Page, url: str, numero_fallback: str) -> Optional[Dict]:
        """Extrai dados de processo da 2ª instância"""
        try:
            async def get_text(selector: str) -> str:
                try:
                    el = await page.query_selector(selector)
                    return (await el.inner_text()).strip() if el else ""
                except:
                    return ""
            
            dados = {campo: "" for campo in self.CAMPOS_PADRAO}
            
            # Dados específicos da 2ª instância
            numero = await get_text("#numeroProcesso")
            dados.update({
                "instancia": "2ª Instância",
                "link": url,
                "numero": numero or numero_fallback,
                "classe": await get_text("#classeProcesso span"),
                "assunto": await get_text("#assuntoProcesso span"),
                "relator": await get_text("#relatorProcesso span"),
                "area": await get_text("#areaProcesso span"),
                "valor_acao": await get_text("#valorAcaoProcesso span"),
                "volume_apenso": await get_text("#volumeApensoProcesso span"),
                "julgamento": await get_text("#processoSemJulgamentos")
            })
            
            # Origem
            try:
                origem_el = await page.query_selector("div.line-clamp__2 span[title]")
                if origem_el:
                    dados["origem"] = await origem_el.get_attribute("title")
            except:
                pass
            
            # Números de 1ª instância
            numeros_1inst = []
            try:
                rows_1inst = await page.query_selector_all("table[align='center'] tr.fundoClaro")
                for row in rows_1inst:
                    cols = await row.query_selector_all("td")
                    if cols:
                        num = (await cols[0].inner_text()).strip()
                        numeros_1inst.append(num)
                dados["outros_numeros"] = " | ".join(numeros_1inst)
            except:
                pass
            
            # Partes (específico para 2ª instância)
            partes = await self.extrair_partes_segunda_instancia(page)
            dados.update(partes)
            
            # Movimentações
            movs = await self.extrair_movimentacoes_segunda_instancia(page)
            dados.update(movs)
            
            # Metadados
            dados["hash_processo"] = self.get_processo_hash(dados["numero"])
            dados["data_extracao"] = datetime.now().isoformat()
            dados["status_extracao"] = "sucesso"
            
            return dados
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao extrair dados: {e}")
            return None
    
    async def extrair_partes_segunda_instancia(self, page: Page) -> Dict:
        """Extrai partes específicas da 2ª instância"""
        partes = {
            "requerente": "",
            "requerido": "",
            "polo_terceiro": ""
        }
        
        try:
            partes_trs = await page.query_selector_all("#tablePartesPrincipais tr")
            
            for tr in partes_trs:
                tipo_el = await tr.query_selector(".tipoDeParticipacao")
                nome_el = await tr.query_selector(".nomeParteEAdvogado")
                
                if tipo_el and nome_el:
                    tipo = (await tipo_el.inner_text()).strip()
                    nome = (await nome_el.inner_text()).strip()
                    
                    # Tipos específicos de 2ª instância
                    if any(t in tipo.lower() for t in ["apelante", "agravante", "recorrente"]):
                        partes["requerente"] = nome
                    elif any(t in tipo.lower() for t in ["apelado", "agravado", "recorrido"]):
                        partes["requerido"] = nome
                    elif "interessado" in tipo.lower():
                        partes["polo_terceiro"] = nome
        except:
            pass
        
        return partes
    
    async def extrair_movimentacoes_segunda_instancia(self, page: Page) -> Dict:
        """Extrai movimentações da 2ª instância"""
        movs_data = {
            "movimentacoes": "",
            "movimentacoes_detalhe": ""
        }
        
        try:
            movs = []
            movs_detalhe = []
            
            mov_rows = await page.query_selector_all("#tabelaUltimasMovimentacoes tr")
            
            for row in mov_rows:
                tds = await row.query_selector_all("td")
                if len(tds) >= 3:
                    data = (await tds[0].inner_text()).strip()
                    desc = (await tds[2].inner_text()).strip()
                    
                    movs.append(f"{data} - {desc}")
                    
                    # Detalhes
                    detalhe_span = await tds[2].query_selector("span")
                    if detalhe_span:
                        detalhe = (await detalhe_span.inner_text()).strip()
                        movs_detalhe.append(f"{data} - {desc} => {detalhe}")
                    else:
                        movs_detalhe.append(f"{data} - {desc}")
            
            movs_data["movimentacoes"] = " | ".join(movs[:10])
            movs_data["movimentacoes_detalhe"] = " | ".join(movs_detalhe[:10])
            
        except:
            pass
        
        return movs_data


class ScraperColegioRecursal(TJSPBaseScraper):
    """Scraper especializado para Colégio Recursal do TJSP"""
    
    def __init__(self):
        super().__init__(
            instancia_nome="colegio_recursal",
            url_base="https://esaj.tjsp.jus.br/cposgcr/open.do",
            arquivo_saida="colegio_recursal_tjsp.xlsx"
        )
    
    async def configurar_busca(self, page: Page, cnpj: str) -> bool:
        """Configura busca no Colégio Recursal"""
        # Implementação similar à 2ª instância
        return await ScraperSegundaInstancia().configurar_busca(page, cnpj)
    
    async def extrair_processos_pagina(self, page: Page) -> List[Dict]:
        """Extrai processos do Colégio Recursal"""
        # Pode reutilizar lógica da 2ª instância com ajustes
        processos = []
        
        try:
            await self.aguardar_elemento(page, "ul.unj-list-row", timeout=10000)
            rows = await page.query_selector_all("ul.unj-list-row > li")
            
            for i, row in enumerate(rows):
                try:
                    numero_el = await row.query_selector("div.nuProcesso a.linkProcesso")
                    if not numero_el:
                        continue
                    
                    numero = (await numero_el.inner_text()).strip()
                    
                    if self.is_processo_cached(numero):
                        continue
                    
                    link = await numero_el.get_attribute("href")
                    detalhe_url = f"https://esaj.tjsp.jus.br{link}" if link else ""
                    
                    detalhe_page = await page.context.new_page()
                    
                    try:
                        await detalhe_page.goto(detalhe_url, wait_until='networkidle')
                        
                        # Usar extração similar à 2ª instância
                        processo_info = await self.extrair_dados_processo_segunda(
                            detalhe_page, detalhe_url, numero
                        )
                        
                        # Ajustar instância
                        if processo_info:
                            processo_info["instancia"] = "Colégio Recursal"
                            processos.append(processo_info)
                            self.logger.info(f"✅ Processo {i+1}/{len(rows)}: {processo_info['numero']}")
                        
                    finally:
                        await detalhe_page.close()
                    
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    self.logger.error(f"❌ Erro: {e}")
                    self.stats["processos_erro"] += 1
            
        except Exception as e:
            self.logger.error(f"❌ Erro na extração: {e}")
        
        return processos
    
    async def extrair_dados_processo_segunda(self, page: Page, url: str, numero_fallback: str) -> Optional[Dict]:
        """Reutiliza extração da 2ª instância"""
        # Delegar para implementação da 2ª instância
        scraper_segunda = ScraperSegundaInstancia()
        return await scraper_segunda.extrair_dados_processo_segunda(page, url, numero_fallback)