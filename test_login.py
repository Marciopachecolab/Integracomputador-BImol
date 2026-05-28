import asyncio
from autenticacao.auth_service import AuthService

async def test():
    auth = AuthService()
    try:
        res = await auth.login('admin', '123456')
        print('admin:', res)
    except Exception as e:
        print('admin error:', e)
        
    try:
        res2 = await auth.login('marcio', '123456')
        print('marcio:', res2)
    except Exception as e:
        print('marcio error:', e)

if __name__ == '__main__':
    asyncio.run(test())
