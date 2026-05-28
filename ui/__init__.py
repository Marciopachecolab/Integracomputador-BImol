"""

Módulo de Interface do Usuário - IntegraGAL

Contém todos os componentes relacionados à interface gráfica.

"""



from .main_window import MainWindow, criar_aplicacao_principal

from .menu_handler import MenuHandler

from .navigation import NavigationManager

from .status_manager import StatusManager



__all__ = [

    "MainWindow",

    "criar_aplicacao_principal",

    "MenuHandler",

    "StatusManager",

    "NavigationManager",

]

