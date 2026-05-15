import asyncio
import json
import logging
from typing import Optional, Callable, Dict, Any

from crewai import Crew, Process

from agents.editor_agent import create_editor_agent
from agents.research_agent import create_research_agent
from agents.business_agent import create_business_agent
from agents.writer_agent import create_writer_agent
from services.planning_service import PlanningService, ResearchPlan
from services.context_manager import ContextManager
from config import context_config
from models.structured_output import ReportOutput

logger = logging.getLogger(__name__)


class ResearchCrew:
    def __init__(
        self,
        planning_service: Optional[PlanningService] = None,
        task_id: Optional[str] = None,
        stream_callback: Optional[Callable] = None,
    ):
        self.planning_service = planning_service or PlanningService()
        self._plan: Optional[ResearchPlan] = None
        self.context_manager = ContextManager(
            max_tokens=context_config.max_tokens,
            warning_threshold=context_config.warning_threshold,
            critical_threshold=context_config.critical_threshold,
            task_id=task_id,
        )
        self.task_id = task_id
        self.stream_callback = stream_callback

    async def _emit_event(self, event_type: str, data: Dict[str, Any]):
        if self.stream_callback:
            try:
                if asyncio.iscoroutinefunction(self.stream_callback):
                    await self.stream_callback(event_type, data)
                else:
                    self.stream_callback(event_type, data)
            except Exception as e:
                logger.error(f"Error in stream callback: {e}")

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
        researcher = create_research_agent(task_id=self.task_id)
        analyst = create_business_agent(task_id=self.task_id)
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

    def _render_report_to_markdown(self, result) -> str:
        try:
            if hasattr(result, 'pydantic') and result.pydantic:
                report: ReportOutput = result.pydantic
                return self._format_report_output(report)
            elif hasattr(result, 'raw') and result.raw:
                try:
                    data = json.loads(result.raw)
                    if isinstance(data, dict) and 'title' in data:
                        report = ReportOutput(**data)
                        return self._format_report_output(report)
                except:
                    pass
                return str(result.raw)
            return str(result)
        except Exception as e:
            logger.error(f"Failed to render report: {e}")
            return str(result)

    def _format_report_output(self, report: ReportOutput) -> str:
        lines = []
        lines.append(f"# {report.title}\n")
        
        if report.executive_summary:
            lines.append("## 执行摘要\n")
            lines.append(report.executive_summary)
            lines.append("")
        
        for section in report.sections:
            lines.append(f"## {section.title}\n")
            lines.append(section.content)
            lines.append("")
            
            for subsection in section.subsections:
                lines.append(f"### {subsection.title}\n")
                lines.append(subsection.content)
                lines.append("")
        
        if report.conclusion:
            lines.append("## 结论\n")
            lines.append(report.conclusion)
            lines.append("")
        
        if report.appendices:
            lines.append("## 附录\n")
            for appendix in report.appendices:
                lines.append(f"- {appendix}")
            lines.append("")
        
        if report.sources:
            lines.append("## 参考来源\n")
            for i, source in enumerate(report.sources, 1):
                lines.append(f"{i}. [{source.title}]({source.url})")
            lines.append("")
        
        return "\n".join(lines)

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

        self.context_manager.add_segment(
            content=f"研究主题: {topic}\n研究深度: {depth}\n任务数: {len(plan.tasks)}",
            importance=0.9,
            source="plan",
        )

        result = crew.kickoff()
        logger.info("Crew execution completed")

        status = self.context_manager.get_status()
        logger.info(f"上下文状态: {status}")

        return self._render_report_to_markdown(result)

    async def arun(self, topic: str, depth: str = "standard") -> str:
        plan = self.create_plan(topic, depth)
        crew = self.build_crew(topic, plan)
        logger.info("Starting async crew execution...")
        result = await crew.kickoff_async()
        logger.info("Async crew execution completed")
        return self._render_report_to_markdown(result)

    async def arun_streaming(self, topic: str, depth: str = "standard") -> str:
        await self._emit_event("task_status", {
            "status": "starting",
            "message": "正在启动研究任务...",
        })

        await self._emit_event("progress", {
            "current_step": 0,
            "total_steps": 3,
            "message": "正在生成研究计划...",
            "percent": 0,
        })

        plan = self.create_plan(topic, depth)

        await self._emit_event("agent_start", {
            "agent_name": "主编Agent",
            "task_description": "生成研究计划",
        })

        await self._emit_event("agent_thinking", {
            "agent_name": "主编Agent",
            "thinking": f"已生成包含 {len(plan.tasks)} 个任务的研究计划",
            "step": "plan_created",
        })

        await self._emit_event("agent_complete", {
            "agent_name": "主编Agent",
            "output": f"研究计划已生成，共 {len(plan.tasks)} 个任务",
        })

        await self._emit_event("progress", {
            "current_step": 1,
            "total_steps": 3,
            "message": "正在执行情报采集...",
            "percent": 33,
        })

        await self._emit_event("agent_start", {
            "agent_name": "情报采集Agent",
            "task_description": "搜索和收集相关信息",
        })

        await self._emit_event("agent_thinking", {
            "agent_name": "情报采集Agent",
            "thinking": "正在使用多个搜索引擎收集数据，分析信息来源可靠性...",
            "step": "searching",
        })

        crew = self.build_crew(topic, plan)

        self.context_manager.add_segment(
            content=f"研究主题: {topic}\n研究深度: {depth}\n任务数: {len(plan.tasks)}",
            importance=0.9,
            source="plan",
        )

        await self._emit_event("agent_thinking", {
            "agent_name": "情报采集Agent",
            "thinking": "信息收集完成，正在整理搜索结果...",
            "step": "collecting_done",
        })

        await self._emit_event("agent_complete", {
            "agent_name": "情报采集Agent",
            "output": "已完成信息收集",
        })

        await self._emit_event("progress", {
            "current_step": 2,
            "total_steps": 3,
            "message": "正在进行数据分析...",
            "percent": 66,
        })

        await self._emit_event("agent_start", {
            "agent_name": "商业分析Agent",
            "task_description": "多维度分析收集的信息",
        })

        await self._emit_event("agent_thinking", {
            "agent_name": "商业分析Agent",
            "thinking": "正在进行SWOT分析、竞品对比、趋势预测...",
            "step": "analyzing",
        })

        await self._emit_event("agent_thinking", {
            "agent_name": "商业分析Agent",
            "thinking": "分析完成，正在生成结论...",
            "step": "analysis_done",
        })

        await self._emit_event("agent_complete", {
            "agent_name": "商业分析Agent",
            "output": "已完成数据分析",
        })

        await self._emit_event("progress", {
            "current_step": 3,
            "total_steps": 3,
            "message": "正在生成研究报告...",
            "percent": 90,
        })

        await self._emit_event("agent_start", {
            "agent_name": "报告生成Agent",
            "task_description": "撰写结构化研究报告",
        })

        await self._emit_event("agent_thinking", {
            "agent_name": "报告生成Agent",
            "thinking": "正在整合分析结果，撰写报告各章节...",
            "step": "writing",
        })

        result = await crew.kickoff_async()

        await self._emit_event("agent_thinking", {
            "agent_name": "报告生成Agent",
            "thinking": "报告撰写完成，正在检查格式和完整性...",
            "step": "writing_done",
        })

        await self._emit_event("agent_complete", {
            "agent_name": "报告生成Agent",
            "output": "研究报告已生成",
        })

        await self._emit_event("progress", {
            "current_step": 3,
            "total_steps": 3,
            "message": "研究任务完成",
            "percent": 100,
        })

        await self._emit_event("task_status", {
            "status": "completed",
            "message": "研究任务已完成",
        })

        await self._emit_event("complete", {
            "result": self._render_report_to_markdown(result),
        })

        logger.info("Streaming crew execution completed")
        return self._render_report_to_markdown(result)
