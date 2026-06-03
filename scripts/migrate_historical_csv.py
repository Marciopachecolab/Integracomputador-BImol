#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/migrate_historical_csv.py

Script para migrar histórico CSV existente para o novo formato com:
- id_registro (UUID)
- Campos de rastreamento de envio GAL
- Suporte para múltiplos exames
"""

import sys
import uuid
from datetime import datetime
from pathlib import Path

import pandas as pd

# Garante que o diretório raiz está no path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from utils.logger import registrar_log


def migrate_historical_csv(
    csv_path: str = "logs/historico_analises.csv",
    create_backup: bool = True
) -> bool:
    """
    Migra CSV histórico para novo formato com UUID e campos de envio GAL.
    
    Args:
        csv_path: Caminho do arquivo CSV histórico
        create_backup: Se True, cria backup antes de migrar
    
    Returns:
        True se migração bem-sucedida, False caso contrário
    """
    
    csv_path_obj = Path(csv_path)
    
    # Verifica se arquivo existe
    if not csv_path_obj.exists():
        print(f"❌ Arquivo não encontrado: {csv_path}")
        registrar_log("Migração CSV", f"Arquivo não encontrado: {csv_path}", "ERROR")
        return False
    
    print(f"\n{'='*70}")
    print(f"📋 Migrando Histórico CSV")
    print(f"{'='*70}\n")
    
    try:
        # 1. LEI CSV EXISTENTE
        print(f"1️⃣  Lendo CSV existente...")
        df = pd.read_csv(csv_path_obj, sep=";", encoding="utf-8")
        print(f"   ✅ Carregado com sucesso")
        print(f"   📊 Linhas: {len(df)}")
        print(f"   📋 Colunas: {len(df.columns)}\n")
        
        # 2. CRIAR BACKUP
        if create_backup:
            print(f"2️⃣  Criando backup...")
            backup_path = csv_path_obj.with_stem(
                f"{csv_path_obj.stem}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            df.to_csv(backup_path, sep=";", index=False, encoding="utf-8")
            print(f"   ✅ Backup criado: {backup_path}\n")
        else:
            print(f"2️⃣  Pulando criação de backup\n")
        
        # 3. ADICIONAR UUID
        print(f"3️⃣  Adicionando ID único (UUID)...")
        df.insert(0, "id_registro", [str(uuid.uuid4()) for _ in range(len(df))])
        print(f"   ✅ {len(df)} UUIDs gerados\n")
        
        # 4. ADICIONAR CAMPOS DE RASTREAMENTO GAL
        print(f"4️⃣  Adicionando campos de rastreamento de envio GAL...")
        
        # Se já existem, remove para garantir limpeza
        campos_gal = ["data_hora_envio", "usuario_envio", "sucesso_envio", "detalhes_envio"]
        for campo in campos_gal:
            if campo in df.columns:
                df.drop(columns=[campo], inplace=True)
        
        # Adiciona novamente (vazio)
        df["data_hora_envio"] = None
        df["usuario_envio"] = None
        df["sucesso_envio"] = None  # NULL para não enviável, False/True para enviado
        df["detalhes_envio"] = ""
        print(f"   ✅ 4 novos campos adicionados\n")
        
        # 5. AJUSTAR status_gal
        print(f"5️⃣  Normalizando status_gal...")
        
        # Mapeia valores antigos para novos
        status_map = {
            "analizado e nao enviado": "não enviado",
            "tipo nao enviavel": "não enviável",
        }
        
        for old_status, new_status in status_map.items():
            count = (df["status_gal"] == old_status).sum()
            if count > 0:
                df.loc[df["status_gal"] == old_status, "status_gal"] = new_status
                print(f"   • {count} registros: '{old_status}' → '{new_status}'")
        
        # Se status é "não enviável", marca sucesso_envio como NULL
        mask_nao_enviavel = df["status_gal"] == "não enviável"
        df.loc[mask_nao_enviavel, "sucesso_envio"] = None
        print(f"   • {mask_nao_enviavel.sum()} registros não enviáveis")
        print(f"   ✅ Status_gal normalizado\n")
        
        # 6. VALIDAÇÃO
        print(f"6️⃣  Validando integridade...")
        
        # Verifica se há duplicados de UUID (não deve haver)
        duplicados = df["id_registro"].duplicated().sum()
        if duplicados > 0:
            print(f"   ⚠️  {duplicados} UUIDs duplicados detectados!")
            registrar_log(
                "Migração CSV",
                f"{duplicados} UUIDs duplicados",
                "WARNING"
            )
        else:
            print(f"   ✅ Nenhum UUID duplicado")
        
        # Verifica se há None em campos críticos
        campos_criticos = ["id_registro", "data_hora_analise", "usuario_analise", "exame"]
        for campo in campos_criticos:
            if campo in df.columns:
                nulls = df[campo].isna().sum()
                if nulls > 0:
                    print(f"   ⚠️  {nulls} valores NULL em '{campo}'")
                else:
                    print(f"   ✅ Campo '{campo}' completo ({len(df)} valores)")
        
        print()
        
        # 7. ESCREVER NOVO CSV
        print(f"7️⃣  Escrevendo novo CSV...")
        df.to_csv(csv_path_obj, sep=";", index=False, encoding="utf-8")
        print(f"   ✅ CSV escrito com sucesso\n")
        
        # 8. RESUMO FINAL
        print(f"{'='*70}")
        print(f"✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO")
        print(f"{'='*70}\n")
        
        print(f"📊 Resumo Final:")
        print(f"   • Total de registros: {len(df)}")
        print(f"   • Total de colunas: {len(df.columns)}")
        print(f"   • Status não enviado: {(df['status_gal'] == 'não enviado').sum()}")
        print(f"   • Status não enviável: {(df['status_gal'] == 'não enviável').sum()}")
        print(f"   • Status enviado: {(df['status_gal'] == 'enviado').sum()}")
        print()
        
        print(f"📝 Colunas criadas:")
        for i, col in enumerate(df.columns, 1):
            print(f"   {i:2d}. {col}")
        print()
        
        registrar_log(
            "Migração CSV",
            f"Sucesso: {len(df)} registros migrados",
            "INFO"
        )
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERRO durante migração: {e}")
        registrar_log("Migração CSV", f"Erro: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return False


def validar_csv_apos_migracao(csv_path: str = "logs/historico_analises.csv") -> bool:
    """
    Valida se CSV foi migrado corretamente.
    """
    
    print(f"\n{'='*70}")
    print(f"🔍 Validando CSV Migrado")
    print(f"{'='*70}\n")
    
    try:
        df = pd.read_csv(csv_path, sep=";", encoding="utf-8")
        
        campos_obrigatorios = [
            "id_registro",
            "data_hora_analise",
            "usuario_analise",
            "exame",
            "poco",
            "amostra",
            "codigo",
            "status_gal",
            "data_hora_envio",
            "usuario_envio",
            "sucesso_envio",
            "detalhes_envio",
            "criado_em",
            "atualizado_em"
        ]
        
        print(f"Verificando campos obrigatórios...")
        campos_faltando = []
        for campo in campos_obrigatorios:
            if campo not in df.columns:
                campos_faltando.append(campo)
                print(f"   ❌ Faltando: {campo}")
            else:
                print(f"   ✅ Presente: {campo}")
        
        if campos_faltando:
            print(f"\n❌ Validação falhou: {len(campos_faltando)} campo(s) faltando")
            return False
        
        print(f"\n✅ Todos os campos obrigatórios estão presentes\n")
        
        # Amostra de dados
        print(f"📋 Amostra de primeiros 3 registros:\n")
        print(df.head(3).to_string())
        print()
        
        registrar_log(
            "Validação CSV",
            f"Validação bem-sucedida: {len(df)} registros",
            "INFO"
        )
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na validação: {e}")
        registrar_log("Validação CSV", f"Erro: {e}", "ERROR")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Migra histórico CSV para novo formato com UUID e rastreamento GAL"
    )
    parser.add_argument(
        "--csv-path",
        default="logs/historico_analises.csv",
        help="Caminho do arquivo CSV histórico"
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Não criar backup antes de migrar"
    )
    parser.add_argument(
        "--validar",
        action="store_true",
        help="Apenas validar CSV existente (não migra)"
    )
    
    args = parser.parse_args()
    
    if args.validar:
        sucesso = validar_csv_apos_migracao(args.csv_path)
    else:
        sucesso = migrate_historical_csv(
            csv_path=args.csv_path,
            create_backup=not args.no_backup
        )
        
        if sucesso:
            # Valida após migração
            sucesso = validar_csv_apos_migracao(args.csv_path)
    
    sys.exit(0 if sucesso else 1)
