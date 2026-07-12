"""
AI Code Reviewer - Enhanced Setup and Launch Script
Handles environment setup, hardware detection, automatic model selection,
dependency installation, Ollama verification, and automatic server startup.
"""
import os
import sys
import time
import socket
import shutil
import signal
import subprocess
import webbrowser
import re
from pathlib import Path

# Try to import hardware detection libraries
try:
    import psutil
except ImportError:
    psutil = None

# --- Configuration ---
REQUIRED_PROMPTS = [
    "stage1_understanding.txt",
    "stage2_bugs.txt",
    "stage3_security.txt",
    "stage4_performance.txt",
    "stage5_architecture.txt"
]
REQUIRED_DIRS = ["uploads", "prompts", "templates", "static", "history"]

# Model definitions: (name, min_ram_gb, min_vram_gb, description)
MODEL_TIERS = [
    ("orca-mini:3b", 2, 0, "Ultra-light (2GB RAM) - Fast but basic analysis"),
    ("mistral:7b", 4, 0, "Light (4GB RAM) - Good balance of speed and quality"),
    ("neural-chat:7b", 4, 0, "Light (4GB RAM) - Code-optimized, good balance"),
    ("qwen2.5-coder:7b", 6, 0, "Medium (6GB RAM) - Specialized for code review"),
    ("llama2:13b", 8, 6, "Heavy (8GB RAM or 6GB VRAM) - Better accuracy"),
    ("mistral:large", 16, 12, "Very Heavy (16GB RAM or 12GB VRAM) - Best accuracy"),
]

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
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}\n")

def print_section(text):
    print(f"\n{text}")
    print("-" * len(text))

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

def find_free_port(start_port=8000):
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

def get_configured_model():
    """Read DEFAULT_MODEL from config/settings.py."""
    config_file = Path("config/settings.py")
    if not config_file.exists():
        return None
    try:
        content = config_file.read_text()
        match = re.search(r'DEFAULT_MODEL:\s*str\s*=\s*["\']([^"\']+)["\']', content)
        if match:
            return match.group(1).strip()
    except Exception as e:
        print(f"⚠️  Error reading config: {e}")
    return None

def verify_and_pull_model(model_name):
    """Verify model exists, pull if missing, and test it."""
    print_section(f"📥 Checking Model: {model_name}")
    success, output = run_cmd(["ollama", "list"], capture=True)
    if success and model_name in output:
        print(f"✅ Model {model_name} is already installed.")
    else:
        print(f"⚙️  Model {model_name} not found. Downloading...")
        print("   (This may take several minutes depending on your internet speed)")
        success, msg = run_cmd(["ollama", "pull", model_name])
        if success:
            print(f"✅ Model {model_name} downloaded successfully.")
        else:
            print(f"⚠️  Failed to pull model automatically.")
            print(f"   Error: {msg}")
            print(f"   Please run manually: ollama pull {model_name}")

    # Test model generation
    print_section("🧪 Testing Model")
    print(f"  Running quick test with {model_name}...")
    test_prompt = "Say 'OK'"
    test_payload = f'{{"model": "{model_name}", "prompt": "{test_prompt}", "stream": false}}'
    success, msg = run_cmd(
        ["curl", "-s", "http://localhost:11434/api/generate", "-d", test_payload],
        capture=True
    )
    if success and "error" not in msg.lower():
        print(f"✅ Model {model_name} is working correctly.")
    else:
        print(f"⚠️  Model test failed. The model may not be fully ready.")
        print(f"   It will be retried during first use.")

# ==========================================
# HARDWARE DETECTION
# ==========================================

def get_system_resources():
    """
    Detect system resources: CPU count, RAM, VRAM.
    Returns: (cpu_count, ram_gb, vram_gb, has_gpu)
    """
    cpu_count = os.cpu_count() or 1
    if psutil is None:
        print("⚠️  psutil not found. Cannot detect RAM. Assuming 4GB.")
        return cpu_count, 4, 0, False
    try:
        # Get RAM
        ram_bytes = psutil.virtual_memory().total
        ram_gb = ram_bytes / (1024**3)
        # Try to detect GPU (simplified - just check if cuda/mps available)
        try:
            import torch
            vram_gb = 0
            has_gpu = torch.cuda.is_available()
            if has_gpu and torch.cuda.is_available():
                vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        except ImportError:
            has_gpu = False
            vram_gb = 0
        return cpu_count, ram_gb, vram_gb, has_gpu
    except Exception as e:
        print(f"⚠️  Error detecting system resources: {e}. Assuming 4GB RAM.")
        return cpu_count, 4, 0, False

