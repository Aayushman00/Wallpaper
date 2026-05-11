# =============================================================================
# PROMPT ARCHITECTURE v2.1
# Design principles:
#   1. Each dict answers exactly ONE question about the image
#   2. Subject carries a type tag to govern template selection
#   3. Mood and render are fully separated — no crossover language
#   4. Lighting is split: TIME (chromatic) + QUALITY (physical fall)
#   5. Templates are typed to subject_type to prevent semantic mismatches
#   6. Rarity weights are embedded — rare traits drive long-tail diversity
#   7. Compatibility filters guard: lens×framing, render×quality, theme×location
#   8. Camera angle is an independent orthogonal dimension
#   9. Environmental condition separates weather from lighting time
# =============================================================================

from typing import TypedDict, Literal

SubjectType = Literal["structure", "character", "vehicle", "phenomenon"]

class Subject(TypedDict):
    label: str
    type: SubjectType


# -----------------------------------------------------------------------------
# THEMES — subject type metadata + theme-scoped locations
# Locations now carry a `themes` key to prevent cross-theme mismatches
# (e.g. fantasy phenomena must not land in space locations)
# -----------------------------------------------------------------------------

THEMES: dict[str, dict] = {

            "fantasy": {
                "subjects": [

            {
                "label": "ancient gothic cathedral",
                "type": "structure",
                "material_class": [
                    "hard_mineral",
                ],
            },

            {
                "label": "crumbling stone tower",
                "type": "structure",
                "material_class": [
                    "hard_mineral",
                ],
            },

            {
                "label": "iron fortress built into a cliff",
                "type": "structure",
                "material_class": [
                    "hard_mineral",
                    "fabricated",
                ],
            },

            # Added: non-decayed structure to break the ruin cluster
            {
                "label": "ancient living forest canopy",
                "type": "structure",
                "material_class": [
                    "organic",
                ],
            },

            {
                "label": "armored knight",
                "type": "character",
                "material_class": [
                    "organic",
                    "fabricated",
                ],
            },

            {
                "label": "wandering plague doctor",
                "type": "character",
                "material_class": [
                    "organic",
                    "fabricated",
                ],
            },

            {
                "label": "lone archer",
                "type": "character",
                "material_class": [
                    "organic",
                    "fabricated",
                ],
            },

            {
                "label": "flock of ravens",
                "type": "phenomenon",
                "material_class": [
                    "organic",
                ],
            },

            {
                "label": "bioluminescent ancient tree",
                "type": "phenomenon",
                "material_class": [
                    "organic",
                ],
            },

            # Added: wonder/awe phenomenon to balance decay cluster
            {
                "label": "aurora of drifting bioluminescent spores",
                "type": "phenomenon",
                "material_class": [
                    "organic",
                    "atmospheric",
                ],
            },
        ],

        "subject_weights": [
            0.12,  # gothic cathedral
            0.10,  # crumbling tower
            0.10,  # iron fortress
            0.10,  # living forest canopy  (new — pulls weight from decay subjects)
            0.12,  # armored knight
            0.09,  # plague doctor
            0.10,  # lone archer
            0.10,  # flock of ravens
            0.09,  # bioluminescent tree
            0.08,  # bioluminescent spores (new, rare — wonder anchor)
        ],

        "locations": [
            {
                "label": "a cliff edge above a churning sea",
                "valid_for": ["structure", "character", "phenomenon"],
                "themes":   ["fantasy"],
            },
            {
                "label": "a collapsed bridge over a ravine",
                "valid_for": ["character", "phenomenon"],
                "themes":   ["fantasy"],
            },
            {
                "label": "a flooded ruined city",
                "valid_for": ["structure", "phenomenon"],
                "themes":   ["fantasy"],
            },
            {
                "label": "a frozen mountain pass",
                "valid_for": ["character", "structure"],
                "themes":   ["fantasy"],
            },
            {
                "label": "the edge of a dying forest",
                "valid_for": ["character", "phenomenon"],
                "themes":   ["fantasy"],
            },
            {
                "label": "a hill of ancient gravestones",
                "valid_for": ["structure", "character"],
                "themes":   ["fantasy"],
            },
            # Added: non-decayed location to break ruin monoculture
            {
                "label": "the floor of an ancient forest of impossible scale",
                "valid_for": ["character", "phenomenon", "structure"],
                "themes":   ["fantasy"],
            },
        ],

        "environments": [
            {
                "label": "dead trees across the horizon",
                "type": "noun_phrase",
                "weight": 0.15,
            },
            {
                "label": "low mist between stone ruins",
                "type": "noun_phrase",
                "weight": 0.15,
            },
            {
                "label": "crows circling overhead",
                "type": "scene_clause",
                "weight": 0.12,
            },
            {
                "label": "overgrown vines consuming old stonework",
                "type": "noun_phrase",
                "weight": 0.12,
            },
            {
                "label": "ash drifting down like snow",
                "type": "scene_clause",
                "weight": 0.12,
            },
            {
                "label": "a blood-red harvest moon rising behind the treeline",
                "type": "scene_clause",
                "weight": 0.12,
            },
            # Added: breaks decay cluster — wonder/awe texture
            {
                "label": "bioluminescent spores drifting upward through dark air",
                "type": "scene_clause",
                "weight": 0.12,
            },
            {
                "label": "shafts of light breaking through a cathedral canopy",
                "type": "scene_clause",
                "weight": 0.10,
            },
        ],
    },

    "cyberpunk": {
        "subjects": [

            {
                "label": "autonomous delivery drone swarm",
                "type": "vehicle",
                "material_class": [
                    "fabricated",
                ],
            },

            {
                "label": "derelict corporate megastructure",
                "type": "structure",
                "material_class": [
                    "hard_mineral",
                    "fabricated",
                ],
            },

            {
                "label": "street-level hacker",
                "type": "character",
                "material_class": [
                    "organic",
                    "fabricated",
                ],
            },

            {
                "label": "augmented combat runner",
                "type": "character",
                "material_class": [
                    "organic",
                    "fabricated",
                ],
            },

            {
                "label": "collapsed elevated highway",
                "type": "structure",
                "material_class": [
                    "hard_mineral",
                    "fabricated",
                ],
            },

            {
                "label": "broadcast antenna spire",
                "type": "structure",
                "material_class": [
                    "fabricated",
                ],
            },

            {
                "label": "mass transit maglev train",
                "type": "vehicle",
                "material_class": [
                    "fabricated",
                ],
            },
        ],

        "subject_weights": [
            0.12,
            0.18,
            0.15,
            0.12,
            0.14,
            0.16,
            0.13,
        ],

        "locations": [
            {
                "label": "the upper tier of a stratified megacity",
                "valid_for": ["structure", "vehicle", "phenomenon"],
                "themes":   ["cyberpunk"],
            },
            {
                "label": "a flooded lower district market",
                "valid_for": ["character", "phenomenon"],
                "themes":   ["cyberpunk"],
            },
            {
                "label": "an abandoned factory district",
                "valid_for": ["structure", "character"],
                "themes":   ["cyberpunk"],
            },
            {
                "label": "a rooftop garden above the smog line",
                "valid_for": ["character", "phenomenon"],
                "themes":   ["cyberpunk"],
            },
            {
                "label": "a rain-soaked transit hub",
                "valid_for": ["character", "vehicle"],
                "themes":   ["cyberpunk"],
            },
            {
                "label": "the outer wall of an arcology tower",
                "valid_for": ["structure", "vehicle"],
                "themes":   ["cyberpunk"],
            },
        ],

        "environments": [
            # Shortened verbose labels; added neon-beauty entries to break oppression monoculture
            {
                "label": "holographic ads dissolving in the smog",       # was: "holographic advertisements flickering through the haze"
                "type": "scene_clause",
                "weight": 0.15,
            },
            {
                "label": "power lines between distant towers",
                "type": "noun_phrase",
                "weight": 0.13,
            },
            {
                "label": "steam venting from underground grates",
                "type": "scene_clause",
                "weight": 0.13,
            },
            {
                "label": "smog layer across mid-level floors",           # was: "a smog layer across mid-level floors"
                "type": "noun_phrase",
                "weight": 0.13,
            },
            {
                "label": "protest drones hovering at distance",          # was: "scattered protest drones hovering at distance"
                "type": "scene_clause",
                "weight": 0.13,
            },
            {
                "label": "surveillance cameras on every surface",        # was: "surveillance cameras mounted on every visible surface"
                "type": "scene_clause",
                "weight": 0.13,
            },
            # Added: neon-beauty entries to break oppression cluster
            {
                "label": "wet street reflections of layered neon signs",
                "type": "scene_clause",
                "weight": 0.10,
            },
            {
                "label": "crowded night market below transit lines",
                "type": "noun_phrase",
                "weight": 0.10,
            },
        ],
    },

    "space": {
        "subjects": [

            {
                "label": "generation ship",
                "type": "vehicle",
                "material_class": [
                    "fabricated",
                ],
            },

            {
                "label": "derelict alien megastructure",
                "type": "structure",
                "material_class": [
                    "fabricated",
                    "hard_mineral",
                ],
            },

            {
                "label": "lone astronaut",
                "type": "character",
                "material_class": [
                    "organic",
                    "fabricated",
                ],
            },

            {
                "label": "terraforming apparatus",
                "type": "structure",
                "material_class": [
                    "fabricated",
                ],
            },

            {
                "label": "solar wind aurora",
                "type": "phenomenon",
                "material_class": [
                    "atmospheric",
                ],
            },

            {
                "label": "debris field of a shattered moon",
                "type": "phenomenon",
                "material_class": [
                    "hard_mineral",
                ],
            },

            {
                "label": "solar sail vessel",
                "type": "vehicle",
                "material_class": [
                    "fabricated",
                ],
            },
        ],

        "subject_weights": [
            0.15,
            0.18,
            0.14,
            0.14,
            0.12,
            0.14,
            0.13,
        ],

        "locations": [
            {
                "label": "the shadow of a gas giant",
                "valid_for": ["vehicle", "structure", "character"],
                "themes":   ["space"],
            },
            {
                "label": "the hollow interior of an asteroid",
                "valid_for": ["structure", "vehicle"],
                "themes":   ["space"],
            },
            {
                "label": "the upper atmosphere of a terraformed ice world",
                "valid_for": ["vehicle", "character", "phenomenon"],
                "themes":   ["space"],
            },
            {
                "label": "inside a stellar nursery, young stars ahead",   # was: "the outer boundary of a stellar nursery" — low imageability
                "valid_for": ["phenomenon", "structure"],
                "themes":   ["space"],
            },
            {
                # Fixed: bare void is wallpaper-useless — added nebula anchor
                "label": "open void, faint nebula behind",                # was: "open interstellar void"
                "valid_for": ["vehicle", "character", "phenomenon"],
                "themes":   ["space"],
            },
            {
                "label": "a decaying orbit around a neutron star",
                "valid_for": ["vehicle", "phenomenon"],
                "themes":   ["space"],
            },
        ],

        "environments": [
            {
                "label": "a crescent planet at the edge of frame",
                "type": "noun_phrase",
                "weight": 0.18,
            },
            {
                "label": "dust clouds lit from within by young stars",
                "type": "scene_clause",
                "weight": 0.20,
            },
            {
                "label": "ring debris casting hard shadows",
                "type": "noun_phrase",
                "weight": 0.18,
            },
            {
                # Removed: SD has no coherent visual prior for gravitational lensing
                # Replaced with visually concrete equivalent
                "label": "distorted starlight near a black hole horizon",       # was: "gravitational lensing warping distant starlight"
                "type": "scene_clause",
                "weight": 0.15,
            },
            {
                "label": "a supernova bloom spreading at the edge of the frame",
                "type": "scene_clause",
                "weight": 0.15,
            },
            {
                "label": "satellite debris field in slow drift",          # was: "hundreds of satellites in decaying orbits" — count unrenderable
                "type": "noun_phrase",
                "weight": 0.14,
            },
        ],
    },
}


