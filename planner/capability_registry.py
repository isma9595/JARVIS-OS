"""Explicit planner capability registry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from planner.contracts import PlanCapability, PlanCapabilityDescriptor


class PlannerCapabilityRegistryError(ValueError):
    pass


@dataclass(frozen=True)
class PlannerCapabilityRegistry:
    _capabilities: Mapping[str, PlanCapability]

    @classmethod
    def empty(cls) -> "PlannerCapabilityRegistry":
        return cls({})

    def register(self, capability: PlanCapability) -> "PlannerCapabilityRegistry":
        capability_id = capability.descriptor.capability_id
        if not capability_id:
            raise PlannerCapabilityRegistryError("capability_id must be non-empty")
        if capability_id in self._capabilities:
            raise PlannerCapabilityRegistryError(f"duplicate planner capability: {capability_id}")
        updated = dict(self._capabilities)
        updated[capability_id] = capability
        return PlannerCapabilityRegistry(updated)

    def get(self, capability_id: str) -> PlanCapability:
        try:
            return self._capabilities[str(capability_id or "")]
        except KeyError as exc:
            raise PlannerCapabilityRegistryError(f"unregistered planner capability: {capability_id}") from exc

    def descriptor(self, capability_id: str) -> PlanCapabilityDescriptor:
        return self.get(capability_id).descriptor

    def descriptors(self) -> tuple[PlanCapabilityDescriptor, ...]:
        return tuple(capability.descriptor for capability in self._capabilities.values())

    def capability_ids(self) -> tuple[str, ...]:
        return tuple(self._capabilities.keys())

    def __contains__(self, capability_id: str) -> bool:
        return str(capability_id or "") in self._capabilities
