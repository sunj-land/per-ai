import os
import sys
import importlib
import inspect
from pydantic.fields import FieldInfo
from sqlmodel import SQLModel

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import models

model_modules = [
    'agent_store', 'attachment', 'card', 'channel', 'chat', 'content',
    'note', 'plan', 'progress', 'reminder', 'rss', 'schedule', 'task',
    'user', 'user_profile'
]

missing = []

for mod_name in model_modules:
    mod = importlib.import_module(f'app.models.{mod_name}')
    for name, obj in inspect.getmembers(mod, inspect.isclass):
        if issubclass(obj, SQLModel) and obj.__module__ == mod.__name__:
            fields = getattr(obj, 'model_fields', getattr(obj, '__fields__', {}))
            for field_name, model_field in fields.items():
                if hasattr(model_field, 'description'):
                    description = model_field.description
                elif hasattr(model_field, 'field_info'):
                    description = getattr(model_field.field_info, 'description', None)
                else:
                    description = None
                    
                if not description:
                    missing.append(f"{mod_name}.py: {name}.{field_name}")

if missing:
    print("Missing descriptions:")
    for m in missing:
        print(m)
else:
    print("All fields annotated!")