# =============================================================================
# LIGHTING — Two orthogonal sub-dimensions
# TIME_OF_DAY: chromatic + temporal character of light
# LIGHT_QUALITY: physical fall behaviour (independent of source or time)
# Rule: pick 1 from each. Theme filter: space disables universal TIME entries.
# =============================================================================

LIGHTING_TIME = {
    "universal": [
        {"label": "pre-dawn blue hour",     "weight": 0.14},
        {"label": "golden hour",            "weight": 0.16},
        {"label": "deep overcast midday",   "weight": 0.14},
        {"label": "twilight",               "weight": 0.16},
        {"label": "full dark",              "weight": 0.14},
        # flat grey diffuse: gated to archviz/concept-art render only (see LIGHTING_INCOMPATIBLE)
        {"label": "flat grey diffuse",      "weight": 0.12},
        {"label": "harsh noon",             "weight": 0.14},
    ],
    "space_only": [
        {"label": "harsh unfiltered starlight",     "weight": 0.30},
        {"label": "eclipse backlight",              "weight": 0.25},
        {"label": "dim red dwarf illumination",     "weight": 0.25},
        # Fixed: "multi-star system light" had no SD imageability
        {"label": "dual-star cross-shadows",        "weight": 0.20},  # was: "multi-star system light"
    ],
}

