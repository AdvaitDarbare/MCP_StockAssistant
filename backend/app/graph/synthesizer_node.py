# backend/app/graph/synthesizer_node.py

from typing import Dict
from anthropic import AsyncAnthropic
import os
import asyncio

anthropic = AsyncAnthropic(api_key=os.getenv("CLAUDE_API_KEY"))

async def generate_dynamic_suggestions(user_input: str, agents_used: list, results: dict) -> str:
    """Generate dynamic suggestions based on user query and available tools"""
    
    # All available tools across agents
    available_tools = {
        'stock_tools': {
            'get_stock_data': 'Get current stock price and quote',
            'get_multiple_quotes': 'Compare multiple stocks side-by-side',
            'get_price_history': 'Get historical price performance over time periods',
            'get_market_movers': 'Get top gainers, losers, or most active stocks',
            'get_market_hours': 'Get trading schedules and market status'
        },
        'equity_tools': {
            'get_company_overview': 'Get company information, sectors, and exchange details',
            'get_analyst_ratings': 'Get analyst recommendations and price targets',
            'get_company_news': 'Get recent news articles and press releases',
            'get_insider_trading': 'Get insider buy/sell activity and transactions'
        }
    }
    
    # Extract symbols from results if possible
    symbols = []
    if "stock" in results:
        stock_content = results["stock"]
        # Extract symbols from stock results (simple pattern matching)
        import re
        symbol_matches = re.findall(r'\b[A-Z]{1,5}\b', stock_content)
        symbols = [s for s in symbol_matches if len(s) <= 5][:3]  # Limit to 3 symbols
    
    primary_symbol = symbols[0] if symbols else "AAPL"
    
    # Determine what hasn't been covered yet
    unused_suggestions = []
    
    # Stock suggestions if stock agent wasn't used or limited use
    if "stock" not in agents_used:
        unused_suggestions.extend([
            f"What's {primary_symbol} current stock price?",
            f"Compare {primary_symbol} vs GOOGL vs MSFT",
            f"Show me 6 month price history for {primary_symbol}",
            "What are market hours today?"
        ])
    elif symbols:
        # Add complementary stock suggestions
        unused_suggestions.extend([
            f"Compare {primary_symbol} with other stocks",
            f"Historical performance of {primary_symbol}",
            "Top market gainers today"
        ])
    
    # Equity suggestions if equity agent wasn't used
    if "equity_insights" not in agents_used and symbols:
        unused_suggestions.extend([
            f"Tell me about {primary_symbol} company",
            f"Recent news for {primary_symbol}",
            f"Analyst ratings for {primary_symbol}",
            f"Insider trading activity for {primary_symbol}"
        ])
    elif symbols:
        # Add complementary equity suggestions
        unused_suggestions.extend([
            f"Company overview of {primary_symbol}",
            f"Latest news about {primary_symbol}"
        ])
    
    # Add general market suggestions
    if not symbols:
        unused_suggestions.extend([
            "Top market gainers today",
            "What are market hours?",
            "Compare AAPL vs GOOGL vs MSFT",
            "Recent news for Tesla"
        ])
    
    # Use LLM to refine and select best suggestions
    try:
        validation_prompt = f"""Given this user query: "{user_input}"
And agents used: {agents_used}
For symbols found: {symbols or ['general market']}

From these potential follow-up suggestions:
{chr(10).join([f"- {s}" for s in unused_suggestions[:8]])}

Select and refine the 3-4 MOST relevant, natural follow-up questions that:
1. Complement what was already shown
2. Are directly answerable by our available tools
3. Sound natural and conversational
4. Provide additional value to the user

Available tools include:
- Stock prices, comparisons, historical data, market movers, trading hours
- Company overviews, analyst ratings, news, insider trading

Return ONLY a numbered list with emojis, like:
1. 📊 Compare {primary_symbol} vs GOOGL vs MSFT  
2. 📰 Recent news for {primary_symbol}
3. 🕐 What are market hours today?
4. 🏢 Tell me about {primary_symbol} company"""

        response = await anthropic.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=200,
            temperature=0.3,
            messages=[{"role": "user", "content": validation_prompt}]
        )
        
        llm_suggestions = response.content[0].text.strip()
        
        # Validate that LLM returned a proper numbered list
        if any(char.isdigit() and '. ' in llm_suggestions for char in llm_suggestions):
            return f"\n\n__FOLLOW_UPS_START__\n{llm_suggestions}\n__FOLLOW_UPS_END__"
            
    except Exception as e:
        print(f"⚠️ Dynamic suggestion LLM failed: {e}")
    
    # Fallback to simple suggestions
    if unused_suggestions:
        formatted_suggestions = []
        for i, suggestion in enumerate(unused_suggestions[:4], 1):
            # Add appropriate emoji based on content
            if 'price' in suggestion.lower() and 'history' not in suggestion.lower():
                emoji = "📈"
            elif 'compare' in suggestion.lower():
                emoji = "📊"
            elif 'history' in suggestion.lower():
                emoji = "📉"
            elif 'news' in suggestion.lower():
                emoji = "📰"
            elif 'hours' in suggestion.lower():
                emoji = "🕐"
            elif 'company' in suggestion.lower() or 'about' in suggestion.lower():
                emoji = "🏢"
            elif 'analyst' in suggestion.lower():
                emoji = "📊"
            elif 'insider' in suggestion.lower():
                emoji = "👥"
            elif 'gainers' in suggestion.lower() or 'movers' in suggestion.lower():
                emoji = "🚀"
            else:
                emoji = "🔍"
            
            formatted_suggestions.append(f"{i}. {emoji} {suggestion}")
        
        suggestions_text = "\n".join(formatted_suggestions)
        return f"\n\n__FOLLOW_UPS_START__\n{suggestions_text}\n__FOLLOW_UPS_END__"
    
    return ""

