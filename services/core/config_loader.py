from __future__ import annotations

import csv

from pathlib import Path

from typing import Dict, Optional

from services.path_resolver import resolve_banco_dir





"""

services.config_loader

----------------------



Camada única de acesso aos arquivos de metadados em CSV do Integragal.



Responsabilidades principais:

- Carregar os CSVs de metadados da pasta ``banco/``.

- Indexar cada arquivo em dicionários em memória (cache simples).

- Expor funções de conveniência como ``obter_config_exame(...)`` etc.



Este módulo é propositalmente simples para minimizar pontos de falha

e facilitar a auditoria das configurações.

"""



# Linha comentada devido a alerta do ruff (E402): import em nível de módulo não posicionado no topo do arquivo.

# import csv

# Linha comentada devido a alerta do ruff (E402): import em nível de módulo não posicionado no topo do arquivo.

# from pathlib import Path

# Linha comentada devido a alerta do ruff (E402): import em nível de módulo não posicionado no topo do arquivo.

# from typing import Dict, Optional



# ---------------------------------------------------------------------------

# Localização dos arquivos de metadados

# ---------------------------------------------------------------------------



# Estrutura esperada:

#   Integragal/

#     services/

#       config_loader.py  <-- este arquivo

#     banco/

#       exames_metadata.csv

#       equipamentos_metadata.csv

#       placas_metadata.csv

#       regras_analise_metadata.csv

#

# BASE_DIR = pasta raiz do projeto (Integragal/)





# Caches em memória para evitar leituras repetidas de disco

_exames_cache: Optional[Dict[str, Dict[str, str]]] = None

_equipamentos_cache: Optional[Dict[str, Dict[str, str]]] = None

_placas_cache: Optional[Dict[str, Dict[str, str]]] = None

_regras_cache: Optional[Dict[str, Dict[str, str]]] = None





# ---------------------------------------------------------------------------

# Funções internas de suporte

# ---------------------------------------------------------------------------





def _carregar_csv_para_dict(caminho: Path, chave: str) -> Dict[str, Dict[str, str]]:

    """

    Lê um CSV simples (separado por vírgula) e indexa por uma coluna-chave.



    :param caminho: Caminho completo para o arquivo CSV.

    :param chave: Nome da coluna a ser usada como chave do dicionário.

    :return: dicionário no formato

             { valor_chave: {coluna: valor_str, ...}, ... }.

    """

    dados: Dict[str, Dict[str, str]] = {}



    if not caminho.exists():

        # Arquivo ainda não criado ou não disponível.

        # A decisão aqui é falhar de forma silenciosa e retornar dict vazio;

        # quem chama decide se isso é aceitável ou não.

        return dados



    with caminho.open("r", encoding="utf-8-sig", newline="") as f:

        reader = csv.DictReader(f)

        for row in reader:

            if row is None:

                continue

            k = (row.get(chave) or "").strip()

            if not k:

                continue

            # Normaliza todos os valores como string (strip) para evitar

            # problemas de espaços e valores None.

            dados[k] = {col: (val or "").strip() for col, val in row.items()}



    return dados





# ---------------------------------------------------------------------------

# Carregamento (lazy) dos CSVs

# ---------------------------------------------------------------------------





def _banco_dir() -> Path:
    """Resolve o diretorio de metadados (banco/) via config_service."""
    return resolve_banco_dir()


def carregar_exames_metadata() -> Dict[str, Dict[str, str]]:

    """

    Retorna o dicionário de metadados de exames, indexado por ``exame``.

    """

    global _exames_cache

    if _exames_cache is None:

        caminho = _banco_dir() / "exames_metadata.csv"

        _exames_cache = _carregar_csv_para_dict(caminho, chave="exame")

    return _exames_cache









def carregar_configuracoes_exames() -> Dict[str, Dict[str, str]]:

    """Alias de compatibilidade: retorna os metadados de exames.



    Mantido para compatibilidade com versões anteriores do AnalysisService,

    que ainda utilizam o nome ``carregar_configuracoes_exames``.

    """

    return carregar_exames_metadata()



def carregar_equipamentos_metadata() -> Dict[str, Dict[str, str]]:

    """

    Retorna o dicionário de metadados de equipamentos, indexado por ``equipamento``.

    """

    global _equipamentos_cache

    if _equipamentos_cache is None:

        caminho = _banco_dir() / "equipamentos_metadata.csv"

        _equipamentos_cache = _carregar_csv_para_dict(caminho, chave="equipamento")
        for row in _equipamentos_cache.values():
            row.setdefault("source_of_truth", "legacy_equipment_metadata_csv")
            row.setdefault("legacy_deprecation", "E07")

    return _equipamentos_cache





def carregar_placas_metadata() -> Dict[str, Dict[str, str]]:

    """

    Retorna o dicionário de metadados de tipos de placa, indexado por ``tipo_placa``.

    """

    global _placas_cache

    if _placas_cache is None:

        caminho = _banco_dir() / "placas_metadata.csv"

        _placas_cache = _carregar_csv_para_dict(caminho, chave="tipo_placa")

    return _placas_cache





def carregar_regras_analise_metadata() -> Dict[str, Dict[str, str]]:

    """

    Retorna o dicionário de metadados de regras de análise, indexado por ``exame``.

    """

    global _regras_cache

    if _regras_cache is None:

        caminho = _banco_dir() / "regras_analise_metadata.csv"

        _regras_cache = _carregar_csv_para_dict(caminho, chave="exame")

    return _regras_cache





# ---------------------------------------------------------------------------

# Funções públicas de acesso às configurações

# ---------------------------------------------------------------------------





def obter_config_exame(nome_exame: str) -> Optional[Dict[str, str]]:

    """

    Retorna o dicionário de configuração para um exame específico.



    :param nome_exame: Valor da coluna ``exame`` em exames_metadata.csv.

    """

    if not nome_exame:

        return None

    return carregar_exames_metadata().get(nome_exame)





def obter_config_equipamento(nome_equipamento: str) -> Optional[Dict[str, str]]:

    """

    Retorna o dicionário de configuração para um equipamento específico.



    :param nome_equipamento: Valor da coluna ``equipamento`` em

                             equipamentos_metadata.csv.

    """

    if not nome_equipamento:

        return None

    return carregar_equipamentos_metadata().get(nome_equipamento)





def obter_config_placa(tipo_placa: str) -> Optional[Dict[str, str]]:

    """

    Retorna o dicionário de configuração para um tipo de placa específico.



    :param tipo_placa: Valor da coluna ``tipo_placa`` em placas_metadata.csv.

    """

    if not tipo_placa:

        return None

    return carregar_placas_metadata().get(tipo_placa)





def obter_regras_analise(exame: str) -> Optional[Dict[str, str]]:

    """

    Retorna o dicionário de regras de análise para um exame específico.



    :param exame: Valor da coluna ``exame`` em regras_analise_metadata.csv.

    """

    if not exame:

        return None

    return carregar_regras_analise_metadata().get(exame)





# ---------------------------------------------------------------------------

# Funções auxiliares opcionais

# ---------------------------------------------------------------------------





def limpar_caches() -> None:

    """

    Limpa todos os caches em memória.



    Útil em cenários de recarga dinâmica de configurações sem reiniciar o

    aplicativo (por exemplo, durante testes).

    """

    global _exames_cache, _equipamentos_cache, _placas_cache, _regras_cache

    _exames_cache = None

    _equipamentos_cache = None

    _placas_cache = None

    _regras_cache = None