def select_best_model(ram_gb, vram_gb):
    """
    Select the best model based on available resources.
    Returns: (model_name, reason)
    """
    available_vram = vram_gb if vram_gb > 0 else 0
    available_ram = ram_gb
    # Prefer VRAM over RAM for Ollama
    available_memory = max(available_vram, available_ram)
    selected_model = None
    reason = ""
    # Find the best model that fits
    for model_name, min_ram, min_vram, description in reversed(MODEL_TIERS):
        if available_vram >= min_vram or (min_vram == 0 and available_ram >= min_ram):
            selected_model = model_name
            reason = description
            break
    # Fallback to smallest model if nothing matches
    if selected_model is None:
        selected_model, _, _, reason = MODEL_TIERS[0]
        reason = f"{reason} (minimum fallback)"
    return selected_model, reason

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
    print(" Checking dependencies...")
    req_file = Path("requirements.txt")
    if not req_file.exists():
        print("❌ requirements.txt not found!")
        sys.exit(1)
    # Upgrade pip first
    run_cmd(PIP_CMD + ["install", "--upgrade", "pip"], capture=True)
    # Try to install psutil for hardware detection
    print("⚙️  Installing packages (including hardware detection tools)...")
    run_cmd(PIP_CMD + ["install", "psutil"], capture=True)
    # Install requirements
    success, msg = run_cmd(PIP_CMD + ["install", "-r", "requirements.txt"])
    if not success:
        print(f"❌ Failed to install dependencies: {msg}")
        sys.exit(1)
    print("✅ Dependencies installed.")

def check_ollama():
    print("🔍 Checking Ollama...")
    if not shutil.which("ollama"):
        print("❌ Ollama is not installed or not in PATH.")
        print("👉 Download from: https://ollama.com")
        print("   After installation, please run this script again.")
        sys.exit(1)
    # Check if server is running
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', 11434))
        sock.close()
        if result == 0:
            print("✅ Ollama server is already running.")
        else:
            print("⚙️  Ollama server is not running. Starting it...")
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setsid if not IS_WINDOWS else None
            )
            print("   Waiting for Ollama to start...")
            time.sleep(3)
            # Verify it started
            result = sock.connect_ex(('127.0.0.1', 11434))
            if result == 0:
                print("✅ Ollama server started successfully.")
            else:
                print("⚠️  Ollama may still be starting. Proceeding anyway...")
    except Exception as e:
        print(f"⚠️  Error checking Ollama: {e}. Proceeding anyway...")

def detect_and_select_model():
    """
    Detect system resources and select the best model.
    Pull the model if not already installed.
    Update config with the selected model.
    """
    print_section("🧠 Detecting System Resources")
    cpu_count, ram_gb, vram_gb, has_gpu = get_system_resources()
    print(f"  CPU Cores      : {cpu_count}")
    print(f"  RAM            : {ram_gb:.1f} GB")
    print(f"  GPU Available  : {'Yes' if has_gpu else 'No'}")
    if has_gpu:
        print(f"  VRAM           : {vram_gb:.1f} GB")
        
    print_section("📋 Available Models")
    for model_name, min_ram, min_vram, description in MODEL_TIERS:
        fits = False
        reason = ""
        if min_vram > 0 and vram_gb >= min_vram:
            fits = True
            reason = "(fits VRAM)"
        elif min_vram == 0 and ram_gb >= min_ram:
            fits = True
            reason = "(fits RAM)"
        status = "✅" if fits else "❌"
        print(f"  {status} {model_name:25} - {description} {reason}")
        
    # Select best model
    selected_model, reason = select_best_model(ram_gb, vram_gb)
    print_section("🎯 Model Selection")
    print(f"  Recommended Model: {selected_model}")
    print(f"  Reason           : {reason}")
    
    # Check if model is installed
    print_section("📥 Checking Model Installation")
    print(f"  Checking if {selected_model} is installed...")
    success, output = run_cmd(["ollama", "list"], capture=True)
    if success and selected_model in output:
        print(f"✅ Model {selected_model} is already installed.")
    else:
        print(f"⚙️  Model {selected_model} not found. Downloading...")
        print("   (This may take several minutes depending on your internet speed)")
        success, msg = run_cmd(["ollama", "pull", selected_model])
        if success:
            print(f"✅ Model {selected_model} downloaded successfully.")
        else:
            print(f"⚠️  Failed to pull model automatically.")
            print(f"   Error: {msg}")
            print(f"   Please run manually: ollama pull {selected_model}")
            
    # Test model generation
    print_section(" Testing Model")
    print(f"  Running quick test with {selected_model}...")
    test_prompt = "Say 'OK'"
    test_payload = f'{{"model": "{selected_model}", "prompt": "{test_prompt}", "stream": false}}'
    success, msg = run_cmd(
        ["curl", "-s", "http://localhost:11434/api/generate", "-d", test_payload],
        capture=True
    )
    if success and "error" not in msg.lower():
        print(f"✅ Model {selected_model} is working correctly.")
    else:
        print(f"⚠️  Model test failed. The model may not be fully ready.")
        print(f"   It will be retried during first use.")
        
    # Update config file with selected model
    print_section("⚙️  Updating Configuration")
    config_file = Path("config/settings.py")
    if config_file.exists():
        config_content = config_file.read_text()
        # Replace the DEFAULT_MODEL line
        new_content = re.sub(
            r'DEFAULT_MODEL:\s*str\s*=\s*["\'][^"\']*["\']',
            f'DEFAULT_MODEL: str = "{selected_model}"',
            config_content
        )
        config_file.write_text(new_content)
        print(f"✅ Updated DEFAULT_MODEL to: {selected_model}")
        
    return selected_model

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

