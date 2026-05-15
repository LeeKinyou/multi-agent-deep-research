#!/usr/bin/env python3
"""
Environment Test Script for MultiAgent DeepResearch Project

This script tests:
1. Environment variable loading
2. LLM (LM Studio/OpenAI/DeepSeek) connectivity
3. Search tool (DuckDuckGo/Tavily) connectivity
4. Database connection (optional)
"""

import os
import sys
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_community.tools import DuckDuckGoSearchRun

def test_environment_variables():
    """Test if required environment variables are loaded"""
    print("🔍 Testing Environment Variables...")
    
    # Check for LM Studio configuration first
    lm_studio_vars = [
        'LM_STUDIO_API_BASE',
        'LM_STUDIO_API_KEY'
    ]
    
    # Check for OpenAI configuration as alternative
    openai_vars = ['OPENAI_API_KEY']
    
    lm_studio_configured = all(os.getenv(var) for var in lm_studio_vars)
    openai_configured = all(os.getenv(var) for var in openai_vars)
    
    if not lm_studio_configured and not openai_configured:
        print("❌ Neither LM Studio nor OpenAI configuration found")
        print("Please configure either LM Studio or OpenAI in your .env file")
        return False
    
    # Check search tool configuration
    search_tool = os.getenv('SEARCH_TOOL', 'duckduckgo')
    if search_tool == 'tavily' and not os.getenv('TAVILY_API_KEY'):
        print("❌ Missing TAVILY_API_KEY for Tavily search")
        return False
        
    print("✅ Required environment variables are set")
    return True

def test_llm_connection():
    """Test LLM connection using LangChain"""
    print("\n🤖 Testing LLM Connection...")
    
    try:
        # Determine which LLM to use
        if os.getenv('LM_STUDIO_API_BASE'):
            print("Using LM Studio configuration...")
            llm = ChatOpenAI(
                base_url=os.getenv('LM_STUDIO_API_BASE'),
                api_key=os.getenv('LM_STUDIO_API_KEY'),
                model_name=os.getenv('LM_STUDIO_MODEL_NAME', 'qwen3.5-9b'),
                temperature=0.1,
                max_tokens=100
            )
        elif os.getenv('OPENAI_API_KEY'):
            print("Using OpenAI configuration...")
            llm = ChatOpenAI(
                model_name=os.getenv('OPENAI_MODEL_NAME', 'gpt-4-turbo-preview'),
                temperature=0.1,
                max_tokens=100
            )
        else:
            print("❌ No valid LLM configuration found")
            return False
        
        # Test simple message
        response = llm.invoke("Hello, are you working?")
        print(f"✅ LLM Response: {response.content}...")
        return True
        
    except Exception as e:
        print(f"❌ LLM Connection Failed: {str(e)}")
        return False

def test_search_tool():
    """Test search tool connectivity"""
    print("\n🌐 Testing Search Tool...")
    
    try:
        search_tool_type = os.getenv('SEARCH_TOOL', 'duckduckgo')
        
        if search_tool_type == 'duckduckgo':
            print("Using DuckDuckGo search...")
            search = DuckDuckGoSearchRun()
            results = search.run("current date and time")
            if results:
                print(f"✅ DuckDuckGo Search returned results (length: {len(results)})")
                return True
            else:
                print("❌ DuckDuckGo Search returned no results")
                return False
                
        elif search_tool_type == 'tavily':
            from langchain_community.tools.tavily_search import TavilySearchResults
            print("Using Tavily search...")
            tavily_tool = TavilySearchResults(
                max_results=3,
                search_depth="basic"
            )
            results = tavily_tool.invoke({"query": "current date and time"})
            if results:
                print(f"✅ Tavily Search returned {len(results)} results")
                return True
            else:
                print("❌ Tavily Search returned no results")
                return False
        
        else:
            print(f"❌ Unknown search tool: {search_tool_type}")
            return False
            
    except Exception as e:
        print(f"❌ Search Tool Failed: {str(e)}")
        return False

def main():
    """Main test function"""
    print("=" * 60)
    print("MultiAgent DeepResearch - Environment Test")
    print("=" * 60)
    
    # Load environment variables
    load_dotenv()
    
    # Run all tests
    env_ok = test_environment_variables()
    llm_ok = test_llm_connection() if env_ok else False
    search_ok = test_search_tool() if env_ok else False
    
    print("\n" + "=" * 60)
    print("Test Summary:")
    print(f"Environment Variables: {'✅ PASS' if env_ok else '❌ FAIL'}")
    print(f"LLM Connection: {'✅ PASS' if llm_ok else '❌ FAIL'}")
    print(f"Search Tool: {'✅ PASS' if search_ok else '❌ FAIL'}")
    
    if env_ok and llm_ok and search_ok:
        print("\n🎉 All tests passed! Your environment is ready for development.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please check your .env file and API keys.")
        return 1

if __name__ == "__main__":
    sys.exit(main())