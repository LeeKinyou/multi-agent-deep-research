import pytest
from unittest.mock import patch, MagicMock

from services.planning_service import (
    PlanningService,
    ResearchPlan,
    ResearchSubTask,
)


class TestResearchSubTask:
    def test_create_subtask(self):
        task = ResearchSubTask(
            task_id="T1",
            name="市场信息采集",
            agent="ResearchAgent",
            description="收集市场信息",
            search_queries=["市场规模", "发展趋势"],
            depends_on=[],
            expected_output="市场数据",
        )
        assert task.task_id == "T1"
        assert task.name == "市场信息采集"
        assert task.agent == "ResearchAgent"
        assert len(task.search_queries) == 2
        assert task.depends_on == []

    def test_subtask_defaults(self):
        task = ResearchSubTask(
            task_id="T2",
            name="分析任务",
            agent="BusinessAnalyst",
            description="执行分析",
        )
        assert task.search_queries == []
        assert task.depends_on == []
        assert task.expected_output == ""


class TestResearchPlan:
    def test_create_plan(self):
        plan = ResearchPlan(
            topic="人工智能",
            objectives=["目标1", "目标2"],
            scope_included=["AI技术"],
            scope_excluded=["无关领域"],
            tasks=[
                ResearchSubTask(
                    task_id="T1",
                    name="采集",
                    agent="ResearchAgent",
                    description="信息采集",
                )
            ],
            estimated_duration=300,
            validation_points=["验证点1"],
        )
        assert plan.topic == "人工智能"
        assert len(plan.objectives) == 2
        assert len(plan.tasks) == 1
        assert plan.estimated_duration == 300

    def test_plan_defaults(self):
        plan = ResearchPlan(topic="测试主题")
        assert plan.objectives == []
        assert plan.tasks == []
        assert plan.estimated_duration == 300


class TestPlanningService:
    def setup_method(self):
        self.service = PlanningService()

    def test_extract_json_from_code_block(self):
        text = '```json\n{"topic": "AI", "objectives": []}\n```'
        result = self.service._extract_json(text)
        assert result is not None
        assert "topic" in result

    def test_extract_json_from_plain_block(self):
        text = '```\n{"topic": "AI"}\n```'
        result = self.service._extract_json(text)
        assert result is not None

    def test_extract_json_from_raw(self):
        text = 'Some text {"topic": "AI", "objectives": []} more text'
        result = self.service._extract_json(text)
        assert result is not None

    def test_extract_json_no_json(self):
        text = "This is just plain text without any JSON"
        result = self.service._extract_json(text)
        assert result is None

    def test_parse_plan_response_valid_json(self):
        json_str = '''```json
        {
            "topic": "人工智能",
            "objectives": ["目标1"],
            "scope_included": ["AI"],
            "scope_excluded": [],
            "tasks": [
                {
                    "task_id": "T1",
                    "name": "采集",
                    "agent": "ResearchAgent",
                    "description": "信息采集",
                    "search_queries": ["AI市场"],
                    "depends_on": [],
                    "expected_output": "数据"
                }
            ],
            "estimated_duration": 300,
            "validation_points": ["VP1"]
        }
        ```'''
        plan = self.service._parse_plan_response(json_str, "人工智能")
        assert plan.topic == "人工智能"
        assert len(plan.tasks) == 1
        assert plan.tasks[0].task_id == "T1"

    def test_parse_plan_response_invalid_json_uses_fallback(self):
        plan = self.service._parse_plan_response("not valid json at all", "测试主题")
        assert plan.topic == "测试主题"
        assert len(plan.tasks) >= 4

    def test_get_fallback_plan(self):
        plan = self.service._get_fallback_plan("测试主题")
        assert plan.topic == "测试主题"
        assert len(plan.objectives) >= 1
        assert len(plan.tasks) >= 4
        task_ids = [t.task_id for t in plan.tasks]
        assert "T1" in task_ids
        assert "T4" in task_ids

    def test_fallback_plan_task_dependencies(self):
        plan = self.service._get_fallback_plan("测试")
        task_map = {t.task_id: t for t in plan.tasks}
        assert "T1" in task_map
        assert "T2" in task_map
        assert "T1" in task_map["T2"].depends_on
        assert "T3" in task_map
        assert "T4" in task_map
        assert "T3" in task_map["T4"].depends_on

    def test_fallback_plan_agent_assignment(self):
        plan = self.service._get_fallback_plan("测试")
        task_map = {t.task_id: t for t in plan.tasks}
        assert task_map["T1"].agent == "ResearchAgent"
        assert task_map["T2"].agent == "ResearchAgent"
        assert task_map["T3"].agent == "BusinessAnalyst"
        assert task_map["T4"].agent == "WriterAgent"

    def test_format_plan_display(self):
        plan = self.service._get_fallback_plan("人工智能")
        display = self.service.format_plan_display(plan)
        assert "人工智能" in display
        assert "T1" in display
        assert "ResearchAgent" in display
        assert "BusinessAnalyst" in display
        assert "WriterAgent" in display

    @patch.object(PlanningService, "_parse_plan_response")
    def test_generate_plan_calls_llm(self, mock_parse):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content='{"topic": "AI"}')
        mock_parse.return_value = ResearchPlan(topic="AI")

        service = PlanningService(llm=mock_llm)
        plan = service.generate_plan("AI")

        mock_llm.invoke.assert_called_once()
        assert plan.topic == "AI"

    @patch.object(PlanningService, "_parse_plan_response")
    def test_generate_plan_deep_mode(self, mock_parse):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content='{"topic": "AI"}')
        mock_parse.return_value = ResearchPlan(topic="AI")

        service = PlanningService(llm=mock_llm)
        service.generate_plan("AI", depth="deep")

        call_args = mock_llm.invoke.call_args
        messages = call_args[0][0]
        human_msg = messages[1].content
        assert "深度研究" in human_msg
