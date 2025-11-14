#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
富途OpenAPI设置脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.futu_market_data import get_quote_context, get_trade_context, unlock_trade, close_connections
from database.connection import SessionLocal
from database.models import SystemConfig
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_futu_connection():
    """测试富途连接"""
    try:
        logger.info("测试富途行情连接...")
        quote_ctx = get_quote_context()
        
        # 测试获取股票报价
        from futu import *
        ret, data = quote_ctx.get_stock_quote(['HK.00700'])
        if ret == RET_OK:
            logger.info("✓ 富途行情连接成功")
            logger.info(f"腾讯控股当前价格: {data['cur_price'][0]}")
        else:
            logger.error(f"✗ 富途行情连接失败: {data}")
            return False
        
        logger.info("测试富途交易连接...")
        trd_ctx = get_trade_context()
        
        # 测试获取账户信息（不需要解锁）
        ret, data = trd_ctx.accinfo_query(trd_env=TrdEnv.SIMULATE)
        if ret == RET_OK:
            logger.info("✓ 富途交易连接成功")
            if not data.empty:
                logger.info(f"模拟账户资金: {data['cash'][0]} {data['currency'][0]}")
        else:
            logger.error(f"✗ 富途交易连接失败: {data}")
            return False
        
        return True
    except Exception as e:
        logger.error(f"富途连接测试失败: {e}")
        return False

def setup_futu_credentials():
    """设置富途凭据"""
    try:
        db = SessionLocal()
        
        # 检查是否已有交易密码
        pwd_config = db.query(SystemConfig).filter(SystemConfig.key == "futu_password").first()
        
        if not pwd_config:
            print("\n请输入富途交易密码（用于解锁模拟交易）:")
            password = input("交易密码: ").strip()
            
            if password:
                # 测试解锁
                if unlock_trade(password):
                    # 保存密码
                    pwd_config = SystemConfig(
                        key="futu_password", 
                        value=password, 
                        description="Futu trade password"
                    )
                    db.add(pwd_config)
                    db.commit()
                    logger.info("✓ 富途交易密码设置成功")
                else:
                    logger.error("✗ 富途交易密码验证失败")
                    return False
            else:
                logger.info("跳过交易密码设置")
        else:
            logger.info("富途交易密码已存在")
            # 测试现有密码
            if unlock_trade(pwd_config.value):
                logger.info("✓ 现有富途交易密码验证成功")
            else:
                logger.error("✗ 现有富途交易密码验证失败")
        
        db.close()
        return True
    except Exception as e:
        logger.error(f"设置富途凭据失败: {e}")
        return False

def main():
    """主函数"""
    print("=" * 50)
    print("富途OpenAPI设置向导")
    print("=" * 50)
    
    print("\n1. 请确保已安装富途OpenD客户端")
    print("2. 请确保OpenD已启动并登录富途账户")
    print("3. 默认连接地址: 127.0.0.1:11111")
    
    input("\n按回车键继续...")
    
    # 测试连接
    if not test_futu_connection():
        print("\n❌ 富途连接测试失败")
        print("请检查:")
        print("1. OpenD是否已启动")
        print("2. 是否已登录富途账户")
        print("3. 网络连接是否正常")
        return False
    
    # 设置凭据
    if not setup_futu_credentials():
        print("\n❌ 富途凭据设置失败")
        return False
    
    print("\n✅ 富途OpenAPI设置完成!")
    print("\n可以开始使用富途模拟交易功能了。")
    print("运行 'python main.py' 启动服务器")
    
    # 清理连接
    close_connections()
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n用户取消操作")
        close_connections()
        sys.exit(1)
    except Exception as e:
        logger.error(f"设置过程中发生错误: {e}")
        close_connections()
        sys.exit(1)