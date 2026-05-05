import requests
import json
import re

class PriorityScorer:
    def __init__(self):
        self.keywords = {
            5: ["chest pain", "heart attack", "stroke", "unconscious", "not breathing", "severe bleeding", "anaphylaxis", "seizure", "cardiac arrest"],
            4: ["high fever", "difficulty breathing", "severe pain", "broken bone", "deep cut", "fainting", "severe headache", "vomiting blood"],
            3: ["fever", "infection", "moderate pain", "dizziness", "nausea", "persistent cough", "swelling", "injury"],
            2: ["mild pain", "cold", "flu", "rash", "minor injury", "headache", "fatigue", "sore throat"],
            1: ["checkup", "routine", "prescription refill", "follow-up", "consultation", "vaccination"]
        }
        self.labels = {
            5: "CRITICAL",
            4: "URGENT",
            3: "HIGH",
            2: "MODERATE",
            1: "LOW"
        }

    def _fallback_score(self, symptoms_text: str):
        symptoms_text = symptoms_text.lower()
        matched = []
        max_score = 1
        
        for score_level, words in self.keywords.items():
            for word in words:
                if word in symptoms_text:
                    matched.append(word)
                    if score_level > max_score:
                        max_score = score_level
                        
        return {
            "priority_score": max_score,
            "priority_label": self.labels[max_score],
            "matched_keywords": matched
        }

    def score(self, symptoms_text: str):
        if not symptoms_text:
            return {"priority_score": 1, "priority_label": self.labels[1], "matched_keywords": []}
            
        # Try Ollama GenAI First
        prompt = f"""
You are an expert emergency triage AI. Analyze the following patient symptoms:
"{symptoms_text}"

Assign a priority score from 1 to 5 based strictly on the following guidelines:
5 - CRITICAL (Life-threatening: e.g., heart attack, stroke, not breathing, severe bleeding)
4 - URGENT (Severe distress: e.g., difficulty breathing, broken bone, extremely severe pain)
3 - HIGH (Moderate illness: e.g., persistent fever, moderate pain, infection)
2 - MODERATE (Minor illness: e.g., mild headache, cold, sore throat, minor cut)
1 - LOW (Routine: e.g., regular checkup, mild fatigue, prescription refill, very vague symptoms)

IMPORTANT: If the symptom is just a single word like "head", "leg", or "pain" without specifying severity, you MUST default to 2 (MODERATE) or 1 (LOW). Do not assume it is severe.

Respond STRICTLY in the following JSON format without any markdown or extra text:
{{"score": <number>, "reason": "<short explanation>", "keywords": ["<key symptom 1>", "<key symptom 2>"]}}
"""
        try:
            res = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "gemma3:1b",
                    "prompt": prompt,
                    "stream": False,
                    "format": "json"
                },
                timeout=30
            )
            if res.status_code == 200:
                data = res.json()
                response_text = data.get("response", "")
                
                # Try to parse the JSON
                try:
                    parsed = json.loads(response_text)
                    score_val = int(parsed.get("score", 1))
                    score_val = max(1, min(5, score_val)) # clamp to 1-5
                    
                    return {
                        "priority_score": score_val,
                        "priority_label": self.labels[score_val],
                        "matched_keywords": parsed.get("keywords", []),
                        "ai_reason": parsed.get("reason", "")
                    }
                except json.JSONDecodeError:
                    pass # Fallback if LLM outputs garbage
        except Exception as e:
            print(f"Ollama Triage Failed: {e}. Falling back to keywords.")
            
        return self._fallback_score(symptoms_text)
