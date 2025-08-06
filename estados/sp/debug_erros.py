#!/usr/bin/env python3
"""
Script de diagnóstico para verificar o estado atual dos sites do TJSP
"""

import asyncio
import sys
from datetime import datetime
from playwright.async_api import async_playwright

# URLs dos sites do TJSP
URLS = {
    "primeira_instancia": "https://esaj.tjsp.jus.br/cpopg/open.do",
    "segunda_instancia": "https://esaj.tjsp.jus.br/cposg/open.do", 
    "colegio_recursal": "https://esaj.tjsp.jus.br/cposgcr/open.do"
}

async def diagnosticar_site(nome, url):
    """Diagnostica um site específico do TJSP"""
    print(f"\n{'='*50}")
    print(f"🔍 Diagnosticando: {nome}")
    print(f"📍 URL: {url}")
    print(f"{'='*50}")
    
    async with async_playwright() as p:
        try:
            # Configurações do browser
            browser = await p.chromium.launch(
                headless=False,  # Mostra o navegador para debug
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox'
                ]
            )
            
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            page = await context.new_page()
            
            # Intercepta respostas para debug
            responses = []
            page.on("response", lambda response: responses.append({
                "url": response.url,
                "status": response.status,
                "headers": dict(response.headers)
            }))
            
            print("⏳ Carregando página...")
            start_time = datetime.now()
            
            try:
                await page.goto(url, timeout=30000)
                load_time = (datetime.now() - start_time).total_seconds()
                print(f"✅ Página carregada em {load_time:.2f}s")
                
                # Aguarda estabilizar
                await page.wait_for_load_state("networkidle", timeout=10000)
                print("✅ Página estabilizada")
                
            except Exception as e:
                print(f"❌ Erro ao carregar página: {e}")
                await browser.close()
                return False
            
            # Verifica título da página
            title = await page.title()
            print(f"📄 Título: {title}")
            
            # Verifica se há captcha
            captcha_selectors = [
                "iframe[src*='recaptcha']",
                ".g-recaptcha",
                "[data-sitekey]",
                "img[src*='captcha']",
                "#captcha"
            ]
            
            for selector in captcha_selectors:
                if await page.query_selector(selector):
                    print(f"🚨 CAPTCHA DETECTADO: {selector}")
                    break
            else:
                print("✅ Nenhum captcha detectado")
            
            # Verifica bloqueios ou mensagens de erro
            error_texts = [
                "acesso negado",
                "bloqueado",
                "many requests",
                "rate limit",
                "forbidden",
                "erro interno"
            ]
            
            page_content = await page.content()
            for error_text in error_texts:
                if error_text.lower() in page_content.lower():
                    print(f"🚨 POSSÍVEL BLOQUEIO: '{error_text}' encontrado na página")
            
            # Procura o seletor problemático
            print("\n🔍 Verificando seletores importantes...")
            
            selectors_check = [
                "select#cbPesquisa",
                "#cbPesquisa", 
                "select[id*='Pesquisa']",
                "select[name*='pesquisa']",
                "form",
                "input[type='text']"
            ]
            
            for selector in selectors_check:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        print(f"✅ Encontrado: {selector}")
                        # Se for o seletor principal, mostra as opções
                        if "cbPesquisa" in selector:
                            options = await page.query_selector_all(f"{selector} option")
                            print(f"   📋 Opções disponíveis: {len(options)}")
                            for opt in options[:5]:  # Mostra só as primeiras 5
                                value = await opt.get_attribute("value")
                                text = await opt.inner_text()
                                print(f"      - {value}: {text}")
                    else:
                        print(f"❌ NÃO encontrado: {selector}")
                except Exception as e:
                    print(f"❌ Erro ao verificar {selector}: {e}")
            
            # Verifica estrutura da página
            print("\n📊 Estrutura da página:")
            forms = await page.query_selector_all("form")
            print(f"   📝 Formulários encontrados: {len(forms)}")
            
            selects = await page.query_selector_all("select")
            print(f"   📋 Selects encontrados: {len(selects)}")
            
            inputs = await page.query_selector_all("input")
            print(f"   ⌨️  Inputs encontrados: {len(inputs)}")
            
            # Lista os selects disponíveis
            if selects:
                print("\n📋 Selects disponíveis:")
                for i, select in enumerate(selects[:5]):  # Máximo 5
                    try:
                        id_attr = await select.get_attribute("id")
                        name_attr = await select.get_attribute("name")
                        print(f"   {i+1}. ID: {id_attr or 'N/A'}, Name: {name_attr or 'N/A'}")
                    except:
                        pass
            
            # Cria pasta prints se não existir
            from pathlib import Path
            prints_dir = Path("prints")
            prints_dir.mkdir(exist_ok=True)
            
            # Salva screenshot para análise
            screenshot_path = prints_dir / f"debug_{nome}_{datetime.now().strftime('%H%M%S')}.png"
            await page.screenshot(path=str(screenshot_path))
            print(f"📸 Screenshot salvo: {screenshot_path}")
            
            # Salva HTML da página para análise offline
            html_path = prints_dir / f"debug_{nome}_{datetime.now().strftime('%H%M%S')}.html"
            page_html = await page.content()
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(page_html)
            print(f"📄 HTML salvo: {html_path}")
            
            # Mostra respostas HTTP relevantes
            print(f"\n🌐 Respostas HTTP ({len(responses)} total):")
            for resp in responses[-5:]:  # Últimas 5 respostas
                if resp['status'] >= 400:
                    print(f"   ❌ {resp['status']}: {resp['url'][:80]}...")
                elif resp['status'] >= 300:
                    print(f"   ⚠️  {resp['status']}: {resp['url'][:80]}...")
            
            await browser.close()
            return True
            
        except Exception as e:
            print(f"❌ Erro geral: {e}")
            try:
                await browser.close()
            except:
                pass
            return False

async def main():
    print("="*60)
    print("🔍 DIAGNÓSTICO COMPLETO - SITES TJSP")
    print("="*60)
    print(f"⏰ Iniciado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    resultados = {}
    
    for nome, url in URLS.items():
        sucesso = await diagnosticar_site(nome, url)
        resultados[nome] = sucesso
        
        # Pausa entre sites para evitar rate limiting
        if nome != list(URLS.keys())[-1]:  # Se não for o último
            print("\n⏸️  Pausando 10 segundos entre sites...")
            await asyncio.sleep(10)
    
    # Resumo final
    print(f"\n{'='*60}")
    print("📊 RESUMO DO DIAGNÓSTICO")
    print(f"{'='*60}")
    
    for nome, sucesso in resultados.items():
        status = "✅ OK" if sucesso else "❌ PROBLEMA"
        print(f"   {nome}: {status}")
    
    if all(resultados.values()):
        print("\n🎉 Todos os sites parecem estar funcionais!")
        print("💡 O problema pode estar nos seletores ou timing dos scripts.")
    else:
        print("\n⚠️  Alguns sites apresentaram problemas.")
        print("💡 Verifique as screenshots e logs acima.")
    
    print(f"\n💡 Próximos passos:")
    print("1. Analise as screenshots geradas")
    print("2. Verifique se os seletores encontrados são os corretos")
    print("3. Se houver captcha, considere usar proxy ou delay maior")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️  Diagnóstico interrompido pelo usuário.")
    except Exception as e:
        print(f"\n❌ Erro no diagnóstico: {e}")
        sys.exit(1)