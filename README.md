# AI Code Reviewer

An AI-powered code review application built with **FastAPI** and **Ollama** that performs intelligent multi-stage source code analysis using locally hosted Large Language Models (LLMs).

Instead of sending source code to cloud AI services, the application performs code review completely offline using Ollama, providing better privacy, lower operating costs, and faster local analysis.

> 🚧 Project Status: Work in Progress

---

# 🚀 Project Overview

AI Code Reviewer is designed to help developers analyze source code using AI before submitting it for review.

Users can upload source code files through a web interface, and the application performs a structured multi-stage review using locally running Ollama models.

The project focuses on identifying bugs, security vulnerabilities, performance issues, architectural improvements, and overall code quality while keeping all processing on the developer's machine.

---

# 🎯 Project Purpose

The purpose of this project is to demonstrate how locally hosted Large Language Models can assist software developers during the code review process.

Instead of relying on cloud-based AI services, the application integrates Ollama with FastAPI to provide an offline, privacy-friendly, and extensible code review platform.

The project demonstrates practical implementation of:

- Local AI inference
- FastAPI backend development
- AI-assisted software engineering
- Prompt engineering
- Multi-stage code analysis
- File processing
- Modular application architecture

---

# ✨ Features

## AI Code Review

- Upload source code files
- Automatic language detection
- Local AI-powered code analysis
- Five-stage review pipeline
- Detailed review reports
- Structured AI responses

## Multi-Stage Analysis

The review process analyzes uploaded code through five dedicated stages:

1. Code Understanding
2. Bug Detection
3. Security Analysis
4. Performance Review
5. Architecture Review

Each stage uses its own specialized prompt to provide focused feedback.

---

# 🤖 Ollama Integration

The application uses **Ollama** to perform AI-powered code reviews entirely on the local machine.

Instead of depending on cloud-based AI services, the application integrates with the locally running Ollama server, ensuring that uploaded source code never leaves the user's computer.

Key benefits include:

- Local AI execution
- Privacy-focused code analysis
- Offline support
- No external API dependency
- Lower operational costs
- Flexible model management

The application is designed so that different Ollama models can be used without changing the overall review workflow.

---

# ⚙️ Smart Setup Utility

The project includes an intelligent setup utility (`setup.py`) that automates the complete development environment configuration.

Instead of requiring developers to manually install dependencies, configure AI models, or prepare the application environment, the setup utility performs these tasks automatically.

## What the Setup Utility Does

The setup utility performs the following operations:

- Verifies the installed Python version.
- Creates a virtual environment if one does not already exist.
- Installs all required project dependencies.
- Checks whether Ollama is installed.
- Starts the Ollama server if it is not already running.
- Analyzes the system configuration and available resources.
- Detects a compatible Ollama model for the current machine.
- Automatically downloads and configures the selected model if it is not already available.
- Sets the detected model as the application's default AI model.
- Verifies all required project directories and prompt files.
- Detects an available server port automatically.
- Displays a setup summary and diagnostic information.
- Starts the FastAPI application.
- Opens the application automatically in the default web browser.

No manual model selection or configuration is required.

---

# 🚀 Running the Project

Simply execute:

```bash
python setup.py
```

The setup utility automatically:

1. Configures the development environment.
2. Installs project dependencies.
3. Verifies the Ollama installation.
4. Detects the most suitable AI model for the current system.
5. Downloads the model if required.
6. Configures the detected model as the default reviewer.
7. Starts the FastAPI server.
8. Opens the application in the browser.

The entire initialization process is automated, allowing developers to start using the application with minimal manual configuration.   

# 📂 Project Structure

```
ai-code-reviewer/

api/
config/
services/
utils/
templates/
static/
prompts/
uploads/

setup.py
app.py
requirements.txt
README.md
```

---

# 🛠 Technologies Used

## Backend

- Python
- FastAPI
- Uvicorn

## AI

- Ollama
- qwen2.5-coder:7b
- Prompt Engineering

## Frontend

- HTML
- CSS
- JavaScript

---

# 📚 Skills Demonstrated

- FastAPI
- AI Integration
- Ollama
- Local LLM Deployment
- Prompt Engineering
- Software Architecture
- File Processing
- REST APIs
- Python Development
- AI-assisted Code Review

---

# 🔮 Future Improvements

- Repository-level code review
- Git integration
- Pull request review
- Multiple AI model support
- Review history
- Export reports
- Team collaboration
- Code quality metrics
- Docker deployment

---

# 📜 License

MIT License

---

# 👨‍💻 Author

**Prathamesh Khedkar**

---

⭐ This project is currently under active development with additional AI-powered review capabilities planned.