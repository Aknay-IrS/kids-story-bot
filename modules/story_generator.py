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
- Have a clear beginning, middle, and end with 4-6 chapters
- Include a positive moral lesson (courage, kindness, honesty, cleverness)
- Use vivid descriptions and fun dialogue
- Are 900-1100 words long (8-10 minutes of narration at 130 words/min)
- Use simple language children understand
- Include exciting moments that keep kids engaged
- End with a clear moral lesson

For Indian stories: Use authentic cultural details, settings, and character names.
For Western fairy tales: Keep the classic magical feel with modern positive values.
Never include violence, scary content, or inappropriate themes."""


def generate_story(topic=None):
    if not topic:
        topic = random.choice(config.STORY_TOPICS)

    log.info(f"Generating story: {topic}")

    # Build prompt without f-string for the JSON template part
    json_template = '''{{
  "title": "Full YouTube-friendly title with emojis",
  "hook": "First 2 sentences that grab attention",
  "narration": "Complete story 900-1100 words, written to be read aloud, clear paragraphs",
  "chapters": [
    {{"title": "Chapter 1 name", "start_word": 0}},
    {{"title": "Chapter 2 name", "start_word": 200}},
    {{"title": "Chapter 3 name", "start_word": 450}},
    {{"title": "Chapter 4 name", "start_word": 700}}
  ],
  "scenes": [
    {{"chapter": "Chapter 1", "description": "cartoon illustration description for scene 1, children book art style, colorful"}},
    {{"chapter": "Chapter 2", "description": "cartoon illustration description for scene 2, children book art style, colorful"}},
    {{"chapter": "Chapter 3", "description": "cartoon illustration description for scene 3, children book art style, colorful"}},
    {{"chapter": "Chapter 4", "description": "cartoon illustration description for scene 4, children book art style, colorful"}},
    {{"chapter": "Climax", "description": "cartoon illustration description for climax scene, children book art style, colorful"}},
    {{"chapter": "Ending", "description": "happy ending cartoon illustration, children book art style, colorful, bright"}}
  ],
  "moral": "The moral of this story in one simple sentence",
  "description": "YouTube description 3-4 lines with keywords",
  "tags": ["KidsStories", "BedtimeStories", "StoriesForKids", "FairyTales", "MoralStories"],
  "visual_query": "3 word search for main story setting"
}}'''

    prompt = (
        'Write a complete kids story about: "' + topic + '"\n\n'
        'Return ONLY valid JSON (no markdown, no backticks):\n'
        + json_template
    )

    response = client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=2500,
        messages=[{"role": "user", "content": prompt}],
        system=SYSTEM_PROMPT,
    )

    raw = response.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        story = json.loads(raw)
    except Exception as e:
        log.error(f"JSON parse failed: {e}\nRaw: {raw[:200]}")
        story = _fallback_story(topic)

    story["tags"] = list(set(story.get("tags", []) + [
        "KidsStories", "BedtimeStories", "StoriesForKids",
        "MoralStories", "FairyTales", "KidsChannel",
        "ChildrenStories", "taleForKids"
    ]))

    word_count = len(story.get("narration", "").split())
    log.info(f"Story: {story['title']} | {word_count} words | {len(story.get('scenes',[]))} scenes")
    return story


def _fallback_story(topic):
    return {
        "title": f"\U0001f31f {topic} | Bedtime Story for Kids",
        "hook": "Once upon a time, in a magical land far away, an incredible adventure was about to begin!",
        "narration": ("Once upon a time, there was a wonderful story about " + topic + ". " * 25),
        "chapters": [
            {"title": "The Beginning", "start_word": 0},
            {"title": "The Adventure", "start_word": 250},
            {"title": "The Challenge", "start_word": 500},
            {"title": "The Happy Ending", "start_word": 750}
        ],
        "scenes": [
            {"chapter": "Beginning", "description": topic + " cartoon beginning scene, children illustration, colorful"},
            {"chapter": "Adventure", "description": topic + " adventure scene, fairy tale illustration, bright colors"},
            {"chapter": "Challenge", "description": topic + " challenge scene, children book art, colorful cartoon"},
            {"chapter": "Ending", "description": topic + " happy ending, children illustration, bright cheerful colors"},
        ],
        "moral": "Always be kind and honest, and good things will come to you.",
        "description": f"A wonderful bedtime story about {topic} for kids of all ages.",
        "tags": ["KidsStories", "BedtimeStories"],
        "visual_query": "fairy tale magical forest"
    }
