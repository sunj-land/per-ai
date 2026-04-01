# 数据模型字段说明汇总表

| 模型类名 | 字段名 | 类型 | 中文说明 | 示例值/默认值 |
| --- | --- | --- | --- | --- |
| `AgentModel` | `name` | `str` | Agent唯一系统名称，必填项，用于内部标识和检索 | `PydanticUndefined` |
| `AgentModel` | `user_id` | `typing.Optional[int]` | 创建或拥有该Agent的用户ID，外键关联user表，非必填 | `无` |
| `AgentModel` | `description` | `typing.Optional[str]` | Agent的功能描述信息，非必填 | `无` |
| `AgentModel` | `type` | `str` | Agent的具体类型，默认为标准(standard)，可选值: workflow(工作流), standard(标准) | `standard` |
| `AgentModel` | `status` | `str` | Agent当前的生命周期状态，默认为活跃(active)，可选值: active, inactive | `active` |
| `AgentModel` | `config` | `typing.Optional[typing.Any]` | Agent的详细配置信息(如提示词、模型参数等)，JSON格式存储，非必填 | `无` |
| `AgentModel` | `id` | `uuid.UUID` | Agent唯一全局ID，主键，默认自动生成UUID | `PydanticUndefined` |
| `AgentModel` | `created_at` | `datetime.datetime` | 记录创建时间(UTC)，默认当前时间 | `PydanticUndefined` |
| `AgentModel` | `updated_at` | `datetime.datetime` | 记录最后更新时间(UTC)，默认当前时间 | `PydanticUndefined` |
| `AgentModelBase` | `name` | `str` | Agent唯一系统名称，必填项，用于内部标识和检索 | `PydanticUndefined` |
| `AgentModelBase` | `user_id` | `typing.Optional[int]` | 创建或拥有该Agent的用户ID，外键关联user表，非必填 | `无` |
| `AgentModelBase` | `description` | `typing.Optional[str]` | Agent的功能描述信息，非必填 | `无` |
| `AgentModelBase` | `type` | `str` | Agent的具体类型，默认为标准(standard)，可选值: workflow(工作流), standard(标准) | `standard` |
| `AgentModelBase` | `status` | `str` | Agent当前的生命周期状态，默认为活跃(active)，可选值: active, inactive | `active` |
| `AgentModelBase` | `config` | `typing.Optional[typing.Any]` | Agent的详细配置信息(如提示词、模型参数等)，JSON格式存储，非必填 | `无` |
| `SkillDependencyModel` | `id` | `uuid.UUID` | 依赖关系记录的唯一ID，主键 | `PydanticUndefined` |
| `SkillDependencyModel` | `user_id` | `typing.Optional[int]` | 所属用户ID，非必填 | `无` |
| `SkillDependencyModel` | `skill_name` | `str` | 宿主Skill的名称，必填项 | `PydanticUndefined` |
| `SkillDependencyModel` | `skill_version` | `str` | 宿主Skill的版本，默认0.1.0 | `0.1.0` |
| `SkillDependencyModel` | `dependency_name` | `str` | 依赖包/库的名称，必填项 | `PydanticUndefined` |
| `SkillDependencyModel` | `required_version` | `str` | 依赖包所需的版本约束表达式(如 >=1.0.0)，默认不限制(*) | `*` |
| `SkillDependencyModel` | `resolved_version` | `typing.Optional[str]` | 实际解析并安装的具体版本号，非必填 | `无` |
| `SkillDependencyModel` | `source` | `str` | 依赖的拉取源类型，默认注册中心(registry) | `registry` |
| `SkillDependencyModel` | `created_at` | `datetime.datetime` | 记录创建时间(UTC) | `PydanticUndefined` |
| `SkillDependencyModel` | `updated_at` | `datetime.datetime` | 记录最后更新时间(UTC) | `PydanticUndefined` |
| `SkillInstallRecordModel` | `id` | `uuid.UUID` | 安装操作记录的唯一ID，主键 | `PydanticUndefined` |
| `SkillInstallRecordModel` | `user_id` | `typing.Optional[int]` | 发起操作的用户ID，外键关联user表，非必填 | `无` |
| `SkillInstallRecordModel` | `task_id` | `str` | 后台异步安装任务的ID，必填项 | `PydanticUndefined` |
| `SkillInstallRecordModel` | `skill_name` | `str` | 操作涉及的Skill名称，必填项 | `PydanticUndefined` |
| `SkillInstallRecordModel` | `target_version` | `str` | 目标安装版本，默认为最新版(latest) | `latest` |
| `SkillInstallRecordModel` | `operation` | `str` | 具体操作类型，默认安装(install)，可选值: install(安装), upgrade(升级), uninstall(卸载) | `install` |
| `SkillInstallRecordModel` | `status` | `str` | 任务执行状态，默认待处理(pending)，可选值: pending, running, success, failed | `pending` |
| `SkillInstallRecordModel` | `operator` | `typing.Optional[str]` | 执行该操作的用户标识或系统标识，非必填 | `无` |
| `SkillInstallRecordModel` | `idempotency_key` | `typing.Optional[str]` | 操作的幂等键，非必填 | `无` |
| `SkillInstallRecordModel` | `result_message` | `typing.Optional[str]` | 操作完成后的结果摘要消息，非必填 | `无` |
| `SkillInstallRecordModel` | `log_summary` | `typing.Optional[str]` | 操作执行过程的日志摘要，非必填 | `无` |
| `SkillInstallRecordModel` | `started_at` | `datetime.datetime` | 操作实际开始执行的时间(UTC) | `PydanticUndefined` |
| `SkillInstallRecordModel` | `finished_at` | `typing.Optional[datetime.datetime]` | 操作执行完成的时间(UTC)，非必填 | `无` |
| `SkillInstallRecordModel` | `created_at` | `datetime.datetime` | 记录创建时间(UTC) | `PydanticUndefined` |
| `SkillInstallRecordModel` | `updated_at` | `datetime.datetime` | 记录最后更新时间(UTC) | `PydanticUndefined` |
| `SkillModel` | `name` | `str` | Skill唯一系统名称，必填项 | `PydanticUndefined` |
| `SkillModel` | `user_id` | `typing.Optional[int]` | 归属的用户ID，外键关联user表，非必填 | `无` |
| `SkillModel` | `version` | `str` | Skill当前的版本号(遵循SemVer)，默认0.1.0 | `0.1.0` |
| `SkillModel` | `description` | `typing.Optional[str]` | Skill的详细说明描述，支持Markdown格式，非必填 | `无` |
| `SkillModel` | `author` | `typing.Optional[str]` | Skill的作者名称或机构，非必填 | `无` |
| `SkillModel` | `tags` | `typing.Optional[typing.Any]` | Skill的分类标签列表，JSON数组格式存储，非必填 | `无` |
| `SkillModel` | `source_type` | `str` | Skill的获取来源类型，默认为本地(local)，可选值: local, registry(注册中心), url(远程地址) | `local` |
| `SkillModel` | `source_url` | `typing.Optional[str]` | Skill的源代码仓库地址或主页，非必填 | `无` |
| `SkillModel` | `install_url` | `typing.Optional[str]` | Skill的具体安装包下载URL，非必填 | `无` |
| `SkillModel` | `file_path` | `typing.Optional[str]` | 如果是本地Skill，对应的内部存储文件路径，非必填 | `无` |
| `SkillModel` | `install_dir` | `typing.Optional[str]` | Skill在系统中的安装部署目录，非必填 | `无` |
| `SkillModel` | `status` | `str` | Skill启用状态，默认活跃(active)，可选值: active(活跃), error(异常) | `active` |
| `SkillModel` | `install_status` | `str` | Skill安装状态，默认已安装(installed)，可选值: pending, installing, installed, failed, uninstalled | `installed` |
| `SkillModel` | `dependency_snapshot` | `typing.Optional[typing.Any]` | 安装时的依赖包快照记录，JSON格式存储，非必填 | `无` |
| `SkillModel` | `idempotency_key` | `typing.Optional[str]` | 防止重复操作的幂等键，非必填 | `无` |
| `SkillModel` | `last_install_at` | `typing.Optional[datetime.datetime]` | 最后一次执行安装的时间戳，非必填 | `无` |
| `SkillModel` | `last_error` | `typing.Optional[str]` | 最近一次运行时产生的错误详细信息，文本格式，非必填 | `无` |
| `SkillModel` | `is_deleted` | `bool` | 逻辑删除标记，布尔值，默认False(未删除) | `False` |
| `SkillModel` | `input_schema` | `typing.Optional[typing.Any]` | Skill调用的输入参数Schema(JSON Schema格式)，非必填 | `无` |
| `SkillModel` | `output_schema` | `typing.Optional[typing.Any]` | Skill调用的返回结果Schema(JSON Schema格式)，非必填 | `无` |
| `SkillModel` | `id` | `uuid.UUID` | Skill唯一全局ID，主键，默认自动生成UUID | `PydanticUndefined` |
| `SkillModel` | `created_at` | `datetime.datetime` | 记录创建时间(UTC)，默认当前时间 | `PydanticUndefined` |
| `SkillModel` | `updated_at` | `datetime.datetime` | 记录最后更新时间(UTC)，默认当前时间 | `PydanticUndefined` |
| `SkillModelBase` | `name` | `str` | Skill唯一系统名称，必填项 | `PydanticUndefined` |
| `SkillModelBase` | `user_id` | `typing.Optional[int]` | 归属的用户ID，外键关联user表，非必填 | `无` |
| `SkillModelBase` | `version` | `str` | Skill当前的版本号(遵循SemVer)，默认0.1.0 | `0.1.0` |
| `SkillModelBase` | `description` | `typing.Optional[str]` | Skill的详细说明描述，支持Markdown格式，非必填 | `无` |
| `SkillModelBase` | `author` | `typing.Optional[str]` | Skill的作者名称或机构，非必填 | `无` |
| `SkillModelBase` | `tags` | `typing.Optional[typing.Any]` | Skill的分类标签列表，JSON数组格式存储，非必填 | `无` |
| `SkillModelBase` | `source_type` | `str` | Skill的获取来源类型，默认为本地(local)，可选值: local, registry(注册中心), url(远程地址) | `local` |
| `SkillModelBase` | `source_url` | `typing.Optional[str]` | Skill的源代码仓库地址或主页，非必填 | `无` |
| `SkillModelBase` | `install_url` | `typing.Optional[str]` | Skill的具体安装包下载URL，非必填 | `无` |
| `SkillModelBase` | `file_path` | `typing.Optional[str]` | 如果是本地Skill，对应的内部存储文件路径，非必填 | `无` |
| `SkillModelBase` | `install_dir` | `typing.Optional[str]` | Skill在系统中的安装部署目录，非必填 | `无` |
| `SkillModelBase` | `status` | `str` | Skill启用状态，默认活跃(active)，可选值: active(活跃), error(异常) | `active` |
| `SkillModelBase` | `install_status` | `str` | Skill安装状态，默认已安装(installed)，可选值: pending, installing, installed, failed, uninstalled | `installed` |
| `SkillModelBase` | `dependency_snapshot` | `typing.Optional[typing.Any]` | 安装时的依赖包快照记录，JSON格式存储，非必填 | `无` |
| `SkillModelBase` | `idempotency_key` | `typing.Optional[str]` | 防止重复操作的幂等键，非必填 | `无` |
| `SkillModelBase` | `last_install_at` | `typing.Optional[datetime.datetime]` | 最后一次执行安装的时间戳，非必填 | `无` |
| `SkillModelBase` | `last_error` | `typing.Optional[str]` | 最近一次运行时产生的错误详细信息，文本格式，非必填 | `无` |
| `SkillModelBase` | `is_deleted` | `bool` | 逻辑删除标记，布尔值，默认False(未删除) | `False` |
| `SkillModelBase` | `input_schema` | `typing.Optional[typing.Any]` | Skill调用的输入参数Schema(JSON Schema格式)，非必填 | `无` |
| `SkillModelBase` | `output_schema` | `typing.Optional[typing.Any]` | Skill调用的返回结果Schema(JSON Schema格式)，非必填 | `无` |
| `Attachment` | `uuid` | `str` | 附件全局唯一标识符(UUID)，必填项，支持索引 | `PydanticUndefined` |
| `Attachment` | `original_name` | `str` | 附件的原始文件名，必填项 | `PydanticUndefined` |
| `Attachment` | `ext` | `str` | 附件的文件扩展名(如.pdf, .jpg)，必填项 | `PydanticUndefined` |
| `Attachment` | `size` | `int` | 附件的文件大小，单位为字节(Bytes)，必填项 | `PydanticUndefined` |
| `Attachment` | `mime_type` | `str` | 附件的MIME类型(如image/jpeg)，必填项 | `PydanticUndefined` |
| `Attachment` | `user_id` | `int` | 上传该附件的用户ID，外键关联user表，必填项 | `PydanticUndefined` |
| `Attachment` | `channel_id` | `typing.Optional[int]` | 关联的渠道ID(如果附件属于特定渠道消息)，非必填 | `无` |
| `Attachment` | `is_deleted` | `bool` | 逻辑删除标记，布尔值，默认False(未删除) | `False` |
| `Attachment` | `id` | `typing.Optional[int]` | 附件记录自增主键ID | `无` |
| `Attachment` | `local_path` | `str` | 附件在服务器内部的实际存储路径，必填项 | `PydanticUndefined` |
| `Attachment` | `share_code` | `typing.Optional[str]` | 分享提取码，非必填 | `无` |
| `Attachment` | `share_expiry` | `typing.Optional[datetime.datetime]` | 分享链接的过期时间，非必填 | `无` |
| `Attachment` | `share_password` | `typing.Optional[str]` | 分享链接的访问密码，非必填 | `无` |
| `Attachment` | `created_at` | `datetime.datetime` | 附件上传/创建时间(UTC)，默认当前时间 | `PydanticUndefined` |
| `Attachment` | `updated_at` | `datetime.datetime` | 附件最后更新时间(UTC)，默认当前时间 | `PydanticUndefined` |
| `Attachment` | `deleted_at` | `typing.Optional[datetime.datetime]` | 附件逻辑删除的具体时间，非必填 | `无` |
| `AttachmentBase` | `uuid` | `str` | 附件全局唯一标识符(UUID)，必填项，支持索引 | `PydanticUndefined` |
| `AttachmentBase` | `original_name` | `str` | 附件的原始文件名，必填项 | `PydanticUndefined` |
| `AttachmentBase` | `ext` | `str` | 附件的文件扩展名(如.pdf, .jpg)，必填项 | `PydanticUndefined` |
| `AttachmentBase` | `size` | `int` | 附件的文件大小，单位为字节(Bytes)，必填项 | `PydanticUndefined` |
| `AttachmentBase` | `mime_type` | `str` | 附件的MIME类型(如image/jpeg)，必填项 | `PydanticUndefined` |
| `AttachmentBase` | `user_id` | `int` | 上传该附件的用户ID，外键关联user表，必填项 | `PydanticUndefined` |
| `AttachmentBase` | `channel_id` | `typing.Optional[int]` | 关联的渠道ID(如果附件属于特定渠道消息)，非必填 | `无` |
| `AttachmentBase` | `is_deleted` | `bool` | 逻辑删除标记，布尔值，默认False(未删除) | `False` |
| `AttachmentCreate` | `uuid` | `str` | 生成的唯一UUID | `PydanticUndefined` |
| `AttachmentCreate` | `original_name` | `str` | 原始文件名 | `PydanticUndefined` |
| `AttachmentCreate` | `ext` | `str` | 扩展名 | `PydanticUndefined` |
| `AttachmentCreate` | `size` | `int` | 文件大小(Bytes) | `PydanticUndefined` |
| `AttachmentCreate` | `mime_type` | `str` | MIME类型 | `PydanticUndefined` |
| `AttachmentCreate` | `local_path` | `str` | 本地存储路径 | `PydanticUndefined` |
| `AttachmentCreate` | `user_id` | `int` | 上传用户ID | `PydanticUndefined` |
| `AttachmentCreate` | `channel_id` | `typing.Optional[int]` | 关联的渠道ID | `无` |
| `AttachmentRead` | `uuid` | `str` | 附件全局唯一标识符(UUID)，必填项，支持索引 | `PydanticUndefined` |
| `AttachmentRead` | `original_name` | `str` | 附件的原始文件名，必填项 | `PydanticUndefined` |
| `AttachmentRead` | `ext` | `str` | 附件的文件扩展名(如.pdf, .jpg)，必填项 | `PydanticUndefined` |
| `AttachmentRead` | `size` | `int` | 附件的文件大小，单位为字节(Bytes)，必填项 | `PydanticUndefined` |
| `AttachmentRead` | `mime_type` | `str` | 附件的MIME类型(如image/jpeg)，必填项 | `PydanticUndefined` |
| `AttachmentRead` | `user_id` | `int` | 上传该附件的用户ID，外键关联user表，必填项 | `PydanticUndefined` |
| `AttachmentRead` | `channel_id` | `typing.Optional[int]` | 关联的渠道ID(如果附件属于特定渠道消息)，非必填 | `无` |
| `AttachmentRead` | `is_deleted` | `bool` | 逻辑删除标记，布尔值，默认False(未删除) | `False` |
| `AttachmentRead` | `id` | `int` | 附件ID | `PydanticUndefined` |
| `AttachmentRead` | `created_at` | `datetime.datetime` | 创建时间 | `PydanticUndefined` |
| `AttachmentRead` | `updated_at` | `datetime.datetime` | 更新时间 | `PydanticUndefined` |
| `AttachmentRead` | `url` | `typing.Optional[str]` | 附件的公网可访问URL | `无` |
| `AttachmentRead` | `preview_url` | `typing.Optional[str]` | 附件的缩略图或预览URL | `无` |
| `AttachmentUpdate` | `is_deleted` | `typing.Optional[bool]` | 更新的逻辑删除状态 | `无` |
| `AttachmentUpdate` | `deleted_at` | `typing.Optional[datetime.datetime]` | 更新的逻辑删除时间 | `无` |
| `AttachmentUpdate` | `share_code` | `typing.Optional[str]` | 更新的分享提取码 | `无` |
| `AttachmentUpdate` | `share_expiry` | `typing.Optional[datetime.datetime]` | 更新的分享过期时间 | `无` |
| `AttachmentUpdate` | `share_password` | `typing.Optional[str]` | 更新的分享密码 | `无` |
| `Card` | `name` | `str` | 卡片系统名称，必填且唯一，用于代码或配置中引用 | `PydanticUndefined` |
| `Card` | `type` | `str` | 卡片类型，默认为'custom'(自定义)，可扩展其他内置类型 | `custom` |
| `Card` | `description` | `typing.Optional[str]` | 卡片用途和功能的详细描述，非必填 | `无` |
| `Card` | `status` | `<enum CardStatus` | 卡片当前生命周期状态，默认值为草稿(draft) | `CardStatus.DRAFT` |
| `Card` | `id` | `typing.Optional[int]` | 卡片自增主键ID | `无` |
| `Card` | `version` | `int` | 当前卡片的最新主版本号，默认从1开始 | `1` |
| `Card` | `created_at` | `datetime.datetime` | 卡片首次创建时间(UTC) | `PydanticUndefined` |
| `Card` | `updated_at` | `datetime.datetime` | 卡片最后修改时间(UTC) | `PydanticUndefined` |
| `Card` | `user_id` | `typing.Optional[int]` | 创建该卡片的用户ID，外键关联user表 | `无` |
| `CardBase` | `name` | `str` | 卡片系统名称，必填且唯一，用于代码或配置中引用 | `PydanticUndefined` |
| `CardBase` | `type` | `str` | 卡片类型，默认为'custom'(自定义)，可扩展其他内置类型 | `custom` |
| `CardBase` | `description` | `typing.Optional[str]` | 卡片用途和功能的详细描述，非必填 | `无` |
| `CardBase` | `status` | `<enum CardStatus` | 卡片当前生命周期状态，默认值为草稿(draft) | `CardStatus.DRAFT` |
| `CardCreate` | `name` | `str` | 卡片系统名称，必填且唯一，用于代码或配置中引用 | `PydanticUndefined` |
| `CardCreate` | `type` | `str` | 卡片类型，默认为'custom'(自定义)，可扩展其他内置类型 | `custom` |
| `CardCreate` | `description` | `typing.Optional[str]` | 卡片用途和功能的详细描述，非必填 | `无` |
| `CardCreate` | `status` | `<enum CardStatus` | 卡片当前生命周期状态，默认值为草稿(draft) | `CardStatus.DRAFT` |
| `CardUpdate` | `name` | `typing.Optional[str]` | 更新的卡片名称 | `无` |
| `CardUpdate` | `type` | `typing.Optional[str]` | 更新的卡片类型 | `无` |
| `CardUpdate` | `description` | `typing.Optional[str]` | 更新的卡片描述 | `无` |
| `CardUpdate` | `status` | `typing.Optional[app.models.card.CardStatus]` | 更新的卡片状态 | `无` |
| `CardVersion` | `version` | `int` | 该记录对应的具体版本号，必填 | `PydanticUndefined` |
| `CardVersion` | `user_id` | `typing.Optional[int]` | 提交该版本的用户ID，外键关联user表 | `无` |
| `CardVersion` | `code` | `str` | 卡片的UI代码内容(如React/Vue代码字符串)，必填 | `PydanticUndefined` |
| `CardVersion` | `config` | `typing.Optional[str]` | 卡片属性配置的JSON字符串(Props/Schema)，非必填 | `无` |
| `CardVersion` | `changelog` | `typing.Optional[str]` | 当前版本的更新日志说明，非必填 | `无` |
| `CardVersion` | `id` | `typing.Optional[int]` | 版本记录自增主键ID | `无` |
| `CardVersion` | `card_id` | `int` | 所属卡片的ID，外键关联card表 | `PydanticUndefined` |
| `CardVersion` | `created_at` | `datetime.datetime` | 该版本的创建/提交时间(UTC) | `PydanticUndefined` |
| `CardVersionBase` | `version` | `int` | 该记录对应的具体版本号，必填 | `PydanticUndefined` |
| `CardVersionBase` | `user_id` | `typing.Optional[int]` | 提交该版本的用户ID，外键关联user表 | `无` |
| `CardVersionBase` | `code` | `str` | 卡片的UI代码内容(如React/Vue代码字符串)，必填 | `PydanticUndefined` |
| `CardVersionBase` | `config` | `typing.Optional[str]` | 卡片属性配置的JSON字符串(Props/Schema)，非必填 | `无` |
| `CardVersionBase` | `changelog` | `typing.Optional[str]` | 当前版本的更新日志说明，非必填 | `无` |
| `CardVersionCreate` | `version` | `int` | 该记录对应的具体版本号，必填 | `PydanticUndefined` |
| `CardVersionCreate` | `user_id` | `typing.Optional[int]` | 提交该版本的用户ID，外键关联user表 | `无` |
| `CardVersionCreate` | `code` | `str` | 卡片的UI代码内容(如React/Vue代码字符串)，必填 | `PydanticUndefined` |
| `CardVersionCreate` | `config` | `typing.Optional[str]` | 卡片属性配置的JSON字符串(Props/Schema)，非必填 | `无` |
| `CardVersionCreate` | `changelog` | `typing.Optional[str]` | 当前版本的更新日志说明，非必填 | `无` |
| `Channel` | `name` | `str` | 渠道名称，必填项，支持索引以便快速查找 | `PydanticUndefined` |
| `Channel` | `user_id` | `typing.Optional[int]` | 创建该渠道的用户ID，外键关联user表，非必填 | `无` |
| `Channel` | `description` | `typing.Optional[str]` | 渠道的详细描述信息，非必填 | `无` |
| `Channel` | `type` | `str` | 渠道类型，必填，可选值: dingtalk(钉钉), feishu(飞书), wechat_work(企业微信), slack, email(邮件), webhook, discord, teams | `PydanticUndefined` |
| `Channel` | `config` | `typing.Dict` | 渠道的连接配置信息(如Token、Secret等)，JSON字典格式，默认空字典 | `{}` |
| `Channel` | `is_active` | `bool` | 渠道是否处于激活可用状态，布尔值，默认True(是) | `True` |
| `Channel` | `id` | `uuid.UUID` | 渠道唯一标识，主键，默认自动生成UUID | `PydanticUndefined` |
| `Channel` | `created_at` | `datetime.datetime` | 渠道创建时间，默认为当前时间 | `PydanticUndefined` |
| `Channel` | `updated_at` | `datetime.datetime` | 渠道最后更新时间，默认为当前时间 | `PydanticUndefined` |
| `ChannelBase` | `name` | `str` | 渠道名称，必填项，支持索引以便快速查找 | `PydanticUndefined` |
| `ChannelBase` | `user_id` | `typing.Optional[int]` | 创建该渠道的用户ID，外键关联user表，非必填 | `无` |
| `ChannelBase` | `description` | `typing.Optional[str]` | 渠道的详细描述信息，非必填 | `无` |
| `ChannelBase` | `type` | `str` | 渠道类型，必填，可选值: dingtalk(钉钉), feishu(飞书), wechat_work(企业微信), slack, email(邮件), webhook, discord, teams | `PydanticUndefined` |
| `ChannelBase` | `config` | `typing.Dict` | 渠道的连接配置信息(如Token、Secret等)，JSON字典格式，默认空字典 | `{}` |
| `ChannelBase` | `is_active` | `bool` | 渠道是否处于激活可用状态，布尔值，默认True(是) | `True` |
| `ChannelCreate` | `name` | `str` | 渠道名称，必填项，支持索引以便快速查找 | `PydanticUndefined` |
| `ChannelCreate` | `user_id` | `typing.Optional[int]` | 创建该渠道的用户ID，外键关联user表，非必填 | `无` |
| `ChannelCreate` | `description` | `typing.Optional[str]` | 渠道的详细描述信息，非必填 | `无` |
| `ChannelCreate` | `type` | `str` | 渠道类型，必填，可选值: dingtalk(钉钉), feishu(飞书), wechat_work(企业微信), slack, email(邮件), webhook, discord, teams | `PydanticUndefined` |
| `ChannelCreate` | `config` | `typing.Dict` | 渠道的连接配置信息(如Token、Secret等)，JSON字典格式，默认空字典 | `{}` |
| `ChannelCreate` | `is_active` | `bool` | 渠道是否处于激活可用状态，布尔值，默认True(是) | `True` |
| `ChannelMessage` | `channel_id` | `uuid.UUID` | 发送消息所使用的渠道ID，外键关联channel表 | `PydanticUndefined` |
| `ChannelMessage` | `user_id` | `typing.Optional[int]` | 触发该消息发送的用户ID，外键关联user表，非必填 | `无` |
| `ChannelMessage` | `content` | `str` | 消息正文内容或发送给第三方API的JSON Payload数据，必填项 | `PydanticUndefined` |
| `ChannelMessage` | `status` | `str` | 消息发送状态，必填项，可选值: pending(发送中), success(发送成功), failed(发送失败) | `PydanticUndefined` |
| `ChannelMessage` | `result` | `typing.Optional[str]` | 第三方API的原始响应结果或错误信息，非必填 | `无` |
| `ChannelMessage` | `id` | `uuid.UUID` | 消息记录唯一标识，主键，默认自动生成UUID | `PydanticUndefined` |
| `ChannelMessage` | `created_at` | `datetime.datetime` | 消息记录创建时间，默认为当前时间 | `PydanticUndefined` |
| `ChannelMessageBase` | `channel_id` | `uuid.UUID` | 发送消息所使用的渠道ID，外键关联channel表 | `PydanticUndefined` |
| `ChannelMessageBase` | `user_id` | `typing.Optional[int]` | 触发该消息发送的用户ID，外键关联user表，非必填 | `无` |
| `ChannelMessageBase` | `content` | `str` | 消息正文内容或发送给第三方API的JSON Payload数据，必填项 | `PydanticUndefined` |
| `ChannelMessageBase` | `status` | `str` | 消息发送状态，必填项，可选值: pending(发送中), success(发送成功), failed(发送失败) | `PydanticUndefined` |
| `ChannelMessageBase` | `result` | `typing.Optional[str]` | 第三方API的原始响应结果或错误信息，非必填 | `无` |
| `ChannelMessageCreate` | `channel_id` | `uuid.UUID` | 发送消息所使用的渠道ID，外键关联channel表 | `PydanticUndefined` |
| `ChannelMessageCreate` | `user_id` | `typing.Optional[int]` | 触发该消息发送的用户ID，外键关联user表，非必填 | `无` |
| `ChannelMessageCreate` | `content` | `str` | 消息正文内容或发送给第三方API的JSON Payload数据，必填项 | `PydanticUndefined` |
| `ChannelMessageCreate` | `status` | `str` | 消息发送状态，必填项，可选值: pending(发送中), success(发送成功), failed(发送失败) | `PydanticUndefined` |
| `ChannelMessageCreate` | `result` | `typing.Optional[str]` | 第三方API的原始响应结果或错误信息，非必填 | `无` |
| `ChannelUpdate` | `name` | `typing.Optional[str]` | 更新的渠道名称 | `无` |
| `ChannelUpdate` | `description` | `typing.Optional[str]` | 更新的描述信息 | `无` |
| `ChannelUpdate` | `type` | `typing.Optional[str]` | 更新的渠道类型 | `无` |
| `ChannelUpdate` | `config` | `typing.Optional[typing.Dict]` | 更新的配置信息 | `无` |
| `ChannelUpdate` | `is_active` | `typing.Optional[bool]` | 更新的激活状态 | `无` |
| `ChatMessage` | `role` | `str` | 消息发送者角色，必填，可选值: user(用户), assistant(AI助手), system(系统提示词) | `PydanticUndefined` |
| `ChatMessage` | `user_id` | `typing.Optional[int]` | 发送该消息的用户ID，外键关联user表 | `无` |
| `ChatMessage` | `content` | `str` | 消息的正文文本内容，必填 | `PydanticUndefined` |
| `ChatMessage` | `images` | `typing.Optional[typing.List[str]]` | 消息附带的图片URL列表，JSON格式存储，非必填 | `无` |
| `ChatMessage` | `feedback` | `typing.Optional[str]` | 用户对该条AI回复的反馈，可选值: like(点赞), dislike(点踩) | `无` |
| `ChatMessage` | `is_favorite` | `bool` | 该消息是否被用户收藏，布尔值，默认False(否) | `False` |
| `ChatMessage` | `extra` | `typing.Optional[dict]` | 扩展信息字典(如引用来源、Token消耗等)，JSON格式存储，非必填 | `无` |
| `ChatMessage` | `id` | `uuid.UUID` | 消息全局唯一ID，主键，默认自动生成UUID | `PydanticUndefined` |
| `ChatMessage` | `session_id` | `uuid.UUID` | 所属会话的ID，外键关联chatsession表 | `PydanticUndefined` |
| `ChatMessage` | `created_at` | `datetime.datetime` | 消息发送时间，UTC时间，默认当前时间 | `PydanticUndefined` |
| `ChatMessageBase` | `role` | `str` | 消息发送者角色，必填，可选值: user(用户), assistant(AI助手), system(系统提示词) | `PydanticUndefined` |
| `ChatMessageBase` | `user_id` | `typing.Optional[int]` | 发送该消息的用户ID，外键关联user表 | `无` |
| `ChatMessageBase` | `content` | `str` | 消息的正文文本内容，必填 | `PydanticUndefined` |
| `ChatMessageBase` | `images` | `typing.Optional[typing.List[str]]` | 消息附带的图片URL列表，JSON格式存储，非必填 | `无` |
| `ChatMessageBase` | `feedback` | `typing.Optional[str]` | 用户对该条AI回复的反馈，可选值: like(点赞), dislike(点踩) | `无` |
| `ChatMessageBase` | `is_favorite` | `bool` | 该消息是否被用户收藏，布尔值，默认False(否) | `False` |
| `ChatMessageBase` | `extra` | `typing.Optional[dict]` | 扩展信息字典(如引用来源、Token消耗等)，JSON格式存储，非必填 | `无` |
| `ChatMessageRead` | `role` | `str` | 消息发送者角色，必填，可选值: user(用户), assistant(AI助手), system(系统提示词) | `PydanticUndefined` |
| `ChatMessageRead` | `user_id` | `typing.Optional[int]` | 发送该消息的用户ID，外键关联user表 | `无` |
| `ChatMessageRead` | `content` | `str` | 消息的正文文本内容，必填 | `PydanticUndefined` |
| `ChatMessageRead` | `images` | `typing.Optional[typing.List[str]]` | 消息附带的图片URL列表，JSON格式存储，非必填 | `无` |
| `ChatMessageRead` | `feedback` | `typing.Optional[str]` | 用户对该条AI回复的反馈，可选值: like(点赞), dislike(点踩) | `无` |
| `ChatMessageRead` | `is_favorite` | `bool` | 该消息是否被用户收藏，布尔值，默认False(否) | `False` |
| `ChatMessageRead` | `extra` | `typing.Optional[dict]` | 扩展信息字典(如引用来源、Token消耗等)，JSON格式存储，非必填 | `无` |
| `ChatMessageRead` | `id` | `uuid.UUID` | 消息ID | `PydanticUndefined` |
| `ChatMessageRead` | `created_at` | `datetime.datetime` | 创建时间 | `PydanticUndefined` |
| `ChatSession` | `title` | `str` | 会话标题，默认为'New Chat' | `New Chat` |
| `ChatSession` | `user_id` | `typing.Optional[int]` | 会话所属用户ID，外键关联user表，可为空表示匿名或公共会话 | `无` |
| `ChatSession` | `share_id` | `typing.Optional[str]` | 公开分享时的唯一标识符(UUID/Hash)，非必填 | `无` |
| `ChatSession` | `id` | `uuid.UUID` | 会话全局唯一ID，主键，默认自动生成UUID | `PydanticUndefined` |
| `ChatSession` | `created_at` | `datetime.datetime` | 会话创建时间，UTC时间，默认当前时间 | `PydanticUndefined` |
| `ChatSession` | `updated_at` | `datetime.datetime` | 会话最后更新时间，UTC时间，默认当前时间 | `PydanticUndefined` |
| `ChatSessionBase` | `title` | `str` | 会话标题，默认为'New Chat' | `New Chat` |
| `ChatSessionBase` | `user_id` | `typing.Optional[int]` | 会话所属用户ID，外键关联user表，可为空表示匿名或公共会话 | `无` |
| `ChatSessionBase` | `share_id` | `typing.Optional[str]` | 公开分享时的唯一标识符(UUID/Hash)，非必填 | `无` |
| `ChatSessionRead` | `title` | `str` | 会话标题，默认为'New Chat' | `New Chat` |
| `ChatSessionRead` | `user_id` | `typing.Optional[int]` | 会话所属用户ID，外键关联user表，可为空表示匿名或公共会话 | `无` |
| `ChatSessionRead` | `share_id` | `typing.Optional[str]` | 公开分享时的唯一标识符(UUID/Hash)，非必填 | `无` |
| `ChatSessionRead` | `id` | `uuid.UUID` | 会话ID | `PydanticUndefined` |
| `ChatSessionRead` | `created_at` | `datetime.datetime` | 创建时间 | `PydanticUndefined` |
| `ChatSessionRead` | `updated_at` | `datetime.datetime` | 更新时间 | `PydanticUndefined` |
| `ContentRepo` | `task_id` | `int` | 关联的具体计划任务ID，外键关联plantask表 | `PydanticUndefined` |
| `ContentRepo` | `user_id` | `typing.Optional[int]` | 上传或归属的用户ID，外键关联user表 | `无` |
| `ContentRepo` | `content_type` | `<enum ContentType` | 内容的具体类型(视频、文本、PDF等)，必填 | `PydanticUndefined` |
| `ContentRepo` | `url` | `typing.Optional[str]` | 内容的外部或内部链接URL，非必填 | `无` |
| `ContentRepo` | `text` | `typing.Optional[str]` | 如果是纯文本内容，这里直接存储文本正文，非必填 | `无` |
| `ContentRepo` | `title` | `str` | 内容资源的标题，必填项 | `PydanticUndefined` |
| `ContentRepo` | `duration_sec` | `typing.Optional[int]` | 内容的持续时间或预估消费时间，单位为秒(s)，非必填 | `无` |
| `ContentRepo` | `difficulty` | `float` | 内容难度系数，范围建议0.0-1.0，默认为0.5(中等难度) | `0.5` |
| `ContentRepo` | `tags` | `typing.Optional[str]` | 内容的标签集合，使用逗号分隔的字符串，非必填 | `无` |
| `ContentRepo` | `meta_data` | `typing.Optional[typing.Dict]` | 扩展的元数据信息(如视频分辨率、PDF页数等)，JSON格式存储 | `{}` |
| `ContentRepo` | `content_id` | `typing.Optional[int]` | 内容资源的主键ID | `无` |
| `ContentRepo` | `created_at` | `datetime.datetime` | 内容的创建或入库时间(UTC) | `PydanticUndefined` |
| `ContentRepoBase` | `task_id` | `int` | 关联的具体计划任务ID，外键关联plantask表 | `PydanticUndefined` |
| `ContentRepoBase` | `user_id` | `typing.Optional[int]` | 上传或归属的用户ID，外键关联user表 | `无` |
| `ContentRepoBase` | `content_type` | `<enum ContentType` | 内容的具体类型(视频、文本、PDF等)，必填 | `PydanticUndefined` |
| `ContentRepoBase` | `url` | `typing.Optional[str]` | 内容的外部或内部链接URL，非必填 | `无` |
| `ContentRepoBase` | `text` | `typing.Optional[str]` | 如果是纯文本内容，这里直接存储文本正文，非必填 | `无` |
| `ContentRepoBase` | `title` | `str` | 内容资源的标题，必填项 | `PydanticUndefined` |
| `ContentRepoBase` | `duration_sec` | `typing.Optional[int]` | 内容的持续时间或预估消费时间，单位为秒(s)，非必填 | `无` |
| `ContentRepoBase` | `difficulty` | `float` | 内容难度系数，范围建议0.0-1.0，默认为0.5(中等难度) | `0.5` |
| `ContentRepoBase` | `tags` | `typing.Optional[str]` | 内容的标签集合，使用逗号分隔的字符串，非必填 | `无` |
| `ContentRepoBase` | `meta_data` | `typing.Optional[typing.Dict]` | 扩展的元数据信息(如视频分辨率、PDF页数等)，JSON格式存储 | `{}` |
| `ContentRepoCreate` | `task_id` | `int` | 关联的具体计划任务ID，外键关联plantask表 | `PydanticUndefined` |
| `ContentRepoCreate` | `user_id` | `typing.Optional[int]` | 上传或归属的用户ID，外键关联user表 | `无` |
| `ContentRepoCreate` | `content_type` | `<enum ContentType` | 内容的具体类型(视频、文本、PDF等)，必填 | `PydanticUndefined` |
| `ContentRepoCreate` | `url` | `typing.Optional[str]` | 内容的外部或内部链接URL，非必填 | `无` |
| `ContentRepoCreate` | `text` | `typing.Optional[str]` | 如果是纯文本内容，这里直接存储文本正文，非必填 | `无` |
| `ContentRepoCreate` | `title` | `str` | 内容资源的标题，必填项 | `PydanticUndefined` |
| `ContentRepoCreate` | `duration_sec` | `typing.Optional[int]` | 内容的持续时间或预估消费时间，单位为秒(s)，非必填 | `无` |
| `ContentRepoCreate` | `difficulty` | `float` | 内容难度系数，范围建议0.0-1.0，默认为0.5(中等难度) | `0.5` |
| `ContentRepoCreate` | `tags` | `typing.Optional[str]` | 内容的标签集合，使用逗号分隔的字符串，非必填 | `无` |
| `ContentRepoCreate` | `meta_data` | `typing.Optional[typing.Dict]` | 扩展的元数据信息(如视频分辨率、PDF页数等)，JSON格式存储 | `{}` |
| `ContentRepoRead` | `task_id` | `int` | 关联的具体计划任务ID，外键关联plantask表 | `PydanticUndefined` |
| `ContentRepoRead` | `user_id` | `typing.Optional[int]` | 上传或归属的用户ID，外键关联user表 | `无` |
| `ContentRepoRead` | `content_type` | `<enum ContentType` | 内容的具体类型(视频、文本、PDF等)，必填 | `PydanticUndefined` |
| `ContentRepoRead` | `url` | `typing.Optional[str]` | 内容的外部或内部链接URL，非必填 | `无` |
| `ContentRepoRead` | `text` | `typing.Optional[str]` | 如果是纯文本内容，这里直接存储文本正文，非必填 | `无` |
| `ContentRepoRead` | `title` | `str` | 内容资源的标题，必填项 | `PydanticUndefined` |
| `ContentRepoRead` | `duration_sec` | `typing.Optional[int]` | 内容的持续时间或预估消费时间，单位为秒(s)，非必填 | `无` |
| `ContentRepoRead` | `difficulty` | `float` | 内容难度系数，范围建议0.0-1.0，默认为0.5(中等难度) | `0.5` |
| `ContentRepoRead` | `tags` | `typing.Optional[str]` | 内容的标签集合，使用逗号分隔的字符串，非必填 | `无` |
| `ContentRepoRead` | `meta_data` | `typing.Optional[typing.Dict]` | 扩展的元数据信息(如视频分辨率、PDF页数等)，JSON格式存储 | `{}` |
| `ContentRepoRead` | `content_id` | `int` | 内容资源ID | `PydanticUndefined` |
| `ContentRepoRead` | `created_at` | `datetime.datetime` | 创建时间 | `PydanticUndefined` |
| `ArticleNote` | `article_id` | `int` | 关联的RSS文章ID，外键关联rssarticle表，必填项 | `PydanticUndefined` |
| `ArticleNote` | `user_id` | `typing.Optional[int]` | 创建笔记的用户ID，外键关联user表，非必填 | `无` |
| `ArticleNote` | `selected_text` | `str` | 用户选中的原文高亮内容，必填项 | `PydanticUndefined` |
| `ArticleNote` | `start_offset` | `int` | 选中文本在文章正文中的起始字符位置偏移量，默认0 | `0` |
| `ArticleNote` | `end_offset` | `int` | 选中文本在文章正文中的结束字符位置偏移量，默认0 | `0` |
| `ArticleNote` | `color` | `str` | 高亮标记颜色，默认为黄色(yellow)，可选值: yellow, red, green, blue | `yellow` |
| `ArticleNote` | `content` | `typing.Optional[str]` | 用户针对该高亮段落填写的笔记内容，非必填 | `无` |
| `ArticleNote` | `tags` | `typing.Optional[str]` | 笔记的分类标签，多个标签以逗号分隔，非必填 | `无` |
| `ArticleNote` | `importance` | `int` | 笔记的重要程度等级，取值范围1-5，默认为1 | `1` |
| `ArticleNote` | `id` | `typing.Optional[int]` | 笔记主键ID，自增 | `无` |
| `ArticleNote` | `created_at` | `datetime.datetime` | 笔记创建时间，默认为当前时间 | `PydanticUndefined` |
| `ArticleNote` | `updated_at` | `datetime.datetime` | 笔记最后更新时间，默认为当前时间 | `PydanticUndefined` |
| `ArticleNoteBase` | `article_id` | `int` | 关联的RSS文章ID，外键关联rssarticle表，必填项 | `PydanticUndefined` |
| `ArticleNoteBase` | `user_id` | `typing.Optional[int]` | 创建笔记的用户ID，外键关联user表，非必填 | `无` |
| `ArticleNoteBase` | `selected_text` | `str` | 用户选中的原文高亮内容，必填项 | `PydanticUndefined` |
| `ArticleNoteBase` | `start_offset` | `int` | 选中文本在文章正文中的起始字符位置偏移量，默认0 | `0` |
| `ArticleNoteBase` | `end_offset` | `int` | 选中文本在文章正文中的结束字符位置偏移量，默认0 | `0` |
| `ArticleNoteBase` | `color` | `str` | 高亮标记颜色，默认为黄色(yellow)，可选值: yellow, red, green, blue | `yellow` |
| `ArticleNoteBase` | `content` | `typing.Optional[str]` | 用户针对该高亮段落填写的笔记内容，非必填 | `无` |
| `ArticleNoteBase` | `tags` | `typing.Optional[str]` | 笔记的分类标签，多个标签以逗号分隔，非必填 | `无` |
| `ArticleNoteBase` | `importance` | `int` | 笔记的重要程度等级，取值范围1-5，默认为1 | `1` |
| `ArticleNoteCreate` | `article_id` | `int` | 关联的RSS文章ID，外键关联rssarticle表，必填项 | `PydanticUndefined` |
| `ArticleNoteCreate` | `user_id` | `typing.Optional[int]` | 创建笔记的用户ID，外键关联user表，非必填 | `无` |
| `ArticleNoteCreate` | `selected_text` | `str` | 用户选中的原文高亮内容，必填项 | `PydanticUndefined` |
| `ArticleNoteCreate` | `start_offset` | `int` | 选中文本在文章正文中的起始字符位置偏移量，默认0 | `0` |
| `ArticleNoteCreate` | `end_offset` | `int` | 选中文本在文章正文中的结束字符位置偏移量，默认0 | `0` |
| `ArticleNoteCreate` | `color` | `str` | 高亮标记颜色，默认为黄色(yellow)，可选值: yellow, red, green, blue | `yellow` |
| `ArticleNoteCreate` | `content` | `typing.Optional[str]` | 用户针对该高亮段落填写的笔记内容，非必填 | `无` |
| `ArticleNoteCreate` | `tags` | `typing.Optional[str]` | 笔记的分类标签，多个标签以逗号分隔，非必填 | `无` |
| `ArticleNoteCreate` | `importance` | `int` | 笔记的重要程度等级，取值范围1-5，默认为1 | `1` |
| `ArticleNoteRead` | `article_id` | `int` | 关联的RSS文章ID，外键关联rssarticle表，必填项 | `PydanticUndefined` |
| `ArticleNoteRead` | `user_id` | `typing.Optional[int]` | 创建笔记的用户ID，外键关联user表，非必填 | `无` |
| `ArticleNoteRead` | `selected_text` | `str` | 用户选中的原文高亮内容，必填项 | `PydanticUndefined` |
| `ArticleNoteRead` | `start_offset` | `int` | 选中文本在文章正文中的起始字符位置偏移量，默认0 | `0` |
| `ArticleNoteRead` | `end_offset` | `int` | 选中文本在文章正文中的结束字符位置偏移量，默认0 | `0` |
| `ArticleNoteRead` | `color` | `str` | 高亮标记颜色，默认为黄色(yellow)，可选值: yellow, red, green, blue | `yellow` |
| `ArticleNoteRead` | `content` | `typing.Optional[str]` | 用户针对该高亮段落填写的笔记内容，非必填 | `无` |
| `ArticleNoteRead` | `tags` | `typing.Optional[str]` | 笔记的分类标签，多个标签以逗号分隔，非必填 | `无` |
| `ArticleNoteRead` | `importance` | `int` | 笔记的重要程度等级，取值范围1-5，默认为1 | `1` |
| `ArticleNoteRead` | `id` | `int` | 笔记ID | `PydanticUndefined` |
| `ArticleNoteRead` | `created_at` | `datetime.datetime` | 创建时间 | `PydanticUndefined` |
| `ArticleNoteRead` | `updated_at` | `datetime.datetime` | 更新时间 | `PydanticUndefined` |
| `ArticleNoteUpdate` | `selected_text` | `typing.Optional[str]` | 更新的选中原文 | `无` |
| `ArticleNoteUpdate` | `start_offset` | `typing.Optional[int]` | 更新的起始偏移量 | `无` |
| `ArticleNoteUpdate` | `end_offset` | `typing.Optional[int]` | 更新的结束偏移量 | `无` |
| `ArticleNoteUpdate` | `color` | `typing.Optional[str]` | 更新的高亮颜色 | `无` |
| `ArticleNoteUpdate` | `content` | `typing.Optional[str]` | 更新的笔记内容 | `无` |
| `ArticleNoteUpdate` | `tags` | `typing.Optional[str]` | 更新的标签 | `无` |
| `ArticleNoteUpdate` | `importance` | `typing.Optional[int]` | 更新的重要性 | `无` |
| `ArticleSummary` | `article_id` | `int` | 关联的RSS文章ID，外键关联rssarticle表，必填项 | `PydanticUndefined` |
| `ArticleSummary` | `user_id` | `typing.Optional[int]` | 所属用户ID，外键关联user表，非必填 | `无` |
| `ArticleSummary` | `content` | `str` | 文章的总结内容正文，支持HTML或Markdown格式，必填项 | `PydanticUndefined` |
| `ArticleSummary` | `is_draft` | `bool` | 是否为草稿状态，布尔值，默认False(否) | `False` |
| `ArticleSummary` | `version` | `int` | 总结内容的版本号，默认从1开始 | `1` |
| `ArticleSummary` | `id` | `typing.Optional[int]` | 总结记录的主键ID，自增 | `无` |
| `ArticleSummary` | `created_at` | `datetime.datetime` | 创建时间，默认为当前时间 | `PydanticUndefined` |
| `ArticleSummary` | `updated_at` | `datetime.datetime` | 最后更新时间，默认为当前时间 | `PydanticUndefined` |
| `ArticleSummary` | `is_vectorized` | `bool` | 总结内容是否已进行向量化处理以便检索，布尔值，默认False(否) | `False` |
| `ArticleSummaryBase` | `article_id` | `int` | 关联的RSS文章ID，外键关联rssarticle表，必填项 | `PydanticUndefined` |
| `ArticleSummaryBase` | `user_id` | `typing.Optional[int]` | 所属用户ID，外键关联user表，非必填 | `无` |
| `ArticleSummaryBase` | `content` | `str` | 文章的总结内容正文，支持HTML或Markdown格式，必填项 | `PydanticUndefined` |
| `ArticleSummaryBase` | `is_draft` | `bool` | 是否为草稿状态，布尔值，默认False(否) | `False` |
| `ArticleSummaryBase` | `version` | `int` | 总结内容的版本号，默认从1开始 | `1` |
| `ArticleSummaryCreate` | `article_id` | `int` | 关联的RSS文章ID，外键关联rssarticle表，必填项 | `PydanticUndefined` |
| `ArticleSummaryCreate` | `user_id` | `typing.Optional[int]` | 所属用户ID，外键关联user表，非必填 | `无` |
| `ArticleSummaryCreate` | `content` | `str` | 文章的总结内容正文，支持HTML或Markdown格式，必填项 | `PydanticUndefined` |
| `ArticleSummaryCreate` | `is_draft` | `bool` | 是否为草稿状态，布尔值，默认False(否) | `False` |
| `ArticleSummaryCreate` | `version` | `int` | 总结内容的版本号，默认从1开始 | `1` |
| `ArticleSummaryRead` | `article_id` | `int` | 关联的RSS文章ID，外键关联rssarticle表，必填项 | `PydanticUndefined` |
| `ArticleSummaryRead` | `user_id` | `typing.Optional[int]` | 所属用户ID，外键关联user表，非必填 | `无` |
| `ArticleSummaryRead` | `content` | `str` | 文章的总结内容正文，支持HTML或Markdown格式，必填项 | `PydanticUndefined` |
| `ArticleSummaryRead` | `is_draft` | `bool` | 是否为草稿状态，布尔值，默认False(否) | `False` |
| `ArticleSummaryRead` | `version` | `int` | 总结内容的版本号，默认从1开始 | `1` |
| `ArticleSummaryRead` | `id` | `int` | 总结ID | `PydanticUndefined` |
| `ArticleSummaryRead` | `created_at` | `datetime.datetime` | 创建时间 | `PydanticUndefined` |
| `ArticleSummaryRead` | `updated_at` | `datetime.datetime` | 更新时间 | `PydanticUndefined` |
| `ArticleSummaryUpdate` | `content` | `typing.Optional[str]` | 更新的总结内容 | `无` |
| `ArticleSummaryUpdate` | `is_draft` | `typing.Optional[bool]` | 更新的草稿状态 | `无` |
| `ArticleSummaryUpdate` | `version` | `typing.Optional[int]` | 更新的版本号 | `无` |
| `PlanCreateFull` | `user_id` | `int` | 创建该计划的用户ID，必填项，支持索引 | `PydanticUndefined` |
| `PlanCreateFull` | `goal` | `str` | 计划的总体目标描述，必填项 | `PydanticUndefined` |
| `PlanCreateFull` | `deadline` | `datetime.datetime` | 计划的整体截止时间，必填项 | `PydanticUndefined` |
| `PlanCreateFull` | `status` | `<enum PlanStatus` | 计划当前状态，默认值为草稿(draft) | `PlanStatus.DRAFT` |
| `PlanCreateFull` | `estimated_hours` | `typing.Optional[float]` | 预计完成计划所需的总小时数，非必填 | `无` |
| `PlanCreateFull` | `difficulty_coef` | `float` | 计划的难度系数(例如1.0为标准难度)，默认值为1.0 | `1.0` |
| `PlanCreateFull` | `version` | `int` | 计划的版本号，默认从1开始 | `1` |
| `PlanCreateFull` | `milestones` | `typing.List[app.models.plan.PlanMilestoneCreateNested]` | 包含的里程碑列表 | `[]` |
| `PlanHeader` | `user_id` | `int` | 创建该计划的用户ID，必填项，支持索引 | `PydanticUndefined` |
| `PlanHeader` | `goal` | `str` | 计划的总体目标描述，必填项 | `PydanticUndefined` |
| `PlanHeader` | `deadline` | `datetime.datetime` | 计划的整体截止时间，必填项 | `PydanticUndefined` |
| `PlanHeader` | `status` | `<enum PlanStatus` | 计划当前状态，默认值为草稿(draft) | `PlanStatus.DRAFT` |
| `PlanHeader` | `estimated_hours` | `typing.Optional[float]` | 预计完成计划所需的总小时数，非必填 | `无` |
| `PlanHeader` | `difficulty_coef` | `float` | 计划的难度系数(例如1.0为标准难度)，默认值为1.0 | `1.0` |
| `PlanHeader` | `version` | `int` | 计划的版本号，默认从1开始 | `1` |
| `PlanHeader` | `plan_id` | `typing.Optional[int]` | 计划主键ID，自动递增 | `无` |
| `PlanHeader` | `created_at` | `datetime.datetime` | 计划创建时间(UTC) | `PydanticUndefined` |
| `PlanHeader` | `updated_at` | `datetime.datetime` | 计划最后更新时间(UTC) | `PydanticUndefined` |
| `PlanHeaderBase` | `user_id` | `int` | 创建该计划的用户ID，必填项，支持索引 | `PydanticUndefined` |
| `PlanHeaderBase` | `goal` | `str` | 计划的总体目标描述，必填项 | `PydanticUndefined` |
| `PlanHeaderBase` | `deadline` | `datetime.datetime` | 计划的整体截止时间，必填项 | `PydanticUndefined` |
| `PlanHeaderBase` | `status` | `<enum PlanStatus` | 计划当前状态，默认值为草稿(draft) | `PlanStatus.DRAFT` |
| `PlanHeaderBase` | `estimated_hours` | `typing.Optional[float]` | 预计完成计划所需的总小时数，非必填 | `无` |
| `PlanHeaderBase` | `difficulty_coef` | `float` | 计划的难度系数(例如1.0为标准难度)，默认值为1.0 | `1.0` |
| `PlanHeaderBase` | `version` | `int` | 计划的版本号，默认从1开始 | `1` |
| `PlanHeaderCreate` | `user_id` | `int` | 创建该计划的用户ID，必填项，支持索引 | `PydanticUndefined` |
| `PlanHeaderCreate` | `goal` | `str` | 计划的总体目标描述，必填项 | `PydanticUndefined` |
| `PlanHeaderCreate` | `deadline` | `datetime.datetime` | 计划的整体截止时间，必填项 | `PydanticUndefined` |
| `PlanHeaderCreate` | `status` | `<enum PlanStatus` | 计划当前状态，默认值为草稿(draft) | `PlanStatus.DRAFT` |
| `PlanHeaderCreate` | `estimated_hours` | `typing.Optional[float]` | 预计完成计划所需的总小时数，非必填 | `无` |
| `PlanHeaderCreate` | `difficulty_coef` | `float` | 计划的难度系数(例如1.0为标准难度)，默认值为1.0 | `1.0` |
| `PlanHeaderCreate` | `version` | `int` | 计划的版本号，默认从1开始 | `1` |
| `PlanHeaderRead` | `user_id` | `int` | 创建该计划的用户ID，必填项，支持索引 | `PydanticUndefined` |
| `PlanHeaderRead` | `goal` | `str` | 计划的总体目标描述，必填项 | `PydanticUndefined` |
| `PlanHeaderRead` | `deadline` | `datetime.datetime` | 计划的整体截止时间，必填项 | `PydanticUndefined` |
| `PlanHeaderRead` | `status` | `<enum PlanStatus` | 计划当前状态，默认值为草稿(draft) | `PlanStatus.DRAFT` |
| `PlanHeaderRead` | `estimated_hours` | `typing.Optional[float]` | 预计完成计划所需的总小时数，非必填 | `无` |
| `PlanHeaderRead` | `difficulty_coef` | `float` | 计划的难度系数(例如1.0为标准难度)，默认值为1.0 | `1.0` |
| `PlanHeaderRead` | `version` | `int` | 计划的版本号，默认从1开始 | `1` |
| `PlanHeaderRead` | `plan_id` | `int` | 计划ID | `PydanticUndefined` |
| `PlanHeaderRead` | `created_at` | `datetime.datetime` | 创建时间 | `PydanticUndefined` |
| `PlanMilestone` | `title` | `str` | 里程碑的标题名称，必填项 | `PydanticUndefined` |
| `PlanMilestone` | `user_id` | `typing.Optional[int]` | 所属用户ID，外键关联user表，非必填 | `无` |
| `PlanMilestone` | `deadline` | `typing.Optional[datetime.datetime]` | 该里程碑的具体截止时间，非必填 | `无` |
| `PlanMilestone` | `status` | `<enum MilestoneStatus` | 里程碑状态，默认待开始(pending) | `MilestoneStatus.PENDING` |
| `PlanMilestone` | `order_index` | `int` | 里程碑在计划中的排序权重，数字越小越靠前，默认0 | `0` |
| `PlanMilestone` | `milestone_id` | `typing.Optional[int]` | 里程碑主键ID | `无` |
| `PlanMilestone` | `plan_id` | `int` | 所属的计划ID，外键关联planheader表 | `PydanticUndefined` |
| `PlanMilestone` | `created_at` | `datetime.datetime` | 里程碑创建时间(UTC) | `PydanticUndefined` |
| `PlanMilestoneBase` | `title` | `str` | 里程碑的标题名称，必填项 | `PydanticUndefined` |
| `PlanMilestoneBase` | `user_id` | `typing.Optional[int]` | 所属用户ID，外键关联user表，非必填 | `无` |
| `PlanMilestoneBase` | `deadline` | `typing.Optional[datetime.datetime]` | 该里程碑的具体截止时间，非必填 | `无` |
| `PlanMilestoneBase` | `status` | `<enum MilestoneStatus` | 里程碑状态，默认待开始(pending) | `MilestoneStatus.PENDING` |
| `PlanMilestoneBase` | `order_index` | `int` | 里程碑在计划中的排序权重，数字越小越靠前，默认0 | `0` |
| `PlanMilestoneCreate` | `title` | `str` | 里程碑的标题名称，必填项 | `PydanticUndefined` |
| `PlanMilestoneCreate` | `user_id` | `typing.Optional[int]` | 所属用户ID，外键关联user表，非必填 | `无` |
| `PlanMilestoneCreate` | `deadline` | `typing.Optional[datetime.datetime]` | 该里程碑的具体截止时间，非必填 | `无` |
| `PlanMilestoneCreate` | `status` | `<enum MilestoneStatus` | 里程碑状态，默认待开始(pending) | `MilestoneStatus.PENDING` |
| `PlanMilestoneCreate` | `order_index` | `int` | 里程碑在计划中的排序权重，数字越小越靠前，默认0 | `0` |
| `PlanMilestoneCreate` | `plan_id` | `int` | 所属的计划ID | `PydanticUndefined` |
| `PlanMilestoneCreateNested` | `title` | `str` | 里程碑的标题名称，必填项 | `PydanticUndefined` |
| `PlanMilestoneCreateNested` | `user_id` | `typing.Optional[int]` | 所属用户ID，外键关联user表，非必填 | `无` |
| `PlanMilestoneCreateNested` | `deadline` | `typing.Optional[datetime.datetime]` | 该里程碑的具体截止时间，非必填 | `无` |
| `PlanMilestoneCreateNested` | `status` | `<enum MilestoneStatus` | 里程碑状态，默认待开始(pending) | `MilestoneStatus.PENDING` |
| `PlanMilestoneCreateNested` | `order_index` | `int` | 里程碑在计划中的排序权重，数字越小越靠前，默认0 | `0` |
| `PlanMilestoneCreateNested` | `tasks` | `typing.List[app.models.plan.PlanTaskCreateNested]` | 包含的任务列表 | `[]` |
| `PlanMilestoneRead` | `title` | `str` | 里程碑的标题名称，必填项 | `PydanticUndefined` |
| `PlanMilestoneRead` | `user_id` | `typing.Optional[int]` | 所属用户ID，外键关联user表，非必填 | `无` |
| `PlanMilestoneRead` | `deadline` | `typing.Optional[datetime.datetime]` | 该里程碑的具体截止时间，非必填 | `无` |
| `PlanMilestoneRead` | `status` | `<enum MilestoneStatus` | 里程碑状态，默认待开始(pending) | `MilestoneStatus.PENDING` |
| `PlanMilestoneRead` | `order_index` | `int` | 里程碑在计划中的排序权重，数字越小越靠前，默认0 | `0` |
| `PlanMilestoneRead` | `milestone_id` | `int` | 里程碑ID | `PydanticUndefined` |
| `PlanMilestoneRead` | `plan_id` | `int` | 所属的计划ID | `PydanticUndefined` |
| `PlanTask` | `title` | `str` | 任务的标题名称，必填项 | `PydanticUndefined` |
| `PlanTask` | `user_id` | `typing.Optional[int]` | 所属用户ID，外键关联user表，非必填 | `无` |
| `PlanTask` | `type` | `<enum TaskType` | 任务的具体类型，默认other(其他) | `TaskType.OTHER` |
| `PlanTask` | `status` | `<enum TaskStatus` | 任务执行状态，默认pending(待开始) | `TaskStatus.PENDING` |
| `PlanTask` | `estimated_min` | `int` | 任务预计完成所需的时间，单位为分钟(min)，默认30分钟 | `30` |
| `PlanTask` | `order_index` | `int` | 任务在里程碑内的排序权重，默认0 | `0` |
| `PlanTask` | `description` | `typing.Optional[str]` | 任务的详细描述或指引，非必填 | `无` |
| `PlanTask` | `task_id` | `typing.Optional[int]` | 任务主键ID | `无` |
| `PlanTask` | `milestone_id` | `int` | 所属的里程碑ID，外键关联planmilestone表 | `PydanticUndefined` |
| `PlanTask` | `created_at` | `datetime.datetime` | 任务创建时间(UTC) | `PydanticUndefined` |
| `PlanTaskBase` | `title` | `str` | 任务的标题名称，必填项 | `PydanticUndefined` |
| `PlanTaskBase` | `user_id` | `typing.Optional[int]` | 所属用户ID，外键关联user表，非必填 | `无` |
| `PlanTaskBase` | `type` | `<enum TaskType` | 任务的具体类型，默认other(其他) | `TaskType.OTHER` |
| `PlanTaskBase` | `status` | `<enum TaskStatus` | 任务执行状态，默认pending(待开始) | `TaskStatus.PENDING` |
| `PlanTaskBase` | `estimated_min` | `int` | 任务预计完成所需的时间，单位为分钟(min)，默认30分钟 | `30` |
| `PlanTaskBase` | `order_index` | `int` | 任务在里程碑内的排序权重，默认0 | `0` |
| `PlanTaskBase` | `description` | `typing.Optional[str]` | 任务的详细描述或指引，非必填 | `无` |
| `PlanTaskCreate` | `title` | `str` | 任务的标题名称，必填项 | `PydanticUndefined` |
| `PlanTaskCreate` | `user_id` | `typing.Optional[int]` | 所属用户ID，外键关联user表，非必填 | `无` |
| `PlanTaskCreate` | `type` | `<enum TaskType` | 任务的具体类型，默认other(其他) | `TaskType.OTHER` |
| `PlanTaskCreate` | `status` | `<enum TaskStatus` | 任务执行状态，默认pending(待开始) | `TaskStatus.PENDING` |
| `PlanTaskCreate` | `estimated_min` | `int` | 任务预计完成所需的时间，单位为分钟(min)，默认30分钟 | `30` |
| `PlanTaskCreate` | `order_index` | `int` | 任务在里程碑内的排序权重，默认0 | `0` |
| `PlanTaskCreate` | `description` | `typing.Optional[str]` | 任务的详细描述或指引，非必填 | `无` |
| `PlanTaskCreate` | `milestone_id` | `int` | 所属的里程碑ID | `PydanticUndefined` |
| `PlanTaskCreateNested` | `title` | `str` | 任务的标题名称，必填项 | `PydanticUndefined` |
| `PlanTaskCreateNested` | `user_id` | `typing.Optional[int]` | 所属用户ID，外键关联user表，非必填 | `无` |
| `PlanTaskCreateNested` | `type` | `<enum TaskType` | 任务的具体类型，默认other(其他) | `TaskType.OTHER` |
| `PlanTaskCreateNested` | `status` | `<enum TaskStatus` | 任务执行状态，默认pending(待开始) | `TaskStatus.PENDING` |
| `PlanTaskCreateNested` | `estimated_min` | `int` | 任务预计完成所需的时间，单位为分钟(min)，默认30分钟 | `30` |
| `PlanTaskCreateNested` | `order_index` | `int` | 任务在里程碑内的排序权重，默认0 | `0` |
| `PlanTaskCreateNested` | `description` | `typing.Optional[str]` | 任务的详细描述或指引，非必填 | `无` |
| `PlanTaskRead` | `title` | `str` | 任务的标题名称，必填项 | `PydanticUndefined` |
| `PlanTaskRead` | `user_id` | `typing.Optional[int]` | 所属用户ID，外键关联user表，非必填 | `无` |
| `PlanTaskRead` | `type` | `<enum TaskType` | 任务的具体类型，默认other(其他) | `TaskType.OTHER` |
| `PlanTaskRead` | `status` | `<enum TaskStatus` | 任务执行状态，默认pending(待开始) | `TaskStatus.PENDING` |
| `PlanTaskRead` | `estimated_min` | `int` | 任务预计完成所需的时间，单位为分钟(min)，默认30分钟 | `30` |
| `PlanTaskRead` | `order_index` | `int` | 任务在里程碑内的排序权重，默认0 | `0` |
| `PlanTaskRead` | `description` | `typing.Optional[str]` | 任务的详细描述或指引，非必填 | `无` |
| `PlanTaskRead` | `task_id` | `int` | 任务ID | `PydanticUndefined` |
| `PlanTaskRead` | `milestone_id` | `int` | 所属的里程碑ID | `PydanticUndefined` |
| `EventLog` | `user_id` | `int` | 关联的用户ID，必填项，用于标识事件触发者 | `PydanticUndefined` |
| `EventLog` | `content_id` | `typing.Optional[int]` | 关联的学习内容ID，可选项，标识事件相关的具体内容 | `无` |
| `EventLog` | `event_type` | `<enum EventType` | 事件类型枚举，必填项，表示具体的行为动作 | `PydanticUndefined` |
| `EventLog` | `duration_sec` | `int` | 事件持续时间，单位：秒，默认值为0 | `0` |
| `EventLog` | `score` | `typing.Optional[float]` | 事件相关的得分或进度，可选项，例如测验得分 | `无` |
| `EventLog` | `meta_info` | `typing.Optional[str]` | 附加元数据信息，可选项，以JSON字符串或普通文本格式存储扩展数据 | `无` |
| `EventLog` | `log_id` | `typing.Optional[int]` | 日志记录唯一ID，主键 | `无` |
| `EventLog` | `created_at` | `datetime.datetime` | 日志创建时间，默认自动生成当前UTC时间 | `PydanticUndefined` |
| `EventLogBase` | `user_id` | `int` | 关联的用户ID，必填项，用于标识事件触发者 | `PydanticUndefined` |
| `EventLogBase` | `content_id` | `typing.Optional[int]` | 关联的学习内容ID，可选项，标识事件相关的具体内容 | `无` |
| `EventLogBase` | `event_type` | `<enum EventType` | 事件类型枚举，必填项，表示具体的行为动作 | `PydanticUndefined` |
| `EventLogBase` | `duration_sec` | `int` | 事件持续时间，单位：秒，默认值为0 | `0` |
| `EventLogBase` | `score` | `typing.Optional[float]` | 事件相关的得分或进度，可选项，例如测验得分 | `无` |
| `EventLogBase` | `meta_info` | `typing.Optional[str]` | 附加元数据信息，可选项，以JSON字符串或普通文本格式存储扩展数据 | `无` |
| `UserProgress` | `user_id` | `int` | 关联的用户ID，主键，与用户表一对一对应 | `PydanticUndefined` |
| `UserProgress` | `total_study_time_min` | `float` | 累计学习总时长，单位：分钟，默认值为0.0 | `0.0` |
| `UserProgress` | `completion_rate` | `float` | 整体内容完成率，取值范围0.0-1.0，默认值为0.0 | `0.0` |
| `UserProgress` | `accuracy_rate` | `float` | 测验或练习的整体准确率，取值范围0.0-1.0，默认值为0.0 | `0.0` |
| `UserProgress` | `streak_days` | `int` | 连续学习打卡天数，默认值为0 | `0` |
| `UserProgress` | `updated_at` | `datetime.datetime` | 最后一次更新时间，默认自动生成当前UTC时间 | `PydanticUndefined` |
| `UserProgressBase` | `user_id` | `int` | 关联的用户ID，主键，与用户表一对一对应 | `PydanticUndefined` |
| `UserProgressBase` | `total_study_time_min` | `float` | 累计学习总时长，单位：分钟，默认值为0.0 | `0.0` |
| `UserProgressBase` | `completion_rate` | `float` | 整体内容完成率，取值范围0.0-1.0，默认值为0.0 | `0.0` |
| `UserProgressBase` | `accuracy_rate` | `float` | 测验或练习的整体准确率，取值范围0.0-1.0，默认值为0.0 | `0.0` |
| `UserProgressBase` | `streak_days` | `int` | 连续学习打卡天数，默认值为0 | `0` |
| `UserReminder` | `user_id` | `int` | 关联的用户ID，必填项，建立用户与提醒设置的关联 | `PydanticUndefined` |
| `UserReminder` | `cron_expression` | `str` | Cron定时表达式，决定提醒触发时间，默认每天上午9点 | `0 9 * * *` |
| `UserReminder` | `method` | `<enum ReminderMethod` | 提醒发送方式枚举，默认值为站内信(WEB) | `ReminderMethod.WEB` |
| `UserReminder` | `enabled` | `bool` | 提醒规则是否启用，默认开启(True) | `True` |
| `UserReminder` | `message_template` | `typing.Optional[str]` | 自定义提醒消息模板，可选项，支持变量替换 | `无` |
| `UserReminder` | `target_url` | `typing.Optional[str]` | 目标推送地址，主要用于Webhook或外部接口调用时的目标URL，可选项 | `无` |
| `UserReminder` | `reminder_id` | `typing.Optional[int]` | 提醒规则唯一ID，主键 | `无` |
| `UserReminder` | `created_at` | `datetime.datetime` | 提醒规则创建时间，默认自动生成当前UTC时间 | `PydanticUndefined` |
| `UserReminder` | `updated_at` | `datetime.datetime` | 提醒规则更新时间，默认自动生成当前UTC时间 | `PydanticUndefined` |
| `UserReminderBase` | `user_id` | `int` | 关联的用户ID，必填项，建立用户与提醒设置的关联 | `PydanticUndefined` |
| `UserReminderBase` | `cron_expression` | `str` | Cron定时表达式，决定提醒触发时间，默认每天上午9点 | `0 9 * * *` |
| `UserReminderBase` | `method` | `<enum ReminderMethod` | 提醒发送方式枚举，默认值为站内信(WEB) | `ReminderMethod.WEB` |
| `UserReminderBase` | `enabled` | `bool` | 提醒规则是否启用，默认开启(True) | `True` |
| `UserReminderBase` | `message_template` | `typing.Optional[str]` | 自定义提醒消息模板，可选项，支持变量替换 | `无` |
| `UserReminderBase` | `target_url` | `typing.Optional[str]` | 目标推送地址，主要用于Webhook或外部接口调用时的目标URL，可选项 | `无` |
| `UserReminderCreate` | `user_id` | `int` | 关联的用户ID，必填项，建立用户与提醒设置的关联 | `PydanticUndefined` |
| `UserReminderCreate` | `cron_expression` | `str` | Cron定时表达式，决定提醒触发时间，默认每天上午9点 | `0 9 * * *` |
| `UserReminderCreate` | `method` | `<enum ReminderMethod` | 提醒发送方式枚举，默认值为站内信(WEB) | `ReminderMethod.WEB` |
| `UserReminderCreate` | `enabled` | `bool` | 提醒规则是否启用，默认开启(True) | `True` |
| `UserReminderCreate` | `message_template` | `typing.Optional[str]` | 自定义提醒消息模板，可选项，支持变量替换 | `无` |
| `UserReminderCreate` | `target_url` | `typing.Optional[str]` | 目标推送地址，主要用于Webhook或外部接口调用时的目标URL，可选项 | `无` |
| `UserReminderRead` | `user_id` | `int` | 关联的用户ID，必填项，建立用户与提醒设置的关联 | `PydanticUndefined` |
| `UserReminderRead` | `cron_expression` | `str` | Cron定时表达式，决定提醒触发时间，默认每天上午9点 | `0 9 * * *` |
| `UserReminderRead` | `method` | `<enum ReminderMethod` | 提醒发送方式枚举，默认值为站内信(WEB) | `ReminderMethod.WEB` |
| `UserReminderRead` | `enabled` | `bool` | 提醒规则是否启用，默认开启(True) | `True` |
| `UserReminderRead` | `message_template` | `typing.Optional[str]` | 自定义提醒消息模板，可选项，支持变量替换 | `无` |
| `UserReminderRead` | `target_url` | `typing.Optional[str]` | 目标推送地址，主要用于Webhook或外部接口调用时的目标URL，可选项 | `无` |
| `UserReminderRead` | `reminder_id` | `int` | 提醒规则唯一ID | `PydanticUndefined` |
| `UserReminderRead` | `created_at` | `datetime.datetime` | 提醒规则创建时间 | `PydanticUndefined` |
| `BatchDelete` | `feed_ids` | `typing.List[int]` | 需要批量删除的订阅源ID列表 | `PydanticUndefined` |
| `RSSArticle` | `title` | `str` | 文章的原始标题，必填项 | `PydanticUndefined` |
| `RSSArticle` | `user_id` | `typing.Optional[int]` | 归属的用户ID，非必填 | `无` |
| `RSSArticle` | `link` | `str` | 文章的原始访问链接，必填且建立索引 | `PydanticUndefined` |
| `RSSArticle` | `summary` | `typing.Optional[str]` | 文章的摘要内容或片段，非必填 | `无` |
| `RSSArticle` | `content` | `typing.Optional[str]` | 文章的完整HTML或纯文本正文内容，非必填 | `无` |
| `RSSArticle` | `published_at` | `typing.Optional[datetime.datetime]` | 文章的原始发布时间，非必填 | `无` |
| `RSSArticle` | `author` | `typing.Optional[str]` | 文章的作者名称，非必填 | `无` |
| `RSSArticle` | `category` | `typing.Optional[str]` | 文章的分类信息，非必填 | `无` |
| `RSSArticle` | `enclosure_url` | `typing.Optional[str]` | 文章附带的多媒体附件链接(如播客音频)，非必填 | `无` |
| `RSSArticle` | `enclosure_type` | `typing.Optional[str]` | 附件的MIME类型，非必填 | `无` |
| `RSSArticle` | `content_hash` | `str` | 基于文章内容计算的哈希值，用于重复检测和去重，必填且建立索引 | `PydanticUndefined` |
| `RSSArticle` | `is_read` | `bool` | 用户是否已阅读过该文章，布尔值，默认False(未读) | `False` |
| `RSSArticle` | `is_starred` | `bool` | 用户是否收藏了该文章，布尔值，默认False(未收藏) | `False` |
| `RSSArticle` | `is_vectorized` | `bool` | 文章内容是否已向量化入库以便语义检索，布尔值，默认False(否) | `False` |
| `RSSArticle` | `id` | `typing.Optional[int]` | 文章记录主键ID，自增 | `无` |
| `RSSArticle` | `feed_id` | `typing.Optional[int]` | 关联的订阅源ID，外键关联rssfeed表，非必填 | `无` |
| `RSSArticleBase` | `title` | `str` | 文章的原始标题，必填项 | `PydanticUndefined` |
| `RSSArticleBase` | `user_id` | `typing.Optional[int]` | 归属的用户ID，非必填 | `无` |
| `RSSArticleBase` | `link` | `str` | 文章的原始访问链接，必填且建立索引 | `PydanticUndefined` |
| `RSSArticleBase` | `summary` | `typing.Optional[str]` | 文章的摘要内容或片段，非必填 | `无` |
| `RSSArticleBase` | `content` | `typing.Optional[str]` | 文章的完整HTML或纯文本正文内容，非必填 | `无` |
| `RSSArticleBase` | `published_at` | `typing.Optional[datetime.datetime]` | 文章的原始发布时间，非必填 | `无` |
| `RSSArticleBase` | `author` | `typing.Optional[str]` | 文章的作者名称，非必填 | `无` |
| `RSSArticleBase` | `category` | `typing.Optional[str]` | 文章的分类信息，非必填 | `无` |
| `RSSArticleBase` | `enclosure_url` | `typing.Optional[str]` | 文章附带的多媒体附件链接(如播客音频)，非必填 | `无` |
| `RSSArticleBase` | `enclosure_type` | `typing.Optional[str]` | 附件的MIME类型，非必填 | `无` |
| `RSSArticleBase` | `content_hash` | `str` | 基于文章内容计算的哈希值，用于重复检测和去重，必填且建立索引 | `PydanticUndefined` |
| `RSSArticleBase` | `is_read` | `bool` | 用户是否已阅读过该文章，布尔值，默认False(未读) | `False` |
| `RSSArticleBase` | `is_starred` | `bool` | 用户是否收藏了该文章，布尔值，默认False(未收藏) | `False` |
| `RSSArticleBase` | `is_vectorized` | `bool` | 文章内容是否已向量化入库以便语义检索，布尔值，默认False(否) | `False` |
| `RSSArticleRead` | `title` | `str` | 文章的原始标题，必填项 | `PydanticUndefined` |
| `RSSArticleRead` | `user_id` | `typing.Optional[int]` | 归属的用户ID，非必填 | `无` |
| `RSSArticleRead` | `link` | `str` | 文章的原始访问链接，必填且建立索引 | `PydanticUndefined` |
| `RSSArticleRead` | `summary` | `typing.Optional[str]` | 文章的摘要内容或片段，非必填 | `无` |
| `RSSArticleRead` | `content` | `typing.Optional[str]` | 文章的完整HTML或纯文本正文内容，非必填 | `无` |
| `RSSArticleRead` | `published_at` | `typing.Optional[datetime.datetime]` | 文章的原始发布时间，非必填 | `无` |
| `RSSArticleRead` | `author` | `typing.Optional[str]` | 文章的作者名称，非必填 | `无` |
| `RSSArticleRead` | `category` | `typing.Optional[str]` | 文章的分类信息，非必填 | `无` |
| `RSSArticleRead` | `enclosure_url` | `typing.Optional[str]` | 文章附带的多媒体附件链接(如播客音频)，非必填 | `无` |
| `RSSArticleRead` | `enclosure_type` | `typing.Optional[str]` | 附件的MIME类型，非必填 | `无` |
| `RSSArticleRead` | `content_hash` | `str` | 基于文章内容计算的哈希值，用于重复检测和去重，必填且建立索引 | `PydanticUndefined` |
| `RSSArticleRead` | `is_read` | `bool` | 用户是否已阅读过该文章，布尔值，默认False(未读) | `False` |
| `RSSArticleRead` | `is_starred` | `bool` | 用户是否收藏了该文章，布尔值，默认False(未收藏) | `False` |
| `RSSArticleRead` | `is_vectorized` | `bool` | 文章内容是否已向量化入库以便语义检索，布尔值，默认False(否) | `False` |
| `RSSArticleRead` | `id` | `int` | 文章ID | `PydanticUndefined` |
| `RSSArticleRead` | `feed_title` | `typing.Optional[str]` | 所属的订阅源标题名称，非必填 | `无` |
| `RSSFeed` | `url` | `str` | RSS源的XML链接地址，必填且全局唯一 | `PydanticUndefined` |
| `RSSFeed` | `user_id` | `typing.Optional[int]` | 所属用户ID，外键关联user表，非必填 | `无` |
| `RSSFeed` | `title` | `typing.Optional[str]` | 抓取到的或用户自定义的订阅源标题，非必填 | `无` |
| `RSSFeed` | `description` | `typing.Optional[str]` | 订阅源的描述信息，非必填 | `无` |
| `RSSFeed` | `group_name` | `typing.Optional[str]` | 订阅源分组名称(已废弃，建议使用groups关联)，非必填 | `无` |
| `RSSFeed` | `is_active` | `bool` | 是否启用自动抓取，布尔值，默认True(启用) | `True` |
| `RSSFeed` | `is_whitelisted` | `bool` | 是否被加入白名单(免于被自动清理保护)，布尔值，默认False(否) | `False` |
| `RSSFeed` | `id` | `typing.Optional[int]` | 订阅源主键ID，自增 | `无` |
| `RSSFeed` | `last_fetched_at` | `typing.Optional[datetime.datetime]` | 最后一次成功抓取更新的时间戳，非必填 | `无` |
| `RSSFeed` | `last_fetch_status` | `str` | 最后一次抓取任务的状态，默认为pending，可选值: success(成功), error(失败), pending(待抓取) | `pending` |
| `RSSFeed` | `error_message` | `typing.Optional[str]` | 如果抓取失败，记录的详细错误信息，非必填 | `无` |
| `RSSFeedBase` | `url` | `str` | RSS源的XML链接地址，必填且全局唯一 | `PydanticUndefined` |
| `RSSFeedBase` | `user_id` | `typing.Optional[int]` | 所属用户ID，外键关联user表，非必填 | `无` |
| `RSSFeedBase` | `title` | `typing.Optional[str]` | 抓取到的或用户自定义的订阅源标题，非必填 | `无` |
| `RSSFeedBase` | `description` | `typing.Optional[str]` | 订阅源的描述信息，非必填 | `无` |
| `RSSFeedBase` | `group_name` | `typing.Optional[str]` | 订阅源分组名称(已废弃，建议使用groups关联)，非必填 | `无` |
| `RSSFeedBase` | `is_active` | `bool` | 是否启用自动抓取，布尔值，默认True(启用) | `True` |
| `RSSFeedBase` | `is_whitelisted` | `bool` | 是否被加入白名单(免于被自动清理保护)，布尔值，默认False(否) | `False` |
| `RSSFeedCreate` | `url` | `str` | RSS源的XML链接地址，必填且全局唯一 | `PydanticUndefined` |
| `RSSFeedCreate` | `user_id` | `typing.Optional[int]` | 所属用户ID，外键关联user表，非必填 | `无` |
| `RSSFeedCreate` | `title` | `typing.Optional[str]` | 抓取到的或用户自定义的订阅源标题，非必填 | `无` |
| `RSSFeedCreate` | `description` | `typing.Optional[str]` | 订阅源的描述信息，非必填 | `无` |
| `RSSFeedCreate` | `group_name` | `typing.Optional[str]` | 订阅源分组名称(已废弃，建议使用groups关联)，非必填 | `无` |
| `RSSFeedCreate` | `is_active` | `bool` | 是否启用自动抓取，布尔值，默认True(启用) | `True` |
| `RSSFeedCreate` | `is_whitelisted` | `bool` | 是否被加入白名单(免于被自动清理保护)，布尔值，默认False(否) | `False` |
| `RSSFeedCreate` | `group_ids` | `typing.Optional[typing.List[int]]` | 创建时关联的分组ID列表 | `无` |
| `RSSFeedGroupLink` | `feed_id` | `typing.Optional[int]` | 关联的订阅源ID，联合主键 | `无` |
| `RSSFeedGroupLink` | `group_id` | `typing.Optional[int]` | 关联的分组ID，联合主键 | `无` |
| `RSSFeedRead` | `url` | `str` | RSS源的XML链接地址，必填且全局唯一 | `PydanticUndefined` |
| `RSSFeedRead` | `user_id` | `typing.Optional[int]` | 所属用户ID，外键关联user表，非必填 | `无` |
| `RSSFeedRead` | `title` | `typing.Optional[str]` | 抓取到的或用户自定义的订阅源标题，非必填 | `无` |
| `RSSFeedRead` | `description` | `typing.Optional[str]` | 订阅源的描述信息，非必填 | `无` |
| `RSSFeedRead` | `group_name` | `typing.Optional[str]` | 订阅源分组名称(已废弃，建议使用groups关联)，非必填 | `无` |
| `RSSFeedRead` | `is_active` | `bool` | 是否启用自动抓取，布尔值，默认True(启用) | `True` |
| `RSSFeedRead` | `is_whitelisted` | `bool` | 是否被加入白名单(免于被自动清理保护)，布尔值，默认False(否) | `False` |
| `RSSFeedRead` | `id` | `int` | 订阅源ID | `PydanticUndefined` |
| `RSSFeedRead` | `last_fetched_at` | `typing.Optional[datetime.datetime]` | 最后一次成功抓取的时间 | `无` |
| `RSSFeedRead` | `last_fetch_status` | `str` | 最后一次抓取状态 | `pending` |
| `RSSFeedRead` | `error_message` | `typing.Optional[str]` | 错误信息 | `无` |
| `RSSFeedRead` | `articles_count` | `int` | 该订阅源下入库的文章总数量 | `0` |
| `RSSFeedRead` | `groups` | `typing.List[app.models.rss.RSSGroupRead]` | 所属分组列表 | `[]` |
| `RSSFeedUpdate` | `url` | `typing.Optional[str]` | 更新的URL | `无` |
| `RSSFeedUpdate` | `title` | `typing.Optional[str]` | 更新的标题 | `无` |
| `RSSFeedUpdate` | `description` | `typing.Optional[str]` | 更新的描述 | `无` |
| `RSSFeedUpdate` | `group_name` | `typing.Optional[str]` | 更新的废弃分组名 | `无` |
| `RSSFeedUpdate` | `is_active` | `typing.Optional[bool]` | 更新的启用状态 | `无` |
| `RSSFeedUpdate` | `is_whitelisted` | `typing.Optional[bool]` | 更新的白名单状态 | `无` |
| `RSSFeedUpdate` | `group_ids` | `typing.Optional[typing.List[int]]` | 更新的关联分组列表 | `无` |
| `RSSGroup` | `name` | `str` | 分组名称，必填且全局唯一 | `PydanticUndefined` |
| `RSSGroup` | `user_id` | `typing.Optional[int]` | 创建该分组的用户ID，外键关联user表，非必填 | `无` |
| `RSSGroup` | `parent_id` | `typing.Optional[int]` | 父级分组ID，用于构建树形结构，外键关联自身，非必填 | `无` |
| `RSSGroup` | `icon` | `typing.Optional[str]` | 分组对应的图标或Emoji，非必填 | `无` |
| `RSSGroup` | `color` | `typing.Optional[str]` | 分组的颜色标识代码(如Hex)，非必填 | `无` |
| `RSSGroup` | `order` | `int` | 分组的展示排序权重，数字越小越靠前，默认0 | `0` |
| `RSSGroup` | `id` | `typing.Optional[int]` | 分组主键ID，自增 | `无` |
| `RSSGroupBase` | `name` | `str` | 分组名称，必填且全局唯一 | `PydanticUndefined` |
| `RSSGroupBase` | `user_id` | `typing.Optional[int]` | 创建该分组的用户ID，外键关联user表，非必填 | `无` |
| `RSSGroupBase` | `parent_id` | `typing.Optional[int]` | 父级分组ID，用于构建树形结构，外键关联自身，非必填 | `无` |
| `RSSGroupBase` | `icon` | `typing.Optional[str]` | 分组对应的图标或Emoji，非必填 | `无` |
| `RSSGroupBase` | `color` | `typing.Optional[str]` | 分组的颜色标识代码(如Hex)，非必填 | `无` |
| `RSSGroupBase` | `order` | `int` | 分组的展示排序权重，数字越小越靠前，默认0 | `0` |
| `RSSGroupCreate` | `name` | `str` | 分组名称，必填且全局唯一 | `PydanticUndefined` |
| `RSSGroupCreate` | `user_id` | `typing.Optional[int]` | 创建该分组的用户ID，外键关联user表，非必填 | `无` |
| `RSSGroupCreate` | `parent_id` | `typing.Optional[int]` | 父级分组ID，用于构建树形结构，外键关联自身，非必填 | `无` |
| `RSSGroupCreate` | `icon` | `typing.Optional[str]` | 分组对应的图标或Emoji，非必填 | `无` |
| `RSSGroupCreate` | `color` | `typing.Optional[str]` | 分组的颜色标识代码(如Hex)，非必填 | `无` |
| `RSSGroupCreate` | `order` | `int` | 分组的展示排序权重，数字越小越靠前，默认0 | `0` |
| `RSSGroupRead` | `name` | `str` | 分组名称，必填且全局唯一 | `PydanticUndefined` |
| `RSSGroupRead` | `user_id` | `typing.Optional[int]` | 创建该分组的用户ID，外键关联user表，非必填 | `无` |
| `RSSGroupRead` | `parent_id` | `typing.Optional[int]` | 父级分组ID，用于构建树形结构，外键关联自身，非必填 | `无` |
| `RSSGroupRead` | `icon` | `typing.Optional[str]` | 分组对应的图标或Emoji，非必填 | `无` |
| `RSSGroupRead` | `color` | `typing.Optional[str]` | 分组的颜色标识代码(如Hex)，非必填 | `无` |
| `RSSGroupRead` | `order` | `int` | 分组的展示排序权重，数字越小越靠前，默认0 | `0` |
| `RSSGroupRead` | `id` | `int` | 分组ID | `PydanticUndefined` |
| `RSSGroupRead` | `feeds_count` | `int` | 分组下包含的订阅源数量 | `0` |
| `RSSGroupRead` | `children` | `typing.List[app.models.rss.RSSGroupRead]` | 子分组列表 | `[]` |
| `RSSGroupUpdate` | `name` | `typing.Optional[str]` | 更新的名称 | `无` |
| `RSSGroupUpdate` | `parent_id` | `typing.Optional[int]` | 更新的父分组ID | `无` |
| `RSSGroupUpdate` | `icon` | `typing.Optional[str]` | 更新的图标 | `无` |
| `RSSGroupUpdate` | `color` | `typing.Optional[str]` | 更新的颜色 | `无` |
| `RSSGroupUpdate` | `order` | `typing.Optional[int]` | 更新的排序 | `无` |
| `Schedule` | `title` | `str` | 日程标题，必填项，简明扼要地说明日程内容 | `PydanticUndefined` |
| `Schedule` | `description` | `typing.Optional[str]` | 日程详细描述，非必填，可包含更多背景信息 | `无` |
| `Schedule` | `start_time` | `datetime.datetime` | 日程开始时间，必填项，带时区的时间戳 | `PydanticUndefined` |
| `Schedule` | `end_time` | `typing.Optional[datetime.datetime]` | 日程结束时间，非必填，带时区的时间戳 | `无` |
| `Schedule` | `due_time` | `typing.Optional[datetime.datetime]` | 任务到期时间，非必填，适用于带截止日期的任务 | `无` |
| `Schedule` | `priority` | `<enum Priority` | 日程优先级，默认值为中(medium)，可选值: high, medium, low | `Priority.MEDIUM` |
| `Schedule` | `location` | `typing.Optional[str]` | 日程地点，非必填，可为物理地址或线上会议链接 | `无` |
| `Schedule` | `is_all_day` | `bool` | 是否为全天日程，布尔值，默认为False(否) | `False` |
| `Schedule` | `user_id` | `typing.Optional[int]` | 关联的用户ID，外键指向user表，非必填 | `无` |
| `Schedule` | `id` | `uuid.UUID` | 日程唯一标识，主键，默认自动生成UUID | `PydanticUndefined` |
| `Schedule` | `created_at` | `datetime.datetime` | 创建时间，默认为当前时间 | `PydanticUndefined` |
| `Schedule` | `updated_at` | `datetime.datetime` | 最后更新时间，默认为当前时间 | `PydanticUndefined` |
| `ScheduleBase` | `title` | `str` | 日程标题，必填项，简明扼要地说明日程内容 | `PydanticUndefined` |
| `ScheduleBase` | `description` | `typing.Optional[str]` | 日程详细描述，非必填，可包含更多背景信息 | `无` |
| `ScheduleBase` | `start_time` | `datetime.datetime` | 日程开始时间，必填项，带时区的时间戳 | `PydanticUndefined` |
| `ScheduleBase` | `end_time` | `typing.Optional[datetime.datetime]` | 日程结束时间，非必填，带时区的时间戳 | `无` |
| `ScheduleBase` | `due_time` | `typing.Optional[datetime.datetime]` | 任务到期时间，非必填，适用于带截止日期的任务 | `无` |
| `ScheduleBase` | `priority` | `<enum Priority` | 日程优先级，默认值为中(medium)，可选值: high, medium, low | `Priority.MEDIUM` |
| `ScheduleBase` | `location` | `typing.Optional[str]` | 日程地点，非必填，可为物理地址或线上会议链接 | `无` |
| `ScheduleBase` | `is_all_day` | `bool` | 是否为全天日程，布尔值，默认为False(否) | `False` |
| `ScheduleBase` | `user_id` | `typing.Optional[int]` | 关联的用户ID，外键指向user表，非必填 | `无` |
| `ScheduleCreate` | `title` | `str` | 日程标题，必填项，简明扼要地说明日程内容 | `PydanticUndefined` |
| `ScheduleCreate` | `description` | `typing.Optional[str]` | 日程详细描述，非必填，可包含更多背景信息 | `无` |
| `ScheduleCreate` | `start_time` | `datetime.datetime` | 日程开始时间，必填项，带时区的时间戳 | `PydanticUndefined` |
| `ScheduleCreate` | `end_time` | `typing.Optional[datetime.datetime]` | 日程结束时间，非必填，带时区的时间戳 | `无` |
| `ScheduleCreate` | `due_time` | `typing.Optional[datetime.datetime]` | 任务到期时间，非必填，适用于带截止日期的任务 | `无` |
| `ScheduleCreate` | `priority` | `<enum Priority` | 日程优先级，默认值为中(medium)，可选值: high, medium, low | `Priority.MEDIUM` |
| `ScheduleCreate` | `location` | `typing.Optional[str]` | 日程地点，非必填，可为物理地址或线上会议链接 | `无` |
| `ScheduleCreate` | `is_all_day` | `bool` | 是否为全天日程，布尔值，默认为False(否) | `False` |
| `ScheduleCreate` | `user_id` | `typing.Optional[int]` | 关联的用户ID，外键指向user表，非必填 | `无` |
| `ScheduleCreate` | `reminders` | `typing.Optional[typing.List[app.models.schedule.ScheduleReminderCreate]]` | 创建日程时附带的提醒列表 | `无` |
| `ScheduleReminder` | `remind_at` | `datetime.datetime` | 触发提醒的具体时间，必填项 | `PydanticUndefined` |
| `ScheduleReminder` | `type` | `<enum ReminderType` | 提醒发送方式，默认值为系统通知(notification) | `ReminderType.NOTIFICATION` |
| `ScheduleReminder` | `message_template` | `typing.Optional[str]` | 自定义提醒内容模板，非必填 | `无` |
| `ScheduleReminder` | `id` | `uuid.UUID` | 提醒记录唯一标识，主键，默认自动生成UUID | `PydanticUndefined` |
| `ScheduleReminder` | `schedule_id` | `uuid.UUID` | 关联的日程ID，外键指向schedule表 | `PydanticUndefined` |
| `ScheduleReminder` | `status` | `str` | 提醒发送状态，默认值为待发送(pending)，可选值: pending(待发送), sent(已发送), failed(失败) | `pending` |
| `ScheduleReminderBase` | `remind_at` | `datetime.datetime` | 触发提醒的具体时间，必填项 | `PydanticUndefined` |
| `ScheduleReminderBase` | `type` | `<enum ReminderType` | 提醒发送方式，默认值为系统通知(notification) | `ReminderType.NOTIFICATION` |
| `ScheduleReminderBase` | `message_template` | `typing.Optional[str]` | 自定义提醒内容模板，非必填 | `无` |
| `ScheduleReminderCreate` | `remind_at` | `datetime.datetime` | 触发提醒的具体时间，必填项 | `PydanticUndefined` |
| `ScheduleReminderCreate` | `type` | `<enum ReminderType` | 提醒发送方式，默认值为系统通知(notification) | `ReminderType.NOTIFICATION` |
| `ScheduleReminderCreate` | `message_template` | `typing.Optional[str]` | 自定义提醒内容模板，非必填 | `无` |
| `ScheduleUpdate` | `title` | `typing.Optional[str]` | 更新的日程标题 | `无` |
| `ScheduleUpdate` | `description` | `typing.Optional[str]` | 更新的日程描述 | `无` |
| `ScheduleUpdate` | `start_time` | `typing.Optional[datetime.datetime]` | 更新的开始时间 | `无` |
| `ScheduleUpdate` | `end_time` | `typing.Optional[datetime.datetime]` | 更新的结束时间 | `无` |
| `ScheduleUpdate` | `due_time` | `typing.Optional[datetime.datetime]` | 更新的到期时间 | `无` |
| `ScheduleUpdate` | `priority` | `typing.Optional[app.models.schedule.Priority]` | 更新的优先级 | `无` |
| `ScheduleUpdate` | `location` | `typing.Optional[str]` | 更新的地点 | `无` |
| `ScheduleUpdate` | `is_all_day` | `typing.Optional[bool]` | 更新的全局全天状态 | `无` |
| `ScheduleUpdate` | `reminders` | `typing.Optional[typing.List[app.models.schedule.ScheduleReminderCreate]]` | 更新的提醒列表，通常为全量替换 | `无` |
| `Task` | `name` | `str` | 任务名称，必填项，用于直观识别任务用途 | `PydanticUndefined` |
| `Task` | `description` | `typing.Optional[str]` | 任务的详细说明描述，非必填 | `无` |
| `Task` | `user_id` | `typing.Optional[int]` | 创建或拥有该任务的用户ID，外键关联user表，非必填 | `无` |
| `Task` | `type` | `str` | 任务执行类型，必填项，可选值: script(脚本), function(函数), webhook, ai_dialogue(AI对话) | `PydanticUndefined` |
| `Task` | `payload` | `str` | 任务具体的执行载荷，必填项(如脚本路径、函数名、Webhook URL、AI提示词等) | `PydanticUndefined` |
| `Task` | `schedule_type` | `str` | 调度类型，必填项，可选值: cron(Cron表达式), interval(间隔时间), date(特定日期执行一次) | `PydanticUndefined` |
| `Task` | `schedule_config` | `typing.Dict` | 具体的调度配置参数，JSON格式(如 {'cron': '0 0 * * *'} )，默认空字典 | `{}` |
| `Task` | `is_active` | `bool` | 任务是否处于启用状态，布尔值，默认True(启用) | `True` |
| `Task` | `id` | `uuid.UUID` | 任务全局唯一标识ID，主键，默认自动生成UUID | `PydanticUndefined` |
| `Task` | `last_run_at` | `typing.Optional[datetime.datetime]` | 最近一次实际执行任务的时间戳，非必填 | `无` |
| `Task` | `next_run_at` | `typing.Optional[datetime.datetime]` | 根据调度策略计算出的下一次预期执行时间戳，非必填 | `无` |
| `Task` | `created_at` | `datetime.datetime` | 任务创建时间，默认为当前时间 | `PydanticUndefined` |
| `Task` | `updated_at` | `datetime.datetime` | 任务最后修改时间，默认为当前时间 | `PydanticUndefined` |
| `TaskBase` | `name` | `str` | 任务名称，必填项，用于直观识别任务用途 | `PydanticUndefined` |
| `TaskBase` | `description` | `typing.Optional[str]` | 任务的详细说明描述，非必填 | `无` |
| `TaskBase` | `user_id` | `typing.Optional[int]` | 创建或拥有该任务的用户ID，外键关联user表，非必填 | `无` |
| `TaskBase` | `type` | `str` | 任务执行类型，必填项，可选值: script(脚本), function(函数), webhook, ai_dialogue(AI对话) | `PydanticUndefined` |
| `TaskBase` | `payload` | `str` | 任务具体的执行载荷，必填项(如脚本路径、函数名、Webhook URL、AI提示词等) | `PydanticUndefined` |
| `TaskBase` | `schedule_type` | `str` | 调度类型，必填项，可选值: cron(Cron表达式), interval(间隔时间), date(特定日期执行一次) | `PydanticUndefined` |
| `TaskBase` | `schedule_config` | `typing.Dict` | 具体的调度配置参数，JSON格式(如 {'cron': '0 0 * * *'} )，默认空字典 | `{}` |
| `TaskBase` | `is_active` | `bool` | 任务是否处于启用状态，布尔值，默认True(启用) | `True` |
| `TaskCreate` | `name` | `str` | 任务名称，必填项，用于直观识别任务用途 | `PydanticUndefined` |
| `TaskCreate` | `description` | `typing.Optional[str]` | 任务的详细说明描述，非必填 | `无` |
| `TaskCreate` | `user_id` | `typing.Optional[int]` | 创建或拥有该任务的用户ID，外键关联user表，非必填 | `无` |
| `TaskCreate` | `type` | `str` | 任务执行类型，必填项，可选值: script(脚本), function(函数), webhook, ai_dialogue(AI对话) | `PydanticUndefined` |
| `TaskCreate` | `payload` | `str` | 任务具体的执行载荷，必填项(如脚本路径、函数名、Webhook URL、AI提示词等) | `PydanticUndefined` |
| `TaskCreate` | `schedule_type` | `str` | 调度类型，必填项，可选值: cron(Cron表达式), interval(间隔时间), date(特定日期执行一次) | `PydanticUndefined` |
| `TaskCreate` | `schedule_config` | `typing.Dict` | 具体的调度配置参数，JSON格式(如 {'cron': '0 0 * * *'} )，默认空字典 | `{}` |
| `TaskCreate` | `is_active` | `bool` | 任务是否处于启用状态，布尔值，默认True(启用) | `True` |
| `TaskLog` | `id` | `uuid.UUID` | 日志记录全局唯一ID，主键 | `PydanticUndefined` |
| `TaskLog` | `task_id` | `uuid.UUID` | 关联的任务ID，外键指向task表，必填项 | `PydanticUndefined` |
| `TaskLog` | `user_id` | `typing.Optional[int]` | 关联的用户ID，外键指向user表，非必填 | `无` |
| `TaskLog` | `status` | `str` | 该次执行的结果状态，必填项，可选值: success(成功), failed(失败), running(执行中) | `PydanticUndefined` |
| `TaskLog` | `output` | `typing.Optional[str]` | 任务执行后的标准输出日志或错误堆栈信息，非必填 | `无` |
| `TaskLog` | `duration` | `typing.Optional[float]` | 该次任务执行消耗的时间，单位为毫秒(ms)，非必填 | `无` |
| `TaskLog` | `created_at` | `datetime.datetime` | 日志生成/任务触发时间，默认为当前时间 | `PydanticUndefined` |
| `TaskUpdate` | `name` | `typing.Optional[str]` | 更新的任务名称 | `无` |
| `TaskUpdate` | `description` | `typing.Optional[str]` | 更新的描述 | `无` |
| `TaskUpdate` | `type` | `typing.Optional[str]` | 更新的任务类型 | `无` |
| `TaskUpdate` | `payload` | `typing.Optional[str]` | 更新的执行载荷 | `无` |
| `TaskUpdate` | `schedule_type` | `typing.Optional[str]` | 更新的调度类型 | `无` |
| `TaskUpdate` | `schedule_config` | `typing.Optional[typing.Dict]` | 更新的调度配置 | `无` |
| `TaskUpdate` | `is_active` | `typing.Optional[bool]` | 更新的启用状态 | `无` |
| `LoginLog` | `id` | `typing.Optional[int]` | 登录日志记录全局唯一ID，主键 | `无` |
| `LoginLog` | `user_id` | `int` | 关联的用户ID，必填项，外键指向user表 | `PydanticUndefined` |
| `LoginLog` | `login_time` | `datetime.datetime` | 登录操作发生时间，默认自动生成当前UTC时间 | `PydanticUndefined` |
| `LoginLog` | `ip_address` | `str` | 登录时使用的IP地址，必填项 | `PydanticUndefined` |
| `LoginLog` | `status` | `<enum LoginStatus` | 登录状态枚举，默认值为成功(SUCCESS) | `LoginStatus.SUCCESS` |
| `LoginLog` | `failure_reason` | `typing.Optional[str]` | 登录失败的具体原因，可选项 | `无` |
| `LoginLog` | `user_agent` | `typing.Optional[str]` | 登录时客户端的User-Agent信息，可选项 | `无` |
| `Role` | `id` | `typing.Optional[int]` | 角色记录全局唯一ID，主键 | `无` |
| `Role` | `name` | `str` | 角色名称，必填项，要求唯一且最长50字符 | `PydanticUndefined` |
| `Role` | `description` | `typing.Optional[str]` | 角色描述，可选项，最长255字符 | `无` |
| `Role` | `permissions` | `typing.List[str]` | 权限标识集合，默认空列表，以JSON格式存储 | `[]` |
| `User` | `id` | `typing.Optional[int]` | 用户记录全局唯一ID，主键 | `无` |
| `User` | `username` | `str` | 用户名，必填项，要求唯一且最长50字符 | `PydanticUndefined` |
| `User` | `email` | `typing.Optional[str]` | 用户电子邮箱，可选项，要求唯一且最长100字符 | `无` |
| `User` | `phone` | `typing.Optional[str]` | 用户手机号码，可选项，要求唯一且最长20字符 | `无` |
| `User` | `hashed_password` | `str` | 密码哈希值，必填项，用于安全验证 | `PydanticUndefined` |
| `User` | `salt` | `typing.Optional[str]` | 密码盐值，可选项，配合哈希密码增强安全性 | `无` |
| `User` | `role` | `str` | 用户主角色标识，默认值为'user' | `user` |
| `User` | `role_id` | `typing.Optional[int]` | 关联的主角色ID，可选项，外键指向role表 | `无` |
| `User` | `status` | `<enum UserStatus` | 用户状态枚举，默认值为正常(ACTIVE) | `UserStatus.ACTIVE` |
| `User` | `is_active` | `bool` | 是否处于活跃状态，默认值为True | `True` |
| `User` | `failed_login_count` | `int` | 连续登录失败次数，默认值为0 | `0` |
| `User` | `locked_until` | `typing.Optional[datetime.datetime]` | 账户锁定截止时间，可选项 | `无` |
| `User` | `reset_token` | `typing.Optional[str]` | 密码重置令牌，可选项，用于找回密码流程 | `无` |
| `User` | `reset_token_expires_at` | `typing.Optional[datetime.datetime]` | 密码重置令牌过期时间，可选项 | `无` |
| `User` | `extension_json` | `typing.Optional[dict]` | 扩展JSON字段，可选项，用于存储动态扩展属性 | `无` |
| `User` | `ext_1` | `typing.Optional[str]` | 备用扩展字符串1，可选项 | `无` |
| `User` | `ext_2` | `typing.Optional[str]` | 备用扩展字符串2，可选项 | `无` |
| `User` | `ext_3` | `typing.Optional[str]` | 备用扩展字符串3，可选项 | `无` |
| `User` | `int_1` | `typing.Optional[int]` | 备用扩展整数1，可选项 | `无` |
| `User` | `int_2` | `typing.Optional[int]` | 备用扩展整数2，可选项 | `无` |
| `User` | `int_3` | `typing.Optional[int]` | 备用扩展整数3，可选项 | `无` |
| `User` | `created_at` | `datetime.datetime` | 用户记录创建时间，默认自动生成当前UTC时间 | `PydanticUndefined` |
| `User` | `updated_at` | `datetime.datetime` | 用户记录更新时间，默认自动生成当前UTC时间 | `PydanticUndefined` |
| `UserBase` | `username` | `str` | 用户名，必填项 | `PydanticUndefined` |
| `UserBase` | `email` | `typing.Optional[str]` | 电子邮箱，可选项 | `无` |
| `UserBase` | `phone` | `typing.Optional[str]` | 手机号码，可选项 | `无` |
| `UserBase` | `full_name` | `typing.Optional[str]` | 全名，可选项 | `无` |
| `UserCreate` | `username` | `str` | 用户名，必填项 | `PydanticUndefined` |
| `UserCreate` | `email` | `typing.Optional[str]` | 电子邮箱，可选项 | `无` |
| `UserCreate` | `phone` | `typing.Optional[str]` | 手机号码，可选项 | `无` |
| `UserCreate` | `full_name` | `typing.Optional[str]` | 全名，可选项 | `无` |
| `UserCreate` | `password` | `str` | 明文密码，必填项，后端将进行哈希处理 | `PydanticUndefined` |
| `UserCreate` | `role_ids` | `typing.List[int]` | 角色ID列表，可选项，指定用户拥有的角色 | `[]` |
| `UserListResponse` | `items` | `typing.List[app.models.user.UserRead]` | 用户列表数据 | `PydanticUndefined` |
| `UserListResponse` | `total` | `int` | 用户总数 | `PydanticUndefined` |
| `UserRead` | `username` | `str` | 用户名，必填项 | `PydanticUndefined` |
| `UserRead` | `email` | `typing.Optional[str]` | 电子邮箱，可选项 | `无` |
| `UserRead` | `phone` | `typing.Optional[str]` | 手机号码，可选项 | `无` |
| `UserRead` | `full_name` | `typing.Optional[str]` | 全名，可选项 | `无` |
| `UserRead` | `id` | `int` | 用户ID | `PydanticUndefined` |
| `UserRead` | `status` | `<enum UserStatus` | 用户当前状态 | `PydanticUndefined` |
| `UserRead` | `roles` | `typing.List[app.models.user.Role]` | 用户拥有的角色列表 | `[]` |
| `UserRead` | `created_at` | `datetime.datetime` | 用户创建时间 | `PydanticUndefined` |
| `UserRoleLink` | `user_id` | `typing.Optional[int]` | 关联的用户ID，联合主键，外键指向user表 | `无` |
| `UserRoleLink` | `role_id` | `typing.Optional[int]` | 关联的角色ID，联合主键，外键指向role表 | `无` |
| `UserUpdate` | `email` | `typing.Optional[str]` | 新的电子邮箱 | `无` |
| `UserUpdate` | `phone` | `typing.Optional[str]` | 新的手机号码 | `无` |
| `UserUpdate` | `full_name` | `typing.Optional[str]` | 新的全名 | `无` |
| `UserUpdate` | `password` | `typing.Optional[str]` | 新的明文密码 | `无` |
| `UserUpdate` | `status` | `typing.Optional[app.models.user.UserStatus]` | 新的用户状态 | `无` |
| `UserUpdate` | `role_ids` | `typing.Optional[typing.List[int]]` | 新的角色ID列表 | `无` |
| `UserProfile` | `id` | `typing.Optional[int]` | 个人信息配置记录的主键ID | `无` |
| `UserProfile` | `identity` | `str` | Soul Identity / 用户身份设定，用于AI对话等场景的系统提示词设定 | `` |
| `UserProfile` | `rules` | `str` | Personal Rules / 个性化规则，用户设定的个人偏好、回复风格等规则 | `` |
| `UserProfile` | `created_at` | `datetime.datetime` | 配置首次创建时间(UTC) | `PydanticUndefined` |
| `UserProfile` | `updated_at` | `datetime.datetime` | 配置最后更新时间(UTC) | `PydanticUndefined` |
| `UserProfileHistory` | `id` | `typing.Optional[int]` | 历史记录主键ID | `无` |
| `UserProfileHistory` | `user_id` | `typing.Optional[int]` | 归属的用户ID，外键关联user表 | `无` |
| `UserProfileHistory` | `profile_id` | `int` | 关联的UserProfile的主键ID，外键关联userprofile表 | `PydanticUndefined` |
| `UserProfileHistory` | `identity` | `str` | 历史版本中的用户身份设定快照 | `PydanticUndefined` |
| `UserProfileHistory` | `rules` | `str` | 历史版本中的个性化规则快照 | `PydanticUndefined` |
| `UserProfileHistory` | `created_at` | `datetime.datetime` | 该快照版本的生成时间(UTC) | `PydanticUndefined` |
| `UserProfileUpdate` | `identity` | `typing.Optional[str]` | 更新的用户身份设定 | `无` |
| `UserProfileUpdate` | `rules` | `typing.Optional[str]` | 更新的个性化规则 | `无` |

## 统计信息

- 总字段数: 845
- 已注释字段数: 845
- 注释覆盖率: 100.00%
