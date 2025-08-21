"""
Sistema de configuração centralizado para o TJSP Scraper
Permite customização via arquivo JSON ou variáveis de ambiente
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
import logging

@dataclass
class ScraperConfig:
    """Configurações do scraper"""
    
    # Configurações de execução
    headless: bool = True
    max_workers: int = 3
    timeout_padrao: int = 30000
    retry_max_attempts: int = 3
    retry_base_delay: float = 5.0
    
    # Configurações de comportamento
    usar_cache: bool = True
    salvar_screenshots_erro: bool = True
    salvar_logs: bool = True
    salvar_estatisticas: bool = True
    
    # Delays humanizados (em segundos)
    delay_min_entre_paginas: float = 2.0
    delay_max_entre_paginas: float = 5.0
    delay_min_digitacao: float = 0.05
    delay_max_digitacao: float = 0.15
    delay_min_clique: float = 0.3
    delay_max_clique: float = 0.8
    
    # Configurações de proxy (opcional)
    usar_proxy: bool = False
    proxy_url: Optional[str] = None
    proxy_username: Optional[str] = None
    proxy_password: Optional[str] = None
    
    # Configurações de notificação
    notificar_email: bool = False
    email_destinatario: Optional[str] = None
    email_remetente: Optional[str] = None
    email_senha: Optional[str] = None
    email_smtp_server: str = "smtp.gmail.com"
    email_smtp_port: int = 587
    
    notificar_telegram: bool = False
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    
    notificar_webhook: bool = False
    webhook_url: Optional[str] = None
    
    # Configurações de exportação
    exportar_json: bool = True
    exportar_csv: bool = True
    exportar_parquet: bool = False
    comprimir_exports: bool = True
    
    # Configurações de análise
    gerar_relatorio_html: bool = True
    gerar_dashboard: bool = False
    calcular_estatisticas: bool = True
    
    # Limites
    max_processos_por_execucao: Optional[int] = None
    max_paginas_por_instancia: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte configuração para dicionário"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScraperConfig':
        """Cria configuração a partir de dicionário"""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})

class ConfigManager:
    """Gerenciador de configurações com suporte a múltiplas fontes"""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.logger = logging.getLogger("ConfigManager")
        self.config_path = config_path or Path(__file__).parent / "config.json"
        self.config = self.load_config()
    
    def load_config(self) -> ScraperConfig:
        """Carrega configuração com prioridade: ENV > arquivo > padrão"""
        config_dict = {}
        
        # 1. Carregar configuração padrão
        config = ScraperConfig()
        
        # 2. Tentar carregar do arquivo
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    file_config = json.load(f)
                    config = ScraperConfig.from_dict(file_config)
                    self.logger.info(f"✅ Configuração carregada de {self.config_path}")
            except Exception as e:
                self.logger.warning(f"⚠️ Erro ao carregar config: {e}. Usando padrões.")
        
        # 3. Sobrescrever com variáveis de ambiente
        config = self.load_from_env(config)
        
        return config
    
    def load_from_env(self, config: ScraperConfig) -> ScraperConfig:
        """Carrega configurações de variáveis de ambiente"""
        env_mapping = {
            "TJSP_HEADLESS": ("headless", lambda x: x.lower() == "true"),
            "TJSP_MAX_WORKERS": ("max_workers", int),
            "TJSP_TIMEOUT": ("timeout_padrao", int),
            "TJSP_USE_CACHE": ("usar_cache", lambda x: x.lower() == "true"),
            "TJSP_PROXY_URL": ("proxy_url", str),
            "TJSP_PROXY_USER": ("proxy_username", str),
            "TJSP_PROXY_PASS": ("proxy_password", str),
            "TJSP_EMAIL_TO": ("email_destinatario", str),
            "TJSP_EMAIL_FROM": ("email_remetente", str),
            "TJSP_EMAIL_PASS": ("email_senha", str),
            "TJSP_TELEGRAM_TOKEN": ("telegram_bot_token", str),
            "TJSP_TELEGRAM_CHAT": ("telegram_chat_id", str),
            "TJSP_WEBHOOK_URL": ("webhook_url", str),
        }
        
        for env_var, (attr_name, converter) in env_mapping.items():
            value = os.getenv(env_var)
            if value is not None:
                try:
                    setattr(config, attr_name, converter(value))
                    self.logger.info(f"✅ Configuração {attr_name} carregada de ENV")
                except Exception as e:
                    self.logger.warning(f"⚠️ Erro ao converter {env_var}: {e}")
        
        # Ativar notificações se credenciais foram fornecidas
        if config.email_destinatario and config.email_senha:
            config.notificar_email = True
        
        if config.telegram_bot_token and config.telegram_chat_id:
            config.notificar_telegram = True
        
        if config.webhook_url:
            config.notificar_webhook = True
        
        if config.proxy_url:
            config.usar_proxy = True
        
        return config
    
    def save_config(self, config: Optional[ScraperConfig] = None):
        """Salva configuração atual em arquivo"""
        config = config or self.config
        try:
            with open(self.config_path, 'w') as f:
                json.dump(config.to_dict(), f, indent=2)
            self.logger.info(f"✅ Configuração salva em {self.config_path}")
        except Exception as e:
            self.logger.error(f"❌ Erro ao salvar configuração: {e}")
    
    def create_default_config_file(self):
        """Cria arquivo de configuração padrão"""
        if not self.config_path.exists():
            default_config = ScraperConfig()
            self.save_config(default_config)
            print(f"📄 Arquivo de configuração criado: {self.config_path}")
            print("💡 Edite o arquivo para customizar as configurações")
        else:
            print(f"⚠️ Arquivo já existe: {self.config_path}")
    
    def validate_config(self) -> bool:
        """Valida configuração atual"""
        is_valid = True
        
        # Validar configurações de email
        if self.config.notificar_email:
            if not all([
                self.config.email_destinatario,
                self.config.email_remetente,
                self.config.email_senha
            ]):
                self.logger.error("❌ Configuração de email incompleta")
                is_valid = False
        
        # Validar configurações de Telegram
        if self.config.notificar_telegram:
            if not all([
                self.config.telegram_bot_token,
                self.config.telegram_chat_id
            ]):
                self.logger.error("❌ Configuração de Telegram incompleta")
                is_valid = False
        
        # Validar proxy
        if self.config.usar_proxy and not self.config.proxy_url:
            self.logger.error("❌ URL do proxy não configurada")
            is_valid = False
        
        # Validar limites
        if self.config.max_workers < 1 or self.config.max_workers > 10:
            self.logger.warning("⚠️ max_workers deve estar entre 1 e 10")
            self.config.max_workers = min(max(self.config.max_workers, 1), 10)
        
        return is_valid
    
    def get_config(self) -> ScraperConfig:
        """Retorna configuração atual validada"""
        self.validate_config()
        return self.config
    
    def update_config(self, **kwargs):
        """Atualiza configurações específicas"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                self.logger.info(f"✅ Configuração {key} atualizada para {value}")
            else:
                self.logger.warning(f"⚠️ Configuração {key} não existe")

