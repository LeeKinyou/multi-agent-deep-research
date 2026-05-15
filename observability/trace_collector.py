"""
Trace 数据采集器

负责采集 Agent 执行全流程的可观测性数据：
- Tool Call 耗时（毫秒级）
- Token 消耗统计
- Prompt 演变记录
- 工具调用参数与返回结果
- 决策节点与分支选择

支持异步采集、批量上报和本地缓存兜底。
"""

import os
import time
import json
import logging
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Callable
from functools import wraps

from observability.langfuse_client import get_langfuse_client, LangfuseClient

logger = logging.getLogger(__name__)

# 当前 Trace 上下文
_current_trace_id: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)
_current_span_stack: ContextVar[List[str]] = ContextVar("span_stack", default=[])


@dataclass
class ToolCallRecord:
    """Tool Call 调用记录"""
    tool_name: str
    start_time: float
    end_time: float = 0.0
    duration_ms: float = 0.0
    input_params: Dict[str, Any] = field(default_factory=dict)
    output_result: Any = None
    success: bool = True
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def finalize(self, output: Any = None, error: Optional[str] = None):
        self.end_time = time.perf_counter()
        self.duration_ms = round((self.end_time - self.start_time) * 1000, 3)
        self.output_result = output
        if error:
            self.success = False
            self.error_message = error


@dataclass
class TokenUsageRecord:
    """Token 消耗记录"""
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class PromptRecord:
    """Prompt 演变记录"""
    version: int
    prompt_text: str
    role: str = "system"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DecisionRecord:
    """决策节点记录"""
    decision_id: str
    decision_type: str
    context: Dict[str, Any] = field(default_factory=dict)
    options: List[str] = field(default_factory=list)
    selected_option: str = ""
    reasoning: str = ""
    confidence: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class TraceData:
    """完整 Trace 数据结构"""
    trace_id: str
    task_id: Optional[str]
    name: str
    start_time: str
    end_time: Optional[str] = None
    status: str = "running"
    agent_type: str = ""
    tool_calls: List[ToolCallRecord] = field(default_factory=list)
    token_usage: List[TokenUsageRecord] = field(default_factory=list)
    prompts: List[PromptRecord] = field(default_factory=list)
    decisions: List[DecisionRecord] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    total_duration_ms: float = 0.0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "task_id": self.task_id,
            "name": self.name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "status": self.status,
            "agent_type": self.agent_type,
            "tool_calls": [
                {
                    "tool_name": tc.tool_name,
                    "duration_ms": tc.duration_ms,
                    "input_params": tc.input_params,
                    "output_result": str(tc.output_result)[:500] if tc.output_result else None,
                    "success": tc.success,
                    "error_message": tc.error_message,
                }
                for tc in self.tool_calls
            ],
            "token_usage": [asdict(tu) for tu in self.token_usage],
            "prompts": [asdict(p) for p in self.prompts],
            "decisions": [asdict(d) for d in self.decisions],
            "metadata": self.metadata,
            "total_duration_ms": self.total_duration_ms,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cost_usd": self.total_cost_usd,
        }


