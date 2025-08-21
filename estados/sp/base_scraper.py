"""
Base class para todos os scrapers do TJSP
Centraliza funcionalidades comuns e elimina duplicação
"""

import asyncio
import logging
import pandas as pd
from pathlib import Path
from random import randint, uniform, choice
from datetime import datetime
from typing import Dict, List, Optional, Any
from playwright.async_api import async_playwright, Page, Browser
import os
import json
import hashlib
from abc import ABC, abstractmethod

class TJSPBaseScraper(ABC):
    """Classe base para scrapers do TJSP com funcionalidades aprimoradas"""
    
    # User agents realistas e atualizados
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    ]
    
    CAMPOS_PADRAO = [
        "instancia", "numero", "link", "classe", "assunto", "relator", 
        "outros_numeros", "origem", "volume_apenso", "ultima_carga", 
        "foro", "vara", "juiz", "requerente", "requerido", "polo_terceiro",
        "audiencia", "julgamento", "distribuicao", "controle", "area", 
        "valor_acao", "movimentacoes", "movimentacoes_detalhe",
        "data_extracao", "hash_processo", "tentativas", "status_extracao"
    ]
    
    def __init__(self, instancia_nome: str, url_base: str, arquivo_saida: str):
        self.instancia_nome = instancia_nome
        self.url_base = url_base
        self.script_dir = Path(__file__).parent
        self.dados_dir = self.script_dir / "dados"
        self.cache_dir = self.script_dir / "cache"
        self.logs_dir = self.script_dir / "logs"
        
        # Criar diretórios necessários
        for dir_path in [self.dados_dir, self.cache_dir, self.logs_dir]:
            dir_path.mkdir(exist_ok=True)
        
        self.excel_path = self.dados_dir / arquivo_saida
        self.cache_file = self.cache_dir / f"cache_{arquivo_saida.replace('.xlsx', '.json')}"
        
        # Configurar logging aprimorado
        self.setup_logging()
        
        # Carregar cache
        self.cache = self.load_cache()
        
        # Estatísticas
        self.stats = {
            "processos_extraidos": 0,
            "processos_erro": 0,
            "paginas_processadas": 0,
            "tempo_inicio": datetime.now(),
            "tentativas_retry": 0
        }
        
    def setup_logging(self):
        """Configura sistema de logging robusto"""
        log_filename = self.logs_dir / f"{self.instancia_nome}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_filename),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(self.instancia_nome)
        
    def load_cache(self) -> Dict:
        """Carrega cache de processos já extraídos"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_cache(self):
        """Salva cache de processos"""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            self.logger.error(f"Erro ao salvar cache: {e}")
    
    def get_processo_hash(self, numero: str) -> str:
        """Gera hash único para o processo"""
        return hashlib.md5(f"{self.instancia_nome}_{numero}".encode()).hexdigest()
    
    def is_processo_cached(self, numero: str) -> bool:
        """Verifica se processo já foi extraído"""
        hash_processo = self.get_processo_hash(numero)
        return hash_processo in self.cache
    
    def add_to_cache(self, numero: str, data: Dict):
        """Adiciona processo ao cache"""
        hash_processo = self.get_processo_hash(numero)
        self.cache[hash_processo] = {
            "numero": numero,
            "data_extracao": datetime.now().isoformat(),
            "data": data
        }
        self.save_cache()
    
    async def create_browser_context(self, playwright):
        """Cria contexto do browser com configurações anti-detecção aprimoradas"""
        browser = await playwright.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-notifications',
                '--disable-geolocation',
                '--disable-infobars',
                '--window-size=1920,1080',
                '--start-maximized'
            ]
        )
        
        # Configurações do contexto
        viewport_width = randint(1366, 1920)
        viewport_height = randint(768, 1080)
        
        context = await browser.new_context(
            viewport={"width": viewport_width, "height": viewport_height},
            user_agent=choice(self.USER_AGENTS),
            locale='pt-BR',
            timezone_id='America/Sao_Paulo',
            permissions=['geolocation'],
            ignore_https_errors=True,
            java_script_enabled=True,
            bypass_csp=True,
            extra_http_headers={
                'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
        )
        
        return browser, context
    
    async def digitar_humanizado(self, page: Page, selector: str, texto: str):
        """Digitação com comportamento mais humano e variado"""
        try:
            # Movimento aleatório do mouse antes de clicar
            await self.movimento_aleatorio_mouse(page)
            
            # Clica no campo
            await page.click(selector)
            await asyncio.sleep(uniform(0.3, 0.8))
            
            # Limpa o campo
            await page.fill(selector, "")
            await asyncio.sleep(uniform(0.2, 0.5))
            
            # Digita caractere por caractere com variações
            for i, char in enumerate(texto):
                await page.type(selector, char)
                
                # Variação no tempo de digitação
                if i % randint(2, 5) == 0:  # Pausa maior ocasional
                    await asyncio.sleep(uniform(0.2, 0.5))
                elif char in '.,;:!?':  # Pausa após pontuação
                    await asyncio.sleep(uniform(0.3, 0.6))
                else:
                    await asyncio.sleep(uniform(0.05, 0.15))
                
                # Simula erro de digitação ocasional (1% de chance)
                if randint(1, 100) == 1 and i > 0 and i < len(texto) - 1:
                    wrong_char = chr(ord(char) + randint(-1, 1))
                    await page.type(selector, wrong_char)
                    await asyncio.sleep(uniform(0.3, 0.5))
                    await page.keyboard.press("Backspace")
                    await asyncio.sleep(uniform(0.1, 0.3))
                    await page.type(selector, char)
            
            # Pausa final
            await asyncio.sleep(uniform(0.5, 1.2))
            
        except Exception as e:
            self.logger.error(f"Erro ao digitar: {e}")
            raise
    
    async def movimento_aleatorio_mouse(self, page: Page):
        """Simula movimento aleatório do mouse"""
        try:
            viewport = page.viewport_size
            if viewport:
                for _ in range(randint(1, 3)):
                    x = randint(100, viewport['width'] - 100)
                    y = randint(100, viewport['height'] - 100)
                    await page.mouse.move(x, y)
                    await asyncio.sleep(uniform(0.1, 0.3))
        except:
            pass
    
    async def aguardar_elemento(self, page: Page, selector: str, timeout: int = 30000) -> bool:
        """Aguarda elemento com retry e logging"""
        tentativas = 3
        for tentativa in range(tentativas):
            try:
                await page.wait_for_selector(selector, timeout=timeout)
                return True
            except:
                if tentativa < tentativas - 1:
                    self.logger.warning(f"Tentativa {tentativa + 1}/{tentativas} para encontrar {selector}")
                    await asyncio.sleep(uniform(2, 5))
                    self.stats["tentativas_retry"] += 1
        return False
    
    async def scroll_suave(self, page: Page):
        """Realiza scroll suave na página"""
        await page.evaluate("""
            window.scrollTo({
                top: document.body.scrollHeight * Math.random(),
                behavior: 'smooth'
            })
        """)
        await asyncio.sleep(uniform(1, 2))
    
    async def salvar_incremental_excel(self, dados: List[Dict]):
        """Salva dados no Excel com validação e backup"""
        try:
            df_novo = pd.DataFrame(dados)
            
            # Adicionar campos padrão se não existirem
            for col in self.CAMPOS_PADRAO:
                if col not in df_novo.columns:
                    df_novo[col] = ""
            
            # Adicionar metadados
            df_novo["data_extracao"] = datetime.now().isoformat()
            df_novo["status_extracao"] = "sucesso"
            
            # Reordenar colunas
            df_novo = df_novo[self.CAMPOS_PADRAO]
            
            # Carregar dados existentes ou criar novo
            if self.excel_path.exists():
                # Fazer backup antes de modificar
                backup_path = self.excel_path.with_suffix('.backup.xlsx')
                import shutil
                shutil.copy2(self.excel_path, backup_path)
                
                # Carregar e concatenar
                df_antigo = pd.read_excel(self.excel_path)
                for col in self.CAMPOS_PADRAO:
                    if col not in df_antigo.columns:
                        df_antigo[col] = ""
                df_antigo = df_antigo[self.CAMPOS_PADRAO]
                
                df_final = pd.concat([df_antigo, df_novo], ignore_index=True)
                df_final.drop_duplicates(subset=["numero", "instancia"], keep="last", inplace=True)
            else:
                df_final = df_novo
            
            # Salvar com proteção
            temp_path = self.excel_path.with_suffix(".temp.xlsx")
            df_final.to_excel(temp_path, index=False, engine='openpyxl')
            
            # Validar arquivo temporário
            test_df = pd.read_excel(temp_path)
            if len(test_df) > 0:
                os.replace(temp_path, self.excel_path)
                self.logger.info(f"✅ Salvos {len(dados)} processos em {self.excel_path}")
                
                # Adicionar ao cache
                for processo in dados:
                    if "numero" in processo:
                        self.add_to_cache(processo["numero"], processo)
            else:
                raise ValueError("Arquivo Excel vazio após salvamento")
                
        except Exception as e:
            self.logger.error(f"❌ Erro ao salvar Excel: {e}")
            raise
    
    async def retry_with_backoff(self, func, max_attempts: int = 3, base_delay: float = 5.0):
        """Executa função com retry exponencial"""
        for attempt in range(max_attempts):
            try:
                return await func()
            except Exception as e:
                if attempt == max_attempts - 1:
                    raise
                delay = base_delay * (2 ** attempt) + uniform(0, 3)
                self.logger.warning(f"Tentativa {attempt + 1}/{max_attempts} falhou. Aguardando {delay:.1f}s...")
                await asyncio.sleep(delay)
                self.stats["tentativas_retry"] += 1
    
    @abstractmethod
    async def extrair_processos_pagina(self, page: Page) -> List[Dict]:
        """Método abstrato para extração de processos - deve ser implementado pelas subclasses"""
        pass
    
    @abstractmethod
    async def configurar_busca(self, page: Page, cnpj: str) -> bool:
        """Método abstrato para configurar a busca - deve ser implementado pelas subclasses"""
        pass
    
    async def executar_busca(self, cnpj: str):
        """Executa busca completa com todas as melhorias"""
        cnpj_formatado = ''.join(filter(str.isdigit, cnpj))
        if len(cnpj_formatado) != 14:
            self.logger.error("❌ CNPJ inválido")
            return
        
        cnpj_mascarado = f"{cnpj_formatado[:2]}.{cnpj_formatado[2:5]}.{cnpj_formatado[5:8]}/{cnpj_formatado[8:12]}-{cnpj_formatado[12:]}"
        
        self.logger.info(f"{'='*60}")
        self.logger.info(f"🏛️ {self.instancia_nome.upper()}")
        self.logger.info(f"📋 CNPJ: {cnpj_mascarado}")
        self.logger.info(f"{'='*60}")
        
        async with async_playwright() as p:
            browser, context = await self.create_browser_context(p)
            page = await context.new_page()
            
            try:
                # Navegar para página inicial
                await self.retry_with_backoff(
                    lambda: page.goto(self.url_base, wait_until='networkidle')
                )
                
                # Configurar busca (implementado pela subclasse)
                sucesso = await self.configurar_busca(page, cnpj_mascarado)
                if not sucesso:
                    self.logger.error("❌ Falha ao configurar busca")
                    return
                
                # Processar páginas de resultados
                pagina_num = 1
                todos_processos = []
                
                while True:
                    self.logger.info(f"📄 Processando página {pagina_num}...")
                    
                    # Extrair processos da página
                    processos = await self.extrair_processos_pagina(page)
                    
                    # Filtrar processos já em cache
                    processos_novos = []
                    for processo in processos:
                        if not self.is_processo_cached(processo.get("numero", "")):
                            processos_novos.append(processo)
                            self.stats["processos_extraidos"] += 1
                        else:
                            self.logger.info(f"⏭️ Processo {processo.get('numero')} já em cache")
                    
                    if processos_novos:
                        todos_processos.extend(processos_novos)
                        # Salvar incrementalmente a cada página
                        await self.salvar_incremental_excel(processos_novos)
                    
                    self.stats["paginas_processadas"] += 1
                    
                    # Verificar próxima página
                    next_btn = await page.query_selector("a.unj-pagination__next")
                    if next_btn and await next_btn.is_visible():
                        await self.scroll_suave(page)
                        await next_btn.scroll_into_view_if_needed()
                        await asyncio.sleep(uniform(2, 4))
                        
                        try:
                            await next_btn.click()
                            await page.wait_for_load_state('networkidle', timeout=30000)
                            pagina_num += 1
                        except:
                            self.logger.info("📋 Não há mais páginas")
                            break
                    else:
                        self.logger.info("✅ Todas as páginas processadas")
                        break
                
                # Salvar estatísticas
                self.salvar_estatisticas()
                
            except Exception as e:
                self.logger.error(f"❌ Erro geral: {e}")
                await self.salvar_screenshot_erro(page)
            finally:
                await browser.close()
                self.exibir_resumo()
    
    async def salvar_screenshot_erro(self, page: Page):
        """Salva screenshot em caso de erro"""
        try:
            screenshots_dir = self.script_dir / "screenshots_erro"
            screenshots_dir.mkdir(exist_ok=True)
            
            filename = screenshots_dir / f"erro_{self.instancia_nome}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            await page.screenshot(path=str(filename))
            self.logger.info(f"📸 Screenshot de erro salvo: {filename}")
        except:
            pass
    
    def salvar_estatisticas(self):
        """Salva estatísticas da execução"""
        try:
            stats_file = self.logs_dir / f"stats_{self.instancia_nome}_{datetime.now().strftime('%Y%m%d')}.json"
            
            tempo_total = (datetime.now() - self.stats["tempo_inicio"]).total_seconds()
            self.stats["tempo_total_segundos"] = tempo_total
            self.stats["tempo_fim"] = datetime.now().isoformat()
            
            with open(stats_file, 'w') as f:
                json.dump(self.stats, f, indent=2, default=str)
                
        except Exception as e:
            self.logger.error(f"Erro ao salvar estatísticas: {e}")
    
    def exibir_resumo(self):
        """Exibe resumo da execução"""
        tempo_total = (datetime.now() - self.stats["tempo_inicio"]).total_seconds()
        
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"📊 RESUMO - {self.instancia_nome}")
        self.logger.info(f"{'='*60}")
        self.logger.info(f"✅ Processos extraídos: {self.stats['processos_extraidos']}")
        self.logger.info(f"❌ Erros: {self.stats['processos_erro']}")
        self.logger.info(f"📄 Páginas processadas: {self.stats['paginas_processadas']}")
        self.logger.info(f"🔄 Tentativas de retry: {self.stats['tentativas_retry']}")
        self.logger.info(f"⏱️ Tempo total: {tempo_total:.1f} segundos")
        self.logger.info(f"📁 Arquivo salvo: {self.excel_path}")
        self.logger.info(f"{'='*60}\n")