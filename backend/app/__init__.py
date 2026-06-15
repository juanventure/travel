# Load environment variables from backend/.env for local development.
# This runs before any submodule (security, graph.agents) reads os.getenv,
# so the API keys are available at import time. override=False means real
# environment variables (e.g. those injected by docker-compose) take priority.
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), os.pardir, ".env"), override=False)
