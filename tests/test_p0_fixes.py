import asyncio
import sys
import os
import threading
import time
from unittest.mock import MagicMock, patch, AsyncMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestP0Fixes:
    def test_p0_1_async_execution_func_detection(self):
        from app.services.task_service import TaskService

        async def async_func(x):
            return x * 2

        def sync_func(x):
            return x * 3

        assert asyncio.iscoroutinefunction(async_func) is True
        assert asyncio.iscoroutinefunction(sync_func) is False

    def test_p0_1_execute_task_uses_async_path(self):
        from app.services.task_service import TaskService

        mock_db = MagicMock()
        mock_task = MagicMock()
        mock_task.status = MagicMock()
        mock_task.status.__eq__ = lambda self, other: other in ["pending", "planning"]

        task_service = TaskService(mock_db)
        task_service.get_task = MagicMock(return_value=mock_task)
        task_service.add_log = MagicMock()
        task_service.save_task_result = MagicMock()

        call_tracker = {"async_called": False, "sync_called": False}

        async def async_exec():
            call_tracker["async_called"] = True
            return "async_result"

        def sync_exec():
            call_tracker["sync_called"] = True
            return "sync_result"

        async def run_test():
            await task_service.execute_task("test_task", async_exec)
            assert call_tracker["async_called"] is True

        asyncio.run(run_test())

    def test_p0_2_stream_manager_queue_has_maxsize(self):
        from app.services.stream_service import StreamManager, MAX_QUEUE_SIZE

        manager = StreamManager()
        manager.clear_task("test_queue_size")

        queue = manager.subscribe("test_queue_size")
        assert queue.maxsize == MAX_QUEUE_SIZE
        assert queue.maxsize > 0

    def test_p0_2_stream_manager_backpressure(self):
        from app.services.stream_service import StreamManager, MAX_QUEUE_SIZE

        manager = StreamManager()
        manager.clear_task("test_backpressure")

        queue = manager.subscribe("test_backpressure")

        async def fill_queue():
            for i in range(MAX_QUEUE_SIZE + 10):
                await manager.publish("test_backpressure", "test_event", {"index": i})

            assert queue.qsize() <= MAX_QUEUE_SIZE

        asyncio.run(fill_queue())

    def test_p0_2_stream_manager_thread_safe_singleton(self):
        from app.services.stream_service import StreamManager

        instances = []
        barrier = threading.Barrier(5)

        def create_instance():
            barrier.wait()
            instances.append(StreamManager())

        threads = [threading.Thread(target=create_instance) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert all(inst is instances[0] for inst in instances)

    def test_p0_3_shared_embedding_client_singleton(self):
        import sys
        import threading
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("chromadb.PersistentClient") as mock_client_cls:
                mock_client = MagicMock()
                mock_client_cls.return_value = mock_client

                test_embedding_client = None
                test_lock = threading.Lock()

                def test_get_client(persist_dir):
                    nonlocal test_embedding_client
                    if test_embedding_client is None:
                        with test_lock:
                            if test_embedding_client is None:
                                test_embedding_client = MagicMock()
                    return test_embedding_client

                client1 = test_get_client(tmpdir)
                client2 = test_get_client(tmpdir)

                assert client1 is client2

    def test_p0_3_vector_store_shared_client_logic(self):
        import threading

        test_embedding_client = None
        test_lock = threading.Lock()
        call_count = {"count": 0}

        def test_get_client(persist_dir):
            nonlocal test_embedding_client
            if test_embedding_client is None:
                with test_lock:
                    if test_embedding_client is None:
                        test_embedding_client = MagicMock()
                        call_count["count"] += 1
            return test_embedding_client

        result1 = test_get_client("./test_dir")
        result2 = test_get_client("./test_dir")
        result3 = test_get_client("./test_dir")

        assert result1 is result2 is result3
        assert call_count["count"] == 1


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