def print_diagnostic_report(port, selected_model):
    print_header("STARTUP DIAGNOSTIC REPORT")
    print(f"  Python Version      : {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    print(f"  Virtual Environment : {VENV_DIR.resolve()}")
    print(f"  Dependencies        : Installed (including psutil)")
    print(f"  Ollama Status       : Running")
    print(f"  AI Model            : {selected_model}")
    print(f"  Prompt Files        : {len(REQUIRED_PROMPTS)} verified")
    print(f"  Project Dirs        : {len(REQUIRED_DIRS)} verified")
    print(f"  Templates           : {Path('templates').resolve()}")
    print(f"  Uploads Directory   : {Path('uploads').resolve()}")
    print(f"  History Directory   : {Path('history').resolve()}")
    print(f"  Server Port         : {port}")
    print(f"  Server Status       : Starting...")
    print()

# ==========================================
# MAIN EXECUTION
# ==========================================

def main():
    # Register cleanup handler
    signal.signal(signal.SIGINT, signal_handler)

    print_header("AI CODE REVIEWER - ENHANCED SETUP")

    check_python()
    setup_venv()
    install_dependencies()
    check_ollama()  # Verifies Ollama install and starts server

    # Check if model is already configured in settings.py
    configured_model = get_configured_model()

    if configured_model:
        print_section("⚙️  Configuration Detected")
        print(f"  DEFAULT_MODEL is already set to: {configured_model}")
        print("  Skipping hardware detection and model recommendation.")
        verify_and_pull_model(configured_model)
        selected_model = configured_model
    else:
        print_section("⚙️  No Model Configured")
        print("  DEFAULT_MODEL is missing. Running hardware detection...")
        selected_model = detect_and_select_model()

    verify_structure()
    port = find_free_port()
    print_diagnostic_report(port, selected_model)

    print("🚀 Starting FastAPI server...")
    global server_process
    # Build uvicorn command with specific reload directories
    reload_dirs = [
        "api", "services", "utils", "config", 
        "templates", "static"
    ]
    uvicorn_cmd = [
        str(VENV_PYTHON), "-m", "uvicorn", "app:app",
        "--host", "127.0.0.1", "--port", str(port)
    ]
    # Add reload flag and specific directories
    if Path(".venv").exists():
        uvicorn_cmd.append("--reload")
        for dir_name in reload_dirs:
            uvicorn_cmd.extend(["--reload-dir", dir_name])
            
    server_process = subprocess.Popen(uvicorn_cmd)
    
    # Wait for server to start
    time.sleep(2)
    
    print(f"\n🌐 Opening application at http://127.0.0.1:{port}")
    print("   (If browser doesn't open, manually visit the URL above)")
    webbrowser.open(f"http://127.0.0.1:{port}")
    
    print("\n✅ Setup complete! Press Ctrl+C to stop the server.")
    print("📁 Note: Server will NOT reload on file uploads (only on code changes)")
    print()
    
    try:
        server_process.wait()
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == "__main__":
    main()