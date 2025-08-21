"""
Sistema de análise avançada de dados extraídos do TJSP
Gera relatórios, estatísticas e visualizações
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import json
import re
from typing import Dict, List, Tuple, Optional, Any
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
import logging

# Configurar matplotlib para não mostrar GUI
plt.switch_backend('Agg')

class AnalisadorTJSP:
    """Analisador avançado de processos do TJSP"""
    
    def __init__(self, caminho_dados: Path):
        self.caminho_dados = Path(caminho_dados)
        self.logger = logging.getLogger("AnalisadorTJSP")
        self.dados = {}
        self.estatisticas = {}
        self.insights = []
        
        # Configurar estilo dos gráficos
        sns.set_style("whitegrid")
        sns.set_palette("husl")
    
    def carregar_dados(self) -> bool:
        """Carrega todos os dados disponíveis"""
        arquivos = {
            'primeira_instancia': 'primeira_instancia_tjsp.xlsx',
            'segunda_instancia': 'segunda_instancia_tjsp.xlsx',
            'colegio_recursal': 'colegio_recursal_tjsp.xlsx'
        }
        
        for key, arquivo in arquivos.items():
            caminho = self.caminho_dados / arquivo
            if caminho.exists():
                try:
                    df = pd.read_excel(caminho)
                    self.dados[key] = df
                    self.logger.info(f"✅ Carregado {arquivo}: {len(df)} processos")
                except Exception as e:
                    self.logger.error(f"❌ Erro ao carregar {arquivo}: {e}")
                    self.dados[key] = pd.DataFrame()
            else:
                self.logger.warning(f"⚠️ Arquivo não encontrado: {arquivo}")
                self.dados[key] = pd.DataFrame()
        
        return any(not df.empty for df in self.dados.values())
    
    def analisar_completo(self) -> Dict[str, Any]:
        """Executa análise completa dos dados"""
        if not self.carregar_dados():
            self.logger.error("❌ Nenhum dado para analisar")
            return {}
        
        self.logger.info("🔍 Iniciando análise completa...")
        
        # Análises básicas
        self.estatisticas['basicas'] = self.analise_basica()
        
        # Análises temporais
        self.estatisticas['temporal'] = self.analise_temporal()
        
        # Análise de partes
        self.estatisticas['partes'] = self.analise_partes()
        
        # Análise de valores
        self.estatisticas['valores'] = self.analise_valores()
        
        # Análise de classes e assuntos
        self.estatisticas['classes'] = self.analise_classes_assuntos()
        
        # Análise de movimentações
        self.estatisticas['movimentacoes'] = self.analise_movimentacoes()
        
        # Análise de padrões
        self.estatisticas['padroes'] = self.detectar_padroes()
        
        # Gerar insights
        self.gerar_insights()
        
        return self.estatisticas
    
    def analise_basica(self) -> Dict[str, Any]:
        """Análise básica dos dados"""
        stats = {}
        
        # Total geral
        total_processos = sum(len(df) for df in self.dados.values())
        stats['total_processos'] = total_processos
        
        # Por instância
        stats['por_instancia'] = {}
        for instancia, df in self.dados.items():
            if not df.empty:
                stats['por_instancia'][instancia] = {
                    'total': len(df),
                    'percentual': (len(df) / total_processos * 100) if total_processos > 0 else 0,
                    'processos_unicos': df['numero'].nunique() if 'numero' in df.columns else 0
                }
        
        # Taxa de preenchimento
        stats['completude'] = {}
        for instancia, df in self.dados.items():
            if not df.empty:
                completude = {}
                for col in df.columns:
                    nao_vazios = df[col].notna().sum()
                    completude[col] = (nao_vazios / len(df) * 100)
                stats['completude'][instancia] = completude
        
        return stats
    
    def analise_temporal(self) -> Dict[str, Any]:
        """Análise temporal dos processos"""
        stats = {}
        
        for instancia, df in self.dados.items():
            if df.empty or 'distribuicao' not in df.columns:
                continue
            
            # Converter datas
            df_temp = df.copy()
            df_temp['distribuicao_dt'] = pd.to_datetime(df_temp['distribuicao'], errors='coerce')
            
            # Remover datas inválidas
            df_temp = df_temp[df_temp['distribuicao_dt'].notna()]
            
            if not df_temp.empty:
                stats[instancia] = {
                    'processo_mais_antigo': df_temp['distribuicao_dt'].min().strftime('%d/%m/%Y') if not df_temp.empty else None,
                    'processo_mais_recente': df_temp['distribuicao_dt'].max().strftime('%d/%m/%Y') if not df_temp.empty else None,
                    'media_idade_dias': (datetime.now() - df_temp['distribuicao_dt']).dt.days.mean(),
                    'mediana_idade_dias': (datetime.now() - df_temp['distribuicao_dt']).dt.days.median()
                }
                
                # Distribuição por ano
                df_temp['ano'] = df_temp['distribuicao_dt'].dt.year
                stats[instancia]['por_ano'] = df_temp['ano'].value_counts().to_dict()
                
                # Distribuição por mês (último ano)
                ultimo_ano = df_temp['distribuicao_dt'].max().year
                df_ultimo_ano = df_temp[df_temp['ano'] == ultimo_ano]
                if not df_ultimo_ano.empty:
                    df_ultimo_ano['mes'] = df_ultimo_ano['distribuicao_dt'].dt.month
                    stats[instancia]['por_mes_ultimo_ano'] = df_ultimo_ano['mes'].value_counts().to_dict()
        
        return stats
    
    def analise_partes(self) -> Dict[str, Any]:
        """Análise das partes envolvidas"""
        stats = {}
        
        for instancia, df in self.dados.items():
            if df.empty:
                continue
            
            inst_stats = {}
            
            # Análise de requerentes
            if 'requerente' in df.columns:
                requerentes = df['requerente'].dropna()
                if not requerentes.empty:
                    # Top requerentes
                    top_requerentes = requerentes.value_counts().head(10)
                    inst_stats['top_requerentes'] = top_requerentes.to_dict()
                    
                    # Diversidade de requerentes
                    inst_stats['total_requerentes_unicos'] = requerentes.nunique()
            
            # Análise de requeridos
            if 'requerido' in df.columns:
                requeridos = df['requerido'].dropna()
                if not requeridos.empty:
                    # Top requeridos
                    top_requeridos = requeridos.value_counts().head(10)
                    inst_stats['top_requeridos'] = top_requeridos.to_dict()
                    
                    # Diversidade de requeridos
                    inst_stats['total_requeridos_unicos'] = requeridos.nunique()
            
            # Análise de advogados (extrair de partes se disponível)
            if 'requerente' in df.columns:
                advogados = []
                for texto in df['requerente'].dropna():
                    # Regex para encontrar OAB
                    oabs = re.findall(r'OAB[:\s]*([A-Z]{2}[/\s]*\d+)', str(texto))
                    advogados.extend(oabs)
                
                if advogados:
                    contador_advogados = Counter(advogados)
                    inst_stats['top_advogados'] = dict(contador_advogados.most_common(10))
                    inst_stats['total_advogados_unicos'] = len(contador_advogados)
            
            if inst_stats:
                stats[instancia] = inst_stats
        
        return stats
    
    def analise_valores(self) -> Dict[str, Any]:
        """Análise dos valores das ações"""
        stats = {}
        
        for instancia, df in self.dados.items():
            if df.empty or 'valor_acao' not in df.columns:
                continue
            
            # Limpar e converter valores
            df_temp = df.copy()
            df_temp['valor_numerico'] = df_temp['valor_acao'].apply(self.extrair_valor_numerico)
            df_valores = df_temp[df_temp['valor_numerico'] > 0]
            
            if not df_valores.empty:
                valores = df_valores['valor_numerico']
                
                stats[instancia] = {
                    'total_processos_com_valor': len(df_valores),
                    'valor_total': float(valores.sum()),
                    'valor_medio': float(valores.mean()),
                    'valor_mediano': float(valores.median()),
                    'valor_minimo': float(valores.min()),
                    'valor_maximo': float(valores.max()),
                    'desvio_padrao': float(valores.std()),
                    'quartis': {
                        'q1': float(valores.quantile(0.25)),
                        'q2': float(valores.quantile(0.50)),
                        'q3': float(valores.quantile(0.75))
                    }
                }
                
                # Classificação por faixa de valor
                faixas = [
                    (0, 1000, 'Até R$ 1.000'),
                    (1000, 5000, 'R$ 1.000 - R$ 5.000'),
                    (5000, 10000, 'R$ 5.000 - R$ 10.000'),
                    (10000, 50000, 'R$ 10.000 - R$ 50.000'),
                    (50000, 100000, 'R$ 50.000 - R$ 100.000'),
                    (100000, float('inf'), 'Acima de R$ 100.000')
                ]
                
                distribuicao_faixas = {}
                for min_val, max_val, label in faixas:
                    count = len(valores[(valores > min_val) & (valores <= max_val)])
                    if count > 0:
                        distribuicao_faixas[label] = count
                
                stats[instancia]['distribuicao_faixas'] = distribuicao_faixas
        
        return stats
    
    def extrair_valor_numerico(self, valor_str: str) -> float:
        """Extrai valor numérico de string"""
        if pd.isna(valor_str):
            return 0.0
        
        # Remover caracteres não numéricos
        valor_str = str(valor_str)
        valor_str = re.sub(r'[^\d,.]', '', valor_str)
        valor_str = valor_str.replace('.', '').replace(',', '.')
        
        try:
            return float(valor_str)
        except:
            return 0.0
    
    def analise_classes_assuntos(self) -> Dict[str, Any]:
        """Análise de classes e assuntos processuais"""
        stats = {}
        
        for instancia, df in self.dados.items():
            if df.empty:
                continue
            
            inst_stats = {}
            
            # Análise de classes
            if 'classe' in df.columns:
                classes = df['classe'].dropna()
                if not classes.empty:
                    top_classes = classes.value_counts().head(15)
                    inst_stats['top_classes'] = top_classes.to_dict()
                    inst_stats['total_classes_unicas'] = classes.nunique()
            
            # Análise de assuntos
            if 'assunto' in df.columns:
                assuntos = df['assunto'].dropna()
                if not assuntos.empty:
                    top_assuntos = assuntos.value_counts().head(15)
                    inst_stats['top_assuntos'] = top_assuntos.to_dict()
                    inst_stats['total_assuntos_unicos'] = assuntos.nunique()
            
            # Análise de áreas
            if 'area' in df.columns:
                areas = df['area'].dropna()
                if not areas.empty:
                    dist_areas = areas.value_counts()
                    inst_stats['distribuicao_areas'] = dist_areas.to_dict()
            
            # Análise de foros e varas
            if 'foro' in df.columns:
                foros = df['foro'].dropna()
                if not foros.empty:
                    top_foros = foros.value_counts().head(10)
                    inst_stats['top_foros'] = top_foros.to_dict()
            
            if 'vara' in df.columns:
                varas = df['vara'].dropna()
                if not varas.empty:
                    top_varas = varas.value_counts().head(10)
                    inst_stats['top_varas'] = top_varas.to_dict()
            
            if inst_stats:
                stats[instancia] = inst_stats
        
        return stats
    
    def analise_movimentacoes(self) -> Dict[str, Any]:
        """Análise das movimentações processuais"""
        stats = {}
        
        for instancia, df in self.dados.items():
            if df.empty or 'movimentacoes' not in df.columns:
                continue
            
            movimentacoes_todas = []
            
            for mov_str in df['movimentacoes'].dropna():
                # Separar movimentações individuais
                movs = str(mov_str).split('|')
                movimentacoes_todas.extend(movs)
            
            if movimentacoes_todas:
                # Extrair tipos de movimentação
                tipos_mov = []
                for mov in movimentacoes_todas:
                    # Tentar extrair o tipo da movimentação
                    partes = mov.split('-')
                    if len(partes) >= 2:
                        tipo = partes[1].strip()
                        tipos_mov.append(tipo)
                
                if tipos_mov:
                    contador_tipos = Counter(tipos_mov)
                    stats[instancia] = {
                        'total_movimentacoes': len(movimentacoes_todas),
                        'media_mov_por_processo': len(movimentacoes_todas) / len(df),
                        'top_tipos_movimentacao': dict(contador_tipos.most_common(20)),
                        'tipos_unicos': len(contador_tipos)
                    }
                    
                    # Identificar movimentações críticas
                    movs_criticas = [
                        'sentença', 'julgamento', 'acordo', 'extinção',
                        'arquivamento', 'recurso', 'apelação', 'embargo'
                    ]
                    
                    stats[instancia]['movimentacoes_criticas'] = {}
                    for mov_critica in movs_criticas:
                        count = sum(1 for t in tipos_mov if mov_critica.lower() in t.lower())
                        if count > 0:
                            stats[instancia]['movimentacoes_criticas'][mov_critica] = count
        
        return stats
    
    def detectar_padroes(self) -> Dict[str, Any]:
        """Detecta padrões e anomalias nos dados"""
        padroes = {}
        
        # Padrão 1: Concentração de processos
        for instancia, df in self.dados.items():
            if df.empty:
                continue
            
            padroes_inst = {}
            
            # Verificar concentração temporal
            if 'distribuicao' in df.columns:
                df_temp = df.copy()
                df_temp['distribuicao_dt'] = pd.to_datetime(df_temp['distribuicao'], errors='coerce')
                df_temp = df_temp[df_temp['distribuicao_dt'].notna()]
                
                if not df_temp.empty:
                    df_temp['mes_ano'] = df_temp['distribuicao_dt'].dt.to_period('M')
                    dist_mensal = df_temp['mes_ano'].value_counts()
                    
                    if len(dist_mensal) > 1:
                        media = dist_mensal.mean()
                        desvio = dist_mensal.std()
                        
                        # Identificar meses com volume anormal
                        meses_anomalos = dist_mensal[dist_mensal > media + 2*desvio]
                        if not meses_anomalos.empty:
                            padroes_inst['meses_volume_anomalo'] = {
                                str(mes): int(count) for mes, count in meses_anomalos.items()
                            }
            
            # Verificar concentração por parte
            if 'requerido' in df.columns:
                requeridos = df['requerido'].value_counts()
                if len(requeridos) > 0:
                    # Verificar se há concentração excessiva
                    top_requerido_pct = (requeridos.iloc[0] / len(df)) * 100
                    if top_requerido_pct > 30:  # Se um requerido representa mais de 30%
                        padroes_inst['concentracao_requerido'] = {
                            'nome': requeridos.index[0],
                            'percentual': float(top_requerido_pct),
                            'quantidade': int(requeridos.iloc[0])
                        }
            
            # Verificar padrões de valores
            if 'valor_acao' in df.columns:
                df_temp = df.copy()
                df_temp['valor_numerico'] = df_temp['valor_acao'].apply(self.extrair_valor_numerico)
                valores = df_temp[df_temp['valor_numerico'] > 0]['valor_numerico']
                
                if len(valores) > 10:
                    # Detectar outliers usando IQR
                    Q1 = valores.quantile(0.25)
                    Q3 = valores.quantile(0.75)
                    IQR = Q3 - Q1
                    
                    outliers = valores[(valores < Q1 - 1.5*IQR) | (valores > Q3 + 1.5*IQR)]
                    if len(outliers) > 0:
                        padroes_inst['outliers_valores'] = {
                            'quantidade': len(outliers),
                            'percentual': (len(outliers) / len(valores)) * 100,
                            'valores_exemplo': outliers.head(5).tolist()
                        }
            
            if padroes_inst:
                padroes[instancia] = padroes_inst
        
        return padroes
    
    def gerar_insights(self):
        """Gera insights automáticos baseados nas análises"""
        self.insights = []
        
        # Insight 1: Volume total
        total = self.estatisticas['basicas']['total_processos']
        self.insights.append(f"📊 Total de {total} processos analisados")
        
        # Insight 2: Instância com mais processos
        if 'por_instancia' in self.estatisticas['basicas']:
            instancias = self.estatisticas['basicas']['por_instancia']
            if instancias:
                maior_inst = max(instancias.items(), key=lambda x: x[1]['total'])
                self.insights.append(
                    f"⚖️ {maior_inst[0].replace('_', ' ').title()} concentra "
                    f"{maior_inst[1]['percentual']:.1f}% dos processos"
                )
        
        # Insight 3: Valor médio das ações
        if 'valores' in self.estatisticas:
            valores_totais = []
            for inst, dados in self.estatisticas['valores'].items():
                if 'valor_medio' in dados:
                    valores_totais.append(dados['valor_medio'])
            
            if valores_totais:
                media_geral = np.mean(valores_totais)
                self.insights.append(f"💰 Valor médio das ações: R$ {media_geral:,.2f}")
        
        # Insight 4: Padrões detectados
        if 'padroes' in self.estatisticas and self.estatisticas['padroes']:
            total_padroes = sum(len(p) for p in self.estatisticas['padroes'].values())
            self.insights.append(f"🔍 {total_padroes} padrões identificados nos dados")
        
        # Insight 5: Tendência temporal
        if 'temporal' in self.estatisticas:
            for inst, dados in self.estatisticas['temporal'].items():
                if 'por_ano' in dados and len(dados['por_ano']) > 1:
                    anos = sorted(dados['por_ano'].keys())
                    if len(anos) >= 2:
                        ultimo = dados['por_ano'][anos[-1]]
                        penultimo = dados['por_ano'][anos[-2]]
                        variacao = ((ultimo - penultimo) / penultimo) * 100
                        
                        if abs(variacao) > 20:
                            tendencia = "aumento" if variacao > 0 else "redução"
                            self.insights.append(
                                f"📈 {tendencia.capitalize()} de {abs(variacao):.1f}% "
                                f"em processos de {anos[-2]} para {anos[-1]}"
                            )
                    break
    
    def gerar_relatorio_html(self, caminho_saida: Optional[Path] = None) -> Path:
        """Gera relatório HTML com as análises"""
        if not caminho_saida:
            caminho_saida = self.caminho_dados / f"relatorio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Relatório de Análise - TJSP Scraper</title>
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    padding: 20px;
                }
                .container {
                    max-width: 1200px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 20px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    overflow: hidden;
                }
                .header {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 40px;
                    text-align: center;
                }
                .header h1 {
                    font-size: 2.5em;
                    margin-bottom: 10px;
                }
                .header .subtitle {
                    font-size: 1.2em;
                    opacity: 0.9;
                }
                .content {
                    padding: 40px;
                }
                .insights {
                    background: #f8f9fa;
                    border-left: 4px solid #667eea;
                    padding: 20px;
                    margin: 20px 0;
                    border-radius: 8px;
                }
                .insight-item {
                    margin: 10px 0;
                    font-size: 1.1em;
                }
                .section {
                    margin: 40px 0;
                }
                .section h2 {
                    color: #667eea;
                    border-bottom: 2px solid #667eea;
                    padding-bottom: 10px;
                    margin-bottom: 20px;
                }
                .stats-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                    gap: 20px;
                    margin: 20px 0;
                }
                .stat-card {
                    background: #f8f9fa;
                    padding: 20px;
                    border-radius: 10px;
                    border: 1px solid #e9ecef;
                    transition: transform 0.3s, box-shadow 0.3s;
                }
                .stat-card:hover {
                    transform: translateY(-5px);
                    box-shadow: 0 5px 20px rgba(0,0,0,0.1);
                }
                .stat-value {
                    font-size: 2em;
                    font-weight: bold;
                    color: #667eea;
                }
                .stat-label {
                    color: #6c757d;
                    margin-top: 5px;
                }
                table {
                    width: 100%;
                    border-collapse: collapse;
                    margin: 20px 0;
                }
                th {
                    background: #667eea;
                    color: white;
                    padding: 12px;
                    text-align: left;
                }
                td {
                    padding: 12px;
                    border-bottom: 1px solid #e9ecef;
                }
                tr:hover {
                    background: #f8f9fa;
                }
                .chart-container {
                    margin: 20px 0;
                    padding: 20px;
                    background: #f8f9fa;
                    border-radius: 10px;
                }
                .footer {
                    background: #f8f9fa;
                    padding: 20px;
                    text-align: center;
                    color: #6c757d;
                    font-size: 0.9em;
                }
                .badge {
                    display: inline-block;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 0.85em;
                    font-weight: bold;
                    margin: 2px;
                }
                .badge-primary { background: #667eea; color: white; }
                .badge-success { background: #28a745; color: white; }
                .badge-warning { background: #ffc107; color: #333; }
                .badge-danger { background: #dc3545; color: white; }
                .progress-bar {
                    width: 100%;
                    height: 20px;
                    background: #e9ecef;
                    border-radius: 10px;
                    overflow: hidden;
                    margin: 10px 0;
                }
                .progress-fill {
                    height: 100%;
                    background: linear-gradient(90deg, #667eea, #764ba2);
                    transition: width 1s ease;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🏛️ Relatório de Análise TJSP</h1>
                    <div class="subtitle">Análise Completa de Processos Judiciais</div>
                    <div class="subtitle">{data_geracao}</div>
                </div>
                
                <div class="content">
        """.format(data_geracao=datetime.now().strftime('%d/%m/%Y às %H:%M'))
        
        # Adicionar insights
        if self.insights:
            html += '<div class="insights"><h3>💡 Principais Insights</h3>'
            for insight in self.insights:
                html += f'<div class="insight-item">{insight}</div>'
            html += '</div>'
        
        # Estatísticas básicas
        if 'basicas' in self.estatisticas:
            basicas = self.estatisticas['basicas']
            html += '<div class="section"><h2>📊 Estatísticas Gerais</h2>'
            html += '<div class="stats-grid">'
            
            html += f'''
                <div class="stat-card">
                    <div class="stat-value">{basicas["total_processos"]:,}</div>
                    <div class="stat-label">Total de Processos</div>
                </div>
            '''
            
            for inst, dados in basicas.get('por_instancia', {}).items():
                html += f'''
                    <div class="stat-card">
                        <div class="stat-value">{dados["total"]:,}</div>
                        <div class="stat-label">{inst.replace("_", " ").title()}</div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {dados["percentual"]:.1f}%"></div>
                        </div>
                        <small>{dados["percentual"]:.1f}% do total</small>
                    </div>
                '''
            
            html += '</div></div>'
        
        # Análise de valores
        if 'valores' in self.estatisticas:
            html += '<div class="section"><h2>💰 Análise de Valores</h2>'
            
            for inst, dados in self.estatisticas['valores'].items():
                html += f'<h3>{inst.replace("_", " ").title()}</h3>'
                html += '<div class="stats-grid">'
                
                metricas = [
                    ('valor_total', 'Valor Total', lambda x: f'R$ {x:,.2f}'),
                    ('valor_medio', 'Valor Médio', lambda x: f'R$ {x:,.2f}'),
                    ('valor_mediano', 'Valor Mediano', lambda x: f'R$ {x:,.2f}'),
                    ('valor_maximo', 'Valor Máximo', lambda x: f'R$ {x:,.2f}')
                ]
                
                for key, label, formatter in metricas:
                    if key in dados:
                        html += f'''
                            <div class="stat-card">
                                <div class="stat-value">{formatter(dados[key])}</div>
                                <div class="stat-label">{label}</div>
                            </div>
                        '''
                
                html += '</div>'
                
                # Distribuição por faixas
                if 'distribuicao_faixas' in dados:
                    html += '<h4>Distribuição por Faixas de Valor</h4>'
                    html += '<table><thead><tr><th>Faixa</th><th>Quantidade</th></tr></thead><tbody>'
                    for faixa, qtd in dados['distribuicao_faixas'].items():
                        html += f'<tr><td>{faixa}</td><td>{qtd}</td></tr>'
                    html += '</tbody></table>'
            
            html += '</div>'
        
        # Top classes e assuntos
        if 'classes' in self.estatisticas:
            html += '<div class="section"><h2>⚖️ Classes e Assuntos</h2>'
            
            for inst, dados in self.estatisticas['classes'].items():
                html += f'<h3>{inst.replace("_", " ").title()}</h3>'
                
                # Top classes
                if 'top_classes' in dados:
                    html += '<h4>Top 10 Classes Processuais</h4>'
                    html += '<table><thead><tr><th>Classe</th><th>Quantidade</th></tr></thead><tbody>'
                    for classe, qtd in list(dados['top_classes'].items())[:10]:
                        html += f'<tr><td>{classe}</td><td>{qtd}</td></tr>'
                    html += '</tbody></table>'
                
                # Top assuntos
                if 'top_assuntos' in dados:
                    html += '<h4>Top 10 Assuntos</h4>'
                    html += '<table><thead><tr><th>Assunto</th><th>Quantidade</th></tr></thead><tbody>'
                    for assunto, qtd in list(dados['top_assuntos'].items())[:10]:
                        html += f'<tr><td>{assunto}</td><td>{qtd}</td></tr>'
                    html += '</tbody></table>'
            
            html += '</div>'
        
        # Padrões detectados
        if 'padroes' in self.estatisticas and self.estatisticas['padroes']:
            html += '<div class="section"><h2>🔍 Padrões e Anomalias</h2>'
            
            for inst, padroes in self.estatisticas['padroes'].items():
                html += f'<h3>{inst.replace("_", " ").title()}</h3>'
                
                for padrao_nome, padrao_dados in padroes.items():
                    html += f'<div class="chart-container">'
                    html += f'<h4>⚠️ {padrao_nome.replace("_", " ").title()}</h4>'
                    html += f'<pre>{json.dumps(padrao_dados, indent=2, ensure_ascii=False)}</pre>'
                    html += '</div>'
            
            html += '</div>'
        
        # Footer
        html += '''
                </div>
                <div class="footer">
                    <p>Relatório gerado automaticamente pelo TJSP Scraper v2.0</p>
                    <p>© 2025 - Sistema de Análise Avançada</p>
                </div>
            </div>
        </body>
        </html>
        '''
        
        # Salvar arquivo
        with open(caminho_saida, 'w', encoding='utf-8') as f:
            f.write(html)
        
        self.logger.info(f"✅ Relatório HTML salvo em: {caminho_saida}")
        return caminho_saida
    
    def exportar_json(self, caminho_saida: Optional[Path] = None) -> Path:
        """Exporta análises para JSON"""
        if not caminho_saida:
            caminho_saida = self.caminho_dados / f"analise_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        dados_export = {
            'data_analise': datetime.now().isoformat(),
            'estatisticas': self.estatisticas,
            'insights': self.insights,
            'metadados': {
                'total_arquivos': len(self.dados),
                'arquivos_analisados': list(self.dados.keys())
            }
        }
        
        with open(caminho_saida, 'w', encoding='utf-8') as f:
            json.dump(dados_export, f, indent=2, ensure_ascii=False, default=str)
        
        self.logger.info(f"✅ Análise exportada para JSON: {caminho_saida}")
        return caminho_saida

# CLI para análise
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Analisador de Dados TJSP")
    parser.add_argument("--dados", type=str, default="dados", help="Pasta com os dados")
    parser.add_argument("--html", action="store_true", help="Gerar relatório HTML")
    parser.add_argument("--json", action="store_true", help="Exportar análise em JSON")
    
    args = parser.parse_args()
    
    analisador = AnalisadorTJSP(Path(args.dados))
    estatisticas = analisador.analisar_completo()
    
    print("\n" + "="*60)
    print("📊 ANÁLISE COMPLETA DOS DADOS")
    print("="*60)
    
    # Mostrar insights
    print("\n💡 Insights Principais:")
    for insight in analisador.insights:
        print(f"  • {insight}")
    
    # Gerar relatórios
    if args.html:
        caminho_html = analisador.gerar_relatorio_html()
        print(f"\n✅ Relatório HTML gerado: {caminho_html}")
    
    if args.json:
        caminho_json = analisador.exportar_json()
        print(f"✅ Análise exportada: {caminho_json}")
    
    print("\n" + "="*60)