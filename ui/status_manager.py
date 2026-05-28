"""

Gerenciador de Status para a aplicação IntegraGAL.

Responsável por gerenciar e atualizar a barra de status.

"""



from typing import Optional



import customtkinter as ctk





class StatusManager:

    """Gerenciador de status da aplicação"""



    def __init__(self, main_window):

        """

        Inicializa o gerenciador de status



        Args:

            main_window: Instância da janela principal (App)

        """

        self.main_window = main_window

        self.status_label: Optional[ctk.CTkLabel] = None

        self._criar_status_bar()



    def _criar_status_bar(self):

        """Cria a barra de status na janela principal"""

        main_frame = self.main_window.main_frame



        self.status_label = ctk.CTkLabel(
            main_frame, text="Status: Aguardando Ação", font=ctk.CTkFont(size=12)
        )
        self.status_label.grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)



        # Adicionar referência ao status manager na janela principal

        self.main_window.status_manager = self



    def update_status(self, message: str):

        """

        Atualiza a mensagem de status



        Args:

            message: Nova mensagem de status

        """

        if self.status_label:

            self.status_label.configure(text=f"Status: {message}")

            self.main_window.update_idletasks()

