# -*- coding: utf-8 -*-
"""Implementacao inicial do AnalysisOrchestratorPort (Fase B2-T01)."""

from __future__ import annotations

from typing import Any, Callable

from models import AppState
from services.analysis.analysis_service import AnaliseResultado, AnalysisService
from services.core.runtime_flags import is_contract_analysis_runtime_enabled

from application.analysis_orchestrator_port import (
    AnalysisExecutionError,
    AnalysisOrchestratorPort,
    AnalysisOrchestratorRequestDTO,
    AnalysisOrchestratorResponseDTO,
    InputFileError,
)


class AnalysisOrchestrator(AnalysisOrchestratorPort):
    """Orquestrador de analise desacoplado da UI."""

    def __init__(
        self,
        app_state: AppState,
        analysis_service: AnalysisService | None = None,
        runtime_flag_resolver: Callable[[str | None], bool] | None = None,
    ) -> None:
        self._app_state = app_state
        self._analysis_service = analysis_service or AnalysisService(app_state)
        self._runtime_flag_resolver = runtime_flag_resolver

    def execute(
        self,
        request: AnalysisOrchestratorRequestDTO,
    ) -> AnalysisOrchestratorResponseDTO:
        self._sync_state(request)
        try:
            analise = self._run_analysis(request)
        except FileNotFoundError as exc:
            raise InputFileError(str(exc)) from exc
        except InputFileError:
            raise
        except Exception as exc:
            raise AnalysisExecutionError(str(exc)) from exc
        return self._build_response(analise)

    def _sync_state(self, request: AnalysisOrchestratorRequestDTO) -> None:
        self._app_state.exame_selecionado = request.exam_name
        self._app_state.lote = request.lote
        setattr(self._app_state, "data_exame", request.data_exame)
        setattr(self._app_state, "caminho_arquivo_corrida", str(request.resultado_path))
        if request.usuario:
            self._app_state.usuario_logado = request.usuario
        if request.equipment_hint:
            self._app_state.tipo_de_placa_selecionado = request.equipment_hint
        if (
            getattr(self._app_state, "dados_extracao", None) is not None
            and getattr(self._app_state, "df_gabarito_extracao", None) is None
        ):
            self._app_state.df_gabarito_extracao = self._app_state.dados_extracao

    def _run_analysis(self, request: AnalysisOrchestratorRequestDTO) -> AnaliseResultado:
        runtime_flag_enabled = (
            self._runtime_flag_resolver(request.usuario or None)
            if self._runtime_flag_resolver is not None
            else is_contract_analysis_runtime_enabled(user_id=request.usuario or None)
        )
        if runtime_flag_enabled:
            return self._analysis_service.analisar_corrida_v2(
                exame=request.exam_name,
                arquivo_resultados=request.resultado_path,
                arquivo_extracao=request.extracao_path,
                lote=request.lote,
            )
        return self._analysis_service.analisar_corrida(
            exame=request.exam_name,
            arquivo_resultados=request.resultado_path,
            arquivo_extracao=request.extracao_path,
            lote=request.lote,
        )

    def _build_response(self, analise: AnaliseResultado) -> AnalysisOrchestratorResponseDTO:
        metadados = getattr(analise, "metadados", {}) or {}
        if not isinstance(metadados, dict):
            metadados = {}
        return AnalysisOrchestratorResponseDTO(
            df_resultado=analise.df_processado,
            status_corrida=self._extract_status(analise.df_processado),
            metadados=dict(metadados),
            contract_versions=self._extract_contract_versions(metadados),
        )

    def _extract_contract_versions(self, metadados: dict[str, Any]) -> dict[str, str]:
        versions = getattr(self._app_state, "contract_versions", None)
        if isinstance(versions, dict):
            return {str(k): str(v) for k, v in versions.items()}
        from_metadata = metadados.get("contract_versions")
        if isinstance(from_metadata, dict):
            return {str(k): str(v) for k, v in from_metadata.items()}
        return {}

    @staticmethod
    def _extract_status(df_resultado) -> str:
        if df_resultado is None or df_resultado.empty:
            return "Indefinido"
        if "Status_Placa" in df_resultado.columns:
            values = [
                str(value).strip()
                for value in df_resultado["Status_Placa"].dropna().tolist()
                if str(value).strip()
            ]
            if not values:
                return "Indefinido"
            unique = sorted(set(values))
            if len(unique) == 1:
                return unique[0]
            return "Misto"
        return "Indefinido"
