"""
Módulo de notificações do sistema IntegRAGal.
Centraliza funções de notificação ao usuário.
"""

import os
from utils.logger import registrar_log


def notificar_gal_saved(path, parent=None, timeout=5000):
    """
    Notifica usuário sobre salvamento de arquivo GAL.
    
    Args:
        path: Caminho do arquivo salvo
        parent: Widget pai para posicionar notificação (opcional)
        timeout: Tempo em ms antes de fechar automaticamente (padrão: 5000)
    """
    try:
        import customtkinter as ctk

        msg = f"GAL salvo: {os.path.basename(path)}\n{path}"
        if parent is None:
            registrar_log("Export GAL", msg, "INFO")
            return
        
        notif = ctk.CTkToplevel(parent)
        notif.overrideredirect(True)
        notif.attributes("-topmost", True)
        
        lbl = ctk.CTkLabel(
            notif, text=msg, fg_color="#222", text_color="white", corner_radius=8
        )
        lbl.pack(padx=10, pady=(8, 6))
        
        btn_frame = ctk.CTkFrame(notif)
        btn_frame.pack(padx=8, pady=(0, 8))

        def _open_path(p):
            try:
                if os.name == "nt":
                    os.startfile(p)
                else:
                    import subprocess
                    subprocess.Popen(["xdg-open" if os.name == "posix" else "open", p])
            except Exception:
                registrar_log("Export GAL", f"Falha ao abrir caminho {p}", "WARNING")

        try:
            folder = os.path.dirname(path)
            ctk.CTkButton(
                btn_frame,
                text="Abrir pasta",
                width=120,
                command=lambda: _open_path(folder),
            ).pack(side="left", padx=6)
            ctk.CTkButton(
                btn_frame,
                text="Abrir arquivo",
                width=120,
                command=lambda: _open_path(path),
            ).pack(side="left", padx=6)
        except Exception:
            pass
        
        try:
            x = parent.winfo_rootx() + 50
            y = parent.winfo_rooty() + 50
            notif.geometry(f"+{x}+{y}")
        except Exception:
            pass
        
        try:
            from utils.gui_utils import safe_destroy_ctk_toplevel
            notif.after(timeout, lambda: safe_destroy_ctk_toplevel(notif))
        except Exception:
            notif.after(timeout, notif.destroy)
        registrar_log(
            "Export GAL", f"Notificação exibida para arquivo GAL: {path}", "INFO"
        )
    except Exception:
        pass
