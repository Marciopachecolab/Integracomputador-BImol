"""
Script de debug para executar o fluxo de login do GalService de forma segura.
Lê as credenciais de ambiente: GAL_TEST_USER e GAL_TEST_PASS.
Se não estiverem definidas, imprime instruções e sai.
Ao falhar grava `debug/gal_login_fail.png` e `debug/gal_login_fail.html` em BASE_DIR.

Uso (PowerShell):
$env:GAL_TEST_USER = 'seu_usuario'
$env:GAL_TEST_PASS = 'sua_senha'
.\venv\Scripts\python .\exportacao\debug_login_runner.py

NÃO coloque credenciais no script. Use variáveis de ambiente.
"""

import os

from seleniumrequests import Firefox

from exportacao.envio_gal import GalService
from services.system_paths import BASE_DIR


def main():
    usuario = os.environ.get("GAL_TEST_USER")
    senha = os.environ.get("GAL_TEST_PASS")
    if not usuario or not senha:
        print("Variáveis de ambiente GAL_TEST_USER / GAL_TEST_PASS não definidas.")
        print("Defina-as antes de rodar. Exemplo (PowerShell):")
        print(
            "$env:GAL_TEST_USER='seu_usuario'; $env:GAL_TEST_PASS='sua_senha'; .\\venv\\Scripts\\python .\\exportacao\\debug_login_runner.py"
        )
        return

    def logger(msg, level="info"):
        print(f"[{level.upper()}] {msg}")

    svc = GalService(logger)
    driver = None
    try:
        print(
            "Iniciando driver Firefox (seleniumrequests). Isso abrirá uma janela do browser visível)."
        )
        driver = Firefox()
        svc.realizar_login(driver, usuario, senha)
        print("Login executado sem exceção (verificar se ocorreu realmente).")
    except Exception as e:
        print("Exception durante login:", repr(e))
        # listar arquivos debug se foram gerados
        ddir = os.path.join(BASE_DIR, "debug")
        if os.path.isdir(ddir):
            print("Arquivos em debug/:")
            for f in os.listdir(ddir):
                print("-", f)
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


if __name__ == "__main__":
    main()
