import customtkinter as ctk
from ui.theme import Theme

class ContentCard(ctk.CTkFrame):
    def __init__(self, master, title=None, **kwargs):
        super().__init__(
            master,
            fg_color=Theme.BG_CARD,
            border_width=1,
            border_color=Theme.BORDER_DEFAULT,
            corner_radius=8,
            **kwargs
        )
        if title:
            self.title_label = ctk.CTkLabel(
                self, 
                text=title, 
                font=Theme.get_font_primary(size=16, weight="bold"),
                text_color=Theme.TEXT_PRIMARY
            )
            self.title_label.pack(anchor="w", padx=20, pady=(20, 10))