# Singleton global de configuração
_config_manager: Optional[ConfigManager] = None

def get_config_manager() -> ConfigManager:
    """Retorna instância singleton do gerenciador de configuração"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager

def get_config() -> ScraperConfig:
    """Atalho para obter configuração atual"""
    return get_config_manager().get_config()

# CLI para gerenciar configurações
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Gerenciador de Configurações TJSP Scraper")
    parser.add_argument("--create", action="store_true", help="Criar arquivo de configuração padrão")
    parser.add_argument("--show", action="store_true", help="Mostrar configuração atual")
    parser.add_argument("--validate", action="store_true", help="Validar configuração")
    parser.add_argument("--set", nargs=2, metavar=("KEY", "VALUE"), help="Definir valor de configuração")
    
    args = parser.parse_args()
    
    manager = get_config_manager()
    
    if args.create:
        manager.create_default_config_file()
    
    elif args.show:
        config = manager.get_config()
        print("\n📋 Configuração Atual:")
        print("=" * 60)
        for key, value in config.to_dict().items():
            # Ocultar senhas
            if "senha" in key.lower() or "password" in key.lower() or "token" in key.lower():
                if value:
                    value = "***" + str(value)[-4:] if len(str(value)) > 4 else "***"
            print(f"{key:30s}: {value}")
        print("=" * 60)
    
    elif args.validate:
        if manager.validate_config():
            print("✅ Configuração válida!")
        else:
            print("❌ Configuração inválida. Verifique os logs.")
    
    elif args.set:
        key, value = args.set
        
        # Tentar converter valor para tipo apropriado
        if value.lower() in ["true", "false"]:
            value = value.lower() == "true"
        elif value.isdigit():
            value = int(value)
        elif value.replace(".", "").isdigit():
            value = float(value)
        
        manager.update_config(**{key: value})
        manager.save_config()
        print(f"✅ {key} = {value}")