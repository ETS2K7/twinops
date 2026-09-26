"""TrueForge agent automated configuration script."""

import os
import sys
from trueforge_sdk import TrueForge
from trueforge_sdk.types.agent_spec import AgentSpec
from trueforge_sdk.types.model import Model
from trueforge_sdk.types.mcp_server import McpServer
from trueforge_sdk.types.google_gemini_model_provider import GoogleGeminiModelProvider
from trueforge_sdk.types.open_ai_model_provider import OpenAiModelProvider
from trueforge_sdk.types.model_provider_auth import ModelProviderAuth


def setup(api_key: str | None = None, provider_type: str = "gemini"):
    client = TrueForge(base_url="http://localhost:8790")

    gemini_key = api_key or os.getenv("GEMINI_API_KEY")
    openai_key = api_key or os.getenv("OPENAI_API_KEY")

    if gemini_key and (provider_type == "gemini" or "AIza" in gemini_key):
        print("Registering Google Gemini model provider...")
        client.settings.model_providers.create_or_update(
            manifest=GoogleGeminiModelProvider(
                auth=ModelProviderAuth(api_key=gemini_key)
            )
        )
        model_name = "google-gemini/gemini-3.6-flash"
    elif openai_key and (provider_type == "openai" or openai_key.startswith("sk-")):
        print("Registering OpenAI model provider...")
        client.settings.model_providers.create_or_update(
            manifest=OpenAiModelProvider(
                auth=ModelProviderAuth(api_key=openai_key)
            )
        )
        model_name = "openai/gpt-4o"
    else:
        # Check if any provider is already registered
        configured = client.settings.model_providers.list()
        if not configured.data:
            print("No model provider configured and no API key supplied.")
            return False
        # Use first available model from configured providers
        available_models = client.models.list()
        if not available_models.data:
            print("No available models found in configured providers.")
            return False
        model_name = available_models.data[0].id
        print(f"Using existing configured model: {model_name}")

    with open("agent/prompt.md") as f:
        instructions = f.read()

    print(f"Creating TwinOps agent with model '{model_name}'...")
    agent = client.agents.create(
        name="twinops",
        description="Autonomous SRE agent with digital twin sandboxing and human canary approval",
        manifest=AgentSpec(
            instructions=instructions,
            model=Model(name=model_name),
            mcp_servers=[
                McpServer(
                    name="twinops",
                    enable_tools=["@all"],
                    require_approval_for_tools=["deploy_canary_remediation"],
                )
            ],
        ),
    )
    print(f"Agent successfully created: id={agent.id}, name={agent.name}")
    return True


if __name__ == "__main__":
    key = sys.argv[1] if len(sys.argv) > 1 else None
    prov = sys.argv[2] if len(sys.argv) > 2 else "gemini"
    success = setup(api_key=key, provider_type=prov)
    sys.exit(0 if success else 1)
