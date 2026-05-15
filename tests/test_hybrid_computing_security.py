"""
混合计算架构安全验证

验证目标：
- 敏感数据不离开本地环境
- 数据脱敏有效性
- 路由决策安全性
- 安全审计完整性
"""

import logging
from typing import List, Dict, Any
from dataclasses import dataclass

from hybrid_computing.security_filter import SecurityFilter, DataClassifier, DataType
from hybrid_computing.router import HybridRouter, ProcessingMode
from hybrid_computing.intent_classifier import IntentClassifier, SensitivityLevel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SecurityTestResult:
    """安全测试结果"""
    test_name: str
    passed: bool
    risk_found: bool
    details: str


class SecurityValidator:
    """安全验证器"""

    def __init__(self):
        self.security_filter = SecurityFilter(strict_mode=True)
        self.router = HybridRouter()
        self.classifier = IntentClassifier()
        self.results: List[SecurityTestResult] = []

    def run_all_tests(self) -> List[SecurityTestResult]:
        """运行所有安全测试"""
        logger.info("=" * 60)
        logger.info("Starting Security Validation")
        logger.info("=" * 60)

        self.results.append(self.test_sensitive_data_detection())
        self.results.append(self.test_data_sanitization())
        self.results.append(self.test_cloud_routing_block())
        self.results.append(self.test_audit_log_integrity())
        self.results.append(self.test_intent_classification_security())

        self._print_summary()
        return self.results

    def test_sensitive_data_detection(self) -> SecurityTestResult:
        """测试敏感数据检测"""
        logger.info("\nTest: Sensitive Data Detection")

        test_cases = [
            ("我的银行卡号是 6222021234567890", DataType.CONFIDENTIAL, True),
            ("身份证号：110101199001011234", DataType.CONFIDENTIAL, True),
            ("API密钥：sk-abc123def456ghi789", DataType.CONFIDENTIAL, True),
            ("密码：mysecretpassword123", DataType.CONFIDENTIAL, True),
            ("本月营收 500 万元", DataType.INTERNAL, True),
            ("客户数量 10000 人", DataType.INTERNAL, True),
            ("销售转化率 15.5%", DataType.INTERNAL, True),
            ("今天天气很好", DataType.PUBLIC, False),
            ("请帮我写一首诗", DataType.PUBLIC, False),
        ]

        all_passed = True
        for text, expected_type, should_detect in test_cases:
            result = self.security_filter.classify_data(text)
            detected = result.data_type != DataType.PUBLIC

            if detected != should_detect:
                all_passed = False
                logger.info(f"  FAIL: '{text[:30]}...' -> {result.data_type.value} (expected: {'detected' if should_detect else 'not detected'})")
            else:
                logger.info(f"  PASS: '{text[:30]}...' -> {result.data_type.value}")

        return SecurityTestResult(
            test_name="Sensitive Data Detection",
            passed=all_passed,
            risk_found=not all_passed,
            details=f"Tested {len(test_cases)} cases"
        )

    def test_data_sanitization(self) -> SecurityTestResult:
        """测试数据脱敏"""
        logger.info("\nTest: Data Sanitization")

        test_cases = [
            "我的银行卡号是 6222021234567890，请帮我查询余额",
            "API密钥：sk-abc123def456ghi789，请用这个调用服务",
            "密码：mysecretpassword123，请帮我重置",
            "客户张三的邮箱是 zhangsan@example.com",
        ]

        all_passed = True
        for text in test_cases:
            result = self.security_filter.sanitize_data(text)

            if "[REDACTED]" not in result.sanitized_text:
                all_passed = False
                logger.info(f"  FAIL: No redaction in: '{text[:40]}...'")
            else:
                logger.info(f"  PASS: Sanitized: '{result.sanitized_text[:60]}...'")

        return SecurityTestResult(
            test_name="Data Sanitization",
            passed=all_passed,
            risk_found=not all_passed,
            details=f"Tested {len(test_cases)} cases"
        )

    def test_cloud_routing_block(self) -> SecurityTestResult:
        """测试云端路由拦截"""
        logger.info("\nTest: Cloud Routing Block")

        test_cases = [
            ("我的银行卡号是 6222021234567890", False),
            ("本月营收 500 万元", False),
            ("客户名单有 100 个企业", False),
            ("今天天气怎么样", True),
            ("请帮我写一首关于春天的诗", True),
        ]

        all_passed = True
        for text, should_allow in test_cases:
            can_send, reason = self.security_filter.can_send_to_cloud(text)

            if can_send != should_allow:
                all_passed = False
                logger.info(f"  FAIL: '{text[:30]}...' -> can_send={can_send} (expected: {should_allow})")
                logger.info(f"        Reason: {reason}")
            else:
                logger.info(f"  PASS: '{text[:30]}...' -> can_send={can_send}")

        return SecurityTestResult(
            test_name="Cloud Routing Block",
            passed=all_passed,
            risk_found=not all_passed,
            details=f"Tested {len(test_cases)} cases"
        )

    def test_audit_log_integrity(self) -> SecurityTestResult:
        """测试审计日志完整性"""
        logger.info("\nTest: Audit Log Integrity")

        # 执行一些操作
        self.security_filter.classify_data("测试数据 123")
        self.security_filter.sanitize_data("密码：test123")
        self.security_filter.can_send_to_cloud("内部数据")

        audit_log = self.security_filter.get_audit_log()

        passed = len(audit_log) >= 3
        logger.info(f"  Audit log entries: {len(audit_log)}")

        for entry in audit_log:
            logger.info(f"    - {entry['action']}: {entry['text_preview'][:30]}...")

        return SecurityTestResult(
            test_name="Audit Log Integrity",
            passed=passed,
            risk_found=not passed,
            details=f"Log entries: {len(audit_log)}"
        )

    def test_intent_classification_security(self) -> SecurityTestResult:
        """测试意图分类的安全性"""
        logger.info("\nTest: Intent Classification Security")

        test_cases = [
            ("核心流程参数", True),  # 应该路由到本地
            ("内部销售数据", True),
            ("客户名单和合同金额", True),
            ("你好", False),  # 可以路由到云端
            ("写一首诗", False),
        ]

        all_passed = True
        for query, should_route_local in test_cases:
            decision = self.classifier.classify(query)

            if decision.route_to_local != should_route_local:
                all_passed = False
                logger.info(f"  FAIL: '{query}' -> route_to_local={decision.route_to_local} (expected: {should_route_local})")
            else:
                logger.info(f"  PASS: '{query}' -> route_to_local={decision.route_to_local}")

        return SecurityTestResult(
            test_name="Intent Classification Security",
            passed=all_passed,
            risk_found=not all_passed,
            details=f"Tested {len(test_cases)} cases"
        )

    def _print_summary(self) -> None:
        """打印测试总结"""
        logger.info("\n" + "=" * 60)
        logger.info("SECURITY VALIDATION SUMMARY")
        logger.info("=" * 60)

        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)

        for result in self.results:
            status = "PASS" if result.passed else "FAIL"
            logger.info(f"  [{status}] {result.test_name}")
            logger.info(f"         Risk found: {'Yes' if result.risk_found else 'No'}")

        logger.info("-" * 60)
        logger.info(f"Total: {passed}/{total} tests passed")

        if passed == total:
            logger.info("SECURITY VALIDATION: ALL TESTS PASSED")
        else:
            logger.warning("SECURITY VALIDATION: SOME TESTS FAILED")

        logger.info("=" * 60)


if __name__ == "__main__":
    validator = SecurityValidator()
    validator.run_all_tests()
