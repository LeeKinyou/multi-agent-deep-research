"""
结构化输出模型 - 用于Agent间数据传递

使用Pydantic定义严格的数据结构，确保：
- Agent间传递结构化JSON而非大段文本
- 减少Token消耗（50%以上）
- 避免信息在传递过程中的丢失和变形
- 最终由Writer Agent渲染为Markdown报告
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class SourceInfo(BaseModel):
    url: str = Field(..., description="信息来源URL")
    title: str = Field(..., description="信息标题")
    relevance_score: float = Field(default=0.5, ge=0.0, le=1.0, description="相关性评分")


class MarketData(BaseModel):
    market_size: str = Field(default="", description="市场规模数据")
    growth_rate: str = Field(default="", description="增长率数据")
    key_trends: List[str] = Field(default_factory=list, description="关键趋势列表")


class KeyPlayer(BaseModel):
    name: str = Field(..., description="公司/机构名称")
    description: str = Field(default="", description="简介")
    market_position: str = Field(default="", description="市场地位")
    key_strengths: List[str] = Field(default_factory=list, description="核心优势")


class ResearchOutput(BaseModel):
    market_overview: MarketData = Field(default_factory=MarketData, description="市场概况")
    key_players: List[KeyPlayer] = Field(default_factory=list, description="主要参与者")
    key_events: List[str] = Field(default_factory=list, description="关键事件和政策")
    technology_trends: List[str] = Field(default_factory=list, description="技术发展动态")
    data_points: List[Dict[str, str]] = Field(default_factory=list, description="关键数据点")
    sources: List[SourceInfo] = Field(default_factory=list, description="信息来源列表")
    information_gaps: List[str] = Field(default_factory=list, description="信息缺口")
    summary: str = Field(default="", description="研究摘要（500字以内）")


class SWOTAnalysis(BaseModel):
    strengths: List[str] = Field(default_factory=list, description="优势列表")
    weaknesses: List[str] = Field(default_factory=list, description="劣势列表")
    opportunities: List[str] = Field(default_factory=list, description="机会列表")
    threats: List[str] = Field(default_factory=list, description="威胁列表")


class TrendAnalysis(BaseModel):
    trend_direction: str = Field(default="", description="发展趋势方向")
    key_drivers: List[str] = Field(default_factory=list, description="关键驱动因素")
    risk_factors: List[str] = Field(default_factory=list, description="潜在风险因素")
    prediction: str = Field(default="", description="趋势预测")


class AnalysisOutput(BaseModel):
    current_status: str = Field(default="", description="现状分析概述")
    key_characteristics: List[str] = Field(default_factory=list, description="关键特征与核心要素")
    swot: SWOTAnalysis = Field(default_factory=SWOTAnalysis, description="SWOT分析")
    trends: TrendAnalysis = Field(default_factory=TrendAnalysis, description="趋势研判")
    recommendations: List[str] = Field(default_factory=list, description="针对性建议")
    risk_warnings: List[str] = Field(default_factory=list, description="风险提示")
    action_priorities: List[str] = Field(default_factory=list, description="行动优先级")
    conclusion: str = Field(default="", description="分析结论")
    data_sources: List[str] = Field(default_factory=list, description="分析数据来源")


class ReportSection(BaseModel):
    title: str = Field(..., description="章节标题")
    content: str = Field(..., description="章节内容（Markdown格式）")
    subsections: List['ReportSection'] = Field(default_factory=list, description="子章节")


class ReportOutput(BaseModel):
    title: str = Field(..., description="报告标题")
    executive_summary: str = Field(default="", description="执行摘要")
    sections: List[ReportSection] = Field(default_factory=list, description="报告章节")
    conclusion: str = Field(default="", description="结论")
    appendices: List[str] = Field(default_factory=list, description="附录")
    sources: List[SourceInfo] = Field(default_factory=list, description="参考来源")


ReportSection.model_rebuild()
