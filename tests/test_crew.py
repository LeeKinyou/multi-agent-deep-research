import pytest
from unittest.mock import patch, MagicMock

from crewai import Agent
from services.planning_service import ResearchPlan, ResearchSubTask


def _make_test_agent(role="TestAgent", goal="test", backstory="test"):
    return Agent(
        role=role,
        goal=goal,
        backstory=backstory,
        llm="gpt-4o-mini",
    )


class TestAgentDefinitions:
    @patch("agents.editor_agent.llm_config")
    def test_editor_agent_definition(self, mock_config):
        mock_config.get_crewai_llm.return_value = "gpt-4o-mini"
        from agents.editor_agent import create_editor_agent
        agent = create_editor_agent()
        assert agent.role == "资深研究主编与项目规划专家"
        assert agent.allow_delegation is True
        assert len(agent.goal) > 0
        assert len(agent.backstory) > 0

    @patch("agents.research_agent.llm_config")
    @patch("agents.research_agent.get_search_tools")
    def test_research_agent_definition(self, mock_tools, mock_config):
        mock_config.get_crewai_llm.return_value = "gpt-4o-mini"
        mock_tools.return_value = []
        from agents.research_agent import create_research_agent
        agent = create_research_agent()
        assert agent.role == "专业情报采集员"
        assert agent.allow_delegation is False

    @patch("agents.business_agent.llm_config")
    def test_business_agent_definition(self, mock_config):
        mock_config.get_crewai_llm.return_value = "gpt-4o-mini"
        from agents.business_agent import create_business_agent
        agent = create_business_agent()
        assert agent.role == "资深分析专家"
        assert agent.allow_delegation is False

    @patch("agents.writer_agent.llm_config")
    def test_writer_agent_definition(self, mock_config):
        mock_config.get_crewai_llm.return_value = "gpt-4o-mini"
        from agents.writer_agent import create_writer_agent
        agent = create_writer_agent()
        assert agent.role == "专业研究报告撰写专家"
        assert agent.allow_delegation is False


class TestTaskDefinitions:
    @patch("tasks.planning_task.create_editor_agent")
    def test_planning_task(self, mock_create):
        mock_create.return_value = _make_test_agent("Editor")
        from tasks.planning_task import create_planning_task
        task = create_planning_task("人工智能")
        assert "人工智能" in task.description
        assert len(task.expected_output) > 0

    @patch("tasks.research_task.create_research_agent")
    def test_research_task_default_queries(self, mock_create):
        mock_create.return_value = _make_test_agent("Researcher")
        from tasks.research_task import create_research_task
        task = create_research_task("人工智能")
        assert "人工智能" in task.description

    @patch("tasks.research_task.create_research_agent")
    def test_research_task_custom_queries(self, mock_create):
        mock_create.return_value = _make_test_agent("Researcher")
        from tasks.research_task import create_research_task
        task = create_research_task("AI", search_queries=["AI market", "AI trends"])
        assert "AI market" in task.description
        assert "AI trends" in task.description

    @patch("tasks.analysis_task.create_business_agent")
    def test_analysis_task(self, mock_create):
        mock_create.return_value = _make_test_agent("Analyst")
        from tasks.analysis_task import create_analysis_task
        task = create_analysis_task("人工智能")
        assert "SWOT" in task.description

    @patch("tasks.analysis_task.create_business_agent")
    def test_analysis_task_with_context(self, mock_create):
        mock_create.return_value = _make_test_agent("Analyst")
        from tasks.analysis_task import create_analysis_task
        task = create_analysis_task("AI", research_context="Some research data")
        assert "Some research data" in task.description

    @patch("tasks.writing_task.create_writer_agent")
    def test_writing_task(self, mock_create):
        mock_create.return_value = _make_test_agent("Writer")
        from tasks.writing_task import create_writing_task
        task = create_writing_task("人工智能")
        assert "研究报告" in task.expected_output

    @patch("tasks.writing_task.create_writer_agent")
    def test_writing_task_with_context(self, mock_create):
        mock_create.return_value = _make_test_agent("Writer")
        from tasks.writing_task import create_writing_task
        task = create_writing_task("AI", analysis_context="Analysis results here")
        assert "Analysis results here" in task.description


class TestResearchCrew:
    @patch("crew.PlanningService")
    def test_create_plan(self, mock_planning_svc_class):
        mock_svc = MagicMock()
        mock_plan = ResearchPlan(topic="AI", tasks=[
            ResearchSubTask(task_id="T1", name="T1", agent="ResearchAgent", description="d")
        ])
        mock_svc.generate_plan.return_value = mock_plan
        mock_planning_svc_class.return_value = mock_svc

        from core.crew import ResearchCrew
        crew = ResearchCrew(planning_service=mock_svc)
        plan = crew.create_plan("AI")
        assert plan.topic == "AI"
        mock_svc.generate_plan.assert_called_once_with("AI", "standard")

    def test_build_crew_without_plan_raises(self):
        from core.crew import ResearchCrew
        crew = ResearchCrew()
        with pytest.raises(ValueError, match="请先创建研究计划"):
            crew.build_crew("AI")

    @patch("tasks.writing_task.create_writer_agent")
    @patch("tasks.analysis_task.create_business_agent")
    @patch("tasks.research_task.create_research_agent")
    @patch("core.crew.create_writer_agent")
    @patch("core.crew.create_business_agent")
    @patch("core.crew.create_research_agent")
    @patch("core.crew.create_editor_agent")
    def test_build_crew_creates_correct_structure(
        self, mock_editor, mock_researcher, mock_analyst, mock_writer,
        mock_task_researcher, mock_task_analyst, mock_task_writer
    ):
        test_editor = _make_test_agent("Editor")
        test_researcher = _make_test_agent("Researcher")
        test_analyst = _make_test_agent("Analyst")
        test_writer = _make_test_agent("Writer")

        mock_editor.return_value = test_editor
        mock_researcher.return_value = test_researcher
        mock_analyst.return_value = test_analyst
        mock_writer.return_value = test_writer
        mock_task_researcher.return_value = test_researcher
        mock_task_analyst.return_value = test_analyst
        mock_task_writer.return_value = test_writer

        plan = ResearchPlan(
            topic="AI",
            tasks=[
                ResearchSubTask(
                    task_id="T1", name="采集", agent="ResearchAgent",
                    description="d", search_queries=["AI market"]
                ),
                ResearchSubTask(
                    task_id="T2", name="分析", agent="BusinessAnalyst",
                    description="d", depends_on=["T1"]
                ),
                ResearchSubTask(
                    task_id="T3", name="撰写", agent="WriterAgent",
                    description="d", depends_on=["T2"]
                ),
            ],
        )

        from core.crew import ResearchCrew
        crew_instance = ResearchCrew()
        crew_instance._plan = plan
        crew = crew_instance.build_crew("AI")

        assert len(crew.agents) == 3
        assert len(crew.tasks) == 3


class TestConfigModule:
    def test_config_loads(self):
        from config import llm_config, search_config, app_config, BASE_DIR, DATA_DIR, REPORTS_DIR
        assert BASE_DIR.exists()
        assert DATA_DIR.exists()
        assert REPORTS_DIR.exists()

    def test_llm_config_defaults(self):
        from config import llm_config
        assert isinstance(llm_config.model, str)
        assert isinstance(llm_config.temperature, float)
        assert isinstance(llm_config.max_tokens, int)

    def test_search_config_defaults(self):
        from config import search_config
        assert search_config.tool in ("duckduckgo", "tavily")
        assert isinstance(search_config.max_results, int)
