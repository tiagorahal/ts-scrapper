import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime
import threading
import queue
import select

scripts = [
    "tjsp_primeira_instancia.py",
    "tjsp_segunda_instancia.py",
    "tjsp_colegio_recursal.py",
]

def validar_cnpj(cnpj):
    """Valida e formata o CNPJ"""
    cnpj_limpo = ''.join(filter(str.isdigit, cnpj))
    if len(cnpj_limpo) != 14:
        return None
    return cnpj_limpo

def criar_pasta_dados():
    """Garante que a pasta dados existe"""
    dados_dir = Path(__file__).parent / "dados"
    dados_dir.mkdir(exist_ok=True)
    return dados_dir

def criar_arquivos_vazios_se_necessario(dados_dir):
    """Cria arquivos Excel vazios se não existirem"""
    import pandas as pd
    
    arquivos_esperados = {
        "primeira_instancia_tjsp.xlsx": "1ª Instância",
        "segunda_instancia_tjsp.xlsx": "2ª Instância",
        "colegio_recursal_tjsp.xlsx": "Colégio Recursal"
    }
    
    campos_padrao = [
        "instancia", "numero", "link", "classe", "assunto", "relator", 
        "outros_numeros", "origem", "volume_apenso", "ultima_carga", 
        "foro", "vara", "juiz", "requerente", "requerido", "polo_terceiro",
        "audiencia", "julgamento", "distribuicao", "controle", "area", 
        "valor_acao", "movimentacoes", "movimentacoes_detalhe"
    ]
    
    for arquivo, instancia in arquivos_esperados.items():
        caminho = dados_dir / arquivo
        if not caminho.exists():
            print(f"📄 Criando arquivo vazio: {arquivo}")
            df_vazio = pd.DataFrame(columns=campos_padrao)
            df_vazio.to_excel(caminho, index=False)
            print(f"   ✅ {arquivo} criado com sucesso!")

def ler_output_processo(proc, nome_script, fila_mensagens):
    """Lê output de um processo em tempo real"""
    while True:
        linha = proc.stdout.readline()
        if not linha:
            break
        linha = linha.strip()
        if linha:
            fila_mensagens.put((nome_script, linha))
    
    # Lê stderr também
    stderr = proc.stderr.read()
    if stderr:
        fila_mensagens.put((nome_script, f"ERRO: {stderr}"))

def mostrar_resumo_final(dados_dir, tempo_total, processos_capturados):
    """Mostra resumo dos arquivos gerados"""
    print("\n" + "="*60)
    print("RESUMO DA EXECUÇÃO")
    print("="*60)
    print(f"Tempo total: {tempo_total:.1f} segundos")
    print(f"\nArquivos gerados em: {dados_dir}")
    
    # Mostra total de processos capturados
    print("\n📊 Processos capturados:")
    for script, count in processos_capturados.items():
        print(f"   {script}: {count} processos")
    
    # Lista arquivos Excel gerados
    arquivos_esperados = [
        "primeira_instancia_tjsp.xlsx",
        "segunda_instancia_tjsp.xlsx",
        "colegio_recursal_tjsp.xlsx"
    ]
    
    print("\nArquivos:")
    for arquivo in arquivos_esperados:
        caminho = dados_dir / arquivo
        if caminho.exists():
            tamanho = caminho.stat().st_size / 1024  # KB
            print(f"  ✅ {arquivo} ({tamanho:.1f} KB)")
        else:
            print(f"  ❌ {arquivo} (não encontrado)")

