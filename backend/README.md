服务启动

确保在项目根目录运行以下命令，或者设置 PYTHONPATH 包含项目根目录：

```bash
# 方法 1：使用提供的脚本 (推荐)
./start_backend.sh

# 方法 2：手动设置 PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$(pwd)/..
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
