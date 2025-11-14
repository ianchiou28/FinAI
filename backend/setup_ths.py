"""
同花顺模拟盘快速设置脚本
"""
import subprocess
import sys

def install_easytrader():
    """安装 easytrader"""
    print("正在安装 easytrader...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "easytrader"])
        print("✓ easytrader 安装成功")
        return True
    except Exception as e:
        print(f"✗ 安装失败: {e}")
        return False

def test_ths_connection():
    """测试同花顺连接"""
    print("\n测试同花顺模拟盘连接...")
    try:
        import easytrader
        user = easytrader.use('ths')
        print("✓ easytrader 导入成功")
        print("\n请按照以下步骤操作:")
        print("1. 打开同花顺客户端")
        print("2. 登录你的模拟盘账户")
        print("3. 使用以下代码登录:")
        print("\n   from services.ths_market_data import login_ths")
        print("   login_ths('你的账号', '你的密码')")
        return True
    except ImportError as e:
        print(f"✗ 导入失败: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("同花顺模拟盘设置")
    print("=" * 50)
    
    if install_easytrader():
        test_ths_connection()
    
    print("\n" + "=" * 50)
    print("设置完成！")
    print("=" * 50)
