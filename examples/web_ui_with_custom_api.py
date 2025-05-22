# This is an example of how to use the custom_app_setup_fn parameter to add custom API endpoints
# to the underlying FastAPI application when using WebUI.

# To run this example:
# 1. Make sure you have all necessary dependencies installed:
#    pip install qwen_agent fastapi uvicorn
# 2. Run this script from your terminal:
#    python examples/web_ui_with_custom_api.py
# 3. Open your browser and navigate to the Gradio UI (usually http://127.0.0.1:7860).
# 4. You can interact with the chatbot as usual.
# 5. To test the custom API endpoint, open a new terminal or use a tool like curl:
#    curl http://127.0.0.1:7860/my_custom_endpoint
#    You should see: {"message":"Hello from custom API!"}

from typing import Optional, Union, List, Iterator, Dict, Any
from fastapi import FastAPI

from qwen_agent.agent import Agent
from qwen_agent.gui import WebUI
from qwen_agent.llm.schema import Message


# 1. Define a simple mock agent for demonstration
class MyMockAgent(Agent):
    def __init__(self, name: str = 'MyMockAgent', description: Optional[str] = 'A mock agent for demonstration.'):
        super().__init__(name=name, description=description)

    def _run(self, messages: List[Message], cfg: Optional[dict] = None) -> Iterator[List[Message]]:
        # Simple echo agent
        response_text = "You said: "
        user_message = next((m.content for m in reversed(messages) if m.role == 'user'), None)
        if user_message and isinstance(user_message, str):
            response_text += user_message
        elif user_message and isinstance(user_message, list): # Handle multimodal messages
            text_content = next((item.text for item in user_message if item.text), None)
            if text_content:
                response_text += text_content

        yield [Message(role='assistant', content=response_text)]

    def _parse_legacy_messages(self, messages: List[Dict[str, Any]]) -> List[Message]:
        # Simplified parser for this mock agent
        parsed_messages = []
        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            parsed_messages.append(Message(role=role, content=content))
        return parsed_messages

# 2. Define the function to set up custom FastAPI routes
def setup_my_custom_routes(app: FastAPI):
    """
    This function will be called with the FastAPI app instance used by Gradio.
    You can add your custom routes, middleware, etc. here.
    """
    @app.get("/my_custom_endpoint")
    async def read_custom_endpoint():
        return {"message": "Hello from custom API!"}

    @app.get("/another_endpoint")
    async def another_endpoint():
        return {"data": [1, 2, 3], "status": "ok"}

    print("Custom FastAPI routes added: /my_custom_endpoint, /another_endpoint")


# 3. Main part of the example
if __name__ == "__main__":
    # Instantiate your agent
    agent = MyMockAgent()

    # Instantiate WebUI
    # You can also pass a list of agents: web_ui = WebUI([agent1, agent2])
    web_ui = WebUI(agent)

    # Run the WebUI, passing your custom setup function
    # The Gradio app will be served, and your custom API endpoints will also be available.
    print("Starting WebUI with custom API setup...")
    print("Gradio UI will be available at http://127.0.0.1:7860 (or another port if 7860 is busy)")
    print("Custom API endpoint will be available at http://127.0.0.1:7860/my_custom_endpoint")
    
    web_ui.run(
        custom_app_setup_fn=setup_my_custom_routes,
        server_name="0.0.0.0", # Listen on all interfaces
        # server_port=7860 # Default port
    )

    # After the server starts, you can access:
    # - The Gradio Chat UI (e.g., http://127.0.0.1:7860)
    # - Your custom endpoint (e.g., http://127.0.0.1:7860/my_custom_endpoint)
    # - Another custom endpoint (e.g., http://127.0.0.1:7860/another_endpoint)
    
    print("WebUI has been launched. Check your terminal for the URL.")
