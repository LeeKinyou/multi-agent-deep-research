import os

from crewai import Agent

from config import llm_config


def create_writer_agent() -> Agent:
    return Agent(
        role="专业研究报告撰写专家",
        goal=(
            "整合所有分析结果，撰写结构清晰、逻辑严谨、内容详实的研究报告，"
            "确保报告专业性和可读性"
        ),
        backstory=(
            "你是一位资深行业研究员，撰写的报告被广泛应用于投资决策和战略规划。"
            "你擅长将复杂信息转化为易读的报告，注重报告的逻辑结构和论证链条。"
            "你的报告风格专业但不晦涩，数据详实但重点突出。"
            "你严格遵循报告模板结构，确保每个章节内容完整、逻辑连贯。"
        ),
        verbose=True,
        allow_delegation=False,
        llm=llm_config.get_crewai_llm(),
    )

    def save_report(self, content, filename):
        # 确保目录存在
        report_dir = "reports"
        if not os.path.exists(report_dir):
            os.makedirs(report_dir)
        
        file_path = os.path.join(report_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"报告已保存至: {os.path.abspath(file_path)}")
