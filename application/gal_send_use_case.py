# -*- coding: utf-8 -*-
"""Caso de uso para orquestracao do envio GAL (U3)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Protocol, Set

import pandas as pd

from application.access_control import ensure_operation_allowed
from services.gal.gal_claims import (
    ClaimOutcome,
    GalClaimsPort,
    SqliteGalClaimsRepository,
    default_owner_token,
)


class GalSendServicePort(Protocol):
    """Porta minima usada pela orquestracao do envio GAL."""

    def realizar_login(self, driver: Any, usuario: str, senha: str) -> None: ...

    def ler_csv_resultados(self, csv_path: str) -> Optional[pd.DataFrame]: ...

    def buscar_metadados(
        self, driver: Any, codigos_amostra_set: Set[str], exam_cfg: Any = None
    ) -> Dict[str, Any]: ...

    def construir_payload(
        self, meta: Dict[str, Any], row: pd.Series, observacao_geral: str
    ) -> Dict[str, Any]: ...

    def enviar_amostra(self, driver: Any, payload: Dict[str, Any]) -> Dict[str, Any]: ...

    def build_idempotency_key(
        self,
        *,
        codigo_amostra: str,
        kit: str,
        lote_kit: str,
        data_exame: str,
        corrida_id: str = "",
        nome_corrida: str = "",
        arquivo_corrida: str = "",
        placa: str = "",
        parte_placa: object = "",
    ) -> str: ...

    def get_transaction_journal_path(self) -> Path: ...

    def load_successful_idempotency_keys(self, journal_path: Path) -> Set[str]: ...

    def get_user_access_level(self, username: str) -> Optional[str]: ...

    def append_journal_events(
        self,
        *,
        relatorio_local: list[dict[str, Any]],
        run_id: str,
        kit_default: str,
    ) -> int: ...

    def salvar_relatorios(
        self,
        relatorio_final: list[Dict[str, Any]],
        relatorio_local: list[Dict[str, Any]],
        usuario: str,
        observacao: str,
        kit: str,
        relatorio_filename: str,
        run_id: Optional[str] = None,
    ) -> None: ...


ProgressCallback = Callable[[str, float], None]

# CONC-003: validade (lease) de um claim de envio. Maior que o tempo maximo
# esperado de um envio individual; leases expirados podem ser recuperados.
_CLAIM_TTL_SECONDS = 300.0


@dataclass(frozen=True)
class GalSendRequest:
    """Dados de entrada do envio GAL."""

    csv_path: str
    usuario: str
    senha: str
    usuario_logado: str
    observacao: str
    relatorio_filename: str
    usuario_nivel: str = ""
    corrida_id: str = ""
    exame_id: str = ""
    lote: str = ""
    data_exame: str = ""
    arquivo_corrida: str = ""
    arquivo_extracao: str = ""
    parte_placa: int = 0
    numero_extracao: str = ""
    nome_corrida: str = ""
    quem_fez_extracao: str = ""
    quem_preparou_placa: str = ""
    observacoes_corrida: str = ""


@dataclass(frozen=True)
class GalSendResult:
    """Resumo de saida do caso de uso."""

    total_amostras: int
    sucessos: int
    kit: str
    relatorio_local: list[Dict[str, Any]]
    relatorio_final: list[Dict[str, Any]]


def _default_webdriver_factory() -> Any:
    """Cria instância Firefox com suporte a headless via config ou feature flag.

    Precedência: feature flag USE_GAL_FIREFOX_HEADLESS > gal_integration.headless (config).
    Rollback: desativar ambos para voltar ao modo visível.
    """
    # Import lazy de Selenium: mantem a camada de aplicacao importavel/testavel
    # sem o pacote instalado (a injecao de webdriver_factory cobre os testes).
    from seleniumrequests import Firefox
    from config.feature_flags import feature_flags as _ff
    from services.core.config_service import config_service as _cs
    _flag_headless = _ff.is_enabled("USE_GAL_FIREFOX_HEADLESS")
    # Default True: config.json não tem "headless" → oculta por padrão.
    # O operador desabilita explicitamente via Settings (grava "headless": false).
    _cfg_headless = bool(_cs.get_gal_config().get("headless", True))
    if _flag_headless or _cfg_headless:
        from selenium.webdriver.firefox.options import Options as _FxOpts
        opts = _FxOpts()
        opts.add_argument("--headless")
        return Firefox(options=opts)
    return Firefox()


def _service_log(service: Any, message: str, level: str = "info") -> None:
    """Encaminha log ao servico quando disponivel, senao usa logging padrao."""
    import logging as _logging
    log_fn = getattr(service, "log", None)
    if callable(log_fn):
        log_fn(message, level)
    else:
        lvl = getattr(_logging, level.upper(), _logging.INFO)
        _logging.getLogger(__name__).log(lvl, message)


class GalSendUseCase:
    """Orquestra o fluxo de envio sem acoplamento com widgets/UI."""

    def __init__(
        self,
        service: GalSendServicePort,
        *,
        webdriver_factory: Optional[Callable[[], Any]] = None,
        claims_repository: Optional[GalClaimsPort] = None,
    ) -> None:
        self._service = service
        self._webdriver_factory = webdriver_factory or _default_webdriver_factory
        self._claims_repository = claims_repository

    def execute(
        self,
        request: GalSendRequest,
        *,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> GalSendResult:
        total_steps = 6
        driver = None

        def _report(text: str, value: float) -> None:
            if progress_callback is not None:
                progress_callback(text, value)

        try:
            access_level = self._resolve_access_level(request)
            ensure_operation_allowed(
                "gal.send",
                access_level,
                actor_username=request.usuario_logado,
            )

            # S10: Validar CSV antes de abrir o browser — falha cedo sem custo de sessão
            _report("Passo 1/6: A validar arquivo CSV...", 1 / total_steps)
            df = self._service.ler_csv_resultados(request.csv_path)
            if df is None:
                raise ValueError("Arquivo CSV invalido ou vazio.")

            from services.exam_registry import get_exam_cfg
            exam_cfg = get_exam_cfg(request.exame_id) if request.exame_id else None

            # S11: Avisar sobre gal_exame_codigo ausente antes de abrir sessão
            gal_exame_codigo = getattr(exam_cfg, "gal_exame_codigo", "") if exam_cfg else ""
            if exam_cfg and not gal_exame_codigo:
                _service_log(
                    self._service,
                    f"[S11] AVISO: exame '{request.exame_id}' sem gal_exame_codigo configurado. "
                    "A busca de metadados usara apenas filtro de data — risco elevado de "
                    "'nao_encontrado'. Configure gal_exame_codigo no perfil do exame.",
                    "warning",
                )

            _report("Passo 2/6: A iniciar o navegador Firefox...", 2 / total_steps)
            driver = self._webdriver_factory()

            _report("Passo 3/6: A realizar login no GAL...", 3 / total_steps)
            self._service.realizar_login(driver, request.usuario, request.senha)
            # 7.2: Confirmação explícita de login no terminal — visível mesmo em headless
            _service_log(self._service, "Login GAL confirmado. Sessao autenticada.", "info")

            _report("Passo 4/6: A buscar metadados no GAL...", 4 / total_steps)
            kit = str(df.iloc[0]["kit"]) if not df.empty else "N/A"
            journal_path = self._service.get_transaction_journal_path()
            successful_keys = self._service.load_successful_idempotency_keys(journal_path)

            import requests
            session = requests.Session()
            try:
                user_agent = driver.execute_script("return navigator.userAgent;")
                session.headers.update({"User-Agent": str(user_agent), "X-Requested-With": "XMLHttpRequest"})
                for cookie in driver.get_cookies():
                    session.cookies.set(cookie['name'], cookie['value'], domain=cookie.get('domain', ''))
                http_client = session
            except Exception:
                http_client = driver

            from config.feature_flags import feature_flags
            from services.core.config_service import config_service as _cs_meta
            from services.core.runtime_flags import FLAG_GAL_ENVIO_SEM_METADADOS
            # Precedência: feature flag > toggle de configurações GAL
            _flag_sem_meta = feature_flags.is_enabled(FLAG_GAL_ENVIO_SEM_METADADOS)
            _cfg_sem_meta = bool(_cs_meta.get_gal_config().get("envio_sem_metadados", False))
            _usar_sem_metadados = _flag_sem_meta or _cfg_sem_meta

            if _usar_sem_metadados:
                # Modo experimental: pula /lista/ e usa codigoAmostra diretamente.
                # O GAL localiza o registro pelo par codigo+gal_exame_codigo.
                # requisicao e paciente ficam vazios — GAL os resolve internamente.
                # ROLLBACK: setar USE_GAL_ENVIO_SEM_METADADOS.enabled=false em
                # config/feature_flags.json para restaurar o comportamento com metadados.
                _service_log(
                    self._service,
                    "[FLAG] USE_GAL_ENVIO_SEM_METADADOS ativo: pulando consulta a /lista/. "
                    "codigo=codigoAmostra, requisicao e paciente enviados vazios. "
                    "O GAL deve localizar o registro pelo par codigoAmostra+gal_exame_codigo. "
                    "Rollback: feature_flags.json > USE_GAL_ENVIO_SEM_METADADOS > enabled: false",
                    "info",
                )
                _report(
                    "Passo 4/6: Modo sem metadados — construindo payload direto do CSV...",
                    4 / total_steps,
                )
                metas = {str(ca).strip(): {} for ca in df["codigoamostra"]}
            else:
                metas = self._service.buscar_metadados(http_client, set(df["codigoamostra"]), exam_cfg=exam_cfg)
                # S2: Não abortar o lote inteiro quando metadados vierem vazios.
                # Amostras sem correspondência serão marcadas 'nao_encontrado' no loop de envio.
                if not metas:
                    _service_log(
                        self._service,
                        "[S2] AVISO: busca de metadados retornou vazio. "
                        "Verifique gal_exame_codigo e a janela de datas de busca. "
                        "Todas as amostras serao marcadas como 'nao_encontrado'.",
                        "warning",
                    )
                    _report(
                        "Passo 4/6: Metadados nao encontrados — prosseguindo (amostras serao 'nao_encontrado')...",
                        4 / total_steps,
                    )

            relatorio_final: list[Dict[str, Any]] = []
            relatorio_local: list[Dict[str, Any]] = []
            total_amostras = len(df)
            run_id = datetime.now().strftime("%Y%m%dT%H%M%S")

            # CONC-003: claim/lease interprocesso (duravel) antes do envio externo.
            # Default OFF — comportamento inalterado ate habilitar flag/config.
            claims = self._claims_repository
            if claims is None:
                from services.core.runtime_flags import FLAG_GAL_CLAIM_LEASE
                _flag_claim = feature_flags.is_enabled(FLAG_GAL_CLAIM_LEASE)
                _cfg_claim = bool(_cs_meta.get_gal_config().get("claim_lease", False))
                if _flag_claim or _cfg_claim:
                    claims = SqliteGalClaimsRepository(journal_path.parent / "gal_claims.db")
            claim_owner = default_owner_token(run_id) if claims is not None else ""

            from concurrent.futures import ThreadPoolExecutor, as_completed
            import threading
            
            lock = threading.Lock()
            completed_count = 0
            # S22: Chaves em voo — impede envio duplo de linhas idênticas no mesmo
            # CSV. O check-then-send é tornado atômico: a chave é reservada sob lock
            # antes de qualquer envio, impedindo que dois workers passem ambos pela
            # checagem de duplicidade para a mesma amostra.
            inflight_keys: Set[str] = set()

            def _process_row(i_idx, row_data):
                ts_inicial = datetime.now().isoformat()
                codigo_amostra = str(row_data.get("codigoamostra", ""))
                lote_kit = str(row_data.get("lotekit", ""))
                data_exame = str(row_data.get("dataprocessamentofim", ""))
                
                legacy_idempotency_key = self._service.build_idempotency_key(
                    codigo_amostra=codigo_amostra,
                    kit=kit,
                    lote_kit=lote_kit,
                    data_exame=data_exame,
                )
                idempotency_key = self._service.build_idempotency_key(
                    codigo_amostra=codigo_amostra,
                    kit=kit,
                    lote_kit=lote_kit,
                    data_exame=data_exame,
                    corrida_id=request.corrida_id,
                    nome_corrida=request.nome_corrida,
                    arquivo_corrida=request.arquivo_corrida,
                    parte_placa=request.parte_placa,
                )
                
                duplicate_match_key = ""
                with lock:
                    if idempotency_key in successful_keys or idempotency_key in inflight_keys:
                        duplicate_match_key = idempotency_key
                    elif legacy_idempotency_key in successful_keys or legacy_idempotency_key in inflight_keys:
                        duplicate_match_key = legacy_idempotency_key
                    else:
                        # S22: Reservar atomicamente antes de liberar o lock para
                        # que outro worker com a mesma chave seja bloqueado.
                        inflight_keys.add(idempotency_key)
                        inflight_keys.add(legacy_idempotency_key)

                # CONC-003: claim/lease duravel cross-process antes de enviar.
                if claims is not None and not duplicate_match_key:
                    try:
                        _outcome = claims.try_claim(
                            [idempotency_key, legacy_idempotency_key],
                            owner=claim_owner,
                            ttl_seconds=_CLAIM_TTL_SECONDS,
                        )
                    except Exception as _claim_exc:  # noqa: BLE001 - hardening
                        _service_log(
                            self._service,
                            f"[CONC-003] Claim store indisponivel ({_claim_exc}); "
                            "prosseguindo sem claim (degradado).",
                            "warning",
                        )
                        _outcome = None
                    if _outcome in (ClaimOutcome.ALREADY_COMMITTED, ClaimOutcome.HELD_BY_OTHER):
                        duplicate_match_key = idempotency_key

                if duplicate_match_key:
                    ts_final = datetime.now().isoformat()
                    return {
                        "codigoAmostra": codigo_amostra,
                        "registroInterno": codigo_amostra,
                        "paciente": "N/A",
                        "status": "duplicado",
                        "erro": ["Amostra ja enviada com sucesso anteriormente."],
                        "campos_invalidos": [],
                        "status_inicial": "pendente",
                        "ts_status_inicial": ts_inicial,
                        "status_envio": "",
                        "ts_status_envio": "",
                        "status_final": "duplicado",
                        "ts_status_final": ts_final,
                        "selecionado_envio": True,
                        "status_item": "selecionado_duplicado",
                        "idempotencia_chave": idempotency_key,
                        "kit": kit,
                        "loteKit": lote_kit,
                        "data_exame": data_exame,
                        "detalhes": (
                            f"journal={journal_path};"
                            f"matched_idempotencia={duplicate_match_key}"
                        ),
                        "corrida_id": request.corrida_id,
                        "exame_id": request.exame_id,
                        "lote": request.lote or lote_kit,
                        "arquivo_corrida": request.arquivo_corrida,
                        "arquivo_extracao": request.arquivo_extracao,
                        "parte_placa": request.parte_placa,
                        "numero_extracao": request.numero_extracao,
                        "nome_corrida": request.nome_corrida,
                        "quem_fez_extracao": request.quem_fez_extracao,
                        "quem_preparou_placa": request.quem_preparou_placa,
                        "observacoes_corrida": request.observacoes_corrida,
                    }, False, None, idempotency_key, legacy_idempotency_key

                if codigo_amostra in metas:
                    ts_envio = datetime.now().isoformat()
                    payload = self._service.construir_payload(
                        metas[codigo_amostra],
                        row_data,
                        request.observacao,
                        exam_cfg=exam_cfg,
                    )
                    resultado_envio = self._service.enviar_amostra(http_client, payload)
                    ts_final = datetime.now().isoformat()
                    
                    resultado_envio["status_inicial"] = "pendente"
                    resultado_envio["ts_status_inicial"] = ts_inicial
                    resultado_envio["status_envio"] = "em_envio"
                    resultado_envio["ts_status_envio"] = ts_envio
                    resultado_envio["status_final"] = resultado_envio.get("status", "")
                    resultado_envio["ts_status_final"] = ts_final
                    resultado_envio["selecionado_envio"] = True
                    resultado_envio["status_item"] = (
                        "selecionado_enviado"
                        if str(resultado_envio.get("status", "")).lower() == "sucesso"
                        else "selecionado_falha"
                    )
                    resultado_envio["idempotencia_chave"] = idempotency_key
                    resultado_envio["kit"] = payload.get("kit", kit)
                    resultado_envio["loteKit"] = payload.get("loteKit", lote_kit)
                    resultado_envio["data_exame"] = payload.get(
                        "dataProcessamentoFim", data_exame
                    )
                    resultado_envio["corrida_id"] = request.corrida_id
                    resultado_envio["exame_id"] = request.exame_id
                    resultado_envio["lote"] = request.lote or lote_kit
                    resultado_envio["arquivo_corrida"] = request.arquivo_corrida
                    resultado_envio["arquivo_extracao"] = request.arquivo_extracao
                    resultado_envio["parte_placa"] = request.parte_placa
                    resultado_envio["numero_extracao"] = request.numero_extracao
                    resultado_envio["nome_corrida"] = request.nome_corrida
                    resultado_envio["quem_fez_extracao"] = request.quem_fez_extracao
                    resultado_envio["quem_preparou_placa"] = request.quem_preparou_placa
                    resultado_envio["observacoes_corrida"] = request.observacoes_corrida
                    
                    is_success = resultado_envio.get("status") == "sucesso"
                    registro_sucesso = None
                    if is_success:
                        with lock:
                            self._persist_success_immediately(
                                resultado_envio=resultado_envio,
                                run_id=run_id,
                                kit=kit,
                            )
                            successful_keys.add(idempotency_key)
                            successful_keys.add(legacy_idempotency_key)

                        # CONC-003: marca o claim como committed (idempotencia permanente).
                        if claims is not None:
                            try:
                                claims.commit(
                                    [idempotency_key, legacy_idempotency_key],
                                    owner=claim_owner,
                                )
                            except Exception as _c_exc:  # noqa: BLE001 - hardening
                                _service_log(
                                    self._service,
                                    f"[CONC-003] Falha ao commitar claim: {_c_exc}",
                                    "warning",
                                )

                        registro_sucesso = {
                            **payload,
                            "usuario": request.usuario_logado,
                            "timestamp": datetime.now().isoformat(),
                        }
                    elif claims is not None:
                        # Envio nao bem-sucedido: libera o claim para permitir retry.
                        try:
                            claims.release(
                                [idempotency_key, legacy_idempotency_key],
                                owner=claim_owner,
                            )
                        except Exception:  # noqa: BLE001 - hardening
                            pass

                    return resultado_envio, is_success, registro_sucesso, idempotency_key, legacy_idempotency_key
                else:
                    # Claim adquirido mas amostra sem metadados: libera para retry futuro.
                    if claims is not None:
                        try:
                            claims.release(
                                [idempotency_key, legacy_idempotency_key],
                                owner=claim_owner,
                            )
                        except Exception:  # noqa: BLE001 - hardening
                            pass
                    ts_final = datetime.now().isoformat()
                    return {
                        "codigoAmostra": codigo_amostra,
                        "paciente": "N/A",
                        "status": "nao_encontrado",
                        "erro": ["Metadados nao encontrados no GAL"],
                        "campos_invalidos": [],
                        "status_inicial": "pendente",
                        "ts_status_inicial": ts_inicial,
                        "status_envio": "",
                        "ts_status_envio": "",
                        "status_final": "nao_encontrado",
                        "ts_status_final": ts_final,
                        "selecionado_envio": True,
                        "status_item": "nao_encontrado",
                        "idempotencia_chave": idempotency_key,
                        "kit": kit,
                        "loteKit": lote_kit,
                        "data_exame": data_exame,
                        "corrida_id": request.corrida_id,
                        "exame_id": request.exame_id,
                        "lote": request.lote or lote_kit,
                        "arquivo_corrida": request.arquivo_corrida,
                        "arquivo_extracao": request.arquivo_extracao,
                        "parte_placa": request.parte_placa,
                        "numero_extracao": request.numero_extracao,
                        "nome_corrida": request.nome_corrida,
                        "quem_fez_extracao": request.quem_fez_extracao,
                        "quem_preparou_placa": request.quem_preparou_placa,
                        "observacoes_corrida": request.observacoes_corrida,
                    }, False, None, idempotency_key, legacy_idempotency_key

            with ThreadPoolExecutor(max_workers=5) as executor:
                future_to_row = {executor.submit(_process_row, i, row): (i, row) for i, (_, row) in enumerate(df.iterrows())}
                for future in as_completed(future_to_row):
                    completed_count += 1
                    progress = (4 / total_steps) + (completed_count / total_amostras * (1 / total_steps))
                    _report(
                        f"Passo 5/6: A enviar lote... processadas {completed_count} de {total_amostras} amostras",
                        progress,
                    )
                    try:
                        res_envio, is_success, reg_sucesso, id_key, leg_key = future.result()
                        relatorio_local.append(res_envio)
                        if is_success and reg_sucesso:
                            relatorio_final.append(reg_sucesso)
                        # Item 8: log por amostra no terminal — código + resultado
                        # Rollback: USE_GAL_TERMINAL_LOG_POR_AMOSTRA.enabled=false
                        from services.core.runtime_flags import FLAG_GAL_TERMINAL_LOG_POR_AMOSTRA
                        if feature_flags.is_enabled(FLAG_GAL_TERMINAL_LOG_POR_AMOSTRA):
                            _ca_log = str(res_envio.get("codigoAmostra", ""))
                            _st_log = str(res_envio.get("status", "")).upper()
                            _erros_log = res_envio.get("erro") or []
                            _detalhe_log = (
                                f" ({str(_erros_log[0])[:70]})" if _erros_log else ""
                            )
                            _level_log = (
                                "info" if res_envio.get("status") in ("sucesso", "duplicado")
                                else "warning" if res_envio.get("status") == "nao_encontrado"
                                else "error"
                            )
                            _service_log(
                                self._service,
                                f"  {_ca_log} → {_st_log}{_detalhe_log}",
                                _level_log,
                            )
                    except Exception as e:
                        # S4: Registrar amostra como erro_critico em vez de silenciar
                        # com print(). A amostra aparece no relatorio e no journal.
                        import traceback as _tb
                        _i_idx, _row_failed = future_to_row[future]
                        _ca = str(_row_failed.get("codigoamostra", ""))
                        _service_log(
                            self._service,
                            f"[S4] Erro critico no worker (amostra={_ca}): {e}\n{_tb.format_exc()}",
                            "critical",
                        )
                        _service_log(
                            self._service,
                            f"  {_ca} → ERRO_CRITICO ({str(e)[:70]})",
                            "error",
                        )
                        relatorio_local.append({
                            "codigoAmostra": _ca,
                            "paciente": "N/A",
                            "status": "erro_critico",
                            "erro": [f"Erro inesperado no worker: {e}"],
                            "campos_invalidos": [],
                            "transaction_id": "",
                            "ts_sucesso": "",
                            "status_final": "erro_critico",
                            "ts_status_final": datetime.now().isoformat(),
                            "corrida_id": request.corrida_id,
                            "exame_id": request.exame_id,
                        })

            _report("Passo 6/6: A salvar relatorios...", 6 / total_steps)
            self._service.salvar_relatorios(
                relatorio_final=relatorio_final,
                relatorio_local=relatorio_local,
                usuario=request.usuario_logado,
                observacao=request.observacao,
                kit=kit,
                relatorio_filename=request.relatorio_filename,
                run_id=run_id,
            )

            sucessos = sum(1 for item in relatorio_local if item.get("status") == "sucesso")
            return GalSendResult(
                total_amostras=total_amostras,
                sucessos=sucessos,
                kit=kit,
                relatorio_local=relatorio_local,
                relatorio_final=relatorio_final,
            )
        finally:
            if driver is not None:
                driver.quit()

    def _resolve_access_level(self, request: GalSendRequest) -> str:
        """Resolve nivel de acesso canonico do usuario logado."""
        canonical = self._service.get_user_access_level(request.usuario_logado)
        if canonical:
            return str(canonical)
        return str(request.usuario_nivel or "")

    def _persist_success_immediately(
        self,
        *,
        resultado_envio: Dict[str, Any],
        run_id: str,
        kit: str,
    ) -> None:
        """Persiste sucesso no journal antes do fechamento do lote."""
        try:
            self._service.append_journal_events(
                relatorio_local=[resultado_envio],
                run_id=run_id,
                kit_default=str(kit),
            )
        except Exception as exc:  # noqa: BLE001 - caminho de hardening operacional
            codigo = str(
                resultado_envio.get("codigoAmostra")
                or resultado_envio.get("registroInterno")
                or ""
            )
            raise RuntimeError(
                "Falha ao persistir idempotencia local apos envio GAL "
                f"(amostra={codigo})."
            ) from exc
