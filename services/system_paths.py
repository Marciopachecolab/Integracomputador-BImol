import os

import sys

from typing import Optional





def get_base_dir_from(current_file: Optional[str] = None) -> str:

    if current_file is None:

        current_file = __file__

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(current_file)))

    return base_dir





BASE_DIR = get_base_dir_from()





def ensure_base_dir_on_sys_path(base_dir: Optional[str] = None) -> str:

    if base_dir is None:

        base_dir = BASE_DIR

    if base_dir not in sys.path:

        sys.path.append(base_dir)

    return base_dir





ensure_base_dir_on_sys_path()

