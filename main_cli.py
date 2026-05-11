#!/usr/bin/env python3
import argparse
import datetime
import logging
import sys

from config import REPORTS_DIR, llm_config, search_config
from crew import ResearchCrew
from services.planning_service import PlanningService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def save_report(topic: str, content: str) -> str:
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_topic = "".join(c if c.isalnum() or c in "_-" else "_" for c in topic)[:30]
    filename = f"{safe_topic}_{timestamp}.md"
    filepath = REPORTS_DIR / filename
    filepath.write_text(content, encoding="utf-8")
    return str(filepath)


def check_environment():
    errors = []
    if not llm_config.api_key:
        errors.append("LLM API密钥未配置，请在.env文件中设置LLM_API_KEY")
    if llm_config.provider == "openai" and "localhost" in llm_config.base_url:
        import requests
        try:
            resp = requests.get(f"{llm_config.base_url}/models", timeout=5)
            if resp.status_code != 200:
                errors.append(f"LM Studio本地服务不可用 ({llm_config.base_url})，请确认LM Studio已启动并加载模型")
        except requests.ConnectionError:
            errors.append(f"无法连接到LM Studio ({llm_config.base_url})，请确认LM Studio已启动")
    if search_config.tool == "tavily" and not search_config.tavily_api_key:
        errors.append("Tavily API密钥未配置，请在.env文件中设置TAVILY_API_KEY，或切换为duckduckgo")
    return errors


def interactive_mode():
    print("=" * 60)
    print("  MultiAgentDeepResearch - 多智能体深度研究系统")
    print("=" * 60)

    errors = check_environment()
    if errors:
        print("\n⚠️  环境配置问题：")
        for err in errors:
            print(f"  - {err}")
        print("\n请修复后重试。")
        return 1

    print(f"\n📋 当前配置：")
    print(f"  LLM模型: {llm_config.model}")
    print(f"  搜索工具: {search_config.tool}")
    print(f"  报告目录: {REPORTS_DIR}")

    while True:
        print("\n" + "-" * 60)
        topic = input("🔍 请输入研究主题（输入q退出）: ").strip()
        if topic.lower() == "q":
            print("再见！")
            break
        if not topic:
            print("⚠️  研究主题不能为空")
            continue

        depth_input = input("📊 研究深度 (1=标准, 2=深度) [默认1]: ").strip()
        depth = "deep" if depth_input == "2" else "standard"

        confirm_input = input("✋ 是否需要确认研究计划？(y/n) [默认y]: ").strip().lower()
        auto_confirm = confirm_input == "n"

        try:
            crew = ResearchCrew()
            result = crew.run(topic, depth=depth, auto_confirm=auto_confirm)

            print("\n" + "=" * 60)
            print("  研究完成！")
            print("=" * 60)

            filepath = save_report(topic, result)
            print(f"\n📄 报告已保存至: {filepath}")

            preview_lines = result.split("\n")[:20]
            print("\n📖 报告预览：")
            print("-" * 40)
            print("\n".join(preview_lines))
            if len(result.split("\n")) > 20:
                print("... (更多内容请查看完整报告)")

        except KeyboardInterrupt:
            print("\n\n⚠️  研究已被用户中断")
        except Exception as e:
            logger.error(f"研究执行失败: {e}", exc_info=True)
            print(f"\n❌ 研究执行失败: {str(e)}")

        continue_choice = input("\n是否继续新的研究？(y/n) [默认n]: ").strip().lower()
        if continue_choice != "y":
            break

    return 0


def single_run(topic: str, depth: str = "standard", auto_confirm: bool = True):
    errors = check_environment()
    if errors:
        print("⚠️  环境配置问题：")
        for err in errors:
            print(f"  - {err}")
        return 1

    try:
        crew = ResearchCrew()
        result = crew.run(topic, depth=depth, auto_confirm=auto_confirm)

        filepath = save_report(topic, result)
        print(f"\n📄 报告已保存至: {filepath}")
        print(f"\n{result}")
        return 0

    except Exception as e:
        logger.error(f"研究执行失败: {e}", exc_info=True)
        print(f"❌ 研究执行失败: {str(e)}")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="MultiAgentDeepResearch - 多智能体深度研究系统"
    )
    parser.add_argument("topic", nargs="?", help="研究主题")
    parser.add_argument("--depth", choices=["standard", "deep"], default="standard", help="研究深度")
    parser.add_argument("--auto-confirm", action="store_true", help="自动确认研究计划")
    parser.add_argument("-i", "--interactive", action="store_true", help="交互模式")

    args = parser.parse_args()

    if args.interactive or not args.topic:
        return interactive_mode()

    return single_run(args.topic, depth=args.depth, auto_confirm=args.auto_confirm)


if __name__ == "__main__":
    sys.exit(main())
