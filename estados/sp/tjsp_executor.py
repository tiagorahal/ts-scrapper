#!/usr/bin/env python3
"""
TJSP Scraper v2.0 - Orquestrador Principal
Sistema completo de extração de processos judiciais do TJSP
"""

import asyncio
import sys
import argparse
from pathlib import Path
from datetime import datetime
import logging
from typing import List, Dict, Optional, Tuple
import signal
import json
from concurrent.futures import ThreadPoolExecutor
import pandas as pd

# Importar módulos do sistema
from config import get_config_manager, get_config
from notificador import GerenciadorNotificacoes
from analisador import AnalisadorTJSP
from scrappers_implementados import (
    ScraperPrimeiraInstancia,
    ScraperSegundaInstancia,
    ScraperColegioRecursal
)

class TJSPOrquestrador:
    """Orquestrador principal do sistema TJSP Scraper"""
    
    def __init__(self):
        self.config = get_config()
        self.logger = self.configurar_logging()
        self.notificador = None
        self.scrapers = []
        self.resultados = {}
        self.cancelado = False
        
        # Configurar handler de sinais
        signal.signal(signal.SIGINT, self.handle_interrupt)
        signal.signal(signal.SIGTERM, self.handle_interrupt)
        
        # Inicializar notificador se configurado
        self.inicializar_notificador()
    
    def configurar_logging(self) -> logging.Logger:
        """Configura sistema de logging centralizado"""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / f"tjsp_executor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        # Formatter customizado
        formatter = logging.Formatter(
            '%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # File handler
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        
        # Console handler com cores
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        
        # Configurar logger root
        logger = logging.getLogger("TJSPOrquestrador")
        logger.setLevel(logging.INFO)
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def inicializar_notificador(self):
        """Inicializa sistema de notificações"""
        config_notif = {
            'notificar_email': self.config.notificar_email,
            'email_destinatario': self.config.email_destinatario,
            'email_remetente': self.config.email_remetente,
            'email_senha': self.config.email_senha,
            'email_smtp_server': self.config.email_smtp_server,
            'email_smtp_port': self.config.email_smtp_port,
            'notificar_telegram': self.config.notificar_telegram,
            'telegram_bot_token': self.config.telegram_bot_token,
            'telegram_chat_id': self.config.telegram_chat_id,
            'notificar_webhook': self.config.notificar_webhook,
            'webhook_url': self.config.webhook_url,
            'notificar_desktop': True
        }
        
        self.notificador = GerenciadorNotificacoes(config_notif)
    
    def handle_interrupt(self, signum, frame):
        """Handler para interrupção do usuário"""
        self.logger.warning("\n⚠️ Interrupção detectada. Finalizando gracefully...")
        self.cancelado = True
        
        # Salvar progresso atual
        self.salvar_progresso()
        
        # Notificar
        if self.notificador:
            asyncio.create_task(
                self.notificador.notificar_erro(
                    "Sistema",
                    "Execução interrompida pelo usuário",
                    {"progresso_salvo": True}
                )
            )
        
        sys.exit(0)
    
    def salvar_progresso(self):
        """Salva progresso atual da execução"""
        try:
            progresso_file = Path("dados") / f"progresso_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            progresso = {
                'timestamp': datetime.now().isoformat(),
                'resultados': {
                    instancia: {
                        'processos_extraidos': scraper.stats['processos_extraidos'],
                        'processos_erro': scraper.stats['processos_erro'],
                        'paginas_processadas': scraper.stats['paginas_processadas']
                    }
                    for instancia, scraper in zip(['primeira', 'segunda', 'colegio'], self.scrapers)
                    if scraper
                },
                'config': self.config.to_dict()
            }
            
            with open(progresso_file, 'w') as f:
                json.dump(progresso, f, indent=2, default=str)
            
            self.logger.info(f"✅ Progresso salvo em: {progresso_file}")
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao salvar progresso: {e}")
    
    def validar_cnpj(self, cnpj: str) -> Optional[str]:
        """Valida e formata CNPJ"""
        # Remover caracteres não numéricos
        cnpj_limpo = ''.join(filter(str.isdigit, cnpj))
        
        if len(cnpj_limpo) != 14:
            return None
        
        # Validar dígitos verificadores (algoritmo completo)
        def calcular_digito(cnpj_parcial: str, pesos: List[int]) -> str:
            soma = sum(int(cnpj_parcial[i]) * pesos[i] for i in range(len(pesos)))
            resto = soma % 11
            return '0' if resto < 2 else str(11 - resto)
        
        # Pesos para validação
        pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        
        # Validar primeiro dígito
        digito1 = calcular_digito(cnpj_limpo[:12], pesos1)
        if digito1 != cnpj_limpo[12]:
            return None
        
        # Validar segundo dígito
        digito2 = calcular_digito(cnpj_limpo[:13], pesos2)
        if digito2 != cnpj_limpo[13]:
            return None
        
        # Formatar CNPJ
        return f"{cnpj_limpo[:2]}.{cnpj_limpo[2:5]}.{cnpj_limpo[5:8]}/{cnpj_limpo[8:12]}-{cnpj_limpo[12:]}"
    
    async def executar_scraper_async(self, scraper_class, cnpj: str) -> Tuple[str, Dict]:
        """Executa um scraper de forma assíncrona"""
        nome = scraper_class.__name__
        
        try:
            self.logger.info(f"🚀 Iniciando {nome}...")
            
            scraper = scraper_class()
            self.scrapers.append(scraper)
            
            await scraper.executar_busca(cnpj)
            
            return nome, scraper.stats
            
        except Exception as e:
            self.logger.error(f"❌ Erro em {nome}: {e}")
            return nome, {"erro": str(e)}
    
    async def executar_paralelo(self, cnpj: str, instancias: List[str]):
        """Executa scrapers em paralelo"""
        # Mapear instâncias para classes
        mapa_scrapers = {
            'primeira': ScraperPrimeiraInstancia,
            'segunda': ScraperSegundaInstancia,
            'colegio': ScraperColegioRecursal
        }
        
        # Criar tarefas apenas para instâncias selecionadas
        tarefas = []
        for instancia in instancias:
            if instancia in mapa_scrapers:
                tarefas.append(
                    self.executar_scraper_async(mapa_scrapers[instancia], cnpj)
                )
        
        # Executar em paralelo com limite de workers
        if self.config.max_workers < len(tarefas):
            # Limitar concorrência
            semaforo = asyncio.Semaphore(self.config.max_workers)
            
            async def executar_com_limite(tarefa):
                async with semaforo:
                    return await tarefa
            
            tarefas = [executar_com_limite(t) for t in tarefas]
        
        # Aguardar conclusão
        resultados = await asyncio.gather(*tarefas, return_exceptions=True)
        
        # Processar resultados
        for resultado in resultados:
            if isinstance(resultado, Exception):
                self.logger.error(f"❌ Erro na execução: {resultado}")
            else:
                nome, stats = resultado
                self.resultados[nome] = stats
    
    async def executar_analise(self) -> Optional[Path]:
        """Executa análise dos dados extraídos"""
        try:
            self.logger.info("📊 Iniciando análise dos dados...")
            
            analisador = AnalisadorTJSP(Path("dados"))
            estatisticas = analisador.analisar_completo()
            
            # Gerar relatório HTML se configurado
            relatorio_path = None
            if self.config.gerar_relatorio_html:
                relatorio_path = analisador.gerar_relatorio_html()
                self.logger.info(f"✅ Relatório HTML gerado: {relatorio_path}")
            
            # Exportar JSON se configurado
            if self.config.exportar_json:
                json_path = analisador.exportar_json()
                self.logger.info(f"✅ Análise exportada: {json_path}")
            
            # Exportar CSV se configurado
            if self.config.exportar_csv:
                await self.exportar_csv()
            
            return relatorio_path
            
        except Exception as e:
            self.logger.error(f"❌ Erro na análise: {e}")
            return None
    
    async def exportar_csv(self):
        """Exporta dados para CSV"""
        try:
            dados_dir = Path("dados")
            
            # Arquivos Excel para converter
            arquivos = [
                "primeira_instancia_tjsp.xlsx",
                "segunda_instancia_tjsp.xlsx",
                "colegio_recursal_tjsp.xlsx"
            ]
            
            for arquivo in arquivos:
                excel_path = dados_dir / arquivo
                if excel_path.exists():
                    csv_path = excel_path.with_suffix('.csv')
                    df = pd.read_excel(excel_path)
                    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
                    self.logger.info(f"✅ CSV exportado: {csv_path}")
                    
        except Exception as e:
            self.logger.error(f"❌ Erro ao exportar CSV: {e}")
    
    async def executar(self, cnpj: str, instancias: Optional[List[str]] = None):
        """Executa o pipeline completo"""
        inicio = datetime.now()
        
        # Instâncias padrão
        if not instancias:
            instancias = ['primeira', 'segunda', 'colegio']
        
        # Validar CNPJ
        cnpj_formatado = self.validar_cnpj(cnpj)
        if not cnpj_formatado:
            self.logger.error("❌ CNPJ inválido!")
            print("CNPJ inválido. Verifique o número digitado.")
            return False
        
        self.logger.info(f"{'='*60}")
        self.logger.info(f"🏛️ TJSP SCRAPER v2.0")
        self.logger.info(f"📋 CNPJ: {cnpj_formatado}")
        self.logger.info(f"🎯 Instâncias: {', '.join(instancias)}")
        self.logger.info(f"{'='*60}")
        
        try:
            # Notificar início
            if self.notificador:
                await self.notificador.notificar_inicio(cnpj_formatado, instancias)
            
            # Executar scrapers
            await self.executar_paralelo(cnpj, instancias)
            
            # Analisar dados se configurado
            relatorio_path = None
            if self.config.calcular_estatisticas:
                relatorio_path = await self.executar_analise()
            
            # Calcular tempo total
            tempo_total = (datetime.now() - inicio).total_seconds()
            
            # Preparar arquivos para notificação
            arquivos = []
            dados_dir = Path("dados")
            for arquivo in dados_dir.glob("*.xlsx"):
                if arquivo.stat().st_mtime > inicio.timestamp():
                    arquivos.append(str(arquivo))
            
            if relatorio_path:
                arquivos.append(str(relatorio_path))
            
            # Notificar conclusão
            if self.notificador:
                stats_notif = {
                    nome: stats
                    for nome, stats in self.resultados.items()
                }
                stats_notif['tempo_inicio'] = inicio
                
                await self.notificador.notificar_conclusao(stats_notif, arquivos)
            
            # Exibir resumo
            self.exibir_resumo_final(tempo_total, arquivos)
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro geral: {e}")
            
            if self.notificador:
                await self.notificador.notificar_erro(
                    "Sistema",
                    str(e),
                    {"traceback": str(e)}
                )
            
            return False
    
    def exibir_resumo_final(self, tempo_total: float, arquivos: List[str]):
        """Exibe resumo final da execução"""
        print("\n" + "="*60)
        print("📊 RESUMO FINAL DA EXECUÇÃO")
        print("="*60)
        
        total_processos = 0
        total_erros = 0
        
        for nome, stats in self.resultados.items():
            if isinstance(stats, dict) and 'processos_extraidos' in stats:
                processos = stats['processos_extraidos']
                erros = stats.get('processos_erro', 0)
                total_processos += processos
                total_erros += erros
                
                print(f"\n{nome}:")
                print(f"  ✅ Processos extraídos: {processos}")
                print(f"  ❌ Erros: {erros}")
                print(f"  📄 Páginas processadas: {stats.get('paginas_processadas', 0)}")
        
        print(f"\n📊 TOTAIS:")
        print(f"  • Total de processos: {total_processos}")
        print(f"  • Total de erros: {total_erros}")
        print(f"  • Tempo total: {tempo_total:.1f} segundos")
        print(f"  • Taxa de sucesso: {((total_processos/(total_processos+total_erros))*100 if (total_processos+total_erros) > 0 else 0):.1f}%")
        
        if arquivos:
            print(f"\n📁 Arquivos gerados:")
            for arquivo in arquivos:
                print(f"  • {Path(arquivo).name}")
        
        print("\n" + "="*60)
        print("✅ Execução concluída com sucesso!")
        print("="*60)


