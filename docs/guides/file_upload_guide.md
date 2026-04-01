# 文件上传与处理功能使用说明书及 API 文档

## 1. 简介
本项目前端文件上传功能已进行全面优化升级，解决"Message Send Failed"问题，并扩展支持多种附件类型。
支持图片识别、文档提取、音视频降级等机制，同时提供拖拽上传、多文件选择及进度条展示功能。

## 2. 支持的文件类型及处理规则
- **图片格式**: jpg, jpeg, png, gif, webp, bmp
  - **处理策略**: 图片将转为 Base64 或可访问 URL，调用支持 Vision 的 AI 模型进行图像识别与内容分析。
- **文档格式**: pdf, doc, docx, xls, xlsx, ppt, pptx, txt, csv
  - **处理策略**: 后端自动解析提取文本内容（支持通过 pypdf, python-docx, pandas 等库解析），将文本内容作为上下文注入给 AI 处理。
- **压缩包**: zip, rar, 7z
  - **处理策略**: 标记为普通附件，自动降级保存至对话记录中。
- **其他格式**: mp4, mp3, json, xml 等
  - **处理策略**: json, xml 作为文本读取；音视频暂时作为普通附件降级处理。
- **限制**: 建议单文件大小 $\le$ 50MB。

## 3. 前端功能特性
- **拖拽上传**: 在聊天输入框区域支持拖拽文件直接上传。
- **多文件上传**: 点击上传图标可一次性选择多个文件。
- **上传进度条**: 每个文件上传时有环形进度条显示上传状态。
- **文件预览与下载**: 上传后的文件会显示为 Chip，点击即可在新标签页中下载/预览。

## 4. API 接入指南
### 4.1. 统一文件上传接口
**Endpoint**: `POST /api/v1/attachments/upload`
**Content-Type**: `multipart/form-data`

**Request Parameters**:
- `file` (File): 必填，要上传的文件。

**Response**:
```json
{
  "code": 0,
  "data": {
    "id": "uuid-string",
    "filename": "example.pdf",
    "url": "/api/v1/attachments/download/uuid-string"
  },
  "message": "success"
}
```

### 4.2. 附件下载/访问接口
**Endpoint**: `GET /api/v1/attachments/download/{id}`
**Description**: 获取/下载对应的附件内容。

### 4.3. 聊天发送接口增强
**Endpoint**: `POST /api/v1/chat/completions`
**Content-Type**: `application/json`

**Request Body**:
在原有参数基础上，支持传入 `attachments`（包含附件 UUID 的数组）。
```json
{
  "content": "帮我总结一下这些文件",
  "model_id": "gpt-4",
  "attachments": ["uuid-string-1", "uuid-string-2"]
}
```

## 5. 后端技术实现
- **存储服务**: 使用 `StorageService` 统一管理，支持大文件切片读取，支持本地及未来扩展云存储。
- **文本提取**: `ChatService._extract_text_from_file` 智能分发各种 MimeType 到对应的解析库。
- **性能优化**: 文本提取在独立线程中执行 (`asyncio.to_thread`)，避免阻塞主事件循环。
- **数据结构**: `ChatMessage` 新增 `attachments` 字段用于存储附件 UUID 引用。

## 6. 测试与监控建议
- **监控**: 对 `/api/v1/attachments/upload` 建立延迟和错误率监控。
- **清理机制**: 建议配合 Cron 任务定期清理超过 90 天的旧附件数据。
