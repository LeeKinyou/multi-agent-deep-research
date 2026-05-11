"""
前端组件单元测试

测试计划展示、报告展示、组件等功能
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from frontend.plan_display import format_plan_summary, validate_plan
from frontend.display import extract_report_summary
from frontend.components import format_task_progress


class TestPlanDisplay:
    """测试计划展示组件"""
    
    def test_format_plan_summary(self):
        """测试计划摘要生成"""
        plan_data = {
            "topic": "人工智能发展趋势",
            "tasks": [
                {
                    "task_id": "1",
                    "description": "搜索相关信息",
                    "agent": "ResearchAgent",
                },
                {
                    "task_id": "2",
                    "description": "进行SWOT分析",
                    "agent": "BusinessAgent",
                },
            ],
        }
        
        summary = format_plan_summary(plan_data)
        
        assert "人工智能发展趋势" in summary
        assert "任务数量：2" in summary
        assert "搜索相关信息" in summary
        assert "进行SWOT分析" in summary
    
    def test_validate_plan_valid(self):
        """测试有效计划验证"""
        plan_data = {
            "topic": "测试主题",
            "tasks": [
                {
                    "task_id": "1",
                    "description": "任务描述",
                    "agent": "TestAgent",
                },
            ],
        }
        
        errors = validate_plan(plan_data)
        assert len(errors) == 0
    
    def test_validate_plan_missing_topic(self):
        """测试缺少主题的验证"""
        plan_data = {
            "tasks": [
                {
                    "task_id": "1",
                    "description": "任务描述",
                    "agent": "TestAgent",
                },
            ],
        }
        
        errors = validate_plan(plan_data)
        assert len(errors) == 1
        assert "缺少研究主题" in errors[0]
    
    def test_validate_plan_empty_tasks(self):
        """测试空任务列表的验证"""
        plan_data = {
            "topic": "测试主题",
            "tasks": [],
        }
        
        errors = validate_plan(plan_data)
        assert len(errors) == 1
        assert "没有研究任务" in errors[0]
    
    def test_validate_plan_missing_description(self):
        """测试缺少任务描述的验证"""
        plan_data = {
            "topic": "测试主题",
            "tasks": [
                {
                    "task_id": "1",
                    "agent": "TestAgent",
                },
            ],
        }
        
        errors = validate_plan(plan_data)
        assert len(errors) == 1
        assert "任务 1 缺少描述" in errors[0]
    
    def test_validate_plan_missing_agent(self):
        """测试缺少Agent的验证"""
        plan_data = {
            "topic": "测试主题",
            "tasks": [
                {
                    "task_id": "1",
                    "description": "任务描述",
                },
            ],
        }
        
        errors = validate_plan(plan_data)
        assert len(errors) == 1
        assert "任务 1 缺少执行Agent" in errors[0]


class TestDisplay:
    """测试报告展示组件"""
    
    def test_extract_report_summary(self):
        """测试报告摘要提取"""
        report_content = """# 人工智能发展趋势研究报告

## 1. 执行摘要
这是执行摘要内容

## 2. 市场分析
这是市场分析内容

## 3. 竞品分析
这是竞品分析内容

## 4. 结论与建议
这是结论与建议内容
"""
        
        summary = extract_report_summary(report_content)
        
        assert summary["title"] == "人工智能发展趋势研究报告"
        assert len(summary["sections"]) == 4
        assert "1. 执行摘要" in summary["sections"]
        assert "2. 市场分析" in summary["sections"]
        assert summary["word_count"] > 0
        assert summary["line_count"] > 0
    
    def test_extract_report_summary_empty(self):
        """测试空报告摘要提取"""
        report_content = ""
        
        summary = extract_report_summary(report_content)
        
        assert summary["title"] == ""
        assert len(summary["sections"]) == 0
        assert summary["word_count"] == 0
        assert summary["line_count"] == 1


class TestComponents:
    """测试通用组件"""
    
    def test_format_task_progress(self):
        """测试任务进度格式化"""
        task_info = {
            "current_step": 2,
            "total_steps": 5,
            "step_name": "商业分析",
        }
        
        progress = format_task_progress(task_info)
        
        assert "商业分析" in progress
        assert "2/5" in progress
        assert "40%" in progress
    
    def test_format_task_progress_zero(self):
        """测试零进度格式化"""
        task_info = {
            "current_step": 0,
            "total_steps": 5,
            "step_name": "开始",
        }
        
        progress = format_task_progress(task_info)
        
        assert "0%" in progress
        assert "0/5" in progress
    
    def test_format_task_progress_complete(self):
        """测试完成进度格式化"""
        task_info = {
            "current_step": 5,
            "total_steps": 5,
            "step_name": "完成",
        }
        
        progress = format_task_progress(task_info)
        
        assert "100%" in progress
        assert "5/5" in progress
    
    def test_format_task_progress_no_total(self):
        """测试无总数时的进度格式化"""
        task_info = {
            "current_step": 2,
            "step_name": "处理中",
        }
        
        progress = format_task_progress(task_info)
        
        assert "0%" in progress
        assert "处理中" in progress


class TestPlanConfirmation:
    """测试计划确认交互"""
    
    def test_plan_data_structure(self):
        """测试计划数据结构"""
        plan_data = {
            "topic": "测试主题",
            "tasks": [
                {
                    "task_id": "1",
                    "description": "任务1",
                    "agent": "Agent1",
                    "expected_output": "输出1",
                },
            ],
            "total_tasks": 1,
            "estimated_time": "3-5分钟",
        }
        
        assert "topic" in plan_data
        assert "tasks" in plan_data
        assert len(plan_data["tasks"]) == 1
        assert "task_id" in plan_data["tasks"][0]
        assert "description" in plan_data["tasks"][0]
        assert "agent" in plan_data["tasks"][0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