class TraceCollector:
    """
    Trace 数据采集器

    单例模式，负责：
    1. 创建和管理 Trace 生命周期
    2. 采集各类可观测性数据
    3. 与 Langfuse 集成上报
    4. 本地数据缓存与查询
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self.langfuse: Optional[LangfuseClient] = None
        self._traces: Dict[str, TraceData] = {}
        self._local_buffer: List[Dict[str, Any]] = []
        self._buffer_size = 100
        self._enabled = True
        self._storage_dir = os.path.join(os.path.dirname(__file__), "..", ".trace_data")

    def initialize(self, langfuse_client: Optional[LangfuseClient] = None) -> None:
        """初始化采集器，连接 Langfuse"""
        if langfuse_client:
            self.langfuse = langfuse_client
        else:
            self.langfuse = get_langfuse_client()

        if self.langfuse and self.langfuse.health_check():
            logger.info("TraceCollector initialized with Langfuse")
        else:
            logger.warning("TraceCollector running in local-only mode")

    def start_trace(
        self,
        name: str,
        task_id: Optional[str] = None,
        agent_type: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """开始一个新的 Trace"""
        trace_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        trace_data = TraceData(
            trace_id=trace_id,
            task_id=task_id,
            name=name,
            start_time=now,
            agent_type=agent_type,
            metadata=metadata or {},
        )
        self._traces[trace_id] = trace_data

        # 设置上下文
        _current_trace_id.set(trace_id)
        _current_span_stack.set([])

        # 上报 Langfuse
        if self.langfuse and self.langfuse.client:
            try:
                self.langfuse.create_trace(
                    name=name,
                    trace_id=trace_id,
                    metadata={
                        "task_id": task_id,
                        "agent_type": agent_type,
                        **(metadata or {}),
                    },
                )
            except Exception as e:
                logger.error(f"Failed to report trace start to Langfuse: {e}")

        logger.info(f"Trace started: {trace_id} - {name}")
        return trace_id

    def end_trace(
        self,
        trace_id: Optional[str] = None,
        status: str = "completed",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[TraceData]:
        """结束一个 Trace"""
        tid = trace_id or _current_trace_id.get()
        if not tid or tid not in self._traces:
            logger.warning(f"Trace not found: {tid}")
            return None

        trace = self._traces[tid]
        trace.end_time = datetime.now(timezone.utc).isoformat()
        trace.status = status

        # 计算汇总指标
        # 使用 start_time 和 end_time 计算实际总耗时（包含 LLM 调用、思考时间等）
        if trace.start_time and trace.end_time:
            start = datetime.fromisoformat(trace.start_time)
            end = datetime.fromisoformat(trace.end_time)
            trace.total_duration_ms = (end - start).total_seconds() * 1000
        else:
            trace.total_duration_ms = sum(tc.duration_ms for tc in trace.tool_calls)
        trace.total_input_tokens = sum(tu.input_tokens for tu in trace.token_usage)
        trace.total_output_tokens = sum(tu.output_tokens for tu in trace.token_usage)
        trace.total_cost_usd = sum(tu.cost_usd for tu in trace.token_usage)

        if metadata:
            trace.metadata.update(metadata)

        # 上报 Langfuse
        if self.langfuse and self.langfuse.client:
            try:
                self.langfuse.client.score(
                    trace_id=tid,
                    name="total_duration_ms",
                    value=trace.total_duration_ms,
                )
                self.langfuse.client.score(
                    trace_id=tid,
                    name="total_tokens",
                    value=trace.total_input_tokens + trace.total_output_tokens,
                )
            except Exception as e:
                logger.error(f"Failed to report trace end to Langfuse: {e}")

        # 本地缓存
        self._local_buffer.append(trace.to_dict())
        if len(self._local_buffer) >= self._buffer_size:
            self._flush_local_buffer()

        logger.info(f"Trace ended: {tid} - status={status}, duration={trace.total_duration_ms}ms")
        return trace

    def record_tool_call(
        self,
        tool_name: str,
        input_params: Dict[str, Any],
        output_result: Any = None,
        error: Optional[str] = None,
        duration_ms: Optional[float] = None,
        trace_id: Optional[str] = None,
    ) -> ToolCallRecord:
        """记录 Tool Call"""
        tid = trace_id or _current_trace_id.get()
        if not tid or tid not in self._traces:
            logger.debug(f"No active trace, skipping tool call record")
            return ToolCallRecord(tool_name=tool_name, start_time=time.perf_counter())

        record = ToolCallRecord(
            tool_name=tool_name,
            start_time=time.perf_counter(),
            input_params=input_params,
        )

        if duration_ms is not None:
            record.duration_ms = duration_ms
            record.end_time = record.start_time + duration_ms / 1000
        elif output_result is not None or error is not None:
            record.finalize(output=output_result, error=error)

        self._traces[tid].tool_calls.append(record)

        # 上报 Langfuse Event
        if self.langfuse and self.langfuse.client:
            try:
                self.langfuse.create_event(
                    trace_id=tid,
                    name=f"tool_call:{tool_name}",
                    metadata={
                        "tool_name": tool_name,
                        "input_params": input_params,
                        "output_preview": str(output_result)[:200] if output_result else None,
                        "success": record.success,
                        "duration_ms": record.duration_ms,
                    },
                )
            except Exception as e:
                logger.error(f"Failed to report tool call: {e}")

        return record

    def record_token_usage(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: Optional[float] = None,
        trace_id: Optional[str] = None,
    ) -> TokenUsageRecord:
        """记录 Token 消耗"""
        tid = trace_id or _current_trace_id.get()

        record = TokenUsageRecord(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost_usd=cost_usd or self._estimate_cost(model, input_tokens, output_tokens),
        )

        if tid and tid in self._traces:
            self._traces[tid].token_usage.append(record)

        return record

    def record_prompt(
        self,
        prompt_text: str,
        role: str = "system",
        version: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ) -> PromptRecord:
        """记录 Prompt 演变"""
        tid = trace_id or _current_trace_id.get()

        if version is None and tid and tid in self._traces:
            version = len(self._traces[tid].prompts) + 1
        else:
            version = version or 1

        record = PromptRecord(
            version=version,
            prompt_text=prompt_text,
            role=role,
            metadata=metadata or {},
        )

        if tid and tid in self._traces:
            self._traces[tid].prompts.append(record)

        return record

    def record_decision(
        self,
        decision_type: str,
        context: Dict[str, Any],
        options: List[str],
        selected_option: str,
        reasoning: str = "",
        confidence: float = 0.0,
        trace_id: Optional[str] = None,
    ) -> DecisionRecord:
        """记录决策节点"""
        tid = trace_id or _current_trace_id.get()

        record = DecisionRecord(
            decision_id=str(uuid.uuid4()),
            decision_type=decision_type,
            context=context,
            options=options,
            selected_option=selected_option,
            reasoning=reasoning,
            confidence=confidence,
        )

        if tid and tid in self._traces:
            self._traces[tid].decisions.append(record)

            # 上报 Langfuse
            if self.langfuse and self.langfuse.client:
                try:
                    self.langfuse.create_event(
                        trace_id=tid,
                        name=f"decision:{decision_type}",
                        metadata={
                            "decision_type": decision_type,
                            "selected_option": selected_option,
                            "options": options,
                            "confidence": confidence,
                            "reasoning_preview": reasoning[:200],
                        },
                    )
                except Exception as e:
                    logger.error(f"Failed to report decision: {e}")

        return record

    def get_trace(self, trace_id: str) -> Optional[TraceData]:
        """获取指定 Trace 数据"""
        return self._traces.get(trace_id)

    def get_traces_by_task(self, task_id: str) -> List[TraceData]:
        """按任务ID查询所有 Trace"""
        return [t for t in self._traces.values() if t.task_id == task_id]

    def get_traces_by_time_range(
        self,
        start: datetime,
        end: datetime,
        agent_type: Optional[str] = None,
    ) -> List[TraceData]:
        """按时间范围查询 Trace"""
        results = []
        for trace in self._traces.values():
            trace_start = datetime.fromisoformat(trace.start_time)
            if start <= trace_start <= end:
                if agent_type is None or trace.agent_type == agent_type:
                    results.append(trace)
        return results

    def _estimate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """估算 Token 成本（USD）"""
        cost_map = {
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},
            "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
            "deepseek-chat": {"input": 0.00014, "output": 0.00028},
            "deepseek-reasoner": {"input": 0.00055, "output": 0.00219},
        }

        for key, rates in cost_map.items():
            if key in model.lower():
                return (input_tokens * rates["input"] + output_tokens * rates["output"]) / 1000

        return 0.0

    def _flush_local_buffer(self) -> None:
        """刷新本地缓冲区，将数据持久化到磁盘"""
        if not self._local_buffer:
            return

        try:
            os.makedirs(self._storage_dir, exist_ok=True)
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filepath = os.path.join(self._storage_dir, f"traces_{timestamp}.json")

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(self._local_buffer, f, ensure_ascii=False, indent=2)

            logger.info(f"Persisted {len(self._local_buffer)} trace records to {filepath}")
        except Exception as e:
            logger.error(f"Failed to persist trace buffer: {e}")

        self._local_buffer.clear()

    def flush(self) -> None:
        """强制刷新所有数据"""
        self._flush_local_buffer()
        if self.langfuse:
            self.langfuse.flush()


# 装饰器和上下文管理器

def trace_span(span_name: str, agent_type: str = ""):
    """装饰器：为函数执行创建 Trace Span"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            collector = TraceCollector()
            trace_id = _current_trace_id.get()

            if not trace_id:
                trace_id = collector.start_trace(
                    name=span_name,
                    agent_type=agent_type,
                )

            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                duration_ms = round((time.perf_counter() - start) * 1000, 3)

                if trace_id in collector._traces:
                    collector._traces[trace_id].metadata[f"{span_name}_duration_ms"] = duration_ms

                return result
            except Exception as e:
                duration_ms = round((time.perf_counter() - start) * 1000, 3)
                if trace_id in collector._traces:
                    collector._traces[trace_id].metadata[f"{span_name}_error"] = str(e)
                    collector._traces[trace_id].metadata[f"{span_name}_duration_ms"] = duration_ms
                raise

        return wrapper
    return decorator


@contextmanager
def trace_tool_call(tool_name: str, input_params: Optional[Dict[str, Any]] = None):
    """上下文管理器：追踪 Tool Call 执行"""
    collector = TraceCollector()
    record = collector.record_tool_call(
        tool_name=tool_name,
        input_params=input_params or {},
    )

    try:
        yield record
        record.finalize(output="completed")
    except Exception as e:
        record.finalize(error=str(e))
        raise


def get_current_trace_id() -> Optional[str]:
    """获取当前 Trace ID"""
    return _current_trace_id.get()


def set_current_trace_id(trace_id: str) -> None:
    """设置当前 Trace ID"""
    _current_trace_id.set(trace_id)