import pytest
import asyncio
from core.skill_framework import SkillRegistry, SkillInvoker, SkillError
from skills.example_weather_skill import WeatherSkill

@pytest.fixture(autouse=True)
def setup_teardown():
    # 注册 Skill
    skill = WeatherSkill()
    SkillRegistry.register(skill)
    # 清理缓存
    SkillInvoker.clear_cache()
    yield
    # 卸载 Skill
    SkillRegistry.unregister("weather_query")

@pytest.mark.asyncio
async def test_skill_success():
    """测试正常的 Skill 调用"""
    context = {"is_authenticated": True, "role": "user"}
    params = {"city": "Beijing", "days": 3}
    
    result = await SkillInvoker.invoke_async("weather_query", params, context=context)
    
    assert result["city"] == "Beijing"
    assert result["temperature"] == "25°C"
    assert len(result["forecast"]) == 3

@pytest.mark.asyncio
async def test_skill_auth_failure():
    """测试无权限/未登录情况"""
    # 缺少 is_authenticated
    context = {"role": "user"}
    params = {"city": "Beijing"}
    
    with pytest.raises(SkillError) as exc_info:
        await SkillInvoker.invoke_async("weather_query", params, context=context)
        
    assert exc_info.value.code == 401
    assert "requires authentication" in str(exc_info.value)
    
    # 角色不符
    context = {"is_authenticated": True, "role": "guest"}
    with pytest.raises(SkillError) as exc_info:
        await SkillInvoker.invoke_async("weather_query", params, context=context)
        
    assert exc_info.value.code == 403
    assert "Permission denied" in str(exc_info.value)

@pytest.mark.asyncio
async def test_skill_validation_error():
    """测试参数验证失败"""
    context = {"is_authenticated": True, "role": "user"}
    # 缺少必填参数 city
    params = {"days": 3}
    
    with pytest.raises(SkillError) as exc_info:
        await SkillInvoker.invoke_async("weather_query", params, context=context)
        
    assert exc_info.value.code == 400
    assert "Parameter validation failed" in str(exc_info.value)

@pytest.mark.asyncio
async def test_skill_timeout():
    """测试超时控制"""
    context = {"is_authenticated": True, "role": "user"}
    params = {"city": "TimeoutCity"} # 模拟一个超时的请求
    
    with pytest.raises(SkillError) as exc_info:
        await SkillInvoker.invoke_async("weather_query", params, context=context)
        
    # 重试最后仍然超时，返回500 (RetryError包装) 或 504
    assert exc_info.value.code in [500, 504]
    assert "failed after retries" in str(exc_info.value) or "timed out" in str(exc_info.value)

@pytest.mark.asyncio
async def test_skill_cache():
    """测试结果缓存功能"""
    context = {"is_authenticated": True, "role": "user"}
    params = {"city": "Shanghai"}
    
    # 第一次调用（无缓存）
    res1 = await SkillInvoker.invoke_async("weather_query", params, context=context, use_cache=True)
    
    # 修改底层 Skill 以验证是否走了缓存（此处可以通过统计耗时来验证，因为正常有 0.5s sleep）
    import time
    start = time.time()
    res2 = await SkillInvoker.invoke_async("weather_query", params, context=context, use_cache=True)
    elapsed = time.time() - start
    
    assert res1 == res2
    assert elapsed < 0.1  # 走缓存应该非常快，远小于0.5s

def test_skill_sync_invoke():
    """测试同步调用包装"""
    context = {"is_authenticated": True, "role": "user"}
    params = {"city": "Guangzhou"}
    
    result = SkillInvoker.invoke_sync("weather_query", params, context=context)
    assert result["city"] == "Guangzhou"
