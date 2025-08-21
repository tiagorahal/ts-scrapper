"""
Sistema de notificações multi-canal para o TJSP Scraper
Suporta Email, Telegram, Webhook e Desktop
"""

import smtplib
import requests
import json
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod
import asyncio
import aiohttp

class NotificadorBase(ABC):
    """Classe base para notificadores"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    async def enviar(self, titulo: str, mensagem: str, dados: Optional[Dict] = None) -> bool:
        """Envia notificação"""
        pass
    
    def formatar_mensagem(self, titulo: str, mensagem: str, dados: Optional[Dict] = None) -> str:
        """Formata mensagem para envio"""
        texto = f"🏛️ TJSP Scraper - {titulo}\n\n{mensagem}"
        
        if dados:
            texto += "\n\n📊 Detalhes:\n"
            for key, value in dados.items():
                texto += f"• {key}: {value}\n"
        
        texto += f"\n⏰ {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
        return texto

class NotificadorEmail(NotificadorBase):
    """Notificador via Email"""
    
    async def enviar(self, titulo: str, mensagem: str, dados: Optional[Dict] = None) -> bool:
        """Envia email com relatório"""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"[TJSP Scraper] {titulo}"
            msg['From'] = self.config['email_remetente']
            msg['To'] = self.config['email_destinatario']
            
            # Criar versão HTML da mensagem
            html_content = self.criar_html_email(titulo, mensagem, dados)
            
            # Criar versão texto
            text_content = self.formatar_mensagem(titulo, mensagem, dados)
            
            # Adicionar partes
            part1 = MIMEText(text_content, 'plain')
            part2 = MIMEText(html_content, 'html')
            
            msg.attach(part1)
            msg.attach(part2)
            
            # Anexar arquivos se houver
            if dados and 'arquivos' in dados:
                for arquivo_path in dados['arquivos']:
                    if Path(arquivo_path).exists():
                        self.anexar_arquivo(msg, arquivo_path)
            
            # Enviar email
            with smtplib.SMTP(self.config['email_smtp_server'], self.config['email_smtp_port']) as server:
                server.starttls()
                server.login(self.config['email_remetente'], self.config['email_senha'])
                server.send_message(msg)
            
            self.logger.info(f"✅ Email enviado para {self.config['email_destinatario']}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao enviar email: {e}")
            return False
    
    def criar_html_email(self, titulo: str, mensagem: str, dados: Optional[Dict]) -> str:
        """Cria versão HTML do email"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    border-radius: 10px 10px 0 0;
                    text-align: center;
                }}
                .content {{
                    background: #f9f9f9;
                    padding: 30px;
                    border: 1px solid #ddd;
                    border-top: none;
                }}
                .stats {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                    gap: 15px;
                    margin: 20px 0;
                }}
                .stat-card {{
                    background: white;
                    padding: 15px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    text-align: center;
                }}
                .stat-value {{
                    font-size: 24px;
                    font-weight: bold;
                    color: #667eea;
                }}
                .stat-label {{
                    font-size: 12px;
                    color: #666;
                    margin-top: 5px;
                }}
                .footer {{
                    text-align: center;
                    padding: 20px;
                    color: #666;
                    font-size: 12px;
                }}
                .success {{ color: #28a745; }}
                .error {{ color: #dc3545; }}
                .warning {{ color: #ffc107; }}
                .button {{
                    display: inline-block;
                    padding: 10px 20px;
                    background: #667eea;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 10px 5px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🏛️ TJSP Scraper</h1>
                <h2>{titulo}</h2>
            </div>
            <div class="content">
                <p>{mensagem}</p>
        """
        
        if dados:
            html += '<div class="stats">'
            
            # Estatísticas principais
            stats_to_show = [
                ('processos_extraidos', '✅ Processos', 'success'),
                ('processos_erro', '❌ Erros', 'error'),
                ('paginas_processadas', '📄 Páginas', ''),
                ('tempo_total', '⏱️ Tempo', '')
            ]
            
            for key, label, css_class in stats_to_show:
                if key in dados:
                    value = dados[key]
                    if key == 'tempo_total':
                        value = f"{value:.1f}s"
                    html += f"""
                    <div class="stat-card">
                        <div class="stat-value {css_class}">{value}</div>
                        <div class="stat-label">{label}</div>
                    </div>
                    """
            
            html += '</div>'
            
            # Detalhes adicionais
            if len(dados) > len(stats_to_show):
                html += '<h3>📊 Detalhes Adicionais</h3><ul>'
                for key, value in dados.items():
                    if key not in [s[0] for s in stats_to_show] and key != 'arquivos':
                        html += f'<li><strong>{key}:</strong> {value}</li>'
                html += '</ul>'
            
            # Links para arquivos
            if 'arquivos' in dados:
                html += '<h3>📁 Arquivos Gerados</h3><ul>'
                for arquivo in dados['arquivos']:
                    nome = Path(arquivo).name
                    html += f'<li>📎 {nome}</li>'
                html += '</ul>'
        
        html += f"""
            </div>
            <div class="footer">
                <p>Gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}</p>
                <p>TJSP Scraper v2.0 - Sistema Automatizado de Extração</p>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def anexar_arquivo(self, msg: MIMEMultipart, arquivo_path: str):
        """Anexa arquivo ao email"""
        try:
            with open(arquivo_path, 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename= {Path(arquivo_path).name}'
                )
                msg.attach(part)
        except Exception as e:
            self.logger.error(f"Erro ao anexar arquivo {arquivo_path}: {e}")

class NotificadorTelegram(NotificadorBase):
    """Notificador via Telegram"""
    
    async def enviar(self, titulo: str, mensagem: str, dados: Optional[Dict] = None) -> bool:
        """Envia notificação via Telegram"""
        try:
            url = f"https://api.telegram.org/bot{self.config['telegram_bot_token']}/sendMessage"
            
            texto = self.formatar_mensagem_telegram(titulo, mensagem, dados)
            
            payload = {
                'chat_id': self.config['telegram_chat_id'],
                'text': texto,
                'parse_mode': 'HTML',
                'disable_web_page_preview': True
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        self.logger.info("✅ Notificação enviada via Telegram")
                        
                        # Enviar arquivos se houver
                        if dados and 'arquivos' in dados:
                            await self.enviar_arquivos_telegram(dados['arquivos'])
                        
                        return True
                    else:
                        error = await response.text()
                        self.logger.error(f"❌ Erro Telegram: {error}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"❌ Erro ao enviar para Telegram: {e}")
            return False
    
    def formatar_mensagem_telegram(self, titulo: str, mensagem: str, dados: Optional[Dict]) -> str:
        """Formata mensagem para Telegram com HTML"""
        texto = f"<b>🏛️ TJSP Scraper</b>\n\n"
        texto += f"<b>{titulo}</b>\n\n"
        texto += f"{mensagem}\n"
        
        if dados:
            texto += "\n<b>📊 Estatísticas:</b>\n"
            
            # Formatar estatísticas principais
            if 'processos_extraidos' in dados:
                texto += f"✅ Processos: <b>{dados['processos_extraidos']}</b>\n"
            if 'processos_erro' in dados:
                texto += f"❌ Erros: <b>{dados['processos_erro']}</b>\n"
            if 'paginas_processadas' in dados:
                texto += f"📄 Páginas: <b>{dados['paginas_processadas']}</b>\n"
            if 'tempo_total' in dados:
                texto += f"⏱️ Tempo: <b>{dados['tempo_total']:.1f}s</b>\n"
        
        texto += f"\n<i>⏰ {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</i>"
        
        return texto
    
    async def enviar_arquivos_telegram(self, arquivos: List[str]):
        """Envia arquivos via Telegram"""
        for arquivo_path in arquivos:
            if not Path(arquivo_path).exists():
                continue
            
            try:
                url = f"https://api.telegram.org/bot{self.config['telegram_bot_token']}/sendDocument"
                
                with open(arquivo_path, 'rb') as f:
                    files = {'document': f}
                    data = {'chat_id': self.config['telegram_chat_id']}
                    
                    async with aiohttp.ClientSession() as session:
                        async with session.post(url, data=data, files=files) as response:
                            if response.status == 200:
                                self.logger.info(f"📎 Arquivo {Path(arquivo_path).name} enviado")
                            
            except Exception as e:
                self.logger.error(f"Erro ao enviar arquivo {arquivo_path}: {e}")

class NotificadorWebhook(NotificadorBase):
    """Notificador via Webhook"""
    
    async def enviar(self, titulo: str, mensagem: str, dados: Optional[Dict] = None) -> bool:
        """Envia notificação via webhook"""
        try:
            payload = {
                'titulo': titulo,
                'mensagem': mensagem,
                'timestamp': datetime.now().isoformat(),
                'origem': 'TJSP_SCRAPER',
                'dados': dados or {}
            }
            
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'TJSP-Scraper/2.0'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.config['webhook_url'],
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status in [200, 201, 202, 204]:
                        self.logger.info("✅ Webhook enviado com sucesso")
                        return True
                    else:
                        error = await response.text()
                        self.logger.error(f"❌ Erro webhook ({response.status}): {error}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"❌ Erro ao enviar webhook: {e}")
            return False

class NotificadorDesktop(NotificadorBase):
    """Notificador via notificação desktop (Windows/Linux/Mac)"""
    
    async def enviar(self, titulo: str, mensagem: str, dados: Optional[Dict] = None) -> bool:
        """Envia notificação desktop"""
        try:
            # Tentar usar plyer para notificações cross-platform
            try:
                from plyer import notification
                
                notification.notify(
                    title=f"TJSP Scraper - {titulo}",
                    message=mensagem[:256],  # Limitar tamanho
                    app_icon=None,
                    timeout=10
                )
                
                self.logger.info("✅ Notificação desktop enviada")
                return True
                
            except ImportError:
                # Fallback para sistema específico
                import platform
                sistema = platform.system()
                
                if sistema == "Windows":
                    from win10toast import ToastNotifier
                    toaster = ToastNotifier()
                    toaster.show_toast(
                        f"TJSP Scraper - {titulo}",
                        mensagem[:256],
                        duration=10
                    )
                elif sistema == "Darwin":  # macOS
                    import subprocess
                    subprocess.run([
                        'osascript', '-e',
                        f'display notification "{mensagem[:256]}" with title "TJSP Scraper - {titulo}"'
                    ])
                elif sistema == "Linux":
                    import subprocess
                    subprocess.run([
                        'notify-send',
                        f'TJSP Scraper - {titulo}',
                        mensagem[:256]
                    ])
                
                return True
                
        except Exception as e:
            self.logger.error(f"❌ Erro na notificação desktop: {e}")
            return False

class GerenciadorNotificacoes:
    """Gerenciador central de notificações"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger("GerenciadorNotificacoes")
        self.notificadores = self._inicializar_notificadores()
    
    def _inicializar_notificadores(self) -> List[NotificadorBase]:
        """Inicializa notificadores configurados"""
        notificadores = []
        
        if self.config.get('notificar_email'):
            notificadores.append(NotificadorEmail(self.config))
            
        if self.config.get('notificar_telegram'):
            notificadores.append(NotificadorTelegram(self.config))
            
        if self.config.get('notificar_webhook'):
            notificadores.append(NotificadorWebhook(self.config))
            
        if self.config.get('notificar_desktop', True):
            notificadores.append(NotificadorDesktop(self.config))
        
        self.logger.info(f"✅ {len(notificadores)} notificadores inicializados")
        return notificadores
    
    async def notificar_inicio(self, cnpj: str, instancias: List[str]):
        """Notifica início da execução"""
        titulo = "Execução Iniciada"
        mensagem = f"Iniciando extração para CNPJ {cnpj}"
        dados = {
            'cnpj': cnpj,
            'instancias': ', '.join(instancias),
            'hora_inicio': datetime.now().isoformat()
        }
        
        await self._enviar_todas(titulo, mensagem, dados)
    
    async def notificar_progresso(self, instancia: str, pagina: int, processos: int):
        """Notifica progresso da execução"""
        titulo = f"Progresso - {instancia}"
        mensagem = f"Página {pagina} processada com {processos} processos"
        dados = {
            'instancia': instancia,
            'pagina': pagina,
            'processos_ate_agora': processos
        }
        
        # Notificar apenas a cada 5 páginas para não spammar
        if pagina % 5 == 0:
            await self._enviar_todas(titulo, mensagem, dados)
    
    async def notificar_erro(self, instancia: str, erro: str, contexto: Optional[Dict] = None):
        """Notifica erro na execução"""
        titulo = f"⚠️ Erro - {instancia}"
        mensagem = f"Erro detectado: {erro}"
        dados = {
            'instancia': instancia,
            'erro': erro,
            'timestamp': datetime.now().isoformat()
        }
        if contexto:
            dados.update(contexto)
        
        await self._enviar_todas(titulo, mensagem, dados)
    
    async def notificar_conclusao(self, stats: Dict[str, Any], arquivos: List[str]):
        """Notifica conclusão da execução"""
        titulo = "✅ Execução Concluída"
        
        total_processos = sum(s.get('processos_extraidos', 0) for s in stats.values())
        total_erros = sum(s.get('processos_erro', 0) for s in stats.values())
        tempo_total = (datetime.now() - stats.get('tempo_inicio', datetime.now())).total_seconds()
        
        mensagem = f"Extração concluída com sucesso!\n"
        mensagem += f"Total de {total_processos} processos extraídos"
        
        dados = {
            'processos_extraidos': total_processos,
            'processos_erro': total_erros,
            'tempo_total': tempo_total,
            'arquivos': arquivos
        }
        
        # Adicionar detalhes por instância
        for instancia, stat in stats.items():
            dados[f"{instancia}_processos"] = stat.get('processos_extraidos', 0)
        
        await self._enviar_todas(titulo, mensagem, dados)
    
    async def _enviar_todas(self, titulo: str, mensagem: str, dados: Optional[Dict] = None):
        """Envia notificação para todos os canais configurados"""
        tasks = []
        for notificador in self.notificadores:
            tasks.append(notificador.enviar(titulo, mensagem, dados))
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            sucesso = sum(1 for r in results if r is True)
            falhas = len(results) - sucesso
            
            if falhas > 0:
                self.logger.warning(f"⚠️ {falhas} notificações falharam")
            
            return sucesso > 0
        
        return False

# Exemplo de uso
if __name__ == "__main__":
    import asyncio
    
    # Configuração de exemplo
    config = {
        'notificar_desktop': True,
        'notificar_email': False,  # Configurar credenciais para testar
        'notificar_telegram': False,  # Configurar token e chat_id para testar
        'notificar_webhook': False,  # Configurar URL para testar
    }
    
    async def teste():
        gerenciador = GerenciadorNotificacoes(config)
        
        # Teste de notificação
        await gerenciador.notificar_inicio("00.000.000/0001-00", ["1ª Instância", "2ª Instância"])
        
        await asyncio.sleep(2)
        
        await gerenciador.notificar_conclusao(
            {
                'primeira_instancia': {'processos_extraidos': 10, 'processos_erro': 1},
                'segunda_instancia': {'processos_extraidos': 5, 'processos_erro': 0},
                'tempo_inicio': datetime.now()
            },
            ['dados/primeira_instancia.xlsx', 'dados/segunda_instancia.xlsx']
        )
    
    asyncio.run(teste())