LIGHT_QUALITY = [
    {"label": "hard-edged directional",         "weight": 0.18},
    {"label": "soft wrap-around",               "weight": 0.16},
    {"label": "rim-lit silhouette",             "weight": 0.18},
    {"label": "diffused atmospheric glow",      "weight": 0.14},   # fog/dust/nebula contexts
    {"label": "specular highlights only",       "weight": 0.12},   # minimal light, max contrast
    {"label": "self-illuminated elements",      "weight": 0.12},   # neon, bioluminescence, screens
    {"label": "multiple competing sources",     "weight": 0.10},   # rare, complex scenes
]

LIGHTING_INCOMPATIBLE = [
    # Original pairs
    (
        "flat grey diffuse",
        "rim-lit silhouette"
    ),
    (
        "flat grey diffuse",
        "hard-edged directional"
    ),
    (
        "deep overcast midday",    
        "specular highlights only"
        ),
    (
        "deep overcast midday",    
        "hard-edged directional"
        ),
    (
        "harsh noon",              
        "rim-lit silhouette"
    ),
    (
        "deep overcast midday",
        "diffused atmospheric glow",
    ),

    (
        "golden hour",
        "specular highlights only",
    ),

    (
        "harsh noon",
        "soft wrap-around",
    ),

    (
        "deep overcast midday",
        "multiple competing sources",
    ),

    (
        "golden hour",
        "multiple competing sources",
    ),

    (
        "full dark",
        "hard-edged directional",
    ),
    # Added: flat grey is only usable with archviz or concept art render
    # (enforced in RENDER_LIGHTING_INCOMPATIBLE below)
]

