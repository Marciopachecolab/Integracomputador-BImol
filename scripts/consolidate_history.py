"""
Script de Consolidação de Histórico de Processamento

Objetivo: Resolver R6 e R10 do RELATORIO_REDUNDANCIA_CONFLITOS.md
- Define PostgreSQL como fonte de verdade única
- Consolida CSV em logs/ como visão auxiliar
- Migra dados de reports/historico_analises.csv se existir

ARQUITETURA:
- ✅ Fonte de verdade: PostgreSQL (db.db_utils.salvar_historico_processamento)
- 🔄 Visão auxiliar: logs/historico_analises.csv (gerado a partir do banco)
- ❌ Deprecado: reports/historico_analises.csv (movido para logs/)
"""

import pandas as pd
from pathlib import Path
import shutil
from datetime import datetime
import sys

# Adicionar diretório pai ao path para permitir imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.db_utils import get_postgres_connection
from utils.logger import registrar_log


def migrate_csv_to_postgres():
    """
    Migra dados de reports/historico_analises.csv para PostgreSQL.
    Executa apenas se o arquivo existir e o banco estiver disponível.
    """
    reports_csv = Path("reports/historico_analises.csv")
    
    if not reports_csv.exists():
        registrar_log(
            "Consolidate History",
            "reports/historico_analises.csv não encontrado. Nada a migrar.",
            "INFO"
        )
        return 0
    
    conn = get_postgres_connection()
    if conn is None:
        registrar_log(
            "Consolidate History",
            "PostgreSQL indisponível. Migração cancelada.",
            "WARNING"
        )
        return 0
    
    try:
        # Ler CSV existente
        df = pd.read_csv(reports_csv, encoding="utf-8")
        registrar_log(
            "Consolidate History",
            f"Lidos {len(df)} registros de reports/historico_analises.csv",
            "INFO"
        )
        
        # Inserir no PostgreSQL
        migrated = 0
        with conn.cursor() as cursor:
            for _, row in df.iterrows():
                try:
                    cursor.execute(
                        """
                        INSERT INTO historico_processos 
                        (analista, exame, status, detalhes, data_hora)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                        """,
                        (
                            row.get("analista", "Sistema"),
                            row.get("exame", "Desconhecido"),
                            row.get("status", "OK"),
                            row.get("detalhes", "Migração automática"),
                            row.get("data_hora", datetime.now())
                        )
                    )
                    migrated += 1
                except Exception as e:
                    registrar_log(
                        "Consolidate History",
                        f"Erro ao migrar linha: {e}",
                        "WARNING"
                    )
        
        conn.commit()
        registrar_log(
            "Consolidate History",
            f"Migrados {migrated}/{len(df)} registros para PostgreSQL",
            "INFO"
        )
        
        # Fazer backup do arquivo original
        backup_path = reports_csv.parent / f"historico_analises_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        shutil.copy(reports_csv, backup_path)
        registrar_log(
            "Consolidate History",
            f"Backup criado em: {backup_path}",
            "INFO"
        )
        
        return migrated
        
    except Exception as e:
        registrar_log(
            "Consolidate History",
            f"Erro na migração: {e}",
            "ERROR"
        )
        return 0
    finally:
        if conn:
            conn.close()


def generate_csv_from_postgres():
    """
    Gera logs/historico_analises.csv a partir do PostgreSQL.
    Este CSV é apenas uma visão auxiliar, não a fonte de verdade.
    """
    conn = get_postgres_connection()
    if conn is None:
        registrar_log(
            "Consolidate History",
            "PostgreSQL indisponível. CSV não gerado.",
            "WARNING"
        )
        return False
    
    try:
        # Ler do PostgreSQL
        query = """
            SELECT analista, exame, status, detalhes, data_hora
            FROM historico_processos
            ORDER BY data_hora DESC
        """
        
        df = pd.read_sql(query, conn)
        
        # Salvar em logs/
        logs_csv = Path("logs/historico_analises.csv")
        logs_csv.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(logs_csv, index=False, encoding="utf-8")
        
        registrar_log(
            "Consolidate History",
            f"CSV atualizado em logs/ com {len(df)} registros do PostgreSQL",
            "INFO"
        )
        
        return True
        
    except Exception as e:
        registrar_log(
            "Consolidate History",
            f"Erro ao gerar CSV: {e}",
            "ERROR"
        )
        return False
    finally:
        if conn:
            conn.close()


def consolidate_csv_files():
    """
    Consolida arquivos CSV de histórico:
    - Faz backup do CSV existente (que tem formato diferente)
    - Prepara para novo formato baseado no PostgreSQL
    """
    reports_csv = Path("reports/historico_analises.csv")
    logs_csv = Path("logs/historico_analises.csv")
    
    # Fazer backup do CSV existente em logs/ se existir (formato antigo)
    if logs_csv.exists():
        backup_path = logs_csv.parent / f"historico_analises_old_format_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        shutil.copy(logs_csv, backup_path)
        print(f"✅ Backup do formato antigo criado em: {backup_path}")
    
    # Mover reports/ para backup se existir
    if reports_csv.exists():
        backup_path = reports_csv.parent / f"historico_analises_from_reports_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        shutil.move(reports_csv, backup_path)
        print(f"✅ reports/historico_analises.csv movido para: {backup_path}")


def main():
    """Executa consolidação completa."""
    print("=" * 70)
    print("CONSOLIDAÇÃO DE HISTÓRICO DE PROCESSAMENTO")
    print("=" * 70)
    
    print("\n📌 ETAPA 1: Consolidar arquivos CSV")
    consolidate_csv_files()
    
    print("\n📌 ETAPA 2: Migrar CSV para PostgreSQL")
    migrated = migrate_csv_to_postgres()
    print(f"✅ {migrated} registros migrados para PostgreSQL")
    
    print("\n📌 ETAPA 3: Gerar CSV atualizado do PostgreSQL")
    success = generate_csv_from_postgres()
    if success:
        print("✅ logs/historico_analises.csv atualizado do PostgreSQL")
    
    print("\n" + "=" * 70)
    print("✅ CONSOLIDAÇÃO CONCLUÍDA")
    print("=" * 70)
    print("\nArquitetura atual:")
    print("  ✅ Fonte de verdade: PostgreSQL (historico_processos)")
    print("  🔄 Visão auxiliar: logs/historico_analises.csv")
    print("  ❌ Deprecado: reports/historico_analises.csv (removido)")


if __name__ == "__main__":
    main()