def main():
    print("="*60)
    print("TJSP - EXTRATOR DE PROCESSOS (COM LOGS)")
    print("="*60)
    
    # Criar pasta dados
    dados_dir = criar_pasta_dados()
    
    # Verificar e criar arquivos vazios se necessário
    print("\n📁 Verificando estrutura de arquivos...")
    criar_arquivos_vazios_se_necessario(dados_dir)
    
    # Solicitar CNPJ
    while True:
        cnpj = input("\nDigite o CNPJ (com ou sem máscara): ").strip()
        cnpj_validado = validar_cnpj(cnpj)
        
        if cnpj_validado:
            cnpj_formatado = f"{cnpj_validado[:2]}.{cnpj_validado[2:5]}.{cnpj_validado[5:8]}/{cnpj_validado[8:12]}-{cnpj_validado[12:]}"
            print(f"✅ CNPJ válido: {cnpj_formatado}")
            break
        else:
            print("❌ CNPJ inválido! Digite exatamente 14 números.")
    
    # Confirmar execução
    print(f"\nSerão executados {len(scripts)} scripts em paralelo:")
    for script in scripts:
        print(f"  • {script}")
    
    print("\n💡 Os logs serão mostrados em tempo real!")
    
    resposta = input("\nDeseja continuar? (S/n): ").strip().lower()
    if resposta == 'n':
        print("Operação cancelada.")
        return
    
    # Executar scripts
    inicio = time.time()
    processes = []
    threads = []
    fila_mensagens = queue.Queue()
    processos_capturados = {script: 0 for script in scripts}
    
    print(f"\n🚀 Iniciando execução em {datetime.now().strftime('%H:%M:%S')}")
    print("-"*60)
    
    for script in scripts:
        print(f"▶️  Iniciando {script}...")
        try:
            p = subprocess.Popen(
                [sys.executable, script, cnpj],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            processes.append((script, p))
            
            # Cria thread para ler output
            t = threading.Thread(
                target=ler_output_processo,
                args=(p, script, fila_mensagens)
            )
            t.daemon = True
            t.start()
            threads.append(t)
            
        except Exception as e:
            print(f"❌ Erro ao iniciar {script}: {e}")
    
    print("\n📋 Logs em tempo real:")
    print("-"*60)
    
    # Monitora mensagens enquanto os processos rodam
    processos_ativos = len(processes)
    while processos_ativos > 0:
        # Verifica se há mensagens na fila
        try:
            script, mensagem = fila_mensagens.get(timeout=0.1)
            
            # Formata e mostra a mensagem
            timestamp = datetime.now().strftime('%H:%M:%S')
            script_curto = script.replace('tjsp_', '').replace('.py', '')
            
            # Conta processos salvos
            if "✅ Resultado salvo:" in mensagem:
                processos_capturados[script] += 1
                print(f"[{timestamp}] [{script_curto:>15}] {mensagem}")
            elif "🔍 Extraindo" in mensagem or "⏳ Aguarde" in mensagem:
                print(f"[{timestamp}] [{script_curto:>15}] {mensagem}")
            elif "=====" in mensagem:
                print(f"[{timestamp}] [{script_curto:>15}] {mensagem}")
            elif mensagem.strip():
                print(f"[{timestamp}] [{script_curto:>15}] {mensagem}")
                
        except queue.Empty:
            pass
        
        # Verifica quais processos ainda estão rodando
        processos_ativos = 0
        for script, proc in processes:
            if proc.poll() is None:
                processos_ativos += 1
    
    print("-"*60)
    print("✅ Todos os processos foram finalizados!")
    
    # Aguarda threads terminarem
    for t in threads:
        t.join(timeout=1)
    
    # Verifica erros
    erros = []
    for script, proc in processes:
        if proc.returncode != 0:
            erros.append((script, proc.returncode))
    
    # Calcular tempo total
    tempo_total = time.time() - inicio
    
    # Mostrar resumo
    mostrar_resumo_final(dados_dir, tempo_total, processos_capturados)
    
    if not erros:
        print("\n✅ Todos os scripts foram executados com sucesso!")
    else:
        print(f"\n⚠️  {len(erros)} script(s) apresentaram erros:")
        for script, code in erros:
            print(f"   - {script} (código {code})")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Operação interrompida pelo usuário.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        sys.exit(1)