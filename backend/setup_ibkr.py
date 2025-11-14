#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interactive Brokers API设置脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.ibkr_market_data import get_ib_connection, close_connection
from database.connection import SessionLocal
from database.models import SystemConfig
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_ibkr_connection():
    """测试IBKR连接"""
    try:
        logger.info("测试IBKR连接...")
        ib = get_ib_connection()
        
        if ib.isConnected():
            logger.info("✓ IBKR连接成功")
            
            # 测试获取账户信息
            from services.ibkr_market_data import get_account_info
            account_info = get_account_info()
            if account_info:
                logger.info(f"账户资产: ${account_info.get('total_assets', 0)}")
                logger.info(f"现金: ${account_info.get('cash', 0)}")
            
            return True
        else:
            logger.error("✗ IBKR连接失败")
            return False
            
    except Exception as e:
        logger.error(f"IBKR连接测试失败: {e}")
        return False

def setup_ibkr_config():
    """设置IBKR配置"""
    try:
        db = SessionLocal()
        
        print("\n请输入IBKR连接配置:")
        host = input("主机地址 (默认: 127.0.0.1): ").strip() or "127.0.0.1"
        
        print("\n端口选择:")
        print("7497 - TWS Paper Trading")
        print("7496 - TWS Live Trading")
        print("4002 - IB Gateway Paper Trading")
        print("4001 - IB Gateway Live Trading")
        port_input = input("端口 (默认: 7497): ").strip() or "7497"
        port = int(port_input)
        
        client_id_input = input("客户端ID (默认: 1): ").strip() or "1"
        client_id = int(client_id_input)
        
        # 保存配置
        configs = [
            ("ibkr_host", host, "IBKR host"),
            ("ibkr_port", str(port), "IBKR port"),
            ("ibkr_client_id", str(client_id), "IBKR client ID")
        ]
        
        for key, value, desc in configs:
            config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
            if config:
                config.value = value
            else:
                config = SystemConfig(key=key, value=value, description=desc)
                db.add(config)
        
        db.commit()
        db.close()
        
        logger.info("✓ IBKR配置保存成功")
        return True
    except Exception as e:
        logger.error(f"设置IBKR配置失败: {e}")
        return False

def main():
    """主函数"""
    print("=" * 50)
    print("Interactive Brokers API设置向导")
    print("=" * 50)
    
    print("\n请确保:")
    print("1. 已安装TWS或IB Gateway")
    print("2. TWS/Gateway已启动并登录Paper Trading账户")
    print("3. 已在TWS/Gateway中启用API连接")
    print("   - 配置 -> API -> 启用ActiveX和Socket客户端")
    print("   - 设置可信IP地址: 127.0.0.1")
    
    input("\n按回车键继续...")
    
    # 设置配置
    if not setup_ibkr_config():
        print("\n❌ IBKR配置设置失败")
        return False
    
    # 测试连接
    if not test_ibkr_connection():
        print("\n❌ IBKR连接测试失败")
        print("请检查:")
        print("1. TWS/Gateway是否已启动")
        print("2. 是否已登录Paper Trading账户")
        print("3. API设置是否正确")
        print("4. 端口号是否匹配")
        return False
    
    print("\n✅ Interactive Brokers API设置完成!")
    print("\n可以开始使用IBKR模拟交易功能了。")
    print("运行 'python main.py' 启动服务器")
    
    # 清理连接
    close_connection()
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n用户取消操作")
        close_connection()
        sys.exit(1)
    except Exception as e:
        logger.error(f"设置过程中发生错误: {e}")
        close_connection()
        sys.exit(1)