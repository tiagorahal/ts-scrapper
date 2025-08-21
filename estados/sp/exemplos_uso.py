#!/usr/bin/env python3
"""
Exemplos de uso avançado do TJSP Scraper v2.0
Demonstra as capacidades do sistema e casos de uso
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import json

# Adicionar diretório do projeto ao path
sys.path.insert(0, str(Path(__file__).parent))

from config import get_config_manager
from notificador import GerenciadorNotificacoes
from analisador import AnalisadorTJSP
from tjsp_executor import TJSPOrquestrador

class ExemplosAvancados:
    """Exemplos de uso avançado do sistema"""
    
    def __init__(self):
        self.config_manager = get_config_manager()
        self.dados_dir = Path("dados")
    
    async def exemplo_basico(self):
        """Exemplo básico de busca"""
        print("\n" + "="*60)
        print("EXEMPLO 1: Busca Básica")
        print("="*60)
        
        cnpj = "11.222.333/0001-81"  # CNPJ de exemplo
        
        orquestrador = TJSPOrquestrador()
        await orquestrador.executar(cnpj, ['primeira'])
        
        print("✅ Busca básica concluída!")
    
    async def exemplo_multiplas_instancias(self):
        """Busca em múltiplas instâncias simultaneamente"""
        print("\n" + "="*60)
        print("EXEMPLO 2: Múltiplas Instâncias")
        print("="*60)
        
        cnpj = "11.222.333/0001-81"
        
        # Configurar para execução paralela
        self.config_manager.update_config(max_workers=3)
        
        orquestrador = TJSPOrquestrador()
        await orquestrador.executar(cnpj, ['primeira', 'segunda', 'colegio'])
        
        print("✅ Busca em múltiplas instâncias concluída!")
    
    async def exemplo_com_notificacoes(self):
        """Exemplo com notificações configuradas"""
        print("\n" + "="*60)
        print("EXEMPLO 3: Com Notificações")
        print("="*60)
        
        # Configurar notificações
        self.config_manager.update_config(
            notificar_desktop=True,
            notificar_email=False,  # Configure suas credenciais
            gerar_relatorio_html=True
        )
        
        cnpj = "11.222.333/0001-81"
        
        orquestrador = TJSPOrquestrador()
        await orquestrador.executar(cnpj, ['primeira'])
        
        print("✅ Execução com notificações concluída!")
    
    def exemplo_analise_dados(self):
        """Análise avançada de dados extraídos"""
        print("\n" + "="*60)
        print("EXEMPLO 4: Análise de Dados")
        print("="*60)
        
        analisador = AnalisadorTJSP(self.dados_dir)
        
        # Carregar e analisar dados
        if analisador.carregar_dados():
            estatisticas = analisador.analisar_completo()
            
            # Exibir insights
            print("\n💡 Insights Gerados:")
            for insight in analisador.insights:
                print(f"  • {insight}")
            
            # Gerar relatório HTML
            relatorio = analisador.gerar_relatorio_html()
            print(f"\n📊 Relatório gerado: {relatorio}")
            
            # Exportar para JSON
            json_export = analisador.exportar_json()
            print(f"📄 JSON exportado: {json_export}")
        else:
            print("⚠️ Nenhum dado encontrado para análise")
    
    def exemplo_processamento_lote(self):
        """Processar múltiplos CNPJs em lote"""
        print("\n" + "="*60)
        print("EXEMPLO 5: Processamento em Lote")
        print("="*60)
        
        # Lista de CNPJs para processar
        cnpjs = [
            "11.222.333/0001-81",
            "44.555.666/0001-77",
            "77.888.999/0001-33"
        ]
        
        async def processar_lote():
            for i, cnpj in enumerate(cnpjs, 1):
                print(f"\n📋 Processando {i}/{len(cnpjs)}: {cnpj}")
                
                orquestrador = TJSPOrquestrador()
                await orquestrador.executar(cnpj, ['primeira'])
                
                # Delay entre CNPJs para evitar sobrecarga
                if i < len(cnpjs):
                    print("⏳ Aguardando 30 segundos...")
                    await asyncio.sleep(30)
            
            print("\n✅ Lote processado com sucesso!")
        
        asyncio.run(processar_lote())
    
    def exemplo_monitoramento_continuo(self):
        """Monitoramento contínuo com execuções periódicas"""
        print("\n" + "="*60)
        print("EXEMPLO 6: Monitoramento Contínuo")
        print("="*60)
        
        cnpj = "11.222.333/0001-81"
        intervalo_horas = 24  # Executar a cada 24 horas
        
        async def monitorar():
            execucoes = 0
            
            while True:
                execucoes += 1
                print(f"\n🔄 Execução #{execucoes} - {datetime.now()}")
                
                orquestrador = TJSPOrquestrador()
                await orquestrador.executar(cnpj, ['primeira', 'segunda'])
                
                # Analisar mudanças
                self.detectar_novos_processos()
                
                print(f"⏰ Próxima execução em {intervalo_horas} horas...")
                await asyncio.sleep(intervalo_horas * 3600)
        
        try:
            asyncio.run(monitorar())
        except KeyboardInterrupt:
            print("\n⚠️ Monitoramento interrompido")
    
    def detectar_novos_processos(self):
        """Detecta novos processos desde última execução"""
        historico_file = self.dados_dir / "historico_processos.json"
        
        # Carregar histórico
        historico_anterior = {}
        if historico_file.exists():
            with open(historico_file, 'r') as f:
                historico_anterior = json.load(f)
        
        # Processar arquivos atuais
        historico_atual = {}
        novos_processos = []
        
        for arquivo in self.dados_dir.glob("*.xlsx"):
            if "tjsp" in arquivo.name:
                df = pd.read_excel(arquivo)
                if 'numero' in df.columns:
                    processos = set(df['numero'].dropna().unique())
                    historico_atual[arquivo.name] = list(processos)
                    
                    # Comparar com histórico
                    if arquivo.name in historico_anterior:
                        processos_anteriores = set(historico_anterior[arquivo.name])
                        novos = processos - processos_anteriores
                        
                        if novos:
                            novos_processos.extend(novos)
                            print(f"🆕 {len(novos)} novos processos em {arquivo.name}")
        
        # Salvar novo histórico
        with open(historico_file, 'w') as f:
            json.dump(historico_atual, f, indent=2)
        
        if novos_processos:
            print(f"\n📢 Total de {len(novos_processos)} novos processos detectados!")
            
            # Notificar sobre novos processos
            # Aqui você poderia enviar um email ou notificação
        
        return novos_processos
    
    def exemplo_exportacao_customizada(self):
        """Exportação de dados em formatos customizados"""
        print("\n" + "="*60)
        print("EXEMPLO 7: Exportação Customizada")
        print("="*60)
        
        # Consolidar todos os dados
        todos_dados = []
        
        for arquivo in self.dados_dir.glob("*_tjsp.xlsx"):
            df = pd.read_excel(arquivo)
            todos_dados.append(df)
        
        if todos_dados:
            df_consolidado = pd.concat(todos_dados, ignore_index=True)
            
            # Exportar para diferentes formatos
            
            # 1. CSV com encoding UTF-8
            csv_file = self.dados_dir / f"consolidado_{datetime.now().strftime('%Y%m%d')}.csv"
            df_consolidado.to_csv(csv_file, index=False, encoding='utf-8-sig')
            print(f"✅ CSV exportado: {csv_file}")
            
            # 2. JSON estruturado
            json_file = self.dados_dir / f"consolidado_{datetime.now().strftime('%Y%m%d')}.json"
            df_consolidado.to_json(
                json_file,
                orient='records',
                date_format='iso',
                force_ascii=False,
                indent=2
            )
            print(f"✅ JSON exportado: {json_file}")
            
            # 3. Parquet (formato eficiente)
            try:
                parquet_file = self.dados_dir / f"consolidado_{datetime.now().strftime('%Y%m%d')}.parquet"
                df_consolidado.to_parquet(parquet_file, compression='snappy')
                print(f"✅ Parquet exportado: {parquet_file}")
            except:
                print("⚠️ Parquet requer pyarrow ou fastparquet")
            
            # 4. Excel com múltiplas abas
            excel_file = self.dados_dir / f"relatorio_completo_{datetime.now().strftime('%Y%m%d')}.xlsx"
            with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
                # Aba com todos os dados
                df_consolidado.to_excel(writer, sheet_name='Todos', index=False)
                
                # Aba por instância
                for instancia in df_consolidado['instancia'].unique():
                    df_inst = df_consolidado[df_consolidado['instancia'] == instancia]
                    sheet_name = instancia[:30]  # Limitar nome da aba
                    df_inst.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # Aba de estatísticas
                stats_df = pd.DataFrame({
                    'Métrica': [
                        'Total de Processos',
                        'Instâncias Únicas',
                        'Classes Únicas',
                        'Período de Dados'
                    ],
                    'Valor': [
                        len(df_consolidado),
                        df_consolidado['instancia'].nunique(),
                        df_consolidado['classe'].nunique() if 'classe' in df_consolidado else 0,
                        f"{df_consolidado['distribuicao'].min()} a {df_consolidado['distribuicao'].max()}"
                        if 'distribuicao' in df_consolidado else 'N/A'
                    ]
                })
                stats_df.to_excel(writer, sheet_name='Estatísticas', index=False)
            
            print(f"✅ Excel completo exportado: {excel_file}")
        else:
            print("⚠️ Nenhum dado encontrado para exportar")
    
    def exemplo_filtros_avancados(self):
        """Aplicar filtros avançados nos dados"""
        print("\n" + "="*60)
        print("EXEMPLO 8: Filtros Avançados")
        print("="*60)
        
        # Carregar dados
        df_list = []
        for arquivo in self.dados_dir.glob("*_tjsp.xlsx"):
            df_list.append(pd.read_excel(arquivo))
        
        if df_list:
            df = pd.concat(df_list, ignore_index=True)
            
            print(f"📊 Total de processos: {len(df)}")
            
            # Filtro 1: Processos com valor acima de R$ 100.000
            if 'valor_acao' in df.columns:
                df['valor_numerico'] = df['valor_acao'].apply(self.extrair_valor)
                df_alto_valor = df[df['valor_numerico'] > 100000]
                print(f"\n💰 Processos acima de R$ 100.000: {len(df_alto_valor)}")
                
                if not df_alto_valor.empty:
                    print("   Top 5 maiores valores:")
                    top5 = df_alto_valor.nlargest(5, 'valor_numerico')[['numero', 'valor_numerico']]
                    for _, row in top5.iterrows():
                        print(f"   • {row['numero']}: R$ {row['valor_numerico']:,.2f}")
            
            # Filtro 2: Processos por classe específica
            if 'classe' in df.columns:
                classes_interesse = ['Execução', 'Procedimento Comum', 'Monitória']
                df_classes = df[df['classe'].str.contains('|'.join(classes_interesse), na=False)]
                print(f"\n⚖️ Processos das classes de interesse: {len(df_classes)}")
            
            # Filtro 3: Processos dos últimos 30 dias
            if 'data_extracao' in df.columns:
                df['data_extracao_dt'] = pd.to_datetime(df['data_extracao'])
                data_limite = datetime.now() - timedelta(days=30)
                df_recentes = df[df['data_extracao_dt'] > data_limite]
                print(f"\n📅 Processos extraídos nos últimos 30 dias: {len(df_recentes)}")
            
            # Salvar resultados filtrados
            if len(df_alto_valor) > 0:
                filtro_file = self.dados_dir / "processos_alto_valor.xlsx"
                df_alto_valor.to_excel(filtro_file, index=False)
                print(f"\n✅ Processos filtrados salvos em: {filtro_file}")
        else:
            print("⚠️ Nenhum dado encontrado")
    
    def extrair_valor(self, valor_str):
        """Extrai valor numérico de string"""
        if pd.isna(valor_str):
            return 0.0
        
        import re
        valor_str = str(valor_str)
        valor_str = re.sub(r'[^\d,.]', '', valor_str)
        valor_str = valor_str.replace('.', '').replace(',', '.')
        
        try:
            return float(valor_str)
        except:
            return 0.0


class TestesAutomatizados:
    """Testes automatizados do sistema"""
    
    @staticmethod
    async def teste_validacao_cnpj():
        """Testa validação de CNPJ"""
        print("\n🧪 Teste: Validação de CNPJ")
        
        orquestrador = TJSPOrquestrador()
        
        # CNPJs de teste
        testes = [
            ("11.222.333/0001-81", True),   # Válido
            ("11222333000181", True),       # Válido sem máscara
            ("11.222.333/0001-82", False),  # Dígito inválido
            ("123", False),                 # Muito curto
            ("abcd", False),                # Letras
        ]
        
        passou = 0
        for cnpj, esperado in testes:
            resultado = orquestrador.validar_cnpj(cnpj) is not None
            if resultado == esperado:
                print(f"  ✅ {cnpj}: {'Válido' if resultado else 'Inválido'}")
                passou += 1
            else:
                print(f"  ❌ {cnpj}: Esperado {'válido' if esperado else 'inválido'}")
        
        print(f"\nResultado: {passou}/{len(testes)} testes passaram")
    
    @staticmethod
    async def teste_configuracao():
        """Testa sistema de configuração"""
        print("\n🧪 Teste: Sistema de Configuração")
        
        config_manager = get_config_manager()
        
        # Teste 1: Carregar configuração
        config = config_manager.get_config()
        print(f"  ✅ Configuração carregada: {config.headless=}")
        
        # Teste 2: Atualizar configuração
        config_manager.update_config(max_workers=5)
        assert config_manager.get_config().max_workers == 5
        print(f"  ✅ Configuração atualizada: max_workers=5")
        
        # Teste 3: Validar configuração
        is_valid = config_manager.validate_config()
        print(f"  ✅ Validação: {'Válida' if is_valid else 'Inválida'}")
        
        print("\nTodos os testes de configuração passaram!")
    
    @staticmethod
    async def teste_notificacoes():
        """Testa sistema de notificações"""
        print("\n🧪 Teste: Sistema de Notificações")
        
        config_notif = {
            'notificar_desktop': True,
            'notificar_email': False,
            'notificar_telegram': False,
            'notificar_webhook': False
        }
        
        gerenciador = GerenciadorNotificacoes(config_notif)
        
        # Teste de notificação desktop
        await gerenciador.notificar_inicio("11.222.333/0001-81", ["primeira", "segunda"])
        print("  ✅ Notificação de início enviada")
        
        await asyncio.sleep(2)
        
        await gerenciador.notificar_conclusao(
            {'teste': {'processos_extraidos': 10, 'tempo_inicio': datetime.now()}},
            []
        )
        print("  ✅ Notificação de conclusão enviada")
        
        print("\nTestes de notificação concluídos!")


async def menu_principal():
    """Menu principal de exemplos"""
    exemplos = ExemplosAvancados()
    testes = TestesAutomatizados()
    
    while True:
        print("\n" + "="*60)
        print("🏛️ TJSP SCRAPER v2.0 - EXEMPLOS E TESTES")
        print("="*60)
        print("\nEXEMPLOS:")
        print("1. Busca básica")
        print("2. Múltiplas instâncias")
        print("3. Com notificações")
        print("4. Análise de dados")
        print("5. Processamento em lote")
        print("6. Monitoramento contínuo")
        print("7. Exportação customizada")
        print("8. Filtros avançados")
        print("\nTESTES:")
        print("9. Validação de CNPJ")
        print("10. Sistema de configuração")
        print("11. Sistema de notificações")
        print("\n0. Sair")
        
        try:
            opcao = input("\nEscolha uma opção: ").strip()
            
            if opcao == "0":
                print("Saindo...")
                break
            elif opcao == "1":
                await exemplos.exemplo_basico()
            elif opcao == "2":
                await exemplos.exemplo_multiplas_instancias()
            elif opcao == "3":
                await exemplos.exemplo_com_notificacoes()
            elif opcao == "4":
                exemplos.exemplo_analise_dados()
            elif opcao == "5":
                exemplos.exemplo_processamento_lote()
            elif opcao == "6":
                exemplos.exemplo_monitoramento_continuo()
            elif opcao == "7":
                exemplos.exemplo_exportacao_customizada()
            elif opcao == "8":
                exemplos.exemplo_filtros_avancados()
            elif opcao == "9":
                await testes.teste_validacao_cnpj()
            elif opcao == "10":
                await testes.teste_configuracao()
            elif opcao == "11":
                await testes.teste_notificacoes()
            else:
                print("❌ Opção inválida!")
            
            input("\nPressione Enter para continuar...")
            
        except KeyboardInterrupt:
            print("\n\nSaindo...")
            break
        except Exception as e:
            print(f"\n❌ Erro: {e}")
            input("\nPressione Enter para continuar...")


if __name__ == "__main__":
    try:
        asyncio.run(menu_principal())
    except KeyboardInterrupt:
        print("\n\nPrograma encerrado.")
    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()