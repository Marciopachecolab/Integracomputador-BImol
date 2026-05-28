# -*- coding: utf-8 -*-
"""
CSV Lock - Mecanismo de Bloqueio para Ambientes Compartilhados
Implementa trava atômica para evitar corrupção ao escrever em CSVs via rede.
"""

import os
import time
from pathlib import Path


_logging_in_progress = False


def _log(msg: str, level: str = "INFO"):
    global _logging_in_progress
    if _logging_in_progress:
        try:
            print(f"[CSVLock][{level}] {msg}")
        except Exception:
            pass
        return

    try:
        _logging_in_progress = True
        from utils.logger import registrar_log
        registrar_log("CSVLock", msg, level)
    except Exception:
        try:
            print(f"[CSVLock][{level}] {msg}")
        except Exception:
            pass
    finally:
        _logging_in_progress = False

class CSVFileLock:
    """
    Implementação simples de lock de arquivo usando atomicidade de criação (O_EXCL).
    O_CREAT | O_EXCL no nível de sistema operacional garante que apenas um 
    processo consiga criar o arquivo.
    """
    def __init__(self, file_path, timeout=15, delay=0.2, stale_after_seconds: int = 60):
        self.file_path = Path(file_path)
        self.lock_path = self.file_path.with_suffix(self.file_path.suffix + ".lock")
        self.timeout = timeout
        self.delay = delay
        self.stale_after_seconds = stale_after_seconds
        self.is_locked = False

    def __enter__(self):
        start_time = time.time()
        while time.time() - start_time < self.timeout:
            try:
                # O_CREAT | O_EXCL falha se o arquivo já existir (atômico no Win/Linux)
                fd = os.open(str(self.lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.close(fd)
                self.is_locked = True
                return self
            except FileExistsError:
                # Verificação de STALE LOCK (bloqueio órfão)
                try:
                    mtime = os.path.getmtime(self.lock_path)
                    if time.time() - mtime > self.stale_after_seconds:
                        _log(f"Removendo lock estagnado: {self.lock_path}", "WARNING")
                        os.remove(self.lock_path)
                        continue
                except Exception:
                    pass
                time.sleep(self.delay)
            except Exception as e:
                # Outros erros (ex: permissão negada na rede)
                _log(f"Erro ao tentar lock: {e}", "DEBUG")
                time.sleep(self.delay)
        
        _log(f"Timeout ({self.timeout}s) ao obter lock para {self.file_path}", "ERROR")
        raise TimeoutError(f"O arquivo {self.file_path.name} está sendo usado por outro usuário.")

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.is_locked:
            try:
                if os.path.exists(self.lock_path):
                    os.remove(self.lock_path)
                self.is_locked = False
            except Exception as e:
                _log(f"Erro fatal ao remover lock {self.lock_path}: {e}", "CRITICAL")
