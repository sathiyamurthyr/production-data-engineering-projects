# Getting Started

Welcome to Production Data Engineering Projects! This guide will help you set up your environment and start exploring the projects.

## Prerequisites

- Python 3.13 or higher
- Docker and Docker Compose
- Git
- Make (optional)

## Installation

```bash
# Clone the repository
git clone https://github.com/sathiyamurthyr/production-data-engineering-projects.git
cd production-data-engineering-projects

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install pre-commit hooks
pre-commit install
```

## Running Your First Project

```bash
# Navigate to project
cd projects/01_python_fundamentals

# Install project dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v
```

## Project Structure

Each project follows a consistent structure for easy navigation and understanding.

## Next Steps

1. Read the [ROADMAP.md](ROADMAP.md) to understand the learning path
2. Start with [Project 01 - Python Fundamentals](projects/01_python_fundamentals/README.md)
3. Join our community discussions

---

*Detailed setup instructions will be added as projects are implemented.*