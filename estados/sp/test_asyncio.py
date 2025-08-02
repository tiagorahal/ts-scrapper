#!/usr/bin/env python3
"""
Teste simples para verificar se o asyncio está funcionando
"""

import asyncio
import sys

async def teste_basico():
    print("✅ Função async iniciada")
    await asyncio.sleep(1)
    print("✅ Sleep completado")
    return "Sucesso!"

def main():
    print(f"Python: {sys.version}")
    print(f"Testando asyncio...")
    
    try:
        # Testa asyncio.run (Python 3.7+)
        resultado = asyncio.run(teste_basico())
        print(f"✅ asyncio.run() funcionou: {resultado}")
    except AttributeError:
        # Python 3.6 ou anterior
        print("⚠️  asyncio.run() não disponível (Python < 3.7)")
        loop = asyncio.get_event_loop()
        resultado = loop.run_until_complete(teste_basico())
        print(f"✅ Loop manual funcionou: {resultado}")
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    main()