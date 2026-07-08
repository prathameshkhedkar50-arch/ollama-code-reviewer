"""
AI Code Reviewer - Setup and Launch Script
Handles environment setup, dependency installation, Ollama verification, 
and automatic server startup.
"""
import os
import sys
import time
import socket
import shutil
import signal
import subprocess
import webbrowser
from pathlib import Path

# --- Configuration ---
REQUIRED_MODEL = "qwen2.5-coder:7b"
DEFAULT_PORT = 8000
REQUIRED_PROMPTS = [
    "stage1_understanding.txt",
    "stage2_bugs.txt",
    "stage3_security.txt",
    "stage4_performance.txt",
    "stage5_architecture.txt"
]
REQUIRED_DIRS = ["uploads", "prompts", "templates", "static"]

# Determine paths based on OS
IS_WINDOWS = sys.platform.startswith("win")
VENV_DIR = Path(".venv")
VENV_PYTHON = VENV_DIR / ("Scripts/python.exe" if IS_WINDOWS else "bin/python")
PIP_CMD = [str(VENV_PYTHON), "-m", "pip"]

# Global process handle for cleanup
server_process = None

# ==========================================
# UTILITY FUNCTIONS
# ==========================================

def print_header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")

def run_cmd(cmd, capture=False, shell=False):
    """Run a shell command and return the result."""
    try:
        result = subprocess.run(
            cmd, capture_output=capture, text=True, shell=shell, 
            timeout=120
        )
        return result.returncode == 0, result.stdout or result.stderr
    except Exception as e:
        return False, str(e)

def find_free_port(start_port=DEFAULT_PORT):
    """Find a free port starting from start_port."""
    port = start_port
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                port += 1

def cleanup_temp_files():
    """Remove __pycache__ and .pyc files."""
    print("🧹 Cleaning up temporary files...")
    for root, dirs, files in os.walk("."):
        if "__pycache__" in dirs:
            shutil.rmtree(os.path.join(root, "__pycache__"), ignore_errors=True)
        for file in files:
            if file.endswith(".pyc"):
                try:
                    os.remove(os.path.join(root, file))
                except OSError:
                    pass
    print("✅ Cleanup complete.")

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    print("\n\n🛑 Shutting down server...")
    if server_process:
        server_process.terminate()
    cleanup_temp_files()
    sys.exit(0)

# ==========================================
# SETUP STEPS
# ==========================================

def check_python():
    print("🐍 Checking Python version...")
    if sys.version_info < (3, 10):
        print(f"❌ Python 3.10+ required. Found: {sys.version_info.major}.{sys.version_info.minor}")
        sys.exit(1)
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro} detected.")

def setup_venv():
    print("📦 Checking virtual environment...")
    if not VENV_DIR.exists():
        print("⚙️  Creating virtual environment...")
        success, msg = run_cmd([sys.executable, "-m", "venv", ".venv"])
        if not success:
            print(f"❌ Failed to create venv: {msg}")
            sys.exit(1)
    print(f"✅ Virtual environment ready at {VENV_DIR}")

def install_dependencies():
    print("📥 Checking dependencies...")
    req_file = Path("requirements.txt")
    if not req_file.exists():
        print("❌ requirements.txt not found!")
        sys.exit(1)
    
    # Upgrade pip first
    run_cmd(PIP_CMD + ["install", "--upgrade", "pip"], capture=True)
    
    # Install requirements
    print("️  Installing packages...")
    success, msg = run_cmd(PIP_CMD + ["install", "-r", "requirements.txt"])
    if not success:
        print(f"❌ Failed to install dependencies: {msg}")
        sys.exit(1)
    print("✅ Dependencies installed.")

def check_ollama():
    print(" Checking Ollama...")
    if not shutil.which("ollama"):
        print("❌ Ollama is not installed or not in PATH.")
        print("👉 Download from: https://ollama.com")
        sys.exit(1)
    
    # Check if server is running
    success, _ = run_cmd(["curl", "-s", "http://localhost:11434"], capture=True)
    if not success:
        print("⚙️  Ollama server is not running. Starting it...")
        # Start ollama serve in background
        subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(3) # Wait for it to start
        
    print("✅ Ollama is running.")

def check_model():
    print(f"🧠 Checking model: {REQUIRED_MODEL}...")
    success, output = run_cmd(["ollama", "list"], capture=True)
    if not success or REQUIRED_MODEL not in output:
        print(f"️  Model not found. Pulling {REQUIRED_MODEL}...")
        print("   (This may take a while depending on your internet speed)")
        success, _ = run_cmd(["ollama", "pull", REQUIRED_MODEL])
        if not success:
            print(f"❌ Failed to pull model.")
            sys.exit(1)
    
    # Test generation
    print("⚙️  Running quick test generation...")
    test_payload = f'{{"model": "{REQUIRED_MODEL}", "prompt": "Say OK", "stream": false}}'
    success, _ = run_cmd(
        ["curl", "-s", "http://localhost:11434/api/generate", "-d", test_payload], 
        capture=True
    )
    if success:
        print(f"✅ Model {REQUIRED_MODEL} is ready and working.")
    else:
        print("⚠️  Model exists but test generation failed. Proceeding anyway...")

def verify_structure():
    print("📁 Verifying project structure...")
    missing = []
    
    for d in REQUIRED_DIRS:
        if not Path(d).exists():
            Path(d).mkdir(parents=True, exist_ok=True)
            print(f"   Created missing directory: {d}")
            
    for p in REQUIRED_PROMPTS:
        if not Path(f"prompts/{p}").exists():
            missing.append(p)
            
    if missing:
        print(f"❌ Missing prompt files: {', '.join(missing)}")
        sys.exit(1)
        
    print("✅ Project structure verified.")

def print_diagnostic_report(port):
    print_header("STARTUP DIAGNOSTIC REPORT")
    print(f"  Python Version      : {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    print(f"  Virtual Environment : {VENV_DIR.resolve()}")
    print(f"  Dependencies        : Installed")
    print(f"  Ollama Status       : Running")
    print(f"  AI Model            : {REQUIRED_MODEL}")
    print(f"  Prompt Files        : {len(REQUIRED_PROMPTS)} verified")
    print(f"  Templates           : {Path('templates').resolve()}")
    print(f"  Uploads Directory   : {Path('uploads').resolve()}")
    print(f"  Server Port         : {port}")
    print(f"  Server Status       : Starting...")
    print()

# ==========================================
# MAIN EXECUTION
# ==========================================

def main():
    # Register cleanup handler
    signal.signal(signal.SIGINT, signal_handler)
    
    print_header("AI CODE REVIEWER - SETUP")
    
    check_python()
    setup_venv()
    install_dependencies()
    check_ollama()
    check_model()
    verify_structure()
    
    port = find_free_port()
    print_diagnostic_report(port)
    
    print("🚀 Starting FastAPI server...")
    global server_process
    
    # ✅ FIXED: Use specific reload directories to prevent uploads from triggering reload
    reload_dirs = [
        "api", "services", "utils", "config", 
        "templates", "static"
    ]
    
    # Build uvicorn command with specific reload directories
    uvicorn_cmd = [
        str(VENV_PYTHON), "-m", "uvicorn", "app:app",
        "--host", "127.0.0.1", "--port", str(port)
    ]
    
    # Add reload flag and specific directories
    if Path(".venv").exists():  # Only reload in dev mode
        uvicorn_cmd.append("--reload")
        for dir_name in reload_dirs:
            uvicorn_cmd.extend(["--reload-dir", dir_name])
    
    server_process = subprocess.Popen(uvicorn_cmd)
    
    # Wait a moment for server to start
    time.sleep(2)
    
    print(f"🌐 Opening browser at http://127.0.0.1:{port}")
    webbrowser.open(f"http://127.0.0.1:{port}")
    
    print("\n✅ Setup complete! Press Ctrl+C to stop the server.")
    print("📁 Note: Server will NOT reload on file uploads (only on code changes)")
    
    try:
        server_process.wait()
    except KeyboardInterrupt:
        signal_handler(None, None)
        
if __name__ == "__main__":
    main()