# Render-medium × lighting time incompatibilities
# flat grey diffuse produces incoherent output with photorealistic or oil paint pipelines
RENDER_LIGHTING_INCOMPATIBLE = [
    ("flat grey diffuse", "photorealistic"),
    ("flat grey diffuse", "oil paint render"),
    ("flat grey diffuse", "matte painting"),
]


# =============================================================================
# MOOD — Purely emotional/atmospheric. Zero render or technical language.
# Added: "strange and wondrous" to balance decay/oppression overrepresentation
# Fixed: "cold and indifferent" → "clinical and sterile" (visual hook for SD)
# =============================================================================

MOOD = [
    {"label": "desolate and abandoned",     "weight": 0.14},
    {"label": "foreboding and tense",       "weight": 0.14},
    {"label": "serene and vast",            "weight": 0.14},
    {"label": "mythic and ancient",         "weight": 0.14},
    {"label": "oppressive and suffocating", "weight": 0.10},
    {"label": "melancholic and quiet",      "weight": 0.10},
    {"label": "violent and turbulent",      "weight": 0.08},   # rare — avoids over-drama
    {"label": "clinical and sterile",       "weight": 0.08},   # was: "cold and indifferent" — no visual hook
    # Added: missing emotional spaces
    {"label": "strange and wondrous",       "weight": 0.08},   # fantasy/space wonder anchor
    {"label": "frenetic and alive",         "weight": 0.10},   # cyberpunk warmth anchor
]


# =============================================================================
# COMPOSITION — Two orthogonal sub-dimensions
# FRAMING_TYPE: spatial grammar of the shot
# LENS_CHARACTER: physical optics behaviour
#
# LENS_FRAMING_INCOMPATIBLE guards:
#   - telephoto + vast environment (depth collapse contradicts scale)
#   - ultra-wide + symmetrical architectural (barrel distortion breaks symmetry)
#   - tilt-shift + environment-fills-frame (selective blur breaks env coherence)
#   - anamorphic + subject-dominates-center (letterbox prior fights centered subject)
# =============================================================================

