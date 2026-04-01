from typing import Dict, Type, List, Optional
from core.skill import Skill
import logging

logger = logging.getLogger(__name__)

class SkillRegistry:
    """
    Registry for managing available skills.
    """
    _instance = None
    _skills: Dict[str, Type[Skill]] = {}
    _loaded_skills: Dict[str, Skill] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SkillRegistry, cls).__new__(cls)
        return cls._instance

    @classmethod
    def register(cls, skill_class: Type[Skill]):
        """Register a skill class."""
        skill_name = skill_class.__name__
        if skill_name in cls._skills:
            logger.warning(f"Skill {skill_name} is already registered. Overwriting.")
        cls._skills[skill_name] = skill_class
        logger.info(f"Registered skill: {skill_name}")

    @classmethod
    def get_skill_class(cls, name: str) -> Optional[Type[Skill]]:
        """Get a skill class by name."""
        return cls._skills.get(name)

    @classmethod
    def get_skill_instance(cls, name: str) -> Optional[Skill]:
        """Get an instance of a skill, creating it if necessary."""
        if name in cls._loaded_skills:
            return cls._loaded_skills[name]
        
        skill_cls = cls.get_skill_class(name)
        if skill_cls:
            # Note: This assumes default init without args or specific logic needed
            # For complex skills, we might need a factory or config injection
            try:
                instance = skill_cls() 
                cls._loaded_skills[name] = instance
                return instance
            except Exception as e:
                logger.error(f"Failed to instantiate skill {name}: {e}")
                return None
        return None

    @classmethod
    def list_skills(cls) -> List[str]:
        """List all registered skill names."""
        return list(cls._skills.keys())

    @classmethod
    def load_skills_from_directory(cls, directory: str):
        """Dynamically load skill modules from a directory."""
        # This is a simplified implementation. Real-world would use importlib more robustly.
        pass

    @classmethod
    def match_skills(cls, task_description: str) -> List[str]:
        """
        Match skills based on task description.
        (Placeholder for simple keyword matching or semantic search)
        """
        matches = []
        task_desc_lower = task_description.lower()
        for name, skill_cls in cls._skills.items():
            # Create a temporary instance to check description or store metadata on class level
            # Here we assume we can inspect the class or need an instance.
            # For simplicity, let's just match the name for now.
            if name.lower() in task_desc_lower:
                matches.append(name)
        return matches
