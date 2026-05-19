#!/usr/bin/env python
import subprocess
import sys
import os
import time
import signal
import threading
import queue
from pathlib import Path

class ServiceManager:
    def __init__(self):
        self.processes = []
        self.project_root = Path(__file__).parent.parent
        self._stop_event = threading.Event()

    def _stream_output(self, process, prefix=""):
        def reader(pipe, prefix_str):
            for line in iter(pipe.readline, ""):
                if line:
                    print(f"{prefix_str}{line}", end="", flush=True)
            pipe.close()

        if process.stdout:
            t = threading.Thread(target=reader, args=(process.stdout, prefix), daemon=True)
            t.start()

    def run_command(self, cmd, cwd=None, shell=True, capture_output=False):
        work_dir = cwd or str(self.project_root)
        env = os.environ.copy()
        env["PYTHONPATH"] = str(self.project_root)

        try:
            process = subprocess.Popen(
                cmd,
                cwd=work_dir,
                shell=shell,
                stdout=subprocess.PIPE if capture_output else None,
                stderr=subprocess.STDOUT if capture_output else None,
                stdin=subprocess.PIPE if not capture_output else None,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
            )
        except Exception as e:
            print(f"  执行命令失败: {e}")
            return None

        if capture_output:
            self._stream_output(process, prefix="  [OUT] ")
        else:
            self._stream_output(process, prefix="")

        self.processes.append(process)
        return process

    def stop_all(self, signum=None, frame=None):
        print("\n正在停止所有服务...")
        self._stop_event.set()
        for process in self.processes:
            if process.poll() is None:
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                except Exception:
                    pass
        print("所有服务已停止")
        sys.exit(0)

    def kill_port_process(self, port):
        import subprocess as sp
        try:
            result = sp.run(
                f"netstat -ano | findstr :{port}",
                shell=True,
                capture_output=True,
                text=True
            )
            if result.stdout:
                for line in result.stdout.split("\n"):
                    if "LISTENING" in line:
                        parts = line.split()
                        if len(parts) >= 5:
                            pid = parts[-1]
                            try:
                                sp.run(f"taskkill /F /PID {pid}", shell=True, capture_output=True)
                                print(f"  已释放端口 {port} (PID: {pid})")
                                time.sleep(1)
                                return True
                            except Exception:
                                pass
        except Exception:
            pass
        return False

    def check_port_available(self, port):
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(("0.0.0.0", port))
            sock.close()
            return True
        except Exception:
            return False

    def wait_for_server(self, url, timeout=15):
        import urllib.request
        start = time.time()
        while time.time() - start < timeout:
            try:
                urllib.request.urlopen(url, timeout=3)
                return True
            except Exception:
                time.sleep(1)
        return False

    def start_api_server(self):
        print("启动 API 服务器...")

        if not self.check_port_available(8000):
            print("  端口 8000 被占用，尝试释放...")
            self.kill_port_process(8000)
            if not self.check_port_available(8000):
                print("  端口 8000 仍然被占用，请手动检查")
                return None

        cmd = f"{sys.executable} -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
        process = self.run_command(cmd, capture_output=True)
        if not process:
            return None

        print("  等待 API 服务器就绪...")
        if self.wait_for_server("http://localhost:8000/api/docs"):
            print("API 服务器已启动 (http://localhost:8000)")
            print("  API 文档: http://localhost:8000/api/docs")
            return process
        else:
            print("API 服务器启动超时")
            return None

    def start_chainlit_frontend(self, port=8001):
        print(f"启动 Chainlit 前端...")

        if not self.check_port_available(port):
            print(f"  端口 {port} 被占用，尝试释放...")
            self.kill_port_process(port)
            if not self.check_port_available(port):
                print(f"  端口 {port} 仍然被占用，请手动检查")
                return None

        cmd = f"{sys.executable} -m chainlit run frontend/app.py --watch --port {port} --host 0.0.0.0"
        process = self.run_command(cmd, capture_output=True)
        if not process:
            return None

        time.sleep(5)

        if process.poll() is None:
            print(f"Chainlit 前端已启动 (http://localhost:{port})")
        else:
            print(f"Chainlit 前端启动失败")
            print("请检查 frontend/app.py 是否存在或手动运行以下命令调试：")
            print(f"  {cmd}")
        return process

    def start_cli_interactive(self):
        print("启动交互式 CLI...")
        print("=" * 60)
        print("  注意: CLI模式将直接在前台运行")
        print("  按 Ctrl+C 可以停止")
        print("=" * 60)
        print()

        cli_script = self.project_root / "cli" / "main_cli.py"
        if not cli_script.exists():
            print(f"错误: CLI 脚本不存在: {cli_script}")
            sys.exit(1)

        cmd = [sys.executable, str(cli_script), "-i"]

        original_cwd = os.getcwd()
        try:
            os.chdir(self.project_root)
            env = os.environ.copy()
            env["PYTHONPATH"] = str(self.project_root)
            exit_code = subprocess.call(cmd, env=env)
        finally:
            os.chdir(original_cwd)

        print(f"\nCLI已退出 (退出码: {exit_code})")
        sys.exit(0)

    def check_dependencies(self):
        print("检查依赖...")
        required_packages = ["fastapi", "uvicorn", "sqlalchemy", "pydantic", "chainlit"]
        missing = []
        for package in required_packages:
            try:
                __import__(package.replace("-", "_"))
            except ImportError:
                missing.append(package)

        if missing:
            print(f"缺少依赖包: {', '.join(missing)}")
            print("请运行: pip install -r requirements.txt")
            return False
        print("依赖检查通过")
        return True

    def check_env(self):
        print("检查环境配置...")
        env_file = self.project_root / ".env"
        if not env_file.exists():
            print(".env 文件不存在")
            print("请复制 .env.example 为 .env 并配置 API 密钥")
            return False
        print("环境配置检查通过")
        return True

    def run_all(self, mode="api"):
        if sys.platform != "win32":
            signal.signal(signal.SIGINT, self.stop_all)
            signal.signal(signal.SIGTERM, self.stop_all)

        print("=" * 60)
        print("  MultiAgentDeepResearch - 服务启动器")
        print("=" * 60)
        print()

        if not self.check_dependencies():
            sys.exit(1)

        self.check_env()
        print()

        if mode == "api":
            self.start_api_server()
        elif mode == "all":
            api_proc = self.start_api_server()
            if api_proc and api_proc.poll() is None:
                print()
                self.start_chainlit_frontend()
            else:
                print()
                print("API 服务器启动失败，跳过前端启动")
        elif mode == "cli":
            self.start_cli_interactive()

        print()
        print("=" * 60)
        print("  服务运行中... 按 Ctrl+C 停止所有服务")
        print("=" * 60)

        try:
            while not self._stop_event.is_set():
                all_done = True
                for process in self.processes:
                    if process.poll() is None:
                        all_done = False
                        break
                if all_done:
                    break
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop_all()

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MultiAgentDeepResearch 服务启动器")
    parser.add_argument(
        "mode",
        choices=["api", "all", "cli"],
        default="api",
        nargs="?",
        help="启动模式: api=仅API服务, all=API+前端, cli=交互式命令行",
    )

    args = parser.parse_args()

    manager = ServiceManager()
    manager.run_all(mode=args.mode)