def criar_parser():
    """Cria parser de argumentos"""
    parser = argparse.ArgumentParser(
        description='TJSP Scraper v2.0 - Sistema Avançado de Extração de Processos',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  %(prog)s 00.000.000/0001-00              # Executa todas as instâncias
  %(prog)s 00.000.000/0001-00 --primeira   # Apenas 1ª instância
  %(prog)s 00.000.000/0001-00 -1 -2        # 1ª e 2ª instâncias
  %(prog)s --config                        # Mostrar configuração
  %(prog)s --analise                       # Apenas analisar dados existentes
        """
    )
    
    # Argumentos principais
    parser.add_argument(
        'cnpj',
        nargs='?',
        help='CNPJ para busca (com ou sem formatação)'
    )
    
    # Seleção de instâncias
    instancias_group = parser.add_argument_group('Seleção de Instâncias')
    instancias_group.add_argument(
        '-1', '--primeira',
        action='store_true',
        help='Buscar na 1ª Instância'
    )
    instancias_group.add_argument(
        '-2', '--segunda',
        action='store_true',
        help='Buscar na 2ª Instância'
    )
    instancias_group.add_argument(
        '-c', '--colegio',
        action='store_true',
        help='Buscar no Colégio Recursal'
    )
    instancias_group.add_argument(
        '-a', '--todas',
        action='store_true',
        help='Buscar em todas as instâncias (padrão)'
    )
    
    # Opções de configuração
    config_group = parser.add_argument_group('Configuração')
    config_group.add_argument(
        '--config',
        action='store_true',
        help='Mostrar configuração atual'
    )
    config_group.add_argument(
        '--config-criar',
        action='store_true',
        help='Criar arquivo de configuração padrão'
    )
    config_group.add_argument(
        '--headless',
        type=lambda x: x.lower() == 'true',
        help='Executar em modo headless (true/false)'
    )
    config_group.add_argument(
        '--workers',
        type=int,
        metavar='N',
        help='Número máximo de workers paralelos'
    )
    
    # Opções de análise
    analise_group = parser.add_argument_group('Análise e Relatórios')
    analise_group.add_argument(
        '--analise',
        action='store_true',
        help='Executar apenas análise dos dados existentes'
    )
    analise_group.add_argument(
        '--relatorio',
        action='store_true',
        help='Gerar relatório HTML após execução'
    )
    analise_group.add_argument(
        '--export-csv',
        action='store_true',
        help='Exportar dados para CSV'
    )
    analise_group.add_argument(
        '--export-json',
        action='store_true',
        help='Exportar análise para JSON'
    )
    
    # Outras opções
    parser.add_argument(
        '--no-cache',
        action='store_true',
        help='Desabilitar uso de cache'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Ativar modo debug com logs detalhados'
    )
    parser.add_argument(
        '-v', '--version',
        action='version',
        version='%(prog)s 2.0.0'
    )
    
    return parser


async def main():
    """Função principal"""
    parser = criar_parser()
    args = parser.parse_args()
    
    # Configurar logging para debug se necessário
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Gerenciar configuração
    config_manager = get_config_manager()
    
    if args.config_criar:
        config_manager.create_default_config_file()
        return
    
    if args.config:
        config = config_manager.get_config()
        print("\n📋 Configuração Atual:")
        print("="*60)
        for key, value in config.to_dict().items():
            if any(s in key.lower() for s in ['senha', 'password', 'token']):
                if value:
                    value = "***"
            print(f"{key:30s}: {value}")
        print("="*60)
        return
    
    # Aplicar configurações da linha de comando
    if args.headless is not None:
        config_manager.update_config(headless=args.headless)
    
    if args.workers:
        config_manager.update_config(max_workers=args.workers)
    
    if args.no_cache:
        config_manager.update_config(usar_cache=False)
    
    if args.relatorio:
        config_manager.update_config(gerar_relatorio_html=True)
    
    if args.export_csv:
        config_manager.update_config(exportar_csv=True)
    
    if args.export_json:
        config_manager.update_config(exportar_json=True)
    
    # Executar análise apenas
    if args.analise:
        print("\n📊 Executando análise dos dados existentes...")
        analisador = AnalisadorTJSP(Path("dados"))
        analisador.analisar_completo()
        
        if args.relatorio or config_manager.get_config().gerar_relatorio_html:
            relatorio = analisador.gerar_relatorio_html()
            print(f"✅ Relatório gerado: {relatorio}")
        
        if args.export_json or config_manager.get_config().exportar_json:
            json_path = analisador.exportar_json()
            print(f"✅ Análise exportada: {json_path}")
        
        return
    
    # Validar CNPJ
    if not args.cnpj:
        print("❌ CNPJ é obrigatório para executar busca!")
        print("Use --help para ver opções disponíveis")
        return
    
    # Determinar instâncias a buscar
    instancias = []
    if args.primeira:
        instancias.append('primeira')
    if args.segunda:
        instancias.append('segunda')
    if args.colegio:
        instancias.append('colegio')
    
    # Se nenhuma foi especificada, usar todas
    if not instancias or args.todas:
        instancias = ['primeira', 'segunda', 'colegio']
    
    # Executar orquestrador
    orquestrador = TJSPOrquestrador()
    sucesso = await orquestrador.executar(args.cnpj, instancias)
    
    sys.exit(0 if sucesso else 1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ Execução interrompida pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)