FRAMING_TYPE = [
    {
        "label": "subject dominates the frame",          # renamed: clarifies SD should render shallow focus
        "weight": 0.13,
        "valid_for": ["character", "vehicle"],
    },
    {
        "label": "subject small against vast environment",
        "weight": 0.18,
        "valid_for": ["character", "vehicle", "structure"],
    },
    {
        "label": "environment dominates the frame",
        "weight": 0.13,
        "valid_for": ["phenomenon", "structure"],
        # Note: only pair with visually dominant environments (not "low mist between ruins")
    },
    {
        "label": "foreground detail leads to distant subject",
        "weight": 0.16,
        "valid_for": ["structure", "character"],
    },
    {
        "label": "symmetrical architectural framing, horizontal axis",  # added axis lock to prevent portrait drift
        "weight": 0.10,
        "valid_for": ["structure"],
    },
    {
        "label": "asymmetric rule-of-thirds placement",
        "weight": 0.18,
        "valid_for": ["character", "vehicle", "structure"],
    },
    # Added: explicit depth-layering framing (was missing from system)
    {
        "label": "layered depth: foreground frame, midground subject, distant environment",
        "weight": 0.12,
        "valid_for": ["structure", "character", "vehicle"],
    },
]

LENS_CHARACTER = [
    {"label": "14mm ultra-wide, near distortion",   "weight": 0.18},
    {"label": "28mm wide, minimal distortion",       "weight": 0.20},
    {"label": "50mm natural perspective",            "weight": 0.18},
    {"label": "85mm slight compression",             "weight": 0.14},
    {"label": "200mm telephoto compression",         "weight": 0.05},   # flattens depth — see incompatibility rules
    {"label": "tilt-shift selective focus",          "weight": 0.08},   # rare — striking, but gated
    {"label": "anamorphic widescreen 2.39:1",        "weight": 0.10},   # rare — filmic letterbox prior
]

# Guards lens × framing semantic contradictions
LENS_FRAMING_INCOMPATIBLE = [
    # telephoto collapses depth — contradicts scale/vastness framing
    ("200mm telephoto compression",         "subject small against vast environment"),
    ("200mm telephoto compression",         "layered depth: foreground frame, midground subject, distant environment"),
    # ultra-wide barrel distortion breaks symmetry
    ("14mm ultra-wide, near distortion",    "symmetrical architectural framing, horizontal axis"),
    # tilt-shift selective blur breaks environmental coherence
    ("tilt-shift selective focus",          "environment dominates the frame"),
    # anamorphic letterbox prior fights centered subject
    ("anamorphic widescreen 2.39:1",        "subject dominates the frame"),
    (
        "subject dominates the frame",
        "dwarfed by",
    ),
    (
        "200mm telephoto compression",
        "subject small against vast environment",
    ),

    (
        "200mm telephoto compression",
        "environment dominates the frame",
    ),

    (
        "200mm telephoto compression",
        "layered depth: foreground frame, midground subject, distant environment",
    ),
]


# =============================================================================
# CAMERA ANGLE — New independent orthogonal dimension
# Previously absent entirely. High wallpaper-composition impact.
# Governs elevation and tilt of the virtual camera.
# =============================================================================

CAMERA_ANGLE = [
    {"label": "low angle, subject looming overhead",    "weight": 0.22},
    {"label": "eye level",                              "weight": 0.25},
    {"label": "high angle, surveying the scene below",  "weight": 0.20},
    {"label": "bird's eye, directly overhead",          "weight": 0.15},
    {"label": "Dutch tilt, slight unease",              "weight": 0.05},   # rare — psychological unease signal
    {"label": "extreme worm's eye, ground up",          "weight": 0.08},   # rare — monumental scale effect
]


# =============================================================================
# ENVIRONMENTAL CONDITION — New dimension
# Separates weather/season texture from lighting time.
# Affects palette, surface texture, and atmospheric density independently.
# =============================================================================

