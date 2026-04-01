import pytest
import asyncio
from agents.shell_risk_agent.tools import ShellRiskEngine, ShellExecutionTool
from agents.shell_risk_agent.graph import ShellRiskAgent

def test_risk_engine_whitelist():
    engine = ShellRiskEngine()

    # 允许的命令
    res = engine.assess("ls -la")
    assert res["is_safe"] is True
    assert res["risk_level"] == "LOW"

    # 不在白名单的命令 (中危)
    res = engine.assess("unknown_cmd arg1")
    assert res["is_safe"] is False
    assert res["risk_level"] == "MEDIUM"

def test_risk_engine_blacklist():
    engine = ShellRiskEngine()

    # 黑名单命令 (高危)
    res = engine.assess("rm -rf /tmp/test")
    assert res["is_safe"] is False
    assert res["risk_level"] == "HIGH"
    assert "危险参数" in str(res["risk_details"]) or "黑名单" in str(res["risk_details"])

def test_risk_engine_sensitive_paths():
    engine = ShellRiskEngine()

    # 敏感路径 (高危)
    res = engine.assess("cat /etc/passwd")
    assert res["is_safe"] is False
    assert res["risk_level"] == "HIGH"
    assert "敏感路径" in str(res["risk_details"])

def test_risk_engine_dangerous_patterns():
    engine = ShellRiskEngine()

    # 危险参数 (高危)
    res = engine.assess("echo 'test' > /etc/config")
    assert res["is_safe"] is False
    assert res["risk_level"] == "HIGH"
    assert "危险参数" in str(res["risk_details"])

def test_risk_engine_dynamic_config():
    engine = ShellRiskEngine()

    # 正常不在白名单里的命令
    res = engine.assess("my_custom_cmd arg1")
    assert res["is_safe"] is False
    assert res["risk_level"] == "MEDIUM"

    # 通过动态配置放入白名单
    res2 = engine.assess("my_custom_cmd arg1", config_override={"whitelist": ["my_custom_cmd"]})
    assert res2["is_safe"] is True

    # 正常安全的命令，被加入黑名单
    res3 = engine.assess("ls -la", config_override={"blacklist_commands": ["ls"]})
    assert res3["is_safe"] is False
    assert res3["risk_level"] == "HIGH"
    assert "使用了黑名单高危命令" in str(res3["risk_details"])

@pytest.mark.asyncio
async def test_shell_execution_tool():
    tool = ShellExecutionTool()

    res = await tool.execute("echo 'hello world'")
    assert res["returncode"] == 0
    assert res["stdout"] == "hello world"

@pytest.mark.asyncio
async def test_shell_risk_agent_safe_command():
    agent = ShellRiskAgent()

    task = {"command": "echo 'safe command'"}
    result = await agent.process_task(task)

    assert result["status"] == "success"
    assert "safe command" in result["result"]["stdout"]

@pytest.mark.asyncio
async def test_shell_risk_agent_unsafe_command():
    agent = ShellRiskAgent()
    
    task = {"command": "rm -rf /"}
    result = await agent.process_task(task)
    
    assert result["status"] == "rejected"
    assert result["risk_assessment"]["level"] == "HIGH"

@pytest.mark.asyncio
async def test_shell_risk_agent_dynamic_config():
    agent = ShellRiskAgent()
    
    # 默认不允许的命令
    task1 = {"command": "curl http://example.com"}
    result1 = await agent.process_task(task1)
    assert result1["status"] == "rejected"
    
    # 通过任务参数动态覆盖白名单，允许该命令执行
    task2 = {
        "command": "echo 'dynamic config test'",
        "risk_config": {
            "whitelist": ["echo"],
            "dangerous_patterns": []
        }
    }
    result2 = await agent.process_task(task2)
    assert result2["status"] == "success"
    assert "dynamic config test" in result2["result"]["stdout"]
