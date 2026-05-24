import os
from dotenv import load_dotenv
load_dotenv()

CLAUDE_API_KEY    = os.getenv("CLAUDE_API_KEY", "")
YOUTUBE_CLIENT_FILE = os.getenv("YOUTUBE_CLIENT_FILE", "client_secret.json")
PIXABAY_API_KEY   = os.getenv("PIXABAY_API_KEY", "55951851-7282cb13bfe0431ff6400f2a0")

# Video settings - long format 16:9 landscape for regular YouTube
VIDEO_WIDTH       = 1920
VIDEO_HEIGHT      = 1080
VIDEO_FPS         = 24
VIDEO_BITRATE     = "4000k"

# Voice - warm, gentle for kids
VOICE_NAME        = "en-IN-NeerjaNeural"
VOICE_RATE        = "-10%"   # slightly slower for kids
VOICE_PITCH       = "+0Hz"

# Story settings
STORY_LENGTH      = "8-10 minutes"  # target duration
WORDS_PER_MIN     = 130             # narration speed

# YouTube
YT_CATEGORY_ID    = "20"   # Gaming -> changed to Education=27
YT_PRIVACY        = "public"
YT_MADE_FOR_KIDS  = True   # IMPORTANT for kids content

# Claude model
CLAUDE_MODEL      = "claude-haiku-4-5-20251001"

# Story topics pool
STORY_TOPICS = [
    "The Clever Monkey and the Two Cats",
    "Tenali Raman and the Golden Mangoes",
    "The Tortoise and the Hare",
    "Akbar and Birbal - The Wisest Judge",
    "The Lion and the Mouse",
    "Panchatantra - The Blue Jackal",
    "Cinderella",
    "The Three Little Pigs",
    "Jack and the Beanstalk",
    "The Crow and the Pitcher",
    "Akbar and Birbal - The Pot of Wisdom",
    "Snow White and the Seven Dwarfs",
    "The Merchant and the Thieves - Panchatantra",
    "Rapunzel",
    "The Greedy Dog",
    "Tenali Raman and the Cats",
    "Beauty and the Beast",
    "The Ugly Duckling",
    "The Ant and the Grasshopper",
    "Alibaba and the Forty Thieves",
    "The Golden Goose",
    "Birbal and the Beggar",
    "The Fox and the Grapes",
    "Hansel and Gretel",
    "The Fisherman and the Golden Fish",
    "Tenali Raman Outwits the Robbers",
    "The Boy Who Cried Wolf",
    "Aladdin and the Magic Lamp",
    "The Wise Old Owl",
    "King Midas and the Golden Touch",
]