ENVIRONMENTAL_CONDITION = [
    {"label": "heavy rain",                 "weight": 0.16},
    {"label": "snow accumulation",          "weight": 0.14},
    {"label": "heat haze",                  "weight": 0.12},
    {"label": "dust storm edge",            "weight": 0.12},
    {"label": "after the rain, wet surfaces","weight": 0.16},
    {"label": "dry season cracked earth",   "weight": 0.08},   # rare
    {"label": "clear conditions",           "weight": 0.22},   # majority — neutral baseline
]

# Space theme: weather is irrelevant — use this filtered list instead
ENVIRONMENTAL_CONDITION_SPACE = [
    {"label": "solar flare particle wash",  "weight": 0.30},
    {"label": "dense debris interference",  "weight": 0.30},
    {"label": "deep vacuum clarity",        "weight": 0.40},
]


# =============================================================================
# RENDER STYLE — Purely technical/medium language. Zero mood/atmosphere.
#
# CHANGES:
#   - architectural visualization: restricted to cyberpunk/space; incompatible
#     with character subjects (archviz prior = clean empty buildings)
#   - hand-drawn ink: flagged incompatible with space theme
# =============================================================================

RENDER_MEDIUM = [
    {
        "label": "photorealistic",
        "weight": 0.30,
        "incompatible_subject_types": [],
        "incompatible_themes": [],
    },
    {
        "label": "matte painting",
        "weight": 0.22,
        "incompatible_subject_types": [],
        "incompatible_themes": [],
    },
    {
        "label": "oil paint render",
        "weight": 0.16,
        "incompatible_subject_types": [],
        "incompatible_themes": [],
    },
    {
        "label": "concept art",
        "weight": 0.18,
        "incompatible_subject_types": [],
        "incompatible_themes": [],
    },
    {
        "label": "architectural visualization",
        "weight": 0.08,
        # archviz prior: clean empty space, CAD aesthetic — collapses with characters or fantasy
        "incompatible_subject_types": ["character", "phenomenon"],
        "incompatible_themes": ["fantasy"],
    },
    {
        "label": "hand-drawn ink with color",
        "weight": 0.06,
        "incompatible_subject_types": [],
        "incompatible_themes": ["space"],   # ink prior fights space scale/physicality
    },
]

RENDER_QUALITY_MARKERS = [
    {
        "label": "physically accurate material response",
        "weight": 0.25,
        "valid_for": ["organic", "hard_mineral", "fabricated"],
        # concept art and ink have painterly looseness — this marker fights their prior
        "incompatible_render": ["concept art", "hand-drawn ink with color"],
    },
    {
        "label": "diffused atmospheric glow",                   # was: "diffused atmospheric glow in skin and foliage" — scoping redundant
        "weight": 0.20,
        "valid_for": ["organic"],
        "incompatible_render": ["hand-drawn ink with color"],
    },
    {
        "label": "micro surface detail",                    # was: "micro surface texture — rust, stone, and cloth" — examples token-waste
        "weight": 0.20,
        "valid_for": ["organic", "hard_mineral"],
        "incompatible_render": ["hand-drawn ink with color"],
    },
    {
        "label": "atmospheric perspective depth",
        "weight": 0.20,
        "valid_for": ["organic", "hard_mineral", "fabricated", "atmospheric"],
        "incompatible_render": [],
    },
    {
        "label": "specular falloff, polished surfaces",     # was: "accurate specular falloff on polished surfaces" — "accurate" is filler
        "weight": 0.15,
        "valid_for": ["fabricated", "hard_mineral"],
        "incompatible_render": ["hand-drawn ink with color", "concept art"],
    },
    {
        "label": "hard-surface light diffraction",          # was: "edge diffraction and light scatter on hard surfaces" — 9 tokens → 4
        "weight": 0.10,
        "valid_for": ["fabricated"],
        "incompatible_render": ["hand-drawn ink with color", "concept art", "oil paint render"],
    },
]


# =============================================================================
# SEMANTIC TEMPLATES — typed to subject_type
#
# CHANGES from v2:
#   - Broke uniform "X at Y, Z" rhythm throughout
#   - Added fragment-style templates
#   - Added environment-first inversion templates
#   - Added witness/observed-from-behind variants
#   - Removed all "X at Y" repetition as dominant pattern
#   - Every type now has ≥6 templates with distinct rhythmic identities
# =============================================================================

