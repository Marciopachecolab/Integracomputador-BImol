import os
import shutil
import threading
import uuid
import pandas as pd
from utils.logger import registrar_log
from utils.csv_lock import CSVFileLock


class CSVLockManager:
    """
    Gerencia concorrencia para arquivos CSV em ambiente de rede.
    Implementa File Locking simples e Atomic Writes.
    Usa CSVFileLock (utils) como mecanismo canonico de lock.
    """

    def __init__(self, timeout_seconds: int = 10, stale_lock_minutes: int = 5, delay_seconds: float = 0.5):
        self.timeout = timeout_seconds
        self.delay = delay_seconds
        self.stale_after_seconds = int(stale_lock_minutes * 60)
        self._active_locks = {}

    def _get_lock_path(self, filepath: str) -> str:
        """Gera o caminho do arquivo de lock (.lock)."""
        return f"{filepath}.lock"

    def _lock_key(self, filepath: str) -> tuple:
        return (os.path.abspath(filepath), threading.get_ident())

    def acquire(self, filepath: str) -> bool:
        """
        Tenta adquirir o lock para um arquivo.
        Retorna True se conseguiu, False se estourou o timeout.
        """
        lock = CSVFileLock(
            filepath,
            timeout=self.timeout,
            delay=self.delay,
            stale_after_seconds=self.stale_after_seconds,
        )
        key = self._lock_key(filepath)

        try:
            lock.__enter__()
            self._active_locks[key] = lock
            return True
        except TimeoutError:
            registrar_log("CSVLock", f"Timeout ao tentar adquirir lock para {filepath}", "ERROR")
            return False
        except Exception as e:
            registrar_log("CSVLock", f"Erro inesperado ao adquirir lock: {e}", "ERROR")
            return False

    def release(self, filepath: str):
        """Libera o lock (remove o arquivo de lock)."""
        key = self._lock_key(filepath)
        lock = self._active_locks.pop(key, None)
        if lock:
            try:
                lock.__exit__(None, None, None)
                return
            except Exception as e:
                registrar_log("CSVLock", f"Erro ao liberar lock {filepath}: {e}", "ERROR")

        lock_path = self._get_lock_path(filepath)
        try:
            if os.path.exists(lock_path):
                try:
                    os.remove(lock_path)
                except IsADirectoryError:
                    shutil.rmtree(lock_path, ignore_errors=True)
        except Exception as e:
            registrar_log("CSVLock", f"Erro ao liberar lock {lock_path}: {e}", "ERROR")

    def write_locked_dataframe(self, df: pd.DataFrame, filepath: str, **kwargs) -> bool:
        """
        Escreve DataFrame atomicamente (temp + rename), assumindo que o lock JA foi adquirido externamente.
        NAO adquire nem libera o lock.
        """
        temp_path = f"{filepath}.tmp.{uuid.uuid4().hex}"

        try:
            # FIX: Se for append (mode='a'), precisamos copiar o arquivo original para o temp
            # antes de escrever os novos dados, senao o arquivo sera recriado do zero
            # contendo APENAS os novos dados (perda de dados).
            mode = kwargs.get('mode', 'w')
            if 'a' in mode and os.path.exists(filepath):
                try:
                    shutil.copy2(filepath, temp_path)
                except Exception as copy_error:
                    registrar_log("CSVLock", f"Erro ao copiar arquivo original para temp: {copy_error}", "ERROR")
                    return False

            # Forca encoding utf-8 se nao especificado
            kwargs['encoding'] = kwargs.get('encoding', 'utf-8')

            # Escreve no temporario (agora seguro para append)
            df.to_csv(temp_path, **kwargs)

            # Atomicidade do rename garantida pelo OS.
            if os.path.exists(filepath):
                os.replace(temp_path, filepath)
            else:
                os.rename(temp_path, filepath)

            return True

        except Exception as e:
            registrar_log("CSVLock", f"Erro na escrita atomica de {filepath}: {e}", "ERROR")
            # Tenta limpar o temp
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except (OSError, PermissionError) as cleanup_error:
                    registrar_log("CSVLock", f"Erro ao remover arquivo temporario {temp_path}: {cleanup_error}", "WARNING")
            return False

    def atomic_write_dataframe(self, df: pd.DataFrame, filepath: str, **kwargs) -> bool:
        """
        Escreve um DataFrame de forma atomica e segura.
        1. Adquire Lock
        2. Escreve em .tmp
        3. Renomeia .tmp para original (replace)
        4. Libera Lock
        """
        if not self.acquire(filepath):
            return False

        try:
            return self.write_locked_dataframe(df, filepath, **kwargs)

        finally:
            self.release(filepath)


# Instancia global
csv_lock = CSVLockManager()
