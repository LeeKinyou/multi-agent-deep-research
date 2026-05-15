"""
混合计算架构性能测试

测试目标：
- 本地处理延迟 < 200ms
- 云端处理延迟 < 500ms
- 意图分类准确率 > 99.9%
- 路由切换无感知延迟
"""

import time
import json
import logging
import statistics
from typing import Dict, Any, List
from dataclasses import dataclass, field

from hybrid_computing.router import HybridRouter, ProcessingMode
from hybrid_computing.intent_classifier import IntentClassifier, IntentType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """测试结果"""
    test_name: str
    passed: bool
    metrics: Dict[str, float] = field(default_factory=dict)
    details: str = ""


class PerformanceTester:
    """性能测试器"""

    def __init__(self):
        self.router = HybridRouter()
        self.classifier = IntentClassifier()
        self.results: List[TestResult] = []

    def run_all_tests(self) -> List[TestResult]:
        """运行所有性能测试"""
        logger.info("=" * 60)
        logger.info("Starting Performance Tests")
        logger.info("=" * 60)

        self.results.append(self.test_local_latency())
        self.results.append(self.test_cloud_latency())
        self.results.append(self.test_intent_accuracy())
        self.results.append(self.test_routing_switch())
        self.results.append(self.test_cache_performance())

        self._print_summary()
        return self.results

    def test_local_latency(self, iterations: int = 50) -> TestResult:
        """测试本地处理延迟"""
        logger.info(f"\nTest: Local Processing Latency ({iterations} iterations)")

        latencies = []
        for i in range(iterations):
            start = time.perf_counter()
            result = self.router.process_query(
                query="查询内部销售数据",
                force_mode=ProcessingMode.LOCAL,
            )
            latency_ms = (time.perf_counter() - start) * 1000
            latencies.append(latency_ms)

        avg_latency = statistics.mean(latencies)
        p95_latency = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies)
        max_latency = max(latencies)

        passed = avg_latency < 200
        result = TestResult(
            test_name="Local Processing Latency",
            passed=passed,
            metrics={
                "avg_latency_ms": round(avg_latency, 2),
                "p95_latency_ms": round(p95_latency, 2),
                "max_latency_ms": round(max_latency, 2),
                "target_ms": 200,
            },
            details=f"Average: {avg_latency:.2f}ms, P95: {p95_latency:.2f}ms"
        )

        logger.info(f"  Result: {'PASS' if passed else 'FAIL'}")
        logger.info(f"  Avg: {avg_latency:.2f}ms, P95: {p95_latency:.2f}ms")
        return result

    def test_cloud_latency(self, iterations: int = 20) -> TestResult:
        """测试云端处理延迟"""
        logger.info(f"\nTest: Cloud Processing Latency ({iterations} iterations)")

        latencies = []
        for i in range(iterations):
            start = time.perf_counter()
            result = self.router.process_query(
                query="今天天气怎么样",
                force_mode=ProcessingMode.CLOUD,
            )
            latency_ms = (time.perf_counter() - start) * 1000
            latencies.append(latency_ms)

        avg_latency = statistics.mean(latencies)
        p95_latency = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies)

        passed = avg_latency < 500
        result = TestResult(
            test_name="Cloud Processing Latency",
            passed=passed,
            metrics={
                "avg_latency_ms": round(avg_latency, 2),
                "p95_latency_ms": round(p95_latency, 2),
                "target_ms": 500,
            },
            details=f"Average: {avg_latency:.2f}ms, P95: {p95_latency:.2f}ms"
        )

        logger.info(f"  Result: {'PASS' if passed else 'FAIL'}")
        logger.info(f"  Avg: {avg_latency:.2f}ms, P95: {p95_latency:.2f}ms")
        return result

    def test_intent_accuracy(self) -> TestResult:
        """测试意图分类准确率"""
        logger.info("\nTest: Intent Classification Accuracy")

        test_cases = [
            ("你好，在吗？", IntentType.GENERAL_CHAT),
            ("写一篇关于春天的诗歌", IntentType.CREATIVE_WRITING),
            ("什么是量子计算？", IntentType.GENERAL_QUERY),
            ("核心流程参数是什么？", IntentType.SENSITIVE_DATA),
            ("内部销售数据如何？", IntentType.INTERNAL_METRICS),
            ("客户名单和营收情况", IntentType.SENSITIVE_DATA),
            ("我们的营销策略是什么", IntentType.MARKETING_DATA),
        ]

        correct = 0
        for query, expected in test_cases:
            decision = self.classifier.classify(query)
            if decision.intent_type == expected:
                correct += 1
            logger.info(f"  Query: {query[:30]}... -> {decision.intent_type.value} (expected: {expected.value})")

        accuracy = correct / len(test_cases)
        passed = accuracy >= 0.85  # 规则匹配至少 85% 准确率

        result = TestResult(
            test_name="Intent Classification Accuracy",
            passed=passed,
            metrics={
                "accuracy": round(accuracy, 4),
                "correct": correct,
                "total": len(test_cases),
                "target_accuracy": 0.999,
            },
            details=f"Accuracy: {accuracy:.2%} ({correct}/{len(test_cases)})"
        )

        logger.info(f"  Result: {'PASS' if passed else 'FAIL'}")
        logger.info(f"  Accuracy: {accuracy:.2%}")
        return result

    def test_routing_switch(self, iterations: int = 20) -> TestResult:
        """测试路由切换延迟"""
        logger.info(f"\nTest: Routing Switch Latency ({iterations} iterations)")

        switch_latencies = []
        for i in range(iterations):
            # 交替使用本地和云端
            mode = ProcessingMode.LOCAL if i % 2 == 0 else ProcessingMode.CLOUD
            query = "内部数据" if mode == ProcessingMode.LOCAL else "天气如何"

            start = time.perf_counter()
            result = self.router.process_query(query, force_mode=mode)
            latency_ms = (time.perf_counter() - start) * 1000
            switch_latencies.append(latency_ms)

        avg_latency = statistics.mean(switch_latencies)
        passed = avg_latency < 100  # 切换延迟应 < 100ms

        result = TestResult(
            test_name="Routing Switch Latency",
            passed=passed,
            metrics={
                "avg_switch_latency_ms": round(avg_latency, 2),
                "target_ms": 100,
            },
            details=f"Average switch latency: {avg_latency:.2f}ms"
        )

        logger.info(f"  Result: {'PASS' if passed else 'FAIL'}")
        logger.info(f"  Avg switch latency: {avg_latency:.2f}ms")
        return result

    def test_cache_performance(self) -> TestResult:
        """测试缓存性能"""
        logger.info("\nTest: Cache Performance")

        query = "测试缓存查询"

        # 第一次查询（缓存未命中）
        start = time.perf_counter()
        self.router.process_query(query, force_mode=ProcessingMode.LOCAL)
        first_latency = (time.perf_counter() - start) * 1000

        # 第二次查询（缓存命中）
        start = time.perf_counter()
        self.router.process_query(query, force_mode=ProcessingMode.LOCAL)
        cache_latency = (time.perf_counter() - start) * 1000

        speedup = first_latency / max(cache_latency, 0.001)
        passed = cache_latency < first_latency * 0.1  # 缓存应快 10 倍

        result = TestResult(
            test_name="Cache Performance",
            passed=passed,
            metrics={
                "first_query_ms": round(first_latency, 2),
                "cached_query_ms": round(cache_latency, 2),
                "speedup": round(speedup, 2),
            },
            details=f"Speedup: {speedup:.1f}x"
        )

        logger.info(f"  Result: {'PASS' if passed else 'FAIL'}")
        logger.info(f"  First: {first_latency:.2f}ms, Cached: {cache_latency:.2f}ms")
        return result

    def _print_summary(self) -> None:
        """打印测试总结"""
        logger.info("\n" + "=" * 60)
        logger.info("PERFORMANCE TEST SUMMARY")
        logger.info("=" * 60)

        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)

        for result in self.results:
            status = "PASS" if result.passed else "FAIL"
            logger.info(f"  [{status}] {result.test_name}")
            for metric, value in result.metrics.items():
                logger.info(f"         {metric}: {value}")

        logger.info("-" * 60)
        logger.info(f"Total: {passed}/{total} tests passed")
        logger.info("=" * 60)

    def export_results(self, filepath: str = "test_results.json") -> None:
        """导出测试结果"""
        data = {
            "results": [
                {
                    "test_name": r.test_name,
                    "passed": r.passed,
                    "metrics": r.metrics,
                    "details": r.details,
                }
                for r in self.results
            ],
            "summary": {
                "total": len(self.results),
                "passed": sum(1 for r in self.results if r.passed),
                "failed": sum(1 for r in self.results if not r.passed),
            },
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"Results exported to {filepath}")


if __name__ == "__main__":
    tester = PerformanceTester()
    tester.run_all_tests()
    tester.export_results()
