#!/usr/bin/env python3
"""
Script de instalação e configuração do TJSP Scraper v2.0
Automatiza todo o processo de setup do sistema
"""

import os
import sys
import subprocess
import platform
from pathlib import Path
import json
import venv
import shutil

class TJSPSetup:
    """Instalador do TJSP Scraper"""
    
    def __init__(self):
        self.sistema = platform.system()
        self.python_version = sys.version_info
        self.root_dir = Path(__file__).parent
        self.venv_dir = self.root_dir / "venv"
        self.errors = []
        
    def print_header(self):
        """Exibe header do instalador"""
        print("="*60)
        print("🏛️  TJSP SCRAPER v2.0 - INSTALADOR")
        print("="*60)
        print(f"Sistema: {self.sistema}")
        print(f"Python: {self.python_version.major}.{self.python_version.minor}.{self.python_version.micro}")
        print(f"Diretório: {self.root_dir}")
        print("="*60)
    
    def verificar_python(self) -> bool:
        """Verifica versão do Python"""
        print("\n🔍 Verificando Python...")
        
        if self.python_version.major < 3 or \
           (self.python_version.major == 3 and self.python_version.minor < 8):
            print("❌ Python 3.8+ é necessário!")
            print(f"   Versão atual: {self.python_version.major}.{self.python_version.minor}")
            return False
        
        print(f"✅ Python {self.python_version.major}.{self.python_version.minor} detectado")
        return True
    
    def criar_ambiente_virtual(self) -> bool:
        """Cria ambiente virtual"""
        print("\n🔧 Criando ambiente virtual...")
        
        try:
            if self.venv_dir.exists():
                resposta = input("⚠️  Ambiente virtual já existe. Recriar? (s/N): ")
                if resposta.lower() == 's':
                    shutil.rmtree(self.venv_dir)
                else:
                    print("✅ Usando ambiente virtual existente")
                    return True
            
            venv.create(self.venv_dir, with_pip=True)
            print("✅ Ambiente virtual criado")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao criar ambiente virtual: {e}")
            self.errors.append(str(e))
            return False
    
    def get_pip_command(self) -> str:
        """Retorna comando pip do ambiente virtual"""
        if self.sistema == "Windows":
            return str(self.venv_dir / "Scripts" / "pip.exe")
        else:
            return str(self.venv_dir / "bin" / "pip")
    
    def get_python_command(self) -> str:
        """Retorna comando python do ambiente virtual"""
        if self.sistema == "Windows":
            return str(self.venv_dir / "Scripts" / "python.exe")
        else:
            return str(self.venv_dir / "bin" / "python")
    
    def instalar_dependencias(self) -> bool:
        """Instala dependências do requirements.txt"""
        print("\n📦 Instalando dependências...")
        
        pip_cmd = self.get_pip_command()
        requirements_file = self.root_dir.parent.parent / "requirements.txt"
        
        if not requirements_file.exists():
            print("❌ Arquivo requirements.txt não encontrado!")
            return False
        
        try:
            # Atualizar pip
            print("📋 Atualizando pip...")
            subprocess.run(
                [pip_cmd, "install", "--upgrade", "pip"],
                check=True,
                capture_output=True
            )
            
            # Instalar requirements
            print("📋 Instalando pacotes...")
            
            # Instalar em etapas para melhor controle
            etapas = [
                ("Core", ["playwright", "pandas", "openpyxl", "numpy"]),
                ("Async", ["aiohttp", "aiofiles"]),
                ("Visualização", ["matplotlib", "seaborn"]),
                ("Utilitários", ["colorama", "rich", "tqdm", "loguru"]),
                ("Notificações", ["plyer"]),
            ]
            
            for nome_etapa, pacotes in etapas:
                print(f"   📦 {nome_etapa}...")
                for pacote in pacotes:
                    try:
                        subprocess.run(
                            [pip_cmd, "install", pacote],
                            check=True,
                            capture_output=True,
                            text=True
                        )
                        print(f"      ✅ {pacote}")
                    except subprocess.CalledProcessError as e:
                        print(f"      ⚠️ {pacote} - erro não crítico")
            
            # Instalar todos os outros pacotes
            print("   📦 Demais dependências...")
            subprocess.run(
                [pip_cmd, "install", "-r", str(requirements_file)],
                check=False,  # Não falhar se alguns pacotes opcionais falharem
                capture_output=True
            )
            
            print("✅ Dependências instaladas")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao instalar dependências: {e}")
            self.errors.append(str(e))
            return False
    
    def instalar_playwright(self) -> bool:
        """Instala browsers do Playwright"""
        print("\n🌐 Instalando navegadores Playwright...")
        
        python_cmd = self.get_python_command()
        
        try:
            # Instalar chromium
            print("   📥 Baixando Chromium...")
            subprocess.run(
                [python_cmd, "-m", "playwright", "install", "chromium"],
                check=True
            )
            
            # Instalar dependências do sistema se necessário
            if self.sistema == "Linux":
                print("   📥 Instalando dependências do sistema...")
                subprocess.run(
                    [python_cmd, "-m", "playwright", "install-deps"],
                    check=False  # Pode falhar se não tiver sudo
                )
            
            print("✅ Navegadores instalados")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao instalar navegadores: {e}")
            self.errors.append(str(e))
            return False
    
    def criar_estrutura_diretorios(self) -> bool:
        """Cria estrutura de diretórios necessária"""
        print("\n📁 Criando estrutura de diretórios...")
        
        diretorios = [
            "dados",
            "logs",
            "cache",
            "screenshots_erro",
            "relatorios",
            "config",
            "estados/sp/dados",
            "estados/sp/logs",
            "estados/sp/cache",
            "estados/sp/prints"
        ]
        
        try:
            for dir_path in diretorios:
                (self.root_dir / dir_path).mkdir(parents=True, exist_ok=True)
                print(f"   ✅ {dir_path}")
            
            print("✅ Estrutura criada")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao criar diretórios: {e}")
            self.errors.append(str(e))
            return False
    
    def criar_config_padrao(self) -> bool:
        """Cria arquivo de configuração padrão"""
        print("\n⚙️ Criando configuração padrão...")
        
        config_file = self.root_dir / "config" / "config.json"
        
        config_padrao = {
            "headless": True,
            "max_workers": 3,
            "timeout_padrao": 30000,
            "usar_cache": True,
            "salvar_screenshots_erro": True,
            "gerar_relatorio_html": True,
            "exportar_json": True,
            "exportar_csv": True,
            "calcular_estatisticas": True,
            "notificar_desktop": True,
            "notificar_email": False,
            "notificar_telegram": False,
            "notificar_webhook": False
        }
        
        try:
            with open(config_file, 'w') as f:
                json.dump(config_padrao, f, indent=2)
            
            print("✅ Configuração criada")
            print(f"   📄 {config_file}")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao criar configuração: {e}")
            self.errors.append(str(e))
            return False
    
    def criar_scripts_atalho(self) -> bool:
        """Cria scripts de atalho para execução"""
        print("\n🚀 Criando scripts de atalho...")
        
        try:
            # Script para Windows
            if self.sistema == "Windows":
                bat_content = f"""@echo off
cd /d "{self.root_dir}"
call venv\\Scripts\\activate
python tjsp_executor.py %*
pause
"""
                bat_file = self.root_dir / "executar.bat"
                with open(bat_file, 'w') as f:
                    f.write(bat_content)
                print(f"   ✅ executar.bat criado")
                
                # PowerShell
                ps1_content = f"""
Set-Location "{self.root_dir}"
& .\\venv\\Scripts\\Activate.ps1
python tjsp_executor.py $args
Read-Host "Pressione Enter para continuar..."
"""
                ps1_file = self.root_dir / "executar.ps1"
                with open(ps1_file, 'w') as f:
                    f.write(ps1_content)
                print(f"   ✅ executar.ps1 criado")
            
            # Script para Linux/Mac
            else:
                sh_content = f"""#!/bin/bash
cd "{self.root_dir}"
source venv/bin/activate
python tjsp_executor.py "$@"
"""
                sh_file = self.root_dir / "executar.sh"
                with open(sh_file, 'w') as f:
                    f.write(sh_content)
                
                # Tornar executável
                os.chmod(sh_file, 0o755)
                print(f"   ✅ executar.sh criado")
            
            return True
            
        except Exception as e:
            print(f"❌ Erro ao criar scripts: {e}")
            self.errors.append(str(e))
            return False
    
    def verificar_instalacao(self) -> bool:
        """Verifica se a instalação foi bem sucedida"""
        print("\n🔍 Verificando instalação...")
        
        python_cmd = self.get_python_command()
        
        # Testar imports principais
        imports_teste = [
            "playwright",
            "pandas",
            "aiohttp",
            "matplotlib"
        ]
        
        todos_ok = True
        for modulo in imports_teste:
            try:
                subprocess.run(
                    [python_cmd, "-c", f"import {modulo}"],
                    check=True,
                    capture_output=True
                )
                print(f"   ✅ {modulo}")
            except:
                print(f"   ❌ {modulo}")
                todos_ok = False
        
        return todos_ok
    
    def exibir_instrucoes(self):
        """Exibe instruções de uso"""
        print("\n" + "="*60)
        print("✅ INSTALAÇÃO CONCLUÍDA!")
        print("="*60)
        
        print("\n📚 COMO USAR:")
        print("-"*40)
        
        if self.sistema == "Windows":
            print("\n1. Executar com interface:")
            print("   Dê duplo clique em: executar.bat")
            print("\n2. Executar via terminal:")
            print("   > venv\\Scripts\\activate")
            print("   > python tjsp_executor.py 00.000.000/0001-00")
        else:
            print("\n1. Executar com interface:")
            print("   $ ./executar.sh 00.000.000/0001-00")
            print("\n2. Executar via terminal:")
            print("   $ source venv/bin/activate")
            print("   $ python tjsp_executor.py 00.000.000/0001-00")
        
        print("\n📋 OPÇÕES PRINCIPAIS:")
        print("   --help           Mostrar ajuda completa")
        print("   --config         Mostrar configuração")
        print("   --analise        Analisar dados existentes")
        print("   -1 -2 -c         Selecionar instâncias")
        
        print("\n📁 ESTRUTURA:")
        print("   dados/           Arquivos Excel gerados")
        print("   logs/            Logs de execução")
        print("   relatorios/      Relatórios HTML")
        print("   config/          Configurações")
        
        print("\n💡 DICAS:")
        print("   • Edite config/config.json para personalizar")
        print("   • Use --debug para logs detalhados")
        print("   • Relatórios HTML são gerados automaticamente")
        
        print("\n" + "="*60)
    
    def executar(self) -> bool:
        """Executa instalação completa"""
        self.print_header()
        
        # Verificações
        if not self.verificar_python():
            return False
        
        # Instalação
        etapas = [
            ("Ambiente Virtual", self.criar_ambiente_virtual),
            ("Dependências", self.instalar_dependencias),
            ("Playwright", self.instalar_playwright),
            ("Diretórios", self.criar_estrutura_diretorios),
            ("Configuração", self.criar_config_padrao),
            ("Scripts", self.criar_scripts_atalho),
            ("Verificação", self.verificar_instalacao)
        ]
        
        for nome, funcao in etapas:
            if not funcao():
                print(f"\n❌ Falha na etapa: {nome}")
                if self.errors:
                    print("\nErros encontrados:")
                    for erro in self.errors:
                        print(f"  • {erro}")
                return False
        
        self.exibir_instrucoes()
        return True


def main():
    """Função principal"""
    setup = TJSPSetup()
    
    try:
        sucesso = setup.executar()
        sys.exit(0 if sucesso else 1)
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Instalação cancelada pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()