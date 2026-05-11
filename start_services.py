#!/usr/bin/env python
import subprocess
import sys
import os
import time
import signal
from pathlib import Path

class ServiceManager:
    def __init__(self):
        self.processes = []
        self.project_root = Path(__file__).parent

    def run_command(self, cmd, cwd=None, shell=True):
        # Windows 下使用 gb18030 编码处理中文输出
        try:
            process = subprocess.Popen(
                cmd,
                cwd=cwd or self.project_root,
                shell=shell,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='gb18030',
                errors='replace'
            )
        except (ValueError, LookupError):
            # 如果 gb18030 不可用，回退到 utf-8
            process = subprocess.Popen(
                cmd,
                cwd=cwd or self.project_root,
                shell=shell,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
        self.processes.append(process)
        return process

    def stop_all(self, signum=None, frame=None):
        print("\n正在停止所有服务...")
        for process in self.processes:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
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
                for line in result.stdout.split('\n'):
                    if 'LISTENING' in line:
                        parts = line.split()
                        if len(parts) >= 5:
                            pid = parts[-1]
                            try:
                                sp.run(f"taskkill /F /PID {pid}", shell=True, capture_output=True)
                                print(f"  已释放端口 {port} (PID: {pid})")
                                time.sleep(1)
                                return True
                            except:
                                pass
        except:
            pass
        return False

    def check_port_available(self, port):
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(('0.0.0.0', port))
            sock.close()
            return True
        except:
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
        process = self.run_command(cmd)
        time.sleep(3)
        
        if process.poll() is None:
            print("API 服务器已启动 (http://localhost:8000)")
            print("  API 文档: http://localhost:8000/api/docs")
        else:
            print("API 服务器启动失败")
            stdout, stderr = process.communicate()
            if stdout:
                print(f"  错误输出: {stdout[:500]}")
        return process

    def start_chainlit_frontend(self, port=8001):
        print(f"启动 Chainlit 前端...")
        
        if not self.check_port_available(port):
            print(f"  端口 {port} 被占用，尝试释放...")
            self.kill_port_process(port)
            if not self.check_port_available(port):
                print(f"  端口 {port} 仍然被占用，请手动检查")
                return None
        
        cmd = f"{sys.executable} -m chainlit run frontend/app.py --watch --port {port} --host 0.0.0.0"
        process = self.run_command(cmd)
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
        cmd = f"{sys.executable} main_cli.py -i"
        process = self.run_command(cmd)
        return process

    def check_dependencies(self):
        print("检查依赖...")
        required_packages = ['fastapi', 'uvicorn', 'sqlalchemy', 'pydantic', 'chainlit']
        missing = []
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
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
        env_file = self.project_root / '.env'
        if not env_file.exists():
            print(".env 文件不存在")
            print("请复制 .env.example 为 .env 并配置 API 密钥")
            return False
        print("环境配置检查通过")
        return True

    def run_all(self, mode='api'):
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

        if mode == 'api':
            self.start_api_server()
        elif mode == 'all':
            api_proc = self.start_api_server()
            if api_proc and api_proc.poll() is None:
                print()
                self.start_chainlit_frontend()
            else:
                print()
                print("API 服务器启动失败，跳过前端启动")
        elif mode == 'cli':
            self.start_cli_interactive()

        print()
        print("=" * 60)
        print("  服务运行中... 按 Ctrl+C 停止所有服务")
        print("=" * 60)

        try:
            for process in self.processes:
                if process.poll() is None:
                    process.wait()
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
        help="启动模式: api=仅API服务, all=API+前端, cli=交互式命令行"
    )
    
    args = parser.parse_args()
    
    manager = ServiceManager()
    manager.run_all(mode=args.mode)
