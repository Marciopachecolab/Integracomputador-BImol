"""
CLI para gerenciar Feature Flags

Refatoração #4 - Fase 5

Uso:
    python -m utils.feature_flag_admin status
    python -m utils.feature_flag_admin enable --flag USE_ANALISAR_CORRIDA_V2
    python -m utils.feature_flag_admin rollout --flag USE_ANALISAR_CORRIDA_V2 --percentage 50
    python -m utils.feature_flag_admin disable --flag USE_ANALISAR_CORRIDA_V2
"""

import argparse
import sys
from pathlib import Path

# Adicionar ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.feature_flags import feature_flags


def cmd_status(args):
    """Mostra status de todas as flags ou de uma específica"""
    if args.flag:
        # Status de flag específica
        status = feature_flags.get_flag_status(args.flag)
        if not status:
            print(f"❌ Flag '{args.flag}' não encontrada")
            return 1
        
        print(f"\n📊 Status da Flag: {args.flag}")
        print("=" * 60)
        print(f"  Habilitada: {'✅ Sim' if status.get('enabled') else '❌ Não'}")
        print(f"  Rollout: {status.get('rollout_percentage')}%")
        print(f"  Descrição: {status.get('description')}")
        print(f"  Criada em: {status.get('created_at')}")
        print(f"  Owner: {status.get('owner')}")
        
        force_users = status.get('force_users', [])
        exclude_users = status.get('exclude_users', [])
        
        if force_users:
            print(f"  Force users ({len(force_users)}): {', '.join(force_users[:5])}")
        if exclude_users:
            print(f"  Exclude users ({len(exclude_users)}): {', '.join(exclude_users[:5])}")
        
        print("=" * 60)
    else:
        # Status de todas as flags
        all_flags = feature_flags.list_all_flags()
        
        print("\n📊 Status de Todas as Feature Flags")
        print("=" * 60)
        
        for flag_name, status in all_flags.items():
            enabled = '✅' if status.get('enabled') else '❌'
            rollout = status.get('rollout_percentage', 0)
            print(f"{enabled} {flag_name}")
            print(f"   Rollout: {rollout}%")
            print(f"   {status.get('description', '')}")
            print()
        
        print("=" * 60)
    
    return 0


def cmd_enable(args):
    """Habilita uma feature flag"""
    feature_flags.enable_flag(args.flag)
    print(f"✅ Flag '{args.flag}' HABILITADA")
    print(f"   (Rollout atual: {feature_flags.get_flag_status(args.flag)['rollout_percentage']}%)")
    return 0


def cmd_disable(args):
    """Desabilita uma feature flag (rollback)"""
    feature_flags.disable_flag(args.flag)
    print(f"🚨 Flag '{args.flag}' DESABILITADA (ROLLBACK)")
    return 0


def cmd_rollout(args):
    """Atualiza percentual de rollout"""
    if args.percentage < 0 or args.percentage > 100:
        print(f"❌ Percentual inválido: {args.percentage}%")
        print("   Use valor entre 0-100")
        return 1
    
    # Habilitar flag se ainda não estiver
    status = feature_flags.get_flag_status(args.flag)
    if not status.get('enabled'):
        feature_flags.enable_flag(args.flag)
        print(f"ℹ️  Flag '{args.flag}' foi habilitada automaticamente")
    
    feature_flags.set_rollout_percentage(args.flag, args.percentage)
    print(f"📊 Rollout '{args.flag}' atualizado para {args.percentage}%")
    
    if args.percentage == 0:
        print("   ⚠️  0% = nenhum usuário receberá v2")
    elif args.percentage == 100:
        print("   ✅ 100% = todos os usuários receberão v2")
    else:
        print(f"   ℹ️  ~{args.percentage}% dos usuários receberão v2")
    
    return 0


def cmd_force_user(args):
    """Adiciona usuário à lista de forçados"""
    feature_flags.add_force_user(args.flag, args.user_id)
    print(f"➕ User '{args.user_id}' adicionado à force list de '{args.flag}'")
    print(f"   Este usuário SEMPRE receberá v2")
    return 0


def cmd_exclude_user(args):
    """Adiciona usuário à lista de excluídos"""
    if 'exclude_users' not in feature_flags.get_flag_status(args.flag):
        print(f"❌ Flag '{args.flag}' não suporta exclude_users")
        return 1
    
    feature_flags.get_flag_status(args.flag)['exclude_users'].append(args.user_id)
    feature_flags._save_to_file()
    print(f"➖ User '{args.user_id}' adicionado à exclude list de '{args.flag}'")
    print(f"   Este usuário NUNCA receberá v2")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description='Gerenciar Feature Flags do Integragal',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Ver status de todas as flags
  python -m utils.feature_flag_admin status
  
  # Ver status de flag específica
  python -m utils.feature_flag_admin status --flag USE_ANALISAR_CORRIDA_V2
  
  # Habilitar flag
  python -m utils.feature_flag_admin enable --flag USE_ANALISAR_CORRIDA_V2
  
  # Configurar rollout 5%
  python -m utils.feature_flag_admin rollout --flag USE_ANALISAR_CORRIDA_V2 --percentage 5
  
  # Configurar rollout 100%
  python -m utils.feature_flag_admin rollout --flag USE_ANALISAR_CORRIDA_V2 --percentage 100
  
  # Desabilitar flag (rollback)
  python -m utils.feature_flag_admin disable --flag USE_ANALISAR_CORRIDA_V2
  
  # Forçar v2 para usuário específico
  python -m utils.feature_flag_admin force-user --flag USE_ANALISAR_CORRIDA_V2 --user-id user_123
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Comando a executar')
    subparsers.required = True
    
    # Comando: status
    parser_status = subparsers.add_parser('status', help='Mostrar status das flags')
    parser_status.add_argument('--flag', help='Nome da flag específica')
    parser_status.set_defaults(func=cmd_status)
    
    # Comando: enable
    parser_enable = subparsers.add_parser('enable', help='Habilitar feature flag')
    parser_enable.add_argument('--flag', required=True, help='Nome da flag')
    parser_enable.set_defaults(func=cmd_enable)
    
    # Comando: disable
    parser_disable = subparsers.add_parser('disable', help='Desabilitar feature flag')
    parser_disable.add_argument('--flag', required=True, help='Nome da flag')
    parser_disable.set_defaults(func=cmd_disable)
    
    # Comando: rollout
    parser_rollout = subparsers.add_parser('rollout', help='Configurar rollout percentual')
    parser_rollout.add_argument('--flag', required=True, help='Nome da flag')
    parser_rollout.add_argument('--percentage', required=True, type=int, help='Percentual 0-100')
    parser_rollout.set_defaults(func=cmd_rollout)
    
    # Comando: force-user
    parser_force = subparsers.add_parser('force-user', help='Forçar v2 para usuário')
    parser_force.add_argument('--flag', required=True, help='Nome da flag')
    parser_force.add_argument('--user-id', required=True, help='ID do usuário')
    parser_force.set_defaults(func=cmd_force_user)
    
    # Comando: exclude-user
    parser_exclude = subparsers.add_parser('exclude-user', help='Excluir usuário do v2')
    parser_exclude.add_argument('--flag', required=True, help='Nome da flag')
    parser_exclude.add_argument('--user-id', required=True, help='ID do usuário')
    parser_exclude.set_defaults(func=cmd_exclude_user)
    
    args = parser.parse_args()
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
