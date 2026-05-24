"""
story_generator.py - Generates original kids stories using Claude API
"""
import json
import logging
import random
import re

import anthropic
import config

log = logging.getLogger(__name__)
client = anthropic.Anthropic(api_key=config.CLAUDE_API_KEY)

SYSTEM_PROMPT = """You are a master kids story narrator who writes magical, 
engaging stories for children of all ages (2-12 years) and their families.

Your stories:
- Are original, imaginative, and age-appropriate
- Have a clear beginning, middle, and end
- Include a positive moral lesson (courage, kindness, honesty, cleverness)
- Use vivid descriptions and fun dialogue
- Are 900-1100 words long (8-10 minutes of narration at 130 words/min)
- Use simple language children understand
- Include exciting moments that keep kids engaged
- End with a clear moral lesson stated simply

For Indian stories: Use authentic cultural details, settings, and character names.
For Western fairy tales: Keep the classic magical feel with modern positive values.
Never include violence, scary content, or inappropriate themes."""


def generate_story(topic: str = None) -> dict:
    """Generate a complete kids story. Returns structured story dict."""
    if not topic:
        topic = random.choice(config.STORY_TOPICS)

    log.info(f"Generating story: {topic}")

    prompt = f"""Write a complete kids story about: "{topic}"

Return ONLY valid JSON (no markdown, no backticks):
{{
  "title": "Full YouTube-friendly title with emojis (e.g. '🦁 The Lion and the Mouse | Bedtime Story for Kids')",
  "hook": "First 2 sentences that grab attention immediately",
  "narration": "Complete story narration 900-1100 words. Written to be READ ALOUD. Use clear paragraphs. Include character voices in dialogue.",
  "chapters": [
    {{"title": "Chapter name", "start_word": 0}},
    {{"title": "Chapter name", "start_word": 200}},
    {{"title": "Chapter name", "start_word": 500}},
    {{"title": "Chapter name", "start_word": 750}}
  ],
  "moral": "The moral of this story in one simple sentence",
  "description": "YouTube description 3-4 lines with keywords",
  "tags": ["KidsStories", "BedtimeStories", "StoriesForKids", "FairyTales", "MoralStories"],
  "visual_query": "3 word Pixabay search for background video (e.g. 'forest animals nature')"
}}"""

    response = client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
        system=SYSTEM_PROMPT,
    )

    raw = response.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        story = json.loads(raw)
    except Exception as e:
        log.error(f"JSON parse failed: {e}")
        story = _fallback_story(topic)

    # Add standard tags
    story["tags"] = list(set(story.get("tags", []) + [
        "KidsStories", "BedtimeStories", "StoriesForKids",
        "MoralStories", "FairyTales", "KidsChannel",
        "ChildrenStories", "taleForKids"
    ]))

    word_count = len(story.get("narration", "").split())
    log.info(f"Story generated: {story['title']} | {word_count} words")
    return story


def _fallback_story(topic: str) -> dict:
    return {
        "title": f"🌟 {topic} | Bedtime Story for Kids",
        "hook": "Once upon a time, in a magical land far away, an incredible adventure was about to begin!",
        "narration": f"Once upon a time, there was a wonderful story about {topic}. " * 20,
        "chapters": [
            {"title": "The Beginning", "start_word": 0},
            {"title": "The Adventure", "start_word": 250},
            {"title": "The Challenge", "start_word": 500},
            {"title": "The Happy Ending", "start_word": 750}
        ],
        "moral": "Always be kind and honest, and good things will come to you.",
        "description": f"A wonderful bedtime story about {topic} for kids of all ages.",
        "tags": ["KidsStories", "BedtimeStories"],
        "visual_query": "nature forest magical"
    }
