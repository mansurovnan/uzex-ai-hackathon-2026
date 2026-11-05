"""
Section F: Cold-Start & Healthcheck Test Suite.
Verifies /api/health and /api/version endpoints, startup response times,
and cold-start handling logic.
"""

import pytest
import asyncio
import time
from app.main import health_check, version_info, chat_endpoint, ChatRequest

def test_api_health_endpoint():
    """Verifies that /api/health returns ready: True with schema counts."""
    async def _test():
        start_time = time.time()
        res = await health_check()
        latency = time.time() - start_time

        assert res["status"] == "healthy"
        assert res["ready"] is True
        assert res["total_deals"] == 500000
        assert res["total_contracts"] == 6616
        assert res["total_participants"] == 14392
        assert res["total_brokers"] == 120
        assert "version" in res
        assert "commit_sha" in res
        assert latency < 2.0, f"Healthcheck too slow: {latency:.2f}s"
    asyncio.run(_test())

def test_api_version_endpoint():
    """Verifies that /api/version returns correct release info."""
    async def _test():
        data = await version_info()
        assert "version" in data
        assert "commit_sha" in data
        assert data["dataset"]["total_deals"] == 500000
        assert data["dataset"]["date_range"] == "2022-01-03 to 2026-10-30"
    asyncio.run(_test())

def test_chat_endpoint_structure():
    """Verifies that chat_endpoint returns full evidence object and transparency metadata."""
    async def _test():
        req = ChatRequest(
            message="2024 yilda «Пшеница продовольственная» bo'yicha qancha bitim tuzilgan?",
            session_id="test_health_chat"
        )
        res = await chat_endpoint(req)
        assert res.answer is not None
        assert res.sql is not None
        assert res.evidence is not None
        assert res.evidence["row_count"] > 0
        assert res.evidence["verification_passed"] is True
    asyncio.run(_test())
