import logging
from typing import Optional

from crewai import Crew, Process

from agents.editor_agent import create_editor_agent
from agents.research_agent import create_research_agent
from agents.business_agent import create_business_agent
from agents.writer_agent import create_writer_agent
from services.planning_service import PlanningService, ResearchPlan

logger = logging.getLogger(__name__)


class ResearchCrew:
    def __init__(self, planning_service: Optional[PlanningService] = None):
        self.planning_service = planning_service or PlanningService()
        self._plan: Optional[ResearchPlan] = None

    def create_plan(self, topic: str, depth: str = "standard") -> ResearchPlan:
        logger.info(f"Creating research plan for topic: {topic}")
        self._plan = self.planning_service.generate_plan(topic, depth)
        return self._plan

    def get_plan(self) -> Optional[ResearchPlan]:
        return self._plan

    def build_crew(self, topic: str, plan: Optional[ResearchPlan] = None) -> Crew:
        research_plan = plan or self._plan
        if not research_plan:
            raise ValueError("请先创建研究计划 (call create_plan first)")

        editor = create_editor_agent()
        researcher = create_research_agent()
        analyst = create_business_agent()
        writer = create_writer_agent()

        from tasks.research_task import create_research_task
        from tasks.analysis_task import create_analysis_task
        from tasks.writing_task import create_writing_task

        research_queries = []
        for task in research_plan.tasks:
            if task.agent == "ResearchAgent" and task.search_queries:
                research_queries.extend(task.search_queries)

        research_task = create_research_task(topic, research_queries if research_queries else None)
        analysis_task = create_analysis_task(topic)
        writing_task = create_writing_task(topic)

        analysis_task.context = [research_task]
        writing_task.context = [research_task, analysis_task]

        crew = Crew(
            agents=[researcher, analyst, writer],
            tasks=[research_task, analysis_task, writing_task],
            process=Process.sequential,
            verbose=True,
        )

        logger.info(f"Crew built with {len(crew.agents)} agents and {len(crew.tasks)} tasks")
        return crew

    def run(self, topic: str, depth: str = "standard", auto_confirm: bool = True) -> str:
        plan = self.create_plan(topic, depth)

        if not auto_confirm:
            plan_display = self.planning_service.format_plan_display(plan)
            print(plan_display)
            confirm = input("\n是否确认执行此计划？(y/n): ").strip().lower()
            if confirm != "y":
                return "用户取消了研究计划执行"

        crew = self.build_crew(topic, plan)
        logger.info("Starting crew execution...")
        result = crew.kickoff()
        logger.info("Crew execution completed")
        return str(result)

    async def arun(self, topic: str, depth: str = "standard") -> str:
        plan = self.create_plan(topic, depth)
        crew = self.build_crew(topic, plan)
        logger.info("Starting async crew execution...")
        result = await crew.kickoff_async()
        logger.info("Async crew execution completed")
        return str(result)
