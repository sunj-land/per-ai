from typing import Dict, Any, Type
from app.core.channel.base import BaseAdapter
from app.core.channel.dingtalk import DingTalkAdapter
from app.core.channel.qqbot import QQBotAdapter
from app.core.channel.wechat_work import WechatWorkAdapter
from app.core.channel.feishu import FeishuAdapter
from app.core.channel.teams import TeamsAdapter
from app.core.channel.discord import DiscordAdapter
from app.core.channel.slack import SlackAdapter
from app.core.channel.email_adapter import EmailAdapter

class AdapterFactory:
    _adapters: Dict[str, Type[BaseAdapter]] = {
        "dingtalk": DingTalkAdapter,
        "qqbot": QQBotAdapter,
        "wechat_work": WechatWorkAdapter,
        "feishu": FeishuAdapter,
        "teams": TeamsAdapter,
        "discord": DiscordAdapter,
        "slack": SlackAdapter,
        "email": EmailAdapter
    }
    
    @classmethod
    def register(cls, name: str, adapter_cls: Type[BaseAdapter]):
        cls._adapters[name] = adapter_cls
        
    @classmethod
    def get_adapter(cls, type: str, config: Dict[str, Any]) -> BaseAdapter:
        adapter_cls = cls._adapters.get(type)
        if not adapter_cls:
            raise ValueError(f"Unsupported channel type: {type}")
        return adapter_cls(config)