SEMANTIC_TEMPLATES_BY_TYPE = {

    "structure": [

        # Standard cinematic anchor
        {
            "template": "{subject} rising from {location}, {environment}",
            "uses_condition": False,
            "weight": 0.16,
        },

        # Environment-first
        {
            "template": "{environment}, with {subject} visible at {location}",
            "uses_condition": False,
            "weight": 0.14,
        },

        # Fragment hierarchy
        {
            "template": "{subject} towering over {location}. {environment} in the distance.",
            "uses_condition": False,
            "weight": 0.12,
        },

        # Observer perspective
        {
            "template": "seen from below: {subject} at {location}, {environment}",
            "uses_condition": False,
            "weight": 0.12,
        },

        # Atmospheric immersion
        {
            "template": "{environment} surrounding {subject} deep within {location}",
            "uses_condition": False,
            "weight": 0.12,
        },

        # Decay framing
        {
            "template": "the remains of {subject} at {location}, {environment}",
            "uses_condition": False,
            "weight": 0.10,
        },

        # Detail-focused
        {
            "template": "close structural detail of {subject} at {location}, partially obscured by {environment}",
            "uses_condition": False,
            "weight": 0.09,
        },

        # CONDITION TEMPLATE (~30%)
        {
            "template": "{subject} rising from {location} during {condition}, {environment}",
            "uses_condition": True,
            "weight": 0.15,
        },
    ],

    "character": [

        {
            "template": "{subject} at {location}, dwarfed by {environment}",
            "uses_condition": False,
            "weight": 0.16,
        },

        {
            "template": "{subject} moving through {location}, with {environment} ahead",
            "uses_condition": False,
            "weight": 0.14,
        },

        {
            "template": "a silhouette of {subject} against {environment} at {location}",
            "uses_condition": False,
            "weight": 0.14,
        },

        {
            "template": "{subject} crossing {location}. {environment} beyond.",
            "uses_condition": False,
            "weight": 0.12,
        },

        {
            "template": "{subject} standing at {location}, {environment} surrounding the scene",
            "uses_condition": False,
            "weight": 0.12,
        },

        {
            "template": "{subject} seen from behind, facing {environment} at {location}",
            "uses_condition": False,
            "weight": 0.10,
        },

        {
            "template": "{environment} surrounding {location}, with {subject} barely visible within it",
            "uses_condition": False,
            "weight": 0.08,
        },

        # CONDITION TEMPLATE
        {
            "template": "{subject} moving through {location} during {condition}, {environment}",
            "uses_condition": True,
            "weight": 0.14,
        },
    ],

    "vehicle": [

        {
            "template": "{subject} moving through {location}, {environment} surrounding the scene",
            "uses_condition": False,
            "weight": 0.18,
        },

        {
            "template": "{subject} stationed near {location}, {environment} in the background",
            "uses_condition": False,
            "weight": 0.14,
        },

        {
            "template": "a distant view of {subject} crossing {location}, {environment} beyond",
            "uses_condition": False,
            "weight": 0.14,
        },

        {
            "template": "{subject} silhouetted against {environment} at {location}",
            "uses_condition": False,
            "weight": 0.12,
        },

        {
            "template": "{subject} emerging from {location}, {environment} visible beyond",
            "uses_condition": False,
            "weight": 0.12,
        },

        {
            "template": "{environment}, with {subject} passing through {location}",
            "uses_condition": False,
            "weight": 0.10,
        },

        # CONDITION TEMPLATE
        {
            "template": "{subject} crossing {location} during {condition}, {environment}",
            "uses_condition": True,
            "weight": 0.14,
        },
    ],

    "phenomenon": [

        {
            "template": "{subject} spreading across {location}",
            "uses_condition": False,
            "weight": 0.18,
        },

        {
            "template": "{environment} created by {subject}, visible from {location}",
            "uses_condition": False,
            "weight": 0.16,
        },

        {
            "template": "a wide view of {location} dominated by {subject}, {environment}",
            "uses_condition": False,
            "weight": 0.16,
        },

        {
            "template": "{location} illuminated by {subject}, {environment} beyond",
            "uses_condition": False,
            "weight": 0.14,
        },

        {
            "template": "{subject} illuminating {location}, {environment}",
            "uses_condition": False,
            "weight": 0.14,
        },

        {
            "template": "{location} beneath {subject}, {environment} surrounding the scene",
            "uses_condition": False,
            "weight": 0.10,
        },

        # CONDITION TEMPLATE
        {
            "template": "{subject} spreading across {location} during {condition}",
            "uses_condition": True,
            "weight": 0.12,
        },
    ],
}


