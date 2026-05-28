import os
import shutil
import tempfile
from unittest.mock import MagicMock, patch

import pytest
import customtkinter as ctk

from services.core.config_service import config_service
from services.installation_checks import build_setup_report
from ui.admin_initial_setup import InitialSetupPanel
from ui.admin_initial_setup_wizard import InitialSetupWizard


@pytest.fixture
def temp_workspace():
    # Setup a temporary workspace
    temp_dir = tempfile.mkdtemp()
    
    # Backup original config path
    original_config_path = config_service.__module__ + ".CONFIG_PATH" # this doesn't work directly
    # To mock the CONFIG_PATH effectively, we need to mock it where it's used
    # But ConfigService uses a global CONFIG_PATH in its module.
    
    import services.core.config_service as cfg_mod
    orig_path = cfg_mod.CONFIG_PATH
    
    test_config_path = os.path.join(temp_dir, "config_test.json")
    cfg_mod.CONFIG_PATH = test_config_path
    
    # Reload config
    config_service._config = {}
    config_service._initialize()
    
    # Reset path logic to use temp dir
    config_service._config["data_root"] = ""
    config_service._config["allowed_roots"] = []
    config_service.save()
    
    yield temp_dir
    
    # Restore
    cfg_mod.CONFIG_PATH = orig_path
    config_service._config = {}
    config_service._initialize()
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_initial_setup_e2e(temp_workspace):
    # Dummy Tk instance for UI testing
    root = ctk.CTk()
    root.withdraw()
    
    # Set config to use temp_workspace so dirs don't exist yet
    config_service.set("data_root", temp_workspace)
    config_service.set("allowed_roots", [temp_workspace])
    config_service.save()
    
    panel = InitialSetupPanel(root, root, "test_admin", "MASTER")
    
    # 1. Test Dry-Run folders
    fake_paths = {"test_dir": os.path.join(temp_workspace, "does_not_exist_yet")}
    with patch("ui.admin_initial_setup.config_service.get_paths", return_value=fake_paths):
        with patch("ui.admin_initial_setup.messagebox.askyesno", return_value=False) as mock_ask:
            panel._prepare_dirs()
            mock_ask.assert_called_once()
        
    # 2. Test configure shared storage (with lock and backup)
    shared_root = os.path.join(temp_workspace, "shared_test")
    
    with patch("ui.admin_initial_setup.filedialog.askdirectory", return_value=shared_root):
        panel._select_shared_root()
        assert panel.entry_shared_root.get() == shared_root
        
        with patch("ui.admin_initial_setup.messagebox.showinfo") as mock_info:
            panel._apply_shared_storage_standardization()
            mock_info.assert_called_once()
            
    # Check if backup was created
    import services.core.config_service as cfg_mod
    assert os.path.exists(cfg_mod.CONFIG_PATH)
    # The backup is only created if it already existed before saving
    # Here the save is called when standardizing
    
    # 3. Test Wizard E2E
    report = build_setup_report("test_admin")
    wizard = InitialSetupWizard(root, report)
    
    # Check steps
    assert len(wizard.steps) == 5
    assert wizard.step_index == 0
    
    # Navigate
    wizard._next()
    assert wizard.step_index == 1
    
    wizard._prev()
    assert wizard.step_index == 0
    
    # 4. Test Export Report inside wizard
    with patch("ui.admin_initial_setup_wizard.export_setup_report", return_value="fake_path.txt") as mock_export:
        with patch("ui.admin_initial_setup_wizard.messagebox.showinfo") as mock_info:
            wizard._export()
            mock_export.assert_called_once_with(wizard.report)
            mock_info.assert_called_once()
            
    # 5. Test restore backup
    with patch("ui.admin_initial_setup.messagebox.askyesno", return_value=True):
        with patch("ui.admin_initial_setup.messagebox.showinfo") as mock_info:
            panel._restore_backup()
            
    root.destroy()
