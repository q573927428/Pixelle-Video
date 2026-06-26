"""
支付配置：微信商户信息 + 系统配置读取
"""

from api.config import api_config

# 微信商户配置
WECHAT_MCHID = api_config.wechat_payment["mchid"]
WECHAT_API_KEY = api_config.wechat_payment["api_key"]
WECHAT_APPID = api_config.wechat_payment["appid"]
WECHAT_NOTIFY_URL = api_config.wechat_payment["notify_url"]

# 统一下单API地址（微信支付v2 Native）
UNIFIED_ORDER_URL = "https://api.mch.weixin.qq.com/pay/unifiedorder"
# 订单查询API
ORDER_QUERY_URL = "https://api.mch.weixin.qq.com/pay/orderquery"