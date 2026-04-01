"""
模块职责: 本文件作为 agents 微服务的全局统一启动入口，负责解析环境变量并启动基于 FastAPI 的应用实例。
输入输出: 无直接输入输出，通过读取环境变量配置启动参数。
关键算法: 无复杂算法，简单的服务启动引导逻辑。
异常处理: 依赖 uvicorn 内部的异常捕获机制，未在此层做额外拦截。
并发安全: 启动配置自身是线程安全的；运行时并发由 ASGI 服务器 (uvicorn) 管理。
性能瓶颈: uvicorn 单进程启动，高并发场景需结合 Gunicorn 进行多 worker 部署。
外部依赖: uvicorn (ASGI server), os (环境变量读取)
配置项说明:
- AGENT_HOST: 绑定的主机地址，默认 0.0.0.0
- AGENT_PORT: 监听端口，默认 8001
- AGENT_RELOAD: 是否开启热重载（开发环境建议开启），默认 false

维护者: SunJie
"""

import os
import uvicorn

# 常量: 默认监听主机地址
DEFAULT_HOST = "0.0.0.0"
# 常量: 默认监听端口
DEFAULT_PORT = "8001"
# 常量: 默认热重载开关
DEFAULT_RELOAD = "false"

def run() -> None:
    """
    按环境变量启动 FastAPI 服务

    :param: 无
    :return: 无返回值
    :raises: uvicorn.ConfigError (如果配置非法)
    """
    # ========== 步骤1：解析环境变量配置 ==========
    # 读取绑定地址
    host = os.getenv("AGENT_HOST", DEFAULT_HOST)
    # 读取并转换端口号
    port = int(os.getenv("AGENT_PORT", DEFAULT_PORT))
    # 读取并解析热重载开关
    reload_enabled = os.getenv("AGENT_RELOAD", DEFAULT_RELOAD).lower() == "true"

    # ========== 步骤2：启动 uvicorn 服务 ==========
    # 调用 uvicorn.run 启动应用，应用路径为 api.main 模块下的 app 实例
    uvicorn.run("api.main:app", host=host, port=port, reload=reload_enabled)


if __name__ == "__main__":
    run()