async def synthesizer_node(state: Dict) -> Dict:
    """Synthesizer combines all results into final response with dynamic suggestions"""
    accumulated_results = state.get("accumulated_results", {})
    user_input = state.get("input", "")
    
    print(f"🔄 SYNTHESIZER - Combining results: {list(accumulated_results.keys())}")
    
    response_parts = []
    
    # Add advisor recommendation if available (priority)
    advisor_has_followups = False
    advisor_followups = ""
    if "advisor" in accumulated_results:
        advisor_content = accumulated_results["advisor"]
        response_parts.append("🎯 **Investment Advice:**")
        
        # Check if advisor already has follow-ups
        if "__FOLLOW_UPS_START__" in advisor_content:
            # Extract the main content and follow-ups separately
            parts = advisor_content.split("__FOLLOW_UPS_START__")
            main_content = parts[0].strip()
            followups_part = "__FOLLOW_UPS_START__" + parts[1] if len(parts) > 1 else ""
            
            response_parts.append(main_content)
            advisor_has_followups = True
            advisor_followups = followups_part
        else:
            response_parts.append(advisor_content)
        
        response_parts.append("")
    
    # Add stock data if available
    if "stock" in accumulated_results:
        response_parts.append("📈 **Stock Information:**")
        response_parts.append(accumulated_results["stock"])
        response_parts.append("")
    
    # Add equity insights if available  
    if "equity_insights" in accumulated_results:
        response_parts.append("🏢 **Company Insights:**")
        response_parts.append(accumulated_results["equity_insights"])
        response_parts.append("")
    
    # Fallback - use first result if available
    if not response_parts and accumulated_results:
        first_result = next(iter(accumulated_results.values()))
        response_parts.append(first_result)
    
    final_output = "\n".join(response_parts).strip() if response_parts else "❌ No results available."
    
    # Generate dynamic suggestions based on what was used and user query
    agents_used = list(accumulated_results.keys())
    
    # Only generate suggestions if advisor didn't already provide them
    if advisor_has_followups:
        # Use the advisor's follow-ups
        final_output += advisor_followups
    else:
        # Run async suggestion generation
        try:
            suggestions = await generate_dynamic_suggestions(user_input, agents_used, accumulated_results)
            final_output += suggestions
        except Exception as e:
            print(f"⚠️ Failed to generate dynamic suggestions: {e}")
            # Continue without suggestions
    
    return {"output": final_output}