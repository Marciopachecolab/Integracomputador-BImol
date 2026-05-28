import pytest
from application.contracts.ui_view_models import DataGridRowViewModel, PlateMapViewModel, RunSummaryViewModel

def test_data_grid_row_view_model_instantiation():
    """Garante que o DTO da Tabela possa ser construído apenas com literais."""
    vm = DataGridRowViewModel(
        well="A01",
        sample="Paciente_123",
        targets_summary="SC2: DET | FLUA: ND",
        result_tag="detectado",
        is_control=False,
        target_details={"SC2": "18.5", "FLUA": "Und"},
        is_selected=True,
        is_disabled=False
    )
    
    assert vm.well == "A01"
    assert vm.result_tag == "detectado"
    assert "SC2" in vm.target_details
    assert vm.target_details["SC2"] == "18.5"

def test_plate_map_view_model_instantiation():
    """Garante que o DTO do Mapa da Placa armazene apenas coordenadas e cores prévias."""
    vm = PlateMapViewModel(
        well_pos="A1",
        sample_id="CN",
        result_tag="nao_detectavel",
        is_control=True
    )
    
    assert vm.well_pos == "A1"
    assert vm.is_control is True
    assert vm.group_id is None

def test_run_summary_view_model():
    """Garante estatísticas de placa corretas na view."""
    vm = RunSummaryViewModel(
        total_wells=96,
        detected_count=10,
        inconclusive_count=2,
        invalid_count=1,
        control_count=2,
        exam_name="VR1e2 Biomanguinhos 7500",
        plate_id="PLACA_XYZ"
    )
    
    assert vm.total_wells == 96
    assert vm.detected_count == 10
