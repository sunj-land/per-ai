import asyncio
from typing import Any, Dict
from pydantic import BaseModel, Field
from core.skill_framework import BaseSkill, SkillConfig

class WeatherInput(BaseModel):
    city: str = Field(..., description="城市名称，例如：北京、Shanghai")
    days: int = Field(default=1, ge=1, le=7, description="查询未来几天的天气")

class WeatherOutput(BaseModel):
    city: str
    temperature: str
    condition: str
    forecast: list[Dict[str, str]]

class WeatherSkill(BaseSkill):
    """
    具体的天气查询 Skill 实现示例
    """

    def __init__(self):
        super().__init__()
        self.config = SkillConfig(
            name="weather_query",
            version="1.0.0",
            description="获取指定城市的天气预报",
            timeout=1.0,           # 超时1秒
            retry_attempts=2,      # 失败重试2次
            require_auth=True,     # 需要鉴权
            required_roles=["admin", "user"] # 允许的角色
        )
        self.input_model = WeatherInput
        self.output_model = WeatherOutput

    async def _execute(self, params: WeatherInput, context: Dict[str, Any]) -> WeatherOutput:
        """
        模拟调用第三方天气 API
        """
        city = params.city

        # 模拟网络延迟
        await asyncio.sleep(0.1)

        # 模拟异常（例如城市不存在）
        if city == "UnknownCity":
            raise ValueError(f"City '{city}' not found in weather database.")

        # 模拟超时情况
        if city == "TimeoutCity":
            await asyncio.sleep(2.0) # 将会触发外层的 timeout=1.0

        # 构造模拟返回数据
        forecast = [{"day": f"Day {i+1}", "temp": "25°C"} for i in range(params.days)]

        return WeatherOutput(
            city=city,
            temperature="25°C",
            condition="Sunny",
            forecast=forecast
        )