# =============================================================================
# RENDER TEMPLATES — technical/render language only
# Unchanged from v2 — clean and sufficient
# =============================================================================

RENDER_TEMPLATES = [

    {
        "template": "{render_medium}, {lens}",
        "weight": 0.45,
    },

    {
        "template": (
            "{render_medium} "
            "with {quality_marker}, {lens}"
        ),
        "weight": 0.40,
    },

    {
        "template": (
            "{lens}, "
            "{render_medium} aesthetic"
        ),
        "weight": 0.15,
    },
]



SCENE_SUFFIX = [

    {
        "label": "",
        "weight": 0.72,
    },

    {
        "label": "visible beyond",
        "weight": 0.10,
    },

    {
        "label": "faintly visible in the distance",
        "weight": 0.07,
    },

    {
        "label": "barely visible through haze",
        "weight": 0.05,
    },

    {
        "label": "looming in the distance",
        "weight": 0.03,
    },

    {
        "label": "framing the horizon",
        "weight": 0.03,
    },
]

# =============================================================================
# COMPATIBILITY HELPERS
# Utility structures for the generation pipeline to enforce all guards
# =============================================================================

def is_lens_framing_compatible(lens: str, framing: str) -> bool:
    """Return False if this lens+framing pair is in the incompatibility list."""
    return (lens, framing) not in LENS_FRAMING_INCOMPATIBLE


def is_lighting_compatible(time_label: str, quality_label: str) -> bool:
    """Return False if this lighting time+quality pair is incompatible."""
    return (time_label, quality_label) not in LIGHTING_INCOMPATIBLE


def is_render_lighting_compatible(time_label: str, render_label: str) -> bool:
    """Return False if this lighting time+render pair is incompatible."""
    return (time_label, render_label) not in RENDER_LIGHTING_INCOMPATIBLE


def is_render_quality_compatible(quality_marker: dict, render_label: str) -> bool:
    """Return False if the render medium is in the quality marker's incompatible list."""
    return render_label not in quality_marker.get("incompatible_render", [])


def is_render_subject_compatible(render: dict, subject_type: str, theme: str) -> bool:
    """Return False if the render medium is incompatible with this subject type or theme."""
    if subject_type in render.get("incompatible_subject_types", []):
        return False
    if theme in render.get("incompatible_themes", []):
        return False
    return True


def filter_locations_for_subject(locations: list, subject_type: str, theme: str) -> list:
    """
    Return only locations valid for the given subject type AND theme.
    Prevents cross-theme phenomenon/location mismatches.
    """
    return [
        loc for loc in locations
        if subject_type in loc["valid_for"]
        and theme in loc.get("themes", [theme])   # default: allow if no theme key (backwards compat)
    ]


def get_lighting_time(theme: str) -> list:
    """Return the correct lighting time pool for a given theme."""
    if theme == "space":
        return LIGHTING_TIME["space_only"]
    return LIGHTING_TIME["universal"]


def get_environmental_condition(theme: str) -> list:
    """Return the correct environmental condition pool for a given theme."""
    if theme == "space":
        return ENVIRONMENTAL_CONDITION_SPACE
    return ENVIRONMENTAL_CONDITION


# =============================================================================
# COMFYUI / GENERATION CONSTANTS — unchanged
# =============================================================================

COMFY_URL                       = "http://127.0.0.1:8188"
WORKFLOW_PROMPT_NODE_ID         = "6"
GPU_INDEX                       = "0"
GPU_IDLE_THRESHOLD              = 50
GPU_IDLE_RETRIES                = 5
GPU_IDLE_WAIT_SECONDS           = 120
COMFY_BOOT_RETRIES              = 30
COMFY_BOOT_WAIT_SECONDS         = 2
GENERATION_TIMEOUT_SECONDS      = 300
HISTORY_POLL_SECONDS            = 2
BEST_SEED_MUTATION_RANGE        = 5000
BEST_SEED_REUSE_PROBABILITY     = 0.45
BEST_SEED_LIMIT                 = 50