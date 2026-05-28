import customtkinter as ctk
from ui.theme import Theme

class IGCard(ctk.CTkFrame):
    """
    Componente base para agrupamento de contextos (Cards).
    Garante o uso padronizado do fundo BG_CARD e cantos arredondados.
    """
    def __init__(self, master, **kwargs):
        super().__init__(
            master, 
            fg_color=Theme.BG_CARD,
            border_color=Theme.BORDER_DEFAULT,
            border_width=1,
            corner_radius=8,
            **kwargs
        )

class IGButton(ctk.CTkButton):
    """
    Botão padronizado do sistema com suporte a variantes.
    Variantes disponíveis: 'primary' (padrão), 'secondary', 'danger'.
    """
    def __init__(self, master, variant="primary", text_color=None, **kwargs):
        # Define as cores baseadas na variante
        if variant == "danger":
            fg_color = Theme.COLOR_DANGER
            hover_color = "#DC2626"
            txt_color = "#FFFFFF"
        elif variant == "secondary":
            fg_color = "transparent"
            hover_color = Theme.BORDER_LIGHT
            txt_color = Theme.TEXT_PRIMARY
            kwargs.setdefault("border_width", 1)
            kwargs.setdefault("border_color", Theme.BORDER_DEFAULT)
        else:
            # Primary default
            fg_color = Theme.PRIMARY_BLUE
            hover_color = Theme.PRIMARY_BLUE_HOVER
            txt_color = "#FFFFFF"

        if text_color:
            txt_color = text_color

        super().__init__(
            master,
            fg_color=fg_color,
            hover_color=hover_color,
            text_color=txt_color,
            font=Theme.get_font_primary(weight="bold"),
            corner_radius=6,
            **kwargs
        )

class IGTextField(ctk.CTkEntry):
    """
    Campo de texto padronizado com fonte visível no light mode.
    """
    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            font=Theme.get_font_primary(),
            text_color=Theme.TEXT_PRIMARY,
            fg_color="#FFFFFF",
            border_color=Theme.BORDER_DEFAULT,
            **kwargs
        )

class IGSelect(ctk.CTkComboBox):
    """
    Menu dropdown (ComboBox) padronizado.
    """
    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            font=Theme.get_font_primary(),
            text_color=Theme.TEXT_PRIMARY,
            fg_color="#FFFFFF",
            border_color=Theme.BORDER_DEFAULT,
            button_color=Theme.BORDER_DEFAULT,
            button_hover_color=Theme.BORDER_LIGHT,
            dropdown_font=Theme.get_font_primary(),
            dropdown_text_color=Theme.TEXT_PRIMARY,
            dropdown_fg_color="#FFFFFF",
            dropdown_hover_color=Theme.PRIMARY_BLUE_SOFT,
            **kwargs
        )

class IGLabel(ctk.CTkLabel):
    """
    Rótulo padronizado garantindo contraste de texto.
    """
    def __init__(self, master, variant="normal", **kwargs):
        weight = "bold" if variant == "bold" else "normal"
        font = kwargs.pop("font", Theme.get_font_primary(weight=weight))
        text_color = kwargs.pop("text_color", Theme.TEXT_PRIMARY)
        super().__init__(
            master,
            font=font,
            text_color=text_color,
            **kwargs
        )

class IGSidebarMenu(ctk.CTkFrame):
    """
    Menu lateral com estados ativos consistentes e tipografia padronizada.
    Espera uma lista de dicts: [{'label': 'A', 'command': func}, ...]
    """
    def __init__(self, master, items=None, active_index=0, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.buttons = []
        self.active_index = active_index
        
        if items:
            for idx, item in enumerate(items):
                btn = ctk.CTkButton(
                    self,
                    text=item.get("label", ""),
                    command=lambda i=idx, cmd=item.get("command"): self._on_click(i, cmd),
                    fg_color=Theme.PRIMARY_BLUE_SOFT if idx == self.active_index else "transparent",
                    text_color=Theme.PRIMARY_BLUE if idx == self.active_index else Theme.TEXT_PRIMARY,
                    hover_color=Theme.BORDER_LIGHT,
                    font=Theme.get_font_primary(weight="bold"),
                    anchor="w"
                )
                btn.pack(fill="x", pady=2, padx=10)
                self.buttons.append(btn)

    def _on_click(self, index, cmd):
        self.set_active(index)
        if cmd:
            cmd()

    def set_active(self, index):
        self.active_index = index
        for i, btn in enumerate(self.buttons):
            if i == index:
                btn.configure(
                    fg_color=Theme.PRIMARY_BLUE_SOFT,
                    text_color=Theme.PRIMARY_BLUE
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color="#000000"
                )
