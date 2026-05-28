"""
Wrapper para suprimir erros "invalid command name" do CustomTkinter
sem afetar a funcionalidade do sistema.

Esses erros s?o cosm?ticos e ocorrem quando callbacks internos do CustomTkinter
(update, check_dpi_scaling) s?o agendados mas a janela ? fechada antes de executarem.
"""

import sys
import io
import re

import customtkinter as ctk


class SuppressCustomTkinterErrors:
    """
    Context manager que suprime apenas erros "invalid command name" do Tcl/Tk
    sem afetar outros erros ou a funcionalidade do sistema.
    """

    def __init__(self):
        self.original_stderr = None
        self.buffer = None

    def __enter__(self):
        # Capturar stderr
        self.original_stderr = sys.stderr
        self.buffer = io.StringIO()
        sys.stderr = FilteredStderr(self.original_stderr)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restaurar stderr original
        sys.stderr = self.original_stderr
        return False


class FilteredStderr:
    """
    Wrapper de stderr que filtra apenas mensagens espec?ficas de erro do Tcl/Tk
    relacionadas a callbacks do CustomTkinter.
    """

    def __init__(self, original_stderr):
        self.original_stderr = original_stderr
        self.buffer = []
        self._line_buffer = ""
        self._suppress_next_lines = 0

    def write(self, message):
        if not message:
            return

        # Bufferiza por linha para evitar cortes em writes parciais
        self._line_buffer += message
        lines = self._line_buffer.splitlines(keepends=True)

        # Se a ultima linha nao terminou, mantem no buffer
        if lines and not (lines[-1].endswith("\n") or lines[-1].endswith("\r")):
            self._line_buffer = lines.pop()
        else:
            self._line_buffer = ""

        for line in lines:
            if self._should_suppress(line):
                self.buffer.append(line)
                continue
            self.original_stderr.write(line)

    def _should_suppress(self, message):
        """
        Retorna True apenas para erros cosmeticos do CustomTkinter
        que nao afetam a funcionalidade.
        """
        message_lower = message.lower()

        # Se estamos suprimindo linhas subsequentes do mesmo erro
        if self._suppress_next_lines > 0:
            self._suppress_next_lines -= 1
            return True

        # Suprimir apenas "invalid command name" de callbacks internos do CustomTkinter
        if "invalid command name" in message_lower:
            if (
                "update" in message_lower
                or "check_dpi_scaling" in message_lower
                or "click_animation" in message_lower
                or "<lambda>" in message_lower
            ):
                # Suprimir as pr?ximas 2 linhas do mesmo erro Tcl
                self._suppress_next_lines = 2
                return True

        return False

    def flush(self):
        self.original_stderr.flush()

    def fileno(self):
        return self.original_stderr.fileno()


def aplicar_filtro_global():
    """
    Aplica o filtro de erros globalmente ao sistema.
    Chamar no in?cio do main.py.
    """
    sys.stderr = FilteredStderr(sys.stderr)
    print("[Sistema] Filtro de erros CustomTkinter ativado")


def instalar_filtro_bgerror(root):
    """
    Substitui o handler Tcl 'bgerror' para suprimir erros cosm?ticos
    do CustomTkinter (invalid command name ... update/check_dpi_scaling).
    """
    try:
        # Preservar handler original se existir
        try:
            root.tk.call("rename", "bgerror", "_orig_bgerror")
        except Exception:
            pass

        def _bgerror_handler(msg):
            try:
                msg_str = str(msg)
            except Exception:
                msg_str = ""

            msg_lower = msg_str.lower()
            if "invalid command name" in msg_lower and (
                "update" in msg_lower
                or "check_dpi_scaling" in msg_lower
                or "click_animation" in msg_lower
                or "<lambda>" in msg_lower
            ):
                return

            # Encaminhar ao handler original se dispon?vel
            try:
                root.tk.call("_orig_bgerror", msg_str)
            except Exception:
                # Fallback para stderr
                sys.stderr.write(msg_str + "\n")

        root.tk.createcommand("bgerror", _bgerror_handler)
    except Exception:
        pass


def _cancel_internal_after_events(widget, include_update: bool = False) -> None:
    """Cancela callbacks internos conhecidos do CustomTkinter."""
    try:
        after_ids = widget.tk.call("after", "info")
    except Exception:
        return

    if not after_ids:
        return

    if isinstance(after_ids, str):
        after_ids = after_ids.split()

    for after_id in after_ids:
        try:
            info = widget.tk.call("after", "info", after_id)
        except Exception:
            continue

        if isinstance(info, (tuple, list)):
            script = str(info[0]) if info else ""
        else:
            script = str(info)

        script_lower = script.lower()
        is_internal = (
            "check_dpi_scaling" in script_lower
            or "click_animation" in script_lower
            or "windows_set_titlebar_icon" in script_lower
        )
        if include_update:
            is_internal = is_internal or bool(re.match(r"^\d+update$", script_lower))

        if not is_internal:
            continue

        try:
            widget.after_cancel(after_id)
        except Exception:
            pass


def _clear_customtk_trackers() -> None:
    """Limpa trackers globais de scaling/appearance do CustomTkinter."""
    try:
        from customtkinter.windows.widgets.scaling.scaling_tracker import ScalingTracker

        ScalingTracker.window_widgets_dict.clear()
        ScalingTracker.window_dpi_scaling_dict.clear()
        ScalingTracker.update_loop_running = False
    except Exception:
        pass

    try:
        from customtkinter.windows.widgets.appearance_mode.appearance_mode_tracker import (
            AppearanceModeTracker,
        )

        AppearanceModeTracker.app_list.clear()
        AppearanceModeTracker.callback_list.clear()
        AppearanceModeTracker.update_loop_running = False
    except Exception:
        pass


def instalar_guardas_customtkinter() -> None:
    """Instala guardas globais de cleanup para CTk/CTkToplevel.

    Objetivo:
    - garantir filtro `bgerror` em toda janela raiz CTk;
    - cancelar callbacks internos antes de `destroy()`, reduzindo
      mensagens `invalid command name` em encerramentos rapidos.
    """
    if getattr(ctk, "_integragal_ctk_guards_installed", False):
        return

    original_ctk_init = ctk.CTk.__init__
    def _patched_ctk_init(self, *args, **kwargs):
        original_ctk_init(self, *args, **kwargs)
        try:
            instalar_filtro_bgerror(self)
        except Exception:
            pass

    ctk.CTk.__init__ = _patched_ctk_init
    ctk._integragal_ctk_guards_installed = True
