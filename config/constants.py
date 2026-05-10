"""Application constants and static configuration."""

# subject + location + environment + lighting + mood + camera + style

PROMPT_DICT = {
    "fantasy": {
        "subject": [
            "ancient gothic castle",
            "ruined cathedral",
            "dark fantasy fortress",
            "ancient stone tower",
            "armored knight",
            "lone samurai warrior",
        ],
        "location": [
            {
                "preposition": "on",
                "value": "a cliff above the ocean"
            },
            {
                "preposition": "in",
                "value": "a ruined kingdom",
            },
            {
                "preposition": "in",
                "value": "a misty mountain valley",
            },
            {
                "preposition": "",
                "value": "deep inside a dark forest"
            }
        ],
        "environment": [
            "foggy valley below",
            "ancient ruins scattered across landscape",
            "storm clouds gathering",
            "massive cliffs and rocky terrain",
        ],
    },
    "cyberpunk": {
        "subject": [
            "cyberpunk hacker",
            "futuristic bounty hunter",
            "android assassin",
        ],
        "location": [
            {
                "preposition": "in",
                "value": "a neon cyberpunk city"
            },
            {
                "preposition": "on",
                "value": "top of a megacity skyscraper"
            },
            {
                "preposition": "in",
                "value": "a futuristic alleyway"
            }
        ],
        "environment": [
            "neon signs reflecting on wet pavement",
            "flying vehicles in the skyline",
            "rain soaked streets glowing with neon",
        ],
    },
    "space": {
        "subject": [
            "interstellar spaceship fleet",
            "space explorer",
            "massive alien megastructure",
        ],
        "location": [
            {
                "preposition": "",
                "value": "orbiting a distant planet"
            },
            {
                "preposition": "",
                "value": "near a massive ringworld"
            },
            {
                "preposition": "in",
                "value": "deep interstellar space"
            }
        ],
        "environment": [
            "colorful cosmic nebula",
            "asteroid fields drifting slowly",
            "glowing galactic clouds",
        ],
    },
}

ATMOSPHERE = [
    "cinematic lighting",
    "volumetric fog",
    "dramatic shadows",
    "epic cinematic atmosphere",
    "mysterious dark ambiance",
    "high contrast lighting",
]

MORNING_LIGHT = [
    "sunrise lighting",
    "golden morning sunlight",
    "low angle sunlight casting long shadows",
    "sun rays breaking through clouds",
]

NIGHT_LIGHT = [
    "moonlit night sky",
    "cold blue moonlight",
    "starry night sky",
    "dim lunar illumination",
]

CAMERA = [
    "wide angle cinematic shot",
    "low angle perspective",
    "epic aerial view",
    "dramatic perspective shot",
    "ultra wide landscape shot",
]

DETAIL = [
    "incredible environmental detail",
    "intricate architecture",
    "highly detailed terrain",
    "realistic material textures",
]

SCENE_TEMPLATES = [
    "{subject} {location}, {environment}, {lighting}, {atmosphere}, {camera}, {camera_physics}, {detail}",
    "cinematic wide shot of {subject} {location}, {environment}, illuminated by {lighting}, {atmosphere}, {camera_physics}, {detail}",
    "epic scene of {subject} {location}, surrounded by {environment}, dramatic {lighting}, {camera}, {camera_physics}",
    "{subject} standing {location}, {environment}, cinematic {lighting}, {atmosphere}, {camera_physics}, {detail}",
]

SEMANTIC_TEMPLATES = [
    (
        "{subject} "
        "{location_phrase}, "
        "{environment}, "
        "{lighting}"
    ),

    (
        "{subject} "
        "{location_phrase}, "
        "{environment}"
    ),
]

RENDER_TEMPLATES = [
    "{atmosphere}, {camera}, {camera_physics}, {detail}",
    "{camera}, {detail}, {atmosphere}",
]
CAMERA_PHYSICS = [
    "shot on 35mm lens",
    "shot on 50mm lens",
    "wide angle lens",
    "cinematic depth of field",
    "professional landscape photography",
    "ultra wide lens perspective",
    "dramatic cinematic framing",
]

RENDER_TAGS = (
    ", ultra detailed, global illumination, physically based rendering, "
    "ray traced lighting, realistic reflections"
)

COMFY_URL = "http://127.0.0.1:8188"
WORKFLOW_PROMPT_NODE_ID = "6"
GPU_INDEX = "0"
GPU_IDLE_THRESHOLD = 50
GPU_IDLE_RETRIES = 5
GPU_IDLE_WAIT_SECONDS = 120
COMFY_BOOT_RETRIES = 30
COMFY_BOOT_WAIT_SECONDS = 2
GENERATION_TIMEOUT_SECONDS = 300
HISTORY_POLL_SECONDS = 2
BEST_SEED_MUTATION_RANGE = 5000
BEST_SEED_REUSE_PROBABILITY = 0.7
BEST_SEED_LIMIT = 50