# -*- coding: utf-8 -*-
"""
Secure Path Validator - Proteção contra Path Traversal (R1)

Implementa validação de paths para prevenir ataques de travessia de diretório.

CWE-22: Improper Limitation of a Pathname to a Restricted Directory
"""

from pathlib import Path
from typing import Union
import os


class SecurityError(Exception):
    """Exceção levantada quando path inseguro é detectado."""
    pass


class SecurePath:
    """
    Validador de paths seguro para prevenir Path Traversal.
    
    Garante que todos os paths estejam dentro do diretório base do projeto
    OU dentro de raízes adicionais permitidas (allowed_roots).
    
    Uso:
        validator = SecurePath()
        safe_path = validator.validate("logs/historico.csv")  # OK
        safe_path = validator.validate("../../etc/passwd")     # SecurityError!
    """
    
    def __init__(
        self,
        base_dir: Union[str, Path] = None,
        allowed_roots: Union[None, list, tuple, set] = None,
    ):
        """
        Args:
            base_dir: Diretório base permitido (padrão: raiz do projeto)
            allowed_roots: Lista de raízes adicionais permitidas (opcional)
        """
        if base_dir is None:
            # Assumir que utils está em PROJECT_ROOT/utils
            self.base_dir = Path(__file__).parent.parent.resolve()
        else:
            self.base_dir = Path(base_dir).resolve()
        
        # Garantir que base_dir existe
        if not self.base_dir.exists():
            raise ValueError(f"Base directory does not exist: {self.base_dir}")

        roots = [self.base_dir]
        if allowed_roots:
            for root in allowed_roots:
                if not root:
                    continue
                try:
                    roots.append(Path(root).resolve())
                except Exception:
                    # Se houver erro de resolução, ignora este root
                    continue
        # Remove duplicados preservando ordem
        self.allowed_roots = list(dict.fromkeys(roots))
    
    def validate(self, path: Union[str, Path], create_parents: bool = False) -> Path:
        """
        Valida e resolve path, garantindo que está dentro de um root permitido.
        
        Args:
            path: Path a ser validado (relativo ou absoluto)
            create_parents: Se True, cria diretórios pais se não existirem
        
        Returns:
            Path absoluto validado
        
        Raises:
            SecurityError: Se path está fora de base_dir
            
        Examples:
            >>> validator = SecurePath("/home/user/projeto")
            >>> validator.validate("data/output.csv")
            Path('/home/user/projeto/data/output.csv')
            
            >>> validator.validate("../../../etc/passwd")
            SecurityError: Path traversal detected
        """
        # Converter para Path e resolver (normaliza .., ., etc.)
        if isinstance(path, str):
            path_obj = Path(path)
        else:
            path_obj = path
        
        # Se path é relativo, torná-lo absoluto relativo a base_dir
        if not path_obj.is_absolute():
            resolved_path = (self.base_dir / path_obj).resolve()
        else:
            resolved_path = path_obj.resolve()
        
        # VALIDAÇÃO CRÍTICA: Verificar se resolved_path está dentro de algum root permitido
        is_allowed = False
        for root in self.allowed_roots:
            try:
                resolved_path.relative_to(root)
                is_allowed = True
                break
            except ValueError:
                continue
        if not is_allowed:
            allowed_list = ", ".join(str(r) for r in self.allowed_roots)
            raise SecurityError(
                f"Path traversal detected: '{path}' resolves to '{resolved_path}' "
                f"which is outside allowed roots: {allowed_list}"
            )
        
        # Opcionalmente criar diretórios pais
        if create_parents and not resolved_path.parent.exists():
            resolved_path.parent.mkdir(parents=True, exist_ok=True)
        
        return resolved_path
    
    def validate_directory(self, path: Union[str, Path]) -> Path:
        """
        Valida que path é um diretório seguro.
        
        Similar a validate(), mas garante que é diretório.
        """
        validated = self.validate(path, create_parents=False)
        
        if validated.exists() and not validated.is_dir():
            raise SecurityError(f"Path exists but is not a directory: {validated}")
        
        return validated
    
    def safe_join(self, *parts: str) -> Path:
        """
        Junta partes de path de forma segura, validando resultado.
        
        Equivalente seguro de Path.joinpath()
        
        Example:
            >>> validator.safe_join("logs", "2026", "historico.csv")
            Path('/projeto/logs/2026/historico.csv')
        """
        joined = self.base_dir.joinpath(*parts)
        return self.validate(joined)


# Factory para obter validator global (Singleton)
_global_validator: SecurePath = None
_global_validator_key = None


def _normalize_root_value(root: Union[str, Path, None]) -> Union[str, None]:
    if root is None:
        return None
    try:
        root_str = os.path.expandvars(os.path.expanduser(str(root))).strip()
    except Exception:
        return None
    if not root_str:
        return None
    return root_str


def get_secure_path_validator(
    allowed_roots: Union[None, list, tuple, set] = None,
    base_dir: Union[str, Path, None] = None,
) -> SecurePath:
    """Retorna inst?ncia singleton do validador, considerando roots permitidos."""
    global _global_validator
    global _global_validator_key

    base_dir_norm = _normalize_root_value(base_dir) if base_dir else None
    allowed_norm = []
    if allowed_roots:
        for r in allowed_roots:
            r_norm = _normalize_root_value(r)
            if r_norm:
                allowed_norm.append(r_norm)

    key = (base_dir_norm, tuple(allowed_norm))
    if _global_validator is None or _global_validator_key != key:
        _global_validator = SecurePath(base_dir=base_dir_norm, allowed_roots=allowed_norm)
        _global_validator_key = key
    return _global_validator


def reset_secure_path_validator() -> None:
    """Reseta o singleton do validador (uso em testes)."""
    global _global_validator
    global _global_validator_key
    _global_validator = None
    _global_validator_key = None
