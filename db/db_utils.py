# db/db_utils.py

from typing import Optional

# --- MELHORIA: Importa o novo serviço de configuração e o logger ---
from services.core.config_service import config_service
from services.persistence.csv_io import read_csv_strict
# --- Configuração de Paths e Imports ---
from utils.logger import registrar_log
import os
import csv
from datetime import datetime
from pathlib import Path
from utils.csv_lock import CSVFileLock
from utils.csv_safety import sanitize_csv_value
from utils.network_io import RetryPolicy, call_with_retry, open_with_retry, path_exists_with_retry


def get_postgres_connection() -> Optional[object]:
    """
    Facade: o trafego de DB foi redirecionado para CSV.
    Retorna None sempre para forçar o fallback.
    """
    registrar_log(
        "DB Utils",
        "Facade ativo: conexões PostgreSQL desabilitadas. Usando CSV.",
        "INFO",
    )
    return None


def _salvar_historico_csv_fallback(analista: str, exame: str, status: str, detalhes: str):
    """
    Fallback para salvar histórico em CSV se o PostgreSQL falhar.
    Usa CSVFileLock para garantir atomicidade em ambiente de rede.
    """
    try:
        # Obter path das configurações ou usar padrão
        paths = config_service.get_paths()
        csv_path = Path(paths.get("processing_history_csv", "logs/historico_processos.csv"))
        
        # Garantir diretório
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        
        fieldnames = ['data_hora', 'analista', 'exame', 'status', 'detalhes']
        policy = RetryPolicy.from_env()
        
        with CSVFileLock(csv_path) as _lock:
            file_exists = path_exists_with_retry(csv_path, policy=policy)
            with open_with_retry(csv_path, 'a', newline='', encoding='utf-8', policy=policy) as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';')
                if not file_exists:
                    writer.writeheader()
                
                writer.writerow({
                    'data_hora': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'analista': sanitize_csv_value(analista),
                    'exame': sanitize_csv_value(exame),
                    'status': sanitize_csv_value(status),
                    'detalhes': sanitize_csv_value(detalhes)
                })
        registrar_log("DB Utils", f"Histórico salvo em CSV (fallback): {csv_path}", "INFO")
    except Exception as e:
        registrar_log("DB Utils", f"Falha crítica ao salvar histórico (PostgreSQL e CSV): {e}", "CRITICAL")


def salvar_historico_processamento(
    analista: str, exame: str, status: str, detalhes: str
):
    """
    Salva um registo na tabela 'historico_processos' do PostgreSQL.
    
    ⚠️ FALLBACK: Se o PostgreSQL estiver offline, salva em logs/historico_processos.csv
    usando um mecanismo de lock atômico para suporte a rede.
    """
    backend = config_service.get_storage_backend()
    conn = get_postgres_connection()
    if conn is None:
        if backend == "postgres":
            registrar_log(
                "DB Utils",
                "PostgreSQL indisponivel. Iniciando gravacao em CSV compartilhado.",
                "WARNING",
            )
        else:
            registrar_log(
                "DB Utils",
                f"storage_backend={backend}. Gravando historico em CSV.",
                "INFO",
            )
        _salvar_historico_csv_fallback(analista, exame, status, detalhes)
        return

    # Quando get_postgres_connection retornar None, já cai no fallback CSV.
    # Este bloco fica mantido apenas para compatibilidade futura.
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO historico_processos (analista, exame, status, detalhes, data_hora)
                VALUES (%s, %s, %s, %s, NOW())
            """,
                (analista, exame, status, detalhes),
            )
        conn.commit()
    except Exception as e:
        registrar_log(
            "DB Utils", f"Falha ao salvar histórico no PostgreSQL: {e}", "ERROR"
        )
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def obter_historico_analises(limit=None):
    """
    Obtém o histórico de análises do banco de dados.
    Retorna um DataFrame pandas ou None se falhar/desabilitado.
    """
    import pandas as pd
    
    conn = get_postgres_connection()
    if conn is None:
        # FALLBACK: Ler do CSV se o DB estiver offline
        try:
            paths = config_service.get_paths()
            csv_path = Path(paths.get("processing_history_csv", "logs/historico_processos.csv"))
            policy = RetryPolicy.from_env()
            if path_exists_with_retry(csv_path, policy=policy):
                df_csv = call_with_retry(
                    lambda: read_csv_strict(csv_path, contract_name='historico_processos.csv', policy=policy),
                    op_name="read_csv_strict",
                    path=csv_path,
                    policy=policy,
                )
                # Garantir ordenação (mais recente primeiro)
                if 'data_hora' in df_csv.columns:
                    df_csv = df_csv.sort_values(by='data_hora', ascending=False)
                if limit:
                    df_csv = df_csv.head(limit)
                return df_csv
            return None
        except Exception as e:
            registrar_log("DB Utils", f"Erro ao ler histórico do CSV: {e}", "ERROR")
            return None
        
    try:
        query = "SELECT * FROM historico_processos ORDER BY data_hora DESC"
        if limit:
            query += f" LIMIT {limit}"
            
        df = pd.read_sql_query(query, conn)
        return df
    except Exception as e:
        registrar_log("DB Utils", f"Erro ao obter histórico do DB: {e}", "ERROR")
        return None
    finally:
        if conn:
            conn.close()
