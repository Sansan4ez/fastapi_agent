"""
ACP Agent Discovery

Provides agent discovery functionality for the ACP client.
"""

from typing import Any
from datetime import datetime, timedelta

from loguru import logger

from app.acp.core.models import AgentManifest
from app.acp.core.types import AgentStatus


class AgentDiscovery:
    """
    Agent discovery service for finding and caching agent information.

    Provides:
    - Agent manifest caching
    - Agent filtering by capabilities
    - Health status tracking
    """

    def __init__(self, cache_ttl_seconds: int = 300):
        """
        Initialize the discovery service.

        Args:
            cache_ttl_seconds: Cache TTL in seconds (default 5 minutes)
        """
        self._cache: dict[str, CachedAgent] = {}
        self._cache_ttl = timedelta(seconds=cache_ttl_seconds)

    def cache_agent(self, manifest: AgentManifest) -> None:
        """
        Add or update an agent in the cache.

        Args:
            manifest: Agent manifest to cache
        """
        self._cache[manifest.name] = CachedAgent(
            manifest=manifest,
            cached_at=datetime.utcnow(),
        )

    def cache_agents(self, manifests: list[AgentManifest]) -> None:
        """
        Cache multiple agents.

        Args:
            manifests: List of agent manifests
        """
        for manifest in manifests:
            self.cache_agent(manifest)

    def get_cached_agent(self, name: str) -> AgentManifest | None:
        """
        Get an agent from cache if not expired.

        Args:
            name: Agent name

        Returns:
            AgentManifest or None if not cached or expired
        """
        cached = self._cache.get(name)
        if cached and not cached.is_expired(self._cache_ttl):
            return cached.manifest
        return None

    def invalidate_cache(self, name: str | None = None) -> None:
        """
        Invalidate cache for one or all agents.

        Args:
            name: Agent name (None to clear all)
        """
        if name:
            self._cache.pop(name, None)
        else:
            self._cache.clear()

    def find_by_capability(
        self,
        capability: str,
        status: AgentStatus | None = None,
    ) -> list[AgentManifest]:
        """
        Find agents with a specific capability.

        Args:
            capability: Capability to search for
            status: Filter by status

        Returns:
            List of matching agent manifests
        """
        results = []
        for cached in self._cache.values():
            if cached.is_expired(self._cache_ttl):
                continue

            manifest = cached.manifest
            if status and manifest.status != status:
                continue

            if capability in manifest.metadata.capabilities:
                results.append(manifest)

        return results

    def find_by_domain(
        self,
        domain: str,
        status: AgentStatus | None = None,
    ) -> list[AgentManifest]:
        """
        Find agents in a specific domain.

        Args:
            domain: Domain to search for
            status: Filter by status

        Returns:
            List of matching agent manifests
        """
        results = []
        for cached in self._cache.values():
            if cached.is_expired(self._cache_ttl):
                continue

            manifest = cached.manifest
            if status and manifest.status != status:
                continue

            if domain in manifest.metadata.domains:
                results.append(manifest)

        return results

    def find_by_tag(
        self,
        tag: str,
        status: AgentStatus | None = None,
    ) -> list[AgentManifest]:
        """
        Find agents with a specific tag.

        Args:
            tag: Tag to search for
            status: Filter by status

        Returns:
            List of matching agent manifests
        """
        results = []
        for cached in self._cache.values():
            if cached.is_expired(self._cache_ttl):
                continue

            manifest = cached.manifest
            if status and manifest.status != status:
                continue

            if tag in manifest.metadata.tags:
                results.append(manifest)

        return results

    def find_by_content_type(
        self,
        input_type: str | None = None,
        output_type: str | None = None,
    ) -> list[AgentManifest]:
        """
        Find agents by supported content types.

        Args:
            input_type: Required input content type
            output_type: Required output content type

        Returns:
            List of matching agent manifests
        """
        results = []
        for cached in self._cache.values():
            if cached.is_expired(self._cache_ttl):
                continue

            manifest = cached.manifest

            if input_type and input_type not in manifest.input_content_types:
                continue

            if output_type and output_type not in manifest.output_content_types:
                continue

            results.append(manifest)

        return results

    def get_active_agents(self) -> list[AgentManifest]:
        """Get all active (non-expired, ACTIVE status) agents."""
        return [
            cached.manifest
            for cached in self._cache.values()
            if not cached.is_expired(self._cache_ttl)
            and cached.manifest.status == AgentStatus.ACTIVE
        ]

    def get_all_cached(self) -> list[AgentManifest]:
        """Get all cached (non-expired) agents."""
        return [
            cached.manifest
            for cached in self._cache.values()
            if not cached.is_expired(self._cache_ttl)
        ]


class CachedAgent:
    """Wrapper for cached agent data."""

    def __init__(self, manifest: AgentManifest, cached_at: datetime):
        self.manifest = manifest
        self.cached_at = cached_at

    def is_expired(self, ttl: timedelta) -> bool:
        """Check if the cache entry is expired."""
        return datetime.utcnow() - self.cached_at > ttl
