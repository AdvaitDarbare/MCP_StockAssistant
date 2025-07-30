# backend/app/graph/synthesizer_node.py

from typing import Dict

def synthesizer_node(state: Dict) -> Dict:
    """Synthesizer combines all results into final response"""
    accumulated_results = state.get("accumulated_results", {})
    
    print(f"🔄 SYNTHESIZER - Combining results: {list(accumulated_results.keys())}")
    
    response_parts = []
    
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
    
    return {"output": final_output}