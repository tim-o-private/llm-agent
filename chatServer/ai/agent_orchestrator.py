# Agent orchestrator for Clarity v2
# Orchestrates AI agents using router-proxied tools and existing agent_loader_db system

import logging
from typing import Dict, Any, Optional, List
import asyncio
from datetime import datetime
import time

from chat_types.chat import ChatResponse, AgentAction
from ai.tool_registry import ToolRegistry

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class AgentOrchestrator:
    """
    Orchestrates AI agents using router-proxied tools
    
    This orchestrator:
    1. Uses existing agent_loader_db system for agent loading
    2. Integrates router-proxied tools via ToolRegistry
    3. Manages agent execution and response formatting
    4. Handles errors gracefully with fallback responses
    """
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.tool_registry = ToolRegistry(user_id)
        self._agent_cache = {}  # Simple agent caching
        
    async def process_message(
        self,
        message: str,
        session_id: str,
        agent_name: str = "assistant",
        context: Optional[Dict[str, Any]] = None
    ) -> ChatResponse:
        """
        Process a message through AI agent with router-proxied tools
        
        Args:
            message: User message to process
            session_id: Chat session ID for memory
            agent_name: Name of agent to use
            context: Additional context for processing
            
        Returns:
            ChatResponse with AI response and actions
        """
        
        logger.info(f"Processing message for user {self.user_id}, agent {agent_name}")
        
        try:
            # Get or create agent executor
            agent_executor = await self._get_agent_executor(agent_name, session_id)
            
            # Prepare input for agent - include chat_history for prompt compatibility
            agent_input = {
                "input": message,
                "chat_history": []  # Empty chat history for fallback agent
            }
            
            # Execute agent
            logger.debug(f"Executing agent {agent_name} with input: {message[:100]}...")
            start_time = time.time()
            result = await agent_executor.ainvoke(agent_input)
            end_time = time.time()
            
            # Extract response and actions
            response_message = result.get('output', 'I processed your request.')
            actions = self._extract_actions_from_result(result)
            
            logger.info(f"Agent {agent_name} completed successfully with {len(actions)} actions in {end_time - start_time:.2f} seconds")
            
            return ChatResponse(
                message=response_message,
                actions=actions,
                metadata={
                    "agent_name": agent_name,
                    "session_id": session_id,
                    "user_id": self.user_id,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "success": True
                }
            )
            
        except Exception as e:
            logger.error(f"Agent orchestration failed for user {self.user_id}: {e}", exc_info=True)
            
            # Return error response
            return ChatResponse(
                message=f"I apologize, but I encountered an error processing your request. Please try again or contact support if the issue persists.",
                actions=[
                    AgentAction(
                        type="error",
                        data={"error_message": str(e)},
                        status="failed"
                    )
                ],
                metadata={
                    "agent_name": agent_name,
                    "session_id": session_id,
                    "user_id": self.user_id,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "success": False,
                    "error": str(e)
                }
            )
    
    async def _get_agent_executor(self, agent_name: str, session_id: str):
        """
        Get or create agent executor using existing agent_loader_db system
        
        This method integrates with the existing database-driven agent loading
        system while ensuring router-proxied tools are used.
        """
        
        cache_key = f"{agent_name}:{session_id}"
        
        # Check cache first
        if cache_key in self._agent_cache:
            logger.debug(f"Using cached agent executor for {cache_key}")
            return self._agent_cache[cache_key]
        
        logger.debug(f"Loading agent executor for {agent_name} (session: {session_id})")
        load_start = time.time()
        
        try:
            # Use existing agent_loader_db system
            from src.core.agent_loader_db import load_agent_executor_db
            
            logger.debug(f"Attempting to load agent from database...")
            
            # Load agent with router-proxied tools
            agent_executor = load_agent_executor_db(
                agent_name=agent_name,
                user_id=self.user_id,
                session_id=session_id,
                use_cache=True  # Use tool caching for better performance
            )
            
            # Cache the executor
            self._agent_cache[cache_key] = agent_executor
            
            load_time = time.time() - load_start
            logger.info(f"Successfully loaded agent executor for {agent_name} in {load_time:.2f}s")
            return agent_executor
            
        except Exception as e:
            load_time = time.time() - load_start
            logger.error(f"Failed to load agent executor for {agent_name} after {load_time:.2f}s: {e}")
            
            # Fallback: create a simple agent if database loading fails
            logger.debug(f"Creating fallback agent...")
            fallback_start = time.time()
            fallback_agent = await self._create_fallback_agent(agent_name, session_id)
            fallback_time = time.time() - fallback_start
            logger.info(f"Created fallback agent in {fallback_time:.2f}s")
            return fallback_agent
    
    async def _create_fallback_agent(self, agent_name: str, session_id: str):
        """
        Create a fallback agent when database loading fails
        
        This ensures the system remains functional even if there are
        configuration issues with the database-driven agent system.
        """
        
        logger.warning(f"Creating fallback agent for {agent_name}")
        
        try:
            logger.debug(f"Importing LangChain components...")
            import_start = time.time()
            
            from langchain_google_genai import ChatGoogleGenerativeAI
            from langchain.agents import create_tool_calling_agent, AgentExecutor
            from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
            from langchain.memory import ConversationBufferWindowMemory
            from langchain_postgres import PostgresChatMessageHistory
            import os
            
            import_time = time.time() - import_start
            logger.debug(f"Imports completed in {import_time:.2f}s")
            
            # Get Google API key
            logger.debug(f"Getting API key...")
            gemini_api_key = os.getenv("GEMINI_API_KEY")
            if not gemini_api_key:
                raise ValueError("GEMINI_API_KEY not found in environment variables")
            
            # Create Google Gemini LLM (following the original pattern)
            logger.debug(f"Creating Gemini LLM...")
            llm_start = time.time()
            
            llm = ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                google_api_key=gemini_api_key,
                temperature=0.7,
                convert_system_message_to_human=True  # Required for Gemini
            )
            
            llm_time = time.time() - llm_start
            logger.debug(f"LLM created in {llm_time:.2f}s")
            
            # Create prompt with memory support
            logger.debug(f"Creating prompt...")
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are a helpful AI assistant. Be concise and helpful."),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ])
            
            # Get basic tools from registry
            logger.debug(f"Getting tools from registry...")
            tools_start = time.time()
            
            tools = await self.tool_registry.get_basic_tools()
            
            tools_time = time.time() - tools_start
            logger.debug(f"Got {len(tools)} tools in {tools_time:.2f}s")
            
            # Create agent
            logger.debug(f"Creating agent...")
            agent_start = time.time()
            
            agent = create_tool_calling_agent(llm, tools, prompt)
            
            agent_time = time.time() - agent_start
            logger.debug(f"Agent created in {agent_time:.2f}s")
            
            # Create executor with memory (simplified for fallback)
            logger.debug(f"Creating executor...")
            executor_start = time.time()
            
            agent_executor = AgentExecutor(
                agent=agent,
                tools=tools,
                verbose=False,
                handle_parsing_errors=True,
                max_iterations=10
            )
            
            executor_time = time.time() - executor_start
            logger.debug(f"Executor created in {executor_time:.2f}s")
            
            logger.info(f"Created fallback agent for {agent_name}")
            return agent_executor
            
        except Exception as e:
            logger.error(f"Failed to create fallback agent: {e}", exc_info=True)
            raise RuntimeError(f"Could not create any agent for {agent_name}")
    
    def _extract_actions_from_result(self, result: Dict[str, Any]) -> List[AgentAction]:
        """
        Extract actions from agent execution result
        
        This method parses the agent result and converts tool calls
        into structured AgentAction objects for the frontend.
        """
        
        actions = []
        
        try:
            # Check for intermediate steps (tool calls)
            intermediate_steps = result.get('intermediate_steps', [])
            
            for step in intermediate_steps:
                if len(step) >= 2:
                    action, observation = step[0], step[1]
                    
                    # Create AgentAction from tool call
                    agent_action = AgentAction(
                        type=f"tool_{action.tool}",
                        data={
                            "tool_name": action.tool,
                            "tool_input": action.tool_input,
                            "observation": str(observation)[:500]  # Limit observation length
                        },
                        status="completed" if observation else "failed"
                    )
                    
                    actions.append(agent_action)
            
            # If no intermediate steps, check for other action indicators
            if not actions and result.get('output'):
                actions.append(AgentAction(
                    type="response",
                    data={"message": result['output']},
                    status="completed"
                ))
                
        except Exception as e:
            logger.error(f"Error extracting actions from result: {e}")
            
            # Fallback action
            actions.append(AgentAction(
                type="processing",
                data={"message": "Processed request"},
                status="completed"
            ))
        
        return actions
    
    async def get_available_agents(self) -> List[str]:
        """Get list of available agents for this user"""
        
        try:
            # Query database for available agents
            # This could be enhanced to check user permissions, etc.
            return ["assistant", "email_digest_agent", "task_agent"]
            
        except Exception as e:
            logger.error(f"Error getting available agents: {e}")
            return ["assistant"]  # Fallback
    
    def clear_cache(self):
        """Clear agent cache"""
        self._agent_cache.clear()
        logger.info(f"Cleared agent cache for user {self.user_id}") 