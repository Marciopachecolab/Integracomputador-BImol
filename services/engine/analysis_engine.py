"""Motor de analise PCR com compatibilidade ao fluxo oficial."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from config.enums import ResultStatus
from domain.ct_rules import classificar_ct as classificar_ct_domain
from services.analysis.analysis_helpers import identificar_colunas_pcr
from services.analysis.analysis_runtime_contract import (
    build_protocol_and_rules_from_cfg,
)
from services.exam_domain_contracts import uses_default_viral_rule
from services.analysis.analysis_runtime_rollout import resolve_runtime_rollout_decision
from services.engine.config_loader import ConfigLoader
from services.core.runtime_flags import is_analysis_runtime_registry_rules_enabled
from services.engine.data_cleaner import DataCleaner
from services.exam_registry import get_exam_cfg
from services.analysis.rules_engine import aplicar_regras
from utils.logger import registrar_log


def _log_processar_exame_usage(event: str, **payload: Any) -> None:
    """Telemetria runtime para monitorar uso real de AnalysisEngine.processar_exame."""
    parts = ["feature=analysis_engine.processar_exame", f"event={event}"]
    for key, value in payload.items():
        parts.append(f"{key}={value}")
    registrar_log("RuntimeUsage", " ".join(parts), "INFO")


class AnalysisEngine:
    """
    Motor universal de análise de PCR.
    
    Fluxo de Execução:
    1. Recebe arquivo bruto.
    2. Detecta ou recebe Perfil de Equipamento.
    3. Normaliza dados (Clean).
    4. Carrega Protocolo e Regras.
    5. Aplica interpretação (Ct -> Resultado).
    6. Valida Controles e Corrida.
    """

    def __init__(self) -> None:
        self.protocols: Dict[str, Dict[str, Any]] = {
            p["id"]: p for p in ConfigLoader.get_protocols()
        }
        self.rules_db: Dict[str, Dict[str, Any]] = {
            r["protocol_id"]: r for r in ConfigLoader.get_analysis_rules()
        }

    @staticmethod
    def _safe_float(value: Any, default: float) -> float:
        try:
            return float(value)
        except Exception:
            return default

    def _build_protocol_rules_from_cfg(self, protocol_id: str) -> tuple[Dict[str, Any], Dict[str, Any]] | tuple[None, None]:
        cfg = get_exam_cfg(protocol_id)
        return build_protocol_and_rules_from_cfg(
            cfg,
            protocol_id=protocol_id,
        )

    def _resolve_protocol_rules_runtime(self, protocol_id: str) -> tuple[Dict[str, Any] | None, Dict[str, Any] | None, str]:
        requested_enabled = is_analysis_runtime_registry_rules_enabled()
        rollout_decision = resolve_runtime_rollout_decision(requested_enabled=requested_enabled)
        if rollout_decision.get("effective_runtime_enabled", False):
            protocol_cfg, rules_cfg = self._build_protocol_rules_from_cfg(protocol_id)
            if protocol_cfg and rules_cfg:
                return protocol_cfg, rules_cfg, "registry_runtime_rules"
        if requested_enabled and rollout_decision.get("promotion_status") == "BLOCKED":
            return self.protocols.get(protocol_id), self.rules_db.get(protocol_id), "legacy_json_rules_gate_blocked"
        if (
            requested_enabled
            and rollout_decision.get("promotion_status") == "APPROVED"
            and not rollout_decision.get("effective_runtime_enabled", False)
        ):
            return self.protocols.get(protocol_id), self.rules_db.get(protocol_id), "legacy_json_rules_canary_hold"
        if requested_enabled and rollout_decision.get("shadow_compare_enabled", False):
            return self.protocols.get(protocol_id), self.rules_db.get(protocol_id), "legacy_json_rules_shadow_mode"
        return self.protocols.get(protocol_id), self.rules_db.get(protocol_id), "legacy_json_rules"

    def processar_exame(
        self,
        exame: str,
        df_resultados: pd.DataFrame,
        df_extracao: Optional[pd.DataFrame] = None,
        lote: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Processa um DataFrame de resultados e retorna estrutura padronizada.

        Args:
            exame: Nome do exame.
            df_resultados: DataFrame com resultados brutos.
            df_extracao: DataFrame de extracao (nao utilizado neste motor).
            lote: Identificador do lote.

        Returns:
            Dicionario com amostras, controles, metadados e regras aplicadas.

        Raises:
            ValueError: Quando colunas essenciais nao sao encontradas.
        """
        _ = df_extracao
        _log_processar_exame_usage(
            "function_invoked",
            exame=str(exame or ""),
            rows=int(len(df_resultados)) if hasattr(df_resultados, "__len__") else 0,
            has_extracao=bool(df_extracao is not None),
            has_lote=bool(lote),
        )

        def _safe_float(val: Any) -> Optional[float]:
            if val is None:
                return None
            try:
                if pd.isna(val):
                    return None
            except Exception:
                pass
            s = str(val).strip().upper()
            if s in ("", "NA", "N/A", "UNDETERMINED", "UND", "N/D"):
                return None
            try:
                return float(s.replace(",", "."))
            except Exception:
                return None

        def _map_ct_result(ct_val: Optional[float]) -> str:
            """Mapeia CT para resultado textual consistente."""
            status = classificar_ct_domain(ct_val)
            if status == ResultStatus.DETECTAVEL:
                return "Detectado"
            if status == ResultStatus.INDETERMINADO:
                return "Inconclusivo"
            return "Nao Detectado"

        cfg = None
        try:
            cfg = get_exam_cfg(exame)
        except Exception:
            cfg = None

        metadata: Dict[str, Any] = {
            "exame": exame,
            "equipamento": getattr(cfg, "equipamento", "")
            if cfg
            else ("7500" if "7500" in exame.lower() else ""),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "lote": lote or "",
        }

        if df_resultados is None or getattr(df_resultados, "empty", True):
            regras_resultado = aplicar_regras({}, {"alvos": {}})
            _log_processar_exame_usage("empty_input", exame=str(exame or ""))
            return {
                "amostras": [],
                "controles": {},
                "metadata": metadata,
                "valido": False,
                "regras_resultado": regras_resultado,
            }

        try:
            col_map = identificar_colunas_pcr(df_resultados)
        except ValueError as exc:
            registrar_log("AnalysisEngine", str(exc), "ERROR")
            _log_processar_exame_usage("column_detection_error", exame=str(exame or ""))
            raise

        col_well = col_map["well"]
        col_sample = col_map.get("sample")
        col_target = col_map["target"]
        col_ct = col_map["ct"]

        if not col_sample:
            registrar_log(
                "AnalysisEngine",
                "Coluna Sample nao encontrada. Usando Well como fallback.",
                "WARNING",
            )

        sample_series = df_resultados[col_sample] if col_sample else df_resultados[col_well]

        df_norm = pd.DataFrame()
        df_norm["well"] = df_resultados[col_well].astype(str).str.strip().str.upper()
        df_norm["sample_name"] = sample_series.astype(str).str.strip()
        df_norm["target_name"] = df_resultados[col_target].astype(str).str.strip().str.upper()
        df_norm["ct"] = df_resultados[col_ct].apply(_safe_float)

        amostras: List[Dict[str, Any]] = []
        controles: Dict[str, List[str]] = {"cn": [], "cp": []}
        alvos_dict_global: Dict[str, Dict[str, Any]] = {}

        for sample_name, group in df_norm.groupby("sample_name", dropna=False):
            sample_name = "" if pd.isna(sample_name) else str(sample_name).strip()
            targets: Dict[str, Dict[str, Any]] = {}
            for _, row in group.iterrows():
                target = str(row.get("target_name", "")).strip()
                ct_val = row.get("ct", None)
                if not target:
                    continue
                if target not in targets:
                    res = _map_ct_result(ct_val)
                    targets[target] = {"ct": ct_val, "resultado": res}

            amostras.append(
                {
                    "id": sample_name,
                    "nome": sample_name,
                    "alvos": targets,
                }
            )

            # controles simples
            upper = sample_name.upper()
            if any(k in upper for k in ("CTRL_NEG", "CN", "CONTROL NEG", "NEG")):
                controles["cn"].append(sample_name)
            if any(k in upper for k in ("CTRL_POS", "CP", "CONTROL POS", "POS")):
                controles["cp"].append(sample_name)

            # acumula alvos globais para regras
            for alvo, dados in targets.items():
                alvos_dict_global.setdefault(alvo, dados)

        # aplicar regras (se houver configuracao)
        regras_cfg: Dict[str, Any] = {}
        try:
            regras_cfg = getattr(cfg, "regras", None) or {}
        except Exception:
            regras_cfg = {}

        regras_resultado = aplicar_regras(regras_cfg or {}, {"alvos": alvos_dict_global})

        result = {
            "amostras": amostras,
            "controles": controles,
            "metadata": metadata,
            "valido": True,
            "regras_resultado": regras_resultado,
        }
        _log_processar_exame_usage(
            "success",
            exame=str(exame or ""),
            samples=int(len(amostras)),
            cn=int(len(controles.get("cn", []))),
            cp=int(len(controles.get("cp", []))),
        )
        return result

    def process_file(
        self,
        file_path: str,
        protocol_id: str,
        equipment_profile_id: Optional[str] = None,
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Executa o fluxo completo de analise a partir de arquivo.

        Args:
            file_path: Caminho do arquivo de entrada.
            protocol_id: Identificador do protocolo.
            equipment_profile_id: Perfil do equipamento (opcional).

        Returns:
            Tupla com DataFrame resultado e relatorio de validacao.

        Raises:
            ValueError: Quando protocolo, regras ou perfil nao sao encontrados.
            Exception: Para falhas nao previstas durante a execucao.
        """
        try:
            # 1. Configurar Perfil de Equipamento
            profile = self._get_profile(file_path, equipment_profile_id)
            if not profile:
                raise ValueError("Nao foi possivel identificar o perfil do equipamento.")

            # 2. Carregar e Limpar Dados
            cleaner = DataCleaner(profile)

            # TODO (v2.1.0): Suporte a xlsx nativo via pandas
            # NOTA: Funcionalidade disponivel, requer 'pip install openpyxl'
            # Atualmente converte xlsx -> csv temporario (funcional mas nao ideal)
            # Ver documentacao: https://pandas.pydata.org/docs/reference/io.html#excel
            if str(file_path).endswith('.xlsx'):
                df_raw = pd.read_excel(file_path)
            else:
                df_raw = pd.read_csv(
                    file_path,
                    encoding=profile["data_cleaning"].get("encoding", "utf-8"),
                )

            df_norm = cleaner.clean_dataframe(df_raw)

            # 3. Carregar Protocolo/Regras (rota canônica com fallback legado)
            protocol, rules_cfg, route_mode = self._resolve_protocol_rules_runtime(protocol_id)
            if not protocol:
                raise ValueError(f"Protocolo {protocol_id} nao encontrado.")
            if not rules_cfg:
                raise ValueError(f"Regras para {protocol_id} nao encontradas.")
            registrar_log(
                "AnalysisEngine",
                f"Runtime de regras aplicado ({route_mode}) para protocolo={protocol_id}",
                "INFO",
            )

            # 4. Interpretar Resultados (Pivotar e Avaliar)
            df_result = self._evaluate_results(df_norm, protocol, rules_cfg)

            # 5. Validar Corrida e Amostras
            report = self._validate_run(df_result, protocol)

            return df_result, report

        except Exception as e:
            registrar_log("AnalysisEngine", f"Falha fatal na analise: {e}", "CRITICAL")
            raise

    def _get_profile(
        self, file_path: str, profile_id: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """Obtem perfil explicito ou auto-detectado.

        Args:
            file_path: Caminho do arquivo de entrada.
            profile_id: Identificador do perfil (opcional).

        Returns:
            Perfil encontrado ou None.
        """
        if profile_id:
            for p in ConfigLoader.get_equipment_profiles():
                if p["id"] == profile_id:
                    return p
        return ConfigLoader.get_profile_by_signature(file_path)

    def _evaluate_results(
        self,
        df: pd.DataFrame,
        protocol: Dict[str, Any],
        rules_cfg: Dict[str, Any],
    ) -> pd.DataFrame:
        """Aplica regras de Ct para determinar resultado categorico.

        Args:
            df: DataFrame normalizado.
            protocol: Protocolo carregado.
            rules_cfg: Configuracoes de regras.

        Returns:
            DataFrame com resultados avaliados.
        """

        # Mapear regras por alvo
        rules_map: Dict[str, Dict[str, Any]] = {}  # target -> rule_list
        for r in rules_cfg["rules"]:
            tgt = r.get("target")
            if tgt:
                rules_map[tgt] = r

        results: List[Dict[str, Any]] = []

        # Agrupar por Amostra
        for sample_id, group in df.groupby("sample_id"):
            row = {"Amostra": sample_id}
            well = group["well"].iloc[0] if "well" in group.columns else ""
            row["Poco"] = well

            # Dicionario temporario de resultados deste sample para validacao cruzada
            sample_results: Dict[str, Any] = {}

            # Iterar alvos definidos no protocolo
            targets_def = protocol.get("targets_configuration", {})

            for target_name, target_meta in targets_def.items():
                # Encontrar dado correspondente no dataframe
                # Tentar match exato ou case-insensitive
                match = group[group["target_name"] == target_name]
                if match.empty:
                    # Se nao achou exato, tenta ignorar case
                    match = group[group["target_name"].str.upper() == target_name.upper()]

                # Valor Ct
                ct_val = match["ct_value"].iloc[0] if not match.empty else None

                # Armazena Ct na linha
                row[target_name] = ct_val

                # Aplicar Regra
                rule = rules_map.get(target_name)
                # Fallback para regras genericas (ex: 'DEFAULT_VIRAL')
                if not rule and uses_default_viral_rule(target_meta.get("type")):
                    rule = rules_map.get("DEFAULT_VIRAL")

                result_status = "N/A"
                if rule:
                    result_status = self._apply_rule(ct_val, rule)

                col_res = f"Resultado_{target_name}"
                row[col_res] = result_status
                sample_results[target_name] = result_status

            results.append(row)

        return pd.DataFrame(results)

    def _apply_rule(self, ct_val: Optional[float], rule: Dict[str, Any]) -> str:
        """Avalia um unico valor Ct contra uma regra.

        Args:
            ct_val: Valor de Ct.
            rule: Regra configurada.

        Returns:
            Resultado aplicado pela regra.
        """
        default = rule.get("default_result", "ND")

        if ct_val is None:
            # Verifica se regra trata especificamente Nulos (ex: "se nulo -> ND")
            # Por padrao, assume default da regra se for nulo
            return default

        for cond in rule.get("conditions", []):
            rng = cond.get("range")  # [min, max]
            if rng:
                min_v, max_v = rng
                if min_v <= ct_val <= max_v:
                    return cond["result"]

        return default

    def _validate_run(self, df: pd.DataFrame, protocol: Dict[str, Any]) -> Dict[str, Any]:
        """Valida controles da corrida (CN, CP) e regras de amostra.

        Args:
            df: DataFrame de resultados.
            protocol: Protocolo carregado.

        Returns:
            Dicionario com status e detalhes da validacao.
        """
        meta = protocol.get("validation_rules", {})
        run_rules = meta.get("run_validation", [])

        status = "Valida"
        issues = []

        # 1. Validar Controles da Placa
        for rule in run_rules:
            rtype = rule.get("rule")
            target_type = rule.get("target")  # CN ou CP
            severity = rule.get("severity", "WARNING")  # NEW: FATAL vs WARNING

            if rtype == "CONTROL_EXISTS":
                # Busca heuristica por amostras de controle
                keywords = ["CN", "NEG", "NTC"] if target_type == "CN" else ["CP", "POS"]

                found = False
                for _, row in df.iterrows():
                    sname = str(row.get("Amostra", "")).upper()
                    if any(k in sname for k in keywords):
                        found = True
                        break

                if not found:
                    msg = rule.get("error_msg", f"{target_type} nao encontrado")
                    issues.append(msg)
                    if severity == "FATAL":
                        status = "Invalida"

        return {
            "status": status,
            "details": "; ".join(issues) if issues else "Corrida Aprovada",
        }
