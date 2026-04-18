import json
from typing import Optional, List
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()


class ExtractedClues(BaseModel):
    action: Optional[str] = None
    location: Optional[str] = None
    time: Optional[str] = None
    people_or_object: Optional[str] = None
    crime_signal: Optional[str] = None


class IncidentDraft(BaseModel):
    post_id: str
    candidate: bool
    short_reason: str
    extracted_clues: ExtractedClues
    evidence_snippets: List[str] = Field(default_factory=list)
    status: str = "candidate"


prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """
You are the Crawler Agent for PettyCrimeSingapore.

Decide whether a community post is a possible unreported petty-crime
or suspicious-activity incident in Singapore.

Mark candidate=true only if the post suggests a specific real-world event
with useful detail.

Reject:
- general opinions
- vague warnings
- jokes/memes
- non-crime complaints
- posts with no specific event

Return valid JSON only matching this schema:

{
  "post_id": "string",
  "candidate": true,
  "short_reason": "string",
  "extracted_clues": {
    "action": "string or null",
    "location": "string or null",
    "time": "string or null",
    "people_or_object": "string or null",
    "crime_signal": "string or null"
  },
  "evidence_snippets": ["string"],
  "status": "candidate or rejected"
}
"""
    ),
    (
        "human",
        """
Post ID: {post_id}
Platform: {platform}
Source URL: {source_url}
Post text: {text}
Timestamp: {timestamp}
"""
    )
])


endpoint = HuggingFaceEndpoint(
    repo_id="Qwen/Qwen2.5-7B-Instruct",
    task="text-generation",
    max_new_tokens=512,
    temperature=0.1
)

llm = ChatHuggingFace(llm=endpoint)

chain = prompt | llm


def clean_json_text(text: str) -> str:
    text = text.strip()

    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0].strip()

    return text


def process_post(post: dict) -> dict:
    response = chain.invoke({
        "post_id": post["post_id"],
        "platform": post["platform"],
        "source_url": post["source_url"],
        "text": post["text"],
        "timestamp": post["timestamp"]
    })

    raw_text = response.content
    json_text = clean_json_text(raw_text)

    try:
        parsed = json.loads(json_text)
        validated = IncidentDraft(**parsed)
        return validated.model_dump()
    except Exception as e:
        return {
            "post_id": post["post_id"],
            "candidate": False,
            "short_reason": f"Failed to parse model output: {str(e)}",
            "extracted_clues": {
                "action": None,
                "location": None,
                "time": None,
                "people_or_object": None,
                "crime_signal": None
            },
            "evidence_snippets": [],
            "status": "parse_error",
            "raw_model_output": raw_text
        }


def main():
    with open("data/sample_posts.json", "r", encoding="utf-8") as f:
        posts = json.load(f)

    drafts = [process_post(post) for post in posts]

    with open("data/incident_drafts.json", "w", encoding="utf-8") as f:
        json.dump(drafts, f, indent=2, ensure_ascii=False)

    print("Created data/incident_drafts.json")


if __name__ == "__main__":
    main()