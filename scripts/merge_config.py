"""
Script para consolidar config.json (root) e configuracao/config.json
Prioriza dados mais completos de configuracao/config.json
"""
import json
from pathlib import Path
from datetime import datetime
import shutil

def merge_configs():
    """Merge configuracao/config.json (mais completo) com config.json (root)"""
    
    root_dir = Path(__file__).parent.parent
    root_config = root_dir / "config.json"
    configuracao_config = root_dir / "configuracao" / "config.json"
    
    # 1. Criar backup do config.json atual
    backup_dir = root_dir / "config" / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"config_pre_merge_{timestamp}.json"
    
    print(f"📦 Criando backup de config.json em: {backup_file}")
    shutil.copy(root_config, backup_file)
    
    # 2. Carregar ambos os arquivos
    print(f"📖 Lendo {root_config}")
    with open(root_config, 'r', encoding='utf-8') as f:
        root_data = json.load(f)
    
    print(f"📖 Lendo {configuracao_config}")
    with open(configuracao_config, 'r', encoding='utf-8') as f:
        configuracao_data = json.load(f)
    
    # 3. Merge inteligente - prioriza configuracao/config.json por ser mais completo
    merged = {}
    
    # 3.1 General section - existe apenas em configuracao/
    if "general" in configuracao_data:
        merged["general"] = configuracao_data["general"]
        print("✅ Seção 'general' adicionada de configuracao/config.json")
    
    # 3.2 Paths - merge com prioridade para configuracao/ mas mantendo caminhos absolutos do root
    merged["paths"] = {}
    root_paths = root_data.get("paths", {})
    conf_paths = configuracao_data.get("paths", {})
    
    # Manter caminhos absolutos do root (mais específicos) mas adicionar novos de configuracao/
    for key, value in root_paths.items():
        merged["paths"][key] = value
    
    # Adicionar caminhos que só existem em configuracao/
    for key, value in conf_paths.items():
        if key not in merged["paths"]:
            merged["paths"][key] = value
            print(f"✅ Path '{key}' adicionado: {value}")
    
    # 3.3 Postgres - priorizar configuracao/ (enabled=true)
    merged["postgres"] = configuracao_data.get("postgres", root_data.get("postgres", {}))
    print(f"✅ Configuração PostgreSQL: enabled={merged['postgres'].get('enabled', False)}")
    
    # 3.4 GAL Integration - merge profundo
    merged["gal_integration"] = root_data.get("gal_integration", {}).copy()
    conf_gal = configuracao_data.get("gal_integration", {})
    
    # Adicionar campos que só existem em configuracao/
    for key, value in conf_gal.items():
        if key not in merged["gal_integration"]:
            merged["gal_integration"][key] = value
            print(f"✅ GAL integration '{key}' adicionado")
        elif key == "retry_settings":
            # Para retry_settings, pegar backoff_factor maior
            root_backoff = merged["gal_integration"]["retry_settings"].get("backoff_factor", 0)
            conf_backoff = value.get("backoff_factor", 0)
            if conf_backoff > root_backoff:
                merged["gal_integration"]["retry_settings"]["backoff_factor"] = conf_backoff
                print(f"✅ GAL backoff_factor atualizado: {conf_backoff}")
        elif key == "panel_tests":
            # Para panel_tests, usar versão mais completa (configuracao/)
            root_tests = len(merged["gal_integration"].get("panel_tests", {}).get("1", []))
            conf_tests = len(value.get("1", []))
            if conf_tests > root_tests:
                merged["gal_integration"]["panel_tests"] = value
                print(f"✅ Panel tests atualizado: {conf_tests} testes (vs {root_tests} anterior)")
    
    # 3.5 Exams - existe apenas em configuracao/
    if "exams" in configuracao_data:
        merged["exams"] = configuracao_data["exams"]
        num_exams = len(merged["exams"].get("active_exams", []))
        num_configs = len(merged["exams"].get("configs", {}))
        print(f"✅ Seção 'exams' adicionada: {num_exams} exames ativos, {num_configs} configurações")
    
    # 4. Salvar arquivo merged
    print(f"\n💾 Salvando config.json consolidado...")
    with open(root_config, 'w', encoding='utf-8') as f:
        json.dump(merged, f, indent=4, ensure_ascii=False)
    
    print(f"✅ Config.json consolidado salvo!")
    
    # 5. Reportar diferenças
    print(f"\n📊 Resumo do merge:")
    print(f"   - Seções no config original: {len(root_data)}")
    print(f"   - Seções no configuracao/config: {len(configuracao_data)}")
    print(f"   - Seções no merged: {len(merged)}")
    print(f"   - Tamanho original: {root_config.stat().st_size} bytes")
    print(f"   - Tamanho configuracao: {configuracao_config.stat().st_size} bytes")
    print(f"   - Tamanho merged: {root_config.stat().st_size} bytes (novo)")
    
    return merged

if __name__ == "__main__":
    print("=" * 60)
    print("MERGE DE CONFIG.JSON - IntegRAGal")
    print("=" * 60)
    print()
    
    try:
        result = merge_configs()
        print("\n" + "=" * 60)
        print("✅ MERGE CONCLUÍDO COM SUCESSO!")
        print("=" * 60)
        print(f"\n⚠️  PRÓXIMOS PASSOS:")
        print(f"   1. Revisar config.json consolidado")
        print(f"   2. Testar sistema: python -c \"from services.core.config_service import config_service; print(config_service.get('general'))\"")
        print(f"   3. Se OK, deletar configuracao/ folder")
        print(f"   4. Commit mudanças")
    except Exception as e:
        print(f"\n❌ ERRO durante merge: {e}")
        import traceback
        traceback.print_exc()
