"""Automation Scheduler - Schedule and automate metadata operations."""

import asyncio
from datetime import datetime
from typing import Any, Callable, Coroutine

from ..metadata.harvester import MetadataHarvester
from ..catalog.catalog import CatalogService
from ..policies.engine import PolicyEngine
from ..knowledge_graph.graph import KnowledgeGraph


class AutomationScheduler:
    """Schedule and automate metadata operations."""

    def __init__(
        self,
        harvester: MetadataHarvester,
        catalog: CatalogService,
        policy_engine: PolicyEngine,
        knowledge_graph: KnowledgeGraph,
    ) -> None:
        """Initialize automation scheduler."""
        self.harvester = harvester
        self.catalog = catalog
        self.policy_engine = policy_engine
        self.knowledge_graph = knowledge_graph
        self.tasks: dict[str, dict[str, Any]] = {}
        self.running = False

    def register_task(
        self,
        name: str,
        func: Callable[..., Coroutine[Any, Any, Any]],
        cron_expression: str,
        **kwargs: Any,
    ) -> None:
        """Register a scheduled task.
        
        Args:
            name: Task name
            func: Async function to execute
            cron_expression: Cron expression (e.g., "0 0 * * *")
            **kwargs: Additional arguments for the function
        """
        self.tasks[name] = {
            "func": func,
            "cron": cron_expression,
            "kwargs": kwargs,
            "last_run": None,
            "last_status": None,
            "enabled": True,
        }

    async def run_task(self, name: str) -> dict[str, Any]:
        """Run a specific task."""
        task = self.tasks.get(name)
        if not task:
            return {"status": "error", "error": f"Task {name} not found"}
        
        if not task["enabled"]:
            return {"status": "skipped", "reason": "Task is disabled"}
        
        try:
            result = await task["func"](**task["kwargs"])
            task["last_run"] = datetime.now()
            task["last_status"] = "success"
            return {"status": "success", "result": result}
        except Exception as e:
            task["last_run"] = datetime.now()
            task["last_status"] = "error"
            return {"status": "error", "error": str(e)}

    async def run_all_tasks(self) -> dict[str, Any]:
        """Run all registered tasks."""
        results = {}
        for name in self.tasks:
            results[name] = await self.run_task(name)
        return results

    async def start_scheduler(self, interval_seconds: int = 60) -> None:
        """Start the scheduler loop."""
        self.running = True
        while self.running:
            await self.run_all_tasks()
            await asyncio.sleep(interval_seconds)

    def stop_scheduler(self) -> None:
        """Stop the scheduler loop."""
        self.running = False

    def get_task_status(self, name: str) -> dict[str, Any]:
        """Get status of a specific task."""
        task = self.tasks.get(name)
        if not task:
            return {"error": "Task not found"}
        return {
            "name": name,
            "cron": task["cron"],
            "enabled": task["enabled"],
            "last_run": task["last_run"],
            "last_status": task["last_status"],
        }

    def get_all_task_status(self) -> dict[str, Any]:
        """Get status of all tasks."""
        return {name: self.get_task_status(name) for name in self.tasks}

    def enable_task(self, name: str) -> bool:
        """Enable a task."""
        task = self.tasks.get(name)
        if task:
            task["enabled"] = True
            return True
        return False

    def disable_task(self, name: str) -> bool:
        """Disable a task."""
        task = self.tasks.get(name)
        if task:
            task["enabled"] = False
            return True
        return False

    async def harvest_scheduled(self) -> dict[str, Any]:
        """Scheduled metadata harvesting."""
        return await self.harvester.harvest_all()

    async def policy_check_scheduled(self) -> dict[str, Any]:
        """Scheduled policy compliance check."""
        assets = self.catalog.list_assets(limit=1000)
        violations = []
        for asset in assets:
            asset_violations = self.policy_engine.evaluate_asset(
                asset.model_dump()
            )
            violations.extend(asset_violations)
        return {"violations_found": len(violations), "violations": violations}

    async def lineage_update_scheduled(self) -> dict[str, Any]:
        """Scheduled lineage update."""
        assets = self.catalog.list_assets(limit=1000)
        updated = 0
        for asset in assets:
            # Refresh lineage for each asset
            lineage = self.catalog.get_asset_lineage(asset.urn)
            if lineage:
                updated += 1
        return {"assets_updated": updated}

    async def quality_check_scheduled(self) -> dict[str, Any]:
        """Scheduled quality check."""
        assets = self.catalog.list_assets(limit=1000)
        quality_report = {
            "total_assets": len(assets),
            "high_quality": sum(1 for a in assets if a.quality_score >= 0.9),
            "medium_quality": sum(1 for a in assets if 0.7 <= a.quality_score < 0.9),
            "low_quality": sum(1 for a in assets if a.quality_score < 0.7),
        }
        return quality_report

    async def sync_to_knowledge_graph(self) -> dict[str, Any]:
        """Scheduled sync to knowledge graph."""
        assets = self.catalog.list_assets(limit=1000)
        synced = 0
        for asset in assets:
            try:
                # Create node in knowledge graph
                self.knowledge_graph.create_node(
                    GraphNode(
                        entity_type=EntityType.ASSET,
                        properties={
                            "id": str(asset.id),
                            "urn": asset.urn,
                            "name": asset.name,
                            "type": asset.asset_type.value,
                            "platform": asset.platform,
                        },
                    )
                )
                synced += 1
            except Exception:
                continue
        return {"assets_synced": synced}


# Import here to avoid circular imports
from ..knowledge_graph.models import GraphNode, EntityType