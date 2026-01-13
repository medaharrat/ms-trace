"""LLM-based impact summarization."""

import logging
from typing import List, Dict, Any, Optional
import os

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class ImpactSummarizer:
    """Summarize impact using LLM."""
    
    def __init__(self, provider: str = "openai", model: str = "gpt-4", 
                 api_key: Optional[str] = None, base_url: Optional[str] = None):
        """Initialize impact summarizer.
        
        Args:
            provider: LLM provider ("openai", "anthropic", "local")
            model: Model name
            api_key: API key (if not set, uses environment variable)
            base_url: Optional base URL for API
        """
        self.provider = provider
        self.model = model
        self.api_key = api_key or os.getenv("LLM_API_KEY", "")
        self.base_url = base_url
        self.client = None
        
        if self.provider == "openai" and OPENAI_AVAILABLE:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url if self.base_url else None,
            )
    
    def summarize(self, query: str, code_references: List[Dict[str, Any]], 
                  afs_references: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate impact summary.
        
        Args:
            query: Original search query
            code_references: List of code references from Sourcegraph
            afs_references: List of AFS file references
        
        Returns:
            Dictionary with risk_level, impact_summary, and suggested_next_steps
        """
        if not self.client:
            logger.warning("LLM client not available, skipping summarization")
            return {
                "risk_level": "UNKNOWN",
                "impact_summary": "LLM summarization not available",
                "suggested_next_steps": [],
            }
        
        try:
            prompt = self._build_prompt(query, code_references, afs_references)
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert code analyst. Analyze code dependencies and provide risk assessments."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
            )
            
            summary_text = response.choices[0].message.content
            return self._parse_summary(summary_text)
        except Exception as e:
            logger.error(f"Error generating LLM summary: {e}")
            return {
                "risk_level": "UNKNOWN",
                "impact_summary": f"Error generating summary: {e}",
                "suggested_next_steps": [],
            }
    
    def _build_prompt(self, query: str, code_references: List[Dict[str, Any]], 
                     afs_references: List[Dict[str, Any]]) -> str:
        """Build prompt for LLM.
        
        Args:
            query: Original search query
            code_references: Code references
            afs_references: AFS references
        
        Returns:
            Prompt string
        """
        prompt = f"""Analyze the impact of modifying '{query}' based on the following references:

CODE REFERENCES:
"""
        for ref in code_references[:20]:  # Limit to first 20 for token efficiency
            prompt += f"- {ref.get('path', '')} in repo {ref.get('repo', '')}\n"
        
        prompt += "\nAFS FILE REFERENCES:\n"
        for ref in afs_references[:20]:
            prompt += f"- {ref.get('path', '')}\n"
        
        prompt += """
Please provide:
1. Risk level (LOW, MEDIUM, HIGH) based on the number and criticality of dependencies
2. A brief impact summary (1-2 sentences)
3. Suggested next steps (2-3 actionable items)

Format your response as:
RISK_LEVEL: <level>
IMPACT: <summary>
STEPS: <step1>; <step2>; <step3>
"""
        return prompt
    
    def _parse_summary(self, summary_text: str) -> Dict[str, Any]:
        """Parse LLM summary response.
        
        Args:
            summary_text: Raw summary text from LLM
        
        Returns:
            Parsed summary dictionary
        """
        risk_level = "UNKNOWN"
        impact_summary = summary_text
        suggested_next_steps = []
        
        lines = summary_text.split("\n")
        current_section = None
        
        for line in lines:
            if line.startswith("RISK_LEVEL:"):
                risk_level = line.replace("RISK_LEVEL:", "").strip().upper()
            elif line.startswith("IMPACT:"):
                impact_summary = line.replace("IMPACT:", "").strip()
            elif line.startswith("STEPS:"):
                steps_text = line.replace("STEPS:", "").strip()
                suggested_next_steps = [s.strip() for s in steps_text.split(";") if s.strip()]
        
        return {
            "risk_level": risk_level,
            "impact_summary": impact_summary,
            "suggested_next_steps": suggested_next_steps,
        }

