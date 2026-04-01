import os
import sys
import importlib
import inspect
from pydantic.fields import FieldInfo
from sqlmodel import SQLModel

# Add backend dir to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import models

def generate_docs():
    model_modules = [
        'agent_store', 'attachment', 'card', 'channel', 'chat', 'content',
        'note', 'plan', 'progress', 'reminder', 'rss', 'schedule', 'task',
        'user', 'user_profile'
    ]
    
    output_lines = [
        "# 数据模型字段说明汇总表",
        "",
        "| 模型类名 | 字段名 | 类型 | 中文说明 | 示例值/默认值 |",
        "| --- | --- | --- | --- | --- |"
    ]
    
    total_fields = 0
    annotated_fields = 0
    
    for mod_name in model_modules:
        mod = importlib.import_module(f'app.models.{mod_name}')
        for name, obj in inspect.getmembers(mod, inspect.isclass):
            if issubclass(obj, SQLModel) and obj.__module__ == mod.__name__:
                fields = getattr(obj, '__fields__', {})
                for field_name, model_field in fields.items():
                    total_fields += 1
                    
                    # Different pydantic versions handle fields differently
                    if hasattr(model_field, 'field_info'):
                        field_info = model_field.field_info
                    else:
                        field_info = model_field
                        
                    description = getattr(field_info, 'description', '') or ''
                    if description:
                        annotated_fields += 1
                        
                    field_type = str(model_field.annotation) if hasattr(model_field, 'annotation') else str(model_field.type_)
                    field_type = field_type.replace('<class ', '').replace('>', '').replace("'", "")
                    
                    default_val = getattr(field_info, 'default', '')
                    if default_val == ... or default_val is None:
                        default_val = '无'
                    elif callable(default_val):
                        default_val = '动态生成'
                    
                    # Cleanup strings for markdown table
                    description = description.replace('\n', ' ')
                    
                    output_lines.append(f"| `{name}` | `{field_name}` | `{field_type}` | {description} | `{default_val}` |")

    coverage = (annotated_fields / total_fields * 100) if total_fields > 0 else 0
    
    summary = f"\n## 统计信息\n\n- 总字段数: {total_fields}\n- 已注释字段数: {annotated_fields}\n- 注释覆盖率: {coverage:.2f}%\n"
    
    output_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'docs', 'models_dictionary.md'))
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines) + '\n' + summary)
        
    print(f"Coverage: {coverage:.2f}%")
    print(f"Documentation generated at {output_path}")

if __name__ == "__main__":
    generate_docs()
