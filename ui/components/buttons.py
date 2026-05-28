import customtkinter as ctk
from ui.theme import Theme

class PrimaryButton(ctk.CTkButton):
    def __init__(self, master, text, command=None, **kwargs):
        super().__init__(
            master,
            text=text,
            command=command,
            fg_color=Theme.PRIMARY_BLUE,
            hover_color=Theme.PRIMARY_BLUE_HOVER,
            text_color=Theme.BG_CARD,
            font=Theme.get_font_primary(size=12, weight="bold"),
            corner_radius=6,
            height=36,
            **kwargs
        )

class SecondaryButton(ctk.CTkButton):
    def __init__(self, master, text, command=None, **kwargs):
        super().__init__(
            master,
            text=text,
            command=command,
            fg_color=Theme.COLOR_GRAY_SOFT,
            hover_color=Theme.BORDER_DEFAULT,
            text_color=Theme.TEXT_PRIMARY,
            font=Theme.get_font_primary(size=12, weight="bold"),
            corner_radius=6,
            height=36,
            border_width=1,
            border_color=Theme.BORDER_DEFAULT,
            **kwargs
        )
