"""Environment-specific configuration loader."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional

from app.services.logging_utils import get_logger

logger = get_logger("env_config")


class EnvironmentConfig:
    """Load environment-specific configuration."""

    def __init__(self, env: Optional[str] = None) -> None:
        """
        Initialize environment configuration.

        Args:
            env: Environment name (development, staging, production)
                 If None, reads from FOKS_ENV env var
        """
        self.env = env or os.getenv("FOKS_ENV", "development")
        self.config_dir = Path(__file__).parent.parent.parent / "config" / "environments"
        self._config: Dict[str, any] = {}

    def load(self) -> Dict[str, any]:
        """
        Load environment-specific configuration.

        Returns:
            dict: Configuration values for the environment
        """
        # Load base config
        base_config = self._load_file("base.env")

        # Load environment-specific config
        env_config = self._load_file(f"{self.env}.env")

        # Merge: env-specific overrides base
        config = {**base_config, **env_config}

        # Override with actual environment variables (highest priority)
        for key, value in config.items():
            env_value = os.getenv(key)
            if env_value is not None:
                config[key] = self._parse_value(env_value)

        self._config = config
        logger.info("Loaded configuration for environment: %s", self.env)
        return config

    def _load_file(self, filename: str) -> Dict[str, any]:
        """Load configuration from file."""
        file_path = self.config_dir / filename

        if not file_path.exists():
            logger.debug("Config file not found: %s", file_path)
            return {}

        config = {}
        with open(file_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    config[key] = self._parse_value(value)

        return config

    def _parse_value(self, value: str) -> any:
        """Parse configuration value."""
        # Boolean
        if value.lower() in ("true", "1", "yes"):
            return True
        if value.lower() in ("false", "0", "no"):
            return False

        # Integer
        try:
            return int(value)
        except ValueError:
            pass

        # Float
        try:
            return float(value)
        except ValueError:
            pass

        # String
        return value

    def get(self, key: str, default: any = None) -> any:
        """Get configuration value."""
        return self._config.get(key, default)


# Global environment config loader
env_config_loader = EnvironmentConfig()

