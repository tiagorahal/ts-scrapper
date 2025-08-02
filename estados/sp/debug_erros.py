#!/usr/bin/env python3
"""
Script para fazer debug detalhado dos erros
"""

import subprocess
import sys
from pathlib import Path
import ast

def verificar_sintaxe_arquivo(arquivo):
    """Verifica a sintaxe de um arquivo Python"""
    print(f"\n🔍 Verificando {arquivo}...")
    
    if not Path(arquivo).exists():
        print(f"   ❌ Arquivo não encontrado!")
        return False
    
    try:
        with open(arquivo, 'r', encoding='utf-8') as f:
            conteudo = f.read()
            
        # Verifica se há BOM no início
        if conteudo.startswith('\ufeff'):
            print(f"   ⚠️  Arquivo contém BOM (Byte Order Mark)")
            conteudo = conteudo[1:]
            
        # Tenta fazer parse do arquivo
        ast.parse(conteudo)
        print(f"   ✅ Sintaxe OK")
        
        # Verifica primeiras linhas
        primeiras_linhas = conteudo.split('\n')[:5]
        print(f"   📄 Primeiras linhas:")
        for i, linha in enumerate(primeiras_linhas, 1):
            print(f"      {i}: {repr(linha)}")
            
        return True
        
    except SyntaxError as e:
        print(f"   ❌ Erro de sintaxe na linha {e.lineno}:")
        print(f"      {e.msg}")
        print(f"      Linha: {repr(e.text) if e.text else 'N/A'}")
        return False
    except Exception as e:
        print(f"   ❌ Erro ao verificar: {e}")
        return False

def executar_teste_direto(arquivo):
    """Tenta executar o arquivo diretamente para capturar erro completo"""
    print(f"\n🧪 Testando execução direta de {arquivo}...")
    
    # Cria um CNPJ de teste
    cnpj_teste = "00000000000191"
    
    try:
        # Executa com um import teste primeiro
        result = subprocess.run(
            [sys.executable, "-c", f"import sys; sys.path.insert(0, '.'); import {arquivo[:-3]}"],
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        
        if result.returncode != 0:
            print(f"   ❌ Erro ao importar módulo:")
            print(f"      STDOUT: {result.stdout}")
            print(f"      STDERR: {result.stderr}")
            return False
        else:
            print(f"   ✅ Import OK")
            
        # Tenta executar com argumento
        result = subprocess.run(
            [sys.executable, arquivo, cnpj_teste],
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=5  # timeout de 5 segundos
        )
        
        print(f"   Return code: {result.returncode}")
        if result.stdout:
            print(f"   STDOUT: {result.stdout[:200]}...")
        if result.stderr:
            print(f"   STDERR: {result.stderr[:500]}...")
            
    except subprocess.TimeoutExpired:
        print(f"   ⏱️  Timeout - script demorou mais de 5 segundos")
    except Exception as e:
        print(f"   ❌ Erro na execução: {e}")

def verificar_encoding(arquivo):
    """Verifica o encoding do arquivo"""
    print(f"\n🔤 Verificando encoding de {arquivo}...")
    
    encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
    
    for enc in encodings:
        try:
            with open(arquivo, 'r', encoding=enc) as f:
                f.read()
            print(f"   ✅ Arquivo pode ser lido com encoding: {enc}")
            return enc
        except:
            continue
    
    print(f"   ❌ Não foi possível determinar o encoding")
    return None

def limpar_arquivo(arquivo):
    """Cria uma versão limpa do arquivo"""
    print(f"\n🧹 Criando versão limpa de {arquivo}...")
    
    try:
        # Lê o arquivo com encoding detectado
        enc = verificar_encoding(arquivo)
        if not enc:
            return False
            
        with open(arquivo, 'r', encoding=enc) as f:
            conteudo = f.read()
        
        # Remove BOM se existir
        if conteudo.startswith('\ufeff'):
            conteudo = conteudo[1:]
        
        # Salva backup
        backup = f"{arquivo}.backup"
        Path(arquivo).rename(backup)
        print(f"   📁 Backup salvo em: {backup}")
        
        # Salva versão limpa
        with open(arquivo, 'w', encoding='utf-8') as f:
            f.write(conteudo)
        
        print(f"   ✅ Arquivo limpo salvo")
        return True
        
    except Exception as e:
        print(f"   ❌ Erro ao limpar arquivo: {e}")
        return False

def main():
    print("="*60)
    print("DEBUG DETALHADO - TJSP SCRAPER")
    print("="*60)
    
    scripts = [
        "tjsp_primeira_instancia.py",
        "tjsp_segunda_instancia.py",
        "tjsp_colegio_recursal.py"
    ]
    
    problemas = []
    
    for script in scripts:
        print(f"\n{'='*60}")
        print(f"Analisando: {script}")
        print(f"{'='*60}")
        
        # 1. Verifica sintaxe
        sintaxe_ok = verificar_sintaxe_arquivo(script)
        
        # 2. Verifica encoding
        verificar_encoding(script)
        
        # 3. Tenta executar
        executar_teste_direto(script)
        
        if not sintaxe_ok:
            problemas.append(script)
    
    # Resumo e sugestões
    print(f"\n{'='*60}")
    print("RESUMO E SUGESTÕES")
    print(f"{'='*60}")
    
    if problemas:
        print(f"\n❌ Arquivos com problemas: {', '.join(problemas)}")
        print("\n💡 Sugestões:")
        print("1. Limpar os arquivos com problema:")
        for script in problemas:
            print(f"   python debug_erros.py --limpar {script}")
        print("\n2. Ou recriar os arquivos copiando o conteúdo dos artifacts")
    else:
        print("\n✅ Todos os arquivos parecem estar OK")
        print("   O erro pode estar relacionado ao ambiente de execução")
    
    # Verifica versão do asyncio
    print(f"\n📦 Ambiente:")
    print(f"   Python: {sys.version}")
    try:
        import asyncio
        print(f"   asyncio: OK")
    except:
        print(f"   asyncio: NÃO DISPONÍVEL")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--limpar', help='Limpa um arquivo específico')
    args = parser.parse_args()
    
    if args.limpar:
        limpar_arquivo(args.limpar)
    else:
        main()