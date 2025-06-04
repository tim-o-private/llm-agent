import asyncio
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder

async def test_simple_agent():
    """Test a simple agent without tools"""
    try:
        # Get Gemini API key
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            print("Error: GEMINI_API_KEY not found")
            return
        
        print("Creating Gemini LLM...")
        # Create Google Gemini LLM
        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=gemini_api_key,
            temperature=0.7,
            convert_system_message_to_human=True
        )
        
        print("Creating prompt...")
        # Simple prompt with required agent_scratchpad
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful AI assistant. Be concise and helpful."),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        print("Testing direct LLM call...")
        # Test direct LLM call first
        response = await llm.ainvoke([("human", "Hello, how are you?")])
        print(f"Direct LLM response: {response.content}")
        
        print("Creating agent with empty tools...")
        # Create agent with empty tools list
        agent = create_tool_calling_agent(llm, [], prompt)
        
        print("Creating executor...")
        # Create executor
        agent_executor = AgentExecutor(
            agent=agent,
            tools=[],
            verbose=False,
            handle_parsing_errors=True,
            max_iterations=3
        )
        
        print("Testing agent executor...")
        # Test agent executor
        result = await agent_executor.ainvoke({"input": "Hello, how are you?"})
        print(f"Agent response: {result.get('output', 'No output')}")
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test_simple_agent()) 