from typing import Dict, Type
from src.dq_framework.quality_rule import QualityRule

class RuleRegistry:
    """
    A registry to dynamically map rule type names to their implementation classes.
    Supports easy extensibility for custom validation rules.
    """
    _registry: Dict[str, Type[QualityRule]] = {}

    @classmethod
    def register(cls, name: str):
        """
        Decorator to register a custom QualityRule implementation.
        
        Args:
            name (str): The unique string key for the rule (e.g. 'completeness').
        """
        def decorator(subclass: Type[QualityRule]):
            cls._registry[name] = subclass
            return subclass
        return decorator

    @classmethod
    def get_rule_class(cls, name: str) -> Type[QualityRule]:
        """
        Retrieves the rule class registered under the given name.
        
        Args:
            name (str): The registered name.
            
        Returns:
            Type[QualityRule]: The class of the rule.
        """
        if name not in cls._registry:
            raise KeyError(
                f"Rule type '{name}' not found in registry. "
                f"Registered rules: {list(cls._registry.keys())}"
            )
        return cls._registry[name]
