# =============================================================================
# constants_v2.py
# PROMPT ARCHITECTURE v2.3 — SDXL LATENT-OPTIMIZED LANGUAGE LAYER
# Design principles:
#   1. Each dict answers exactly ONE question about the image
#   2. Subject carries a type tag + stability_class to govern render weighting
#   3. Mood is render-directing semantic injection — not an emotional label
#   4. Lighting is split: TIME (chromatic) + QUALITY (physical fall)
#   5. Templates are typed to subject_type to prevent semantic mismatches
#   6. Rarity weights are embedded — rare traits drive long-tail diversity
#   7. Compatibility filters guard: lens×framing, render×quality, theme×location
#      mood×theme, mood×environment, mood×condition (NEW v2.3)
#   8. Camera angle is an independent orthogonal dimension — now integrated
#   9. Environmental condition separates weather from lighting time
#  10. SCENE_SUFFIX is depth-template-gated — not globally injected
#  11. Mood translates to scene/atmosphere/motion/density semantics in engine
#  12. Scene density scoring prevents clutter stacking (NEW v2.3)
#  13. Subject stability class guides render medium selection (NEW v2.3)
#  14. Anti-repetition diversity decay hooks (NEW v2.3)
#  15. Trait pair memory scaffolding (NEW v2.3)
#
# LANGUAGE LAYER NOTE (v2.3 SDXL optimization):
#   All human-readable labels have been rewritten for latent-space efficiency.
#   Prose-style narration replaced with visual descriptor chunks.
#   Abstract cinematic concepts replaced with grounded visual nouns.
#   Camera/lens terminology converted to SDXL-native photographic language.
#   Space prompts anchored with physical geometry and silhouette references.
# =============================================================================

from typing import TypedDict, Literal

SubjectType = Literal["structure", "character", "vehicle", "phenomenon"]

# Stability class governs render medium probability adjustment.
# "stable"   → strong diffusion model priors, photorealistic works well
# "moderate" → some structural risk, painterly preferred
# "unstable" → weak/abstract priors, avoid photorealistic
SubjectStability = Literal["stable", "moderate", "unstable"]

class Subject(TypedDict):
    label: str
    type: SubjectType
    stability: SubjectStability  # NEW v2.3


# =============================================================================
# SCENE DENSITY SCORING — v2.3
# =============================================================================

MAX_SCENE_DENSITY = 6


# =============================================================================
# MOOD COMPATIBILITY — v2.3
# =============================================================================

MOOD_SUPPRESSED_WEIGHT = 0.25
MOOD_RARE_WEIGHT       = 0.08

MOOD_THEME_COMPATIBILITY: dict[str, dict] = {
    "desolate and abandoned": {
        "preferred":   ["fantasy", "space"],
        "suppressed":  ["cyberpunk"],
        "rare":        [],
    },
    "foreboding and tense": {
        "preferred":   ["fantasy", "cyberpunk"],
        "suppressed":  ["space"],
        "rare":        [],
    },
    "serene and vast": {
        "preferred":   ["space", "fantasy"],
        "suppressed":  ["cyberpunk"],
        "rare":        [],
    },
    "mythic and ancient": {
        "preferred":   ["fantasy", "space"],
        "suppressed":  ["cyberpunk"],
        "rare":        [],
    },
    "oppressive and suffocating": {
        "preferred":   ["cyberpunk", "fantasy"],
        "suppressed":  [],
        "rare":        ["space"],
    },
    "melancholic and quiet": {
        "preferred":   ["fantasy", "space"],
        "suppressed":  ["cyberpunk"],
        "rare":        [],
    },
    "violent and turbulent": {
        "preferred":   ["fantasy", "space"],
        "suppressed":  [],
        "rare":        [],
    },
    "clinical and sterile": {
        "preferred":   ["cyberpunk", "space"],
        "suppressed":  ["fantasy"],
        "rare":        [],
    },
    "strange and wondrous": {
        "preferred":   ["space", "fantasy"],
        "suppressed":  [],
        "rare":        [],
    },
    "frenetic and alive": {
        "preferred":   ["cyberpunk"],
        "suppressed":  ["fantasy", "space"],
        "rare":        [],
    },
}

MOOD_CONDITION_COMPATIBILITY: dict[str, dict] = {
    "desolate and abandoned": {
        "preferred":   ["dry cracked earth", "clear skies", "heat haze"],
        "suppressed":  ["heavy rain"],
        "rare":        ["snow cover"],
    },
    "foreboding and tense": {
        "preferred":   ["heavy rain", "dust storm"],
        "suppressed":  ["clear skies"],
        "rare":        [],
    },
    "serene and vast": {
        "preferred":   ["clear skies", "wet ground after rain"],
        "suppressed":  ["heavy rain", "dust storm"],
        "rare":        [],
    },
    "mythic and ancient": {
        "preferred":   ["heat haze", "dust storm", "clear skies"],
        "suppressed":  ["heavy rain"],
        "rare":        [],
    },
    "oppressive and suffocating": {
        "preferred":   ["heavy rain", "dust storm"],
        "suppressed":  ["clear skies"],
        "rare":        [],
    },
    "melancholic and quiet": {
        "preferred":   ["wet ground after rain", "snow cover"],
        "suppressed":  ["dust storm"],
        "rare":        [],
    },
    "violent and turbulent": {
        "preferred":   ["heavy rain", "dust storm"],
        "suppressed":  ["clear skies"],
        "rare":        [],
    },
    "clinical and sterile": {
        "preferred":   ["clear skies", "deep vacuum"],
        "suppressed":  ["heavy rain", "dust storm"],
        "rare":        [],
    },
    "strange and wondrous": {
        "preferred":   [],
        "suppressed":  [],
        "rare":        [],
    },
    "frenetic and alive": {
        "preferred":   ["heavy rain", "wet ground after rain"],
        "suppressed":  ["dry cracked earth"],
        "rare":        [],
    },
}


# =============================================================================
# CAMERA ANGLE ↔ FRAMING COMPATIBILITY — v2.3
# =============================================================================

CAMERA_ANGLE_FRAMING_INCOMPATIBLE = [
    ("bird's eye overhead shot",         "subject dominates the frame"),
    ("bird's eye overhead shot",         "foreground detail leads to distant subject"),
    ("extreme worm's eye low angle",     "subject small against vast environment"),
    ("extreme worm's eye low angle",     "environment dominates the frame"),
    ("dramatic low angle, subject above","environment dominates the frame"),
]

CAMERA_ANGLE_SUBJECT_AFFINITY: dict[str, list[str]] = {
    "dramatic low angle, subject above":  ["structure", "vehicle"],
    "extreme worm's eye low angle":       ["structure"],
    "high angle survey shot":             ["phenomenon", "vehicle"],
    "bird's eye overhead shot":           ["phenomenon"],
    "eye level":                          ["character"],
    "Dutch tilt":                         ["character", "vehicle"],
}


# -----------------------------------------------------------------------------
# THEMES
# -----------------------------------------------------------------------------

THEMES: dict[str, dict] = {

    "fantasy": {
        "subjects": [
            {
                "label": "ancient gothic cathedral",
                "type": "structure",
                "stability": "stable",
                "material_class": ["hard_mineral"],
                "density_score": 1,
            },
            {
                "label": "crumbling stone tower",
                "type": "structure",
                "stability": "stable",
                "material_class": ["hard_mineral"],
                "density_score": 1,
            },
            {
                "label": "iron fortress carved into a cliff face",
                "type": "structure",
                "stability": "stable",
                "material_class": ["hard_mineral", "fabricated"],
                "density_score": 1,
            },
            {
                "label": "massive ancient forest canopy",
                "type": "structure",
                "stability": "moderate",
                "material_class": ["organic"],
                "density_score": 2,
            },
            {
                "label": "armored knight",
                "type": "character",
                "stability": "stable",
                "material_class": ["organic", "fabricated"],
                "density_score": 1,
            },
            {
                "label": "wandering plague doctor",
                "type": "character",
                "stability": "stable",
                "material_class": ["organic", "fabricated"],
                "density_score": 1,
            },
            {
                "label": "lone archer",
                "type": "character",
                "stability": "stable",
                "material_class": ["organic", "fabricated"],
                "density_score": 1,
            },
            {
                "label": "flock of ravens",
                "type": "phenomenon",
                "stability": "moderate",
                "material_class": ["organic"],
                "density_score": 2,
            },
            {
                "label": "glowing ancient tree",
                "type": "phenomenon",
                "stability": "moderate",
                "material_class": ["organic"],
                "density_score": 1,
            },
            {
                "label": "drifting bioluminescent spores",
                "type": "phenomenon",
                "stability": "unstable",
                "material_class": ["organic", "atmospheric"],
                "density_score": 2,
            },
        ],

        "subject_weights": [
            0.14,  # gothic cathedral
            0.12,  # crumbling tower
            0.12,  # iron fortress
            0.10,  # forest canopy
            0.13,  # armored knight
            0.09,  # plague doctor
            0.11,  # lone archer
            0.09,  # flock of ravens
            0.07,  # glowing tree
            0.03,  # bioluminescent spores
        ],

        "locations": [
            {
                "label": "cliff edge above crashing waves",
                "valid_for": ["structure", "character", "phenomenon"],
                "themes": ["fantasy"],
                "density_score": 1,
            },
            {
                "label": "collapsed stone bridge over a deep ravine",
                "valid_for": ["character", "phenomenon"],
                "themes": ["fantasy"],
                "density_score": 1,
            },
            {
                "label": "flooded ruined city",
                "valid_for": ["structure", "phenomenon"],
                "themes": ["fantasy"],
                "density_score": 2,
            },
            {
                "label": "snow-covered mountain pass",
                "valid_for": ["character", "structure"],
                "themes": ["fantasy"],
                "density_score": 0,
            },
            {
                "label": "dead forest edge",
                "valid_for": ["character", "phenomenon"],
                "themes": ["fantasy"],
                "density_score": 1,
            },
            {
                "label": "ancient graveyard on a hillside",
                "valid_for": ["structure", "character"],
                "themes": ["fantasy"],
                "density_score": 1,
            },
            {
                "label": "floor of an ancient forest, massive trees overhead",
                "valid_for": ["character", "phenomenon", "structure"],
                "themes": ["fantasy"],
                "density_score": 1,
            },
        ],

        "environments": [
            {
                "label": "dead trees across the horizon",
                "type": "noun_phrase",
                "weight": 0.15,
                "density_score": 1,
            },
            {
                "label": "low mist between stone ruins",
                "type": "noun_phrase",
                "weight": 0.15,
                "density_score": 1,
            },
            {
                "label": "crows circling overhead",
                "type": "scene_clause",
                "weight": 0.12,
                "density_score": 2,
            },
            {
                "label": "overgrown vines covering old stonework",
                "type": "noun_phrase",
                "weight": 0.12,
                "density_score": 1,
            },
            {
                "label": "falling ash",
                "type": "scene_clause",
                "weight": 0.12,
                "density_score": 2,
            },
            {
                "label": "blood-red moon rising above the treeline",
                "type": "scene_clause",
                "weight": 0.12,
                "density_score": 1,
            },
            {
                "label": "bioluminescent spores drifting upward through dark air",
                "type": "scene_clause",
                "weight": 0.12,
                "density_score": 2,
            },
            {
                "label": "shafts of light through a dense forest canopy",
                "type": "scene_clause",
                "weight": 0.10,
                "density_score": 1,
            },
        ],
    },

    "cyberpunk": {
        "subjects": [
            {
                "label": "autonomous delivery drone swarm",
                "type": "vehicle",
                "stability": "unstable",
                "material_class": ["fabricated"],
                "density_score": 3,
            },
            {
                "label": "derelict corporate megastructure",
                "type": "structure",
                "stability": "stable",
                "material_class": ["hard_mineral", "fabricated"],
                "density_score": 2,
            },
            {
                "label": "street-level hacker",
                "type": "character",
                "stability": "stable",
                "material_class": ["organic", "fabricated"],
                "density_score": 1,
            },
            {
                "label": "augmented combat runner",
                "type": "character",
                "stability": "stable",
                "material_class": ["organic", "fabricated"],
                "density_score": 1,
            },
            {
                "label": "collapsed elevated highway",
                "type": "structure",
                "stability": "stable",
                "material_class": ["hard_mineral", "fabricated"],
                "density_score": 2,
            },
            {
                "label": "broadcast antenna spire",
                "type": "structure",
                "stability": "stable",
                "material_class": ["fabricated"],
                "density_score": 1,
            },
            {
                "label": "mass transit maglev train",
                "type": "vehicle",
                "stability": "stable",
                "material_class": ["fabricated"],
                "density_score": 1,
            },
        ],

        "subject_weights": [0.07, 0.20, 0.16, 0.14, 0.15, 0.16, 0.12],

        "locations": [
            {
                "label": "upper tier of a stratified megacity",
                "valid_for": ["structure", "vehicle", "phenomenon"],
                "themes": ["cyberpunk"],
                "density_score": 2,
            },
            {
                "label": "flooded lower-district market",
                "valid_for": ["character", "phenomenon"],
                "themes": ["cyberpunk"],
                "density_score": 3,
            },
            {
                "label": "abandoned factory district",
                "valid_for": ["structure", "character"],
                "themes": ["cyberpunk"],
                "density_score": 1,
            },
            {
                "label": "rooftop garden above the smog layer",
                "valid_for": ["character", "phenomenon"],
                "themes": ["cyberpunk"],
                "density_score": 1,
            },
            {
                "label": "rain-soaked transit hub",
                "valid_for": ["character", "vehicle"],
                "themes": ["cyberpunk"],
                "density_score": 2,
            },
            {
                "label": "outer wall of a megacity arcology tower",
                "valid_for": ["structure", "vehicle"],
                "themes": ["cyberpunk"],
                "density_score": 1,
            },
        ],

        "environments": [
            {
                "label": "holographic advertisements dissolving in smog",
                "type": "scene_clause",
                "weight": 0.15,
                "density_score": 3,
            },
            {
                "label": "power lines strung between distant towers",
                "type": "noun_phrase",
                "weight": 0.13,
                "density_score": 1,
            },
            {
                "label": "steam venting from underground grates",
                "type": "scene_clause",
                "weight": 0.13,
                "density_score": 2,
            },
            {
                "label": "smog layer swallowing mid-level floors",
                "type": "noun_phrase",
                "weight": 0.13,
                "density_score": 2,
            },
            {
                "label": "protest drones hovering in the distance",
                "type": "scene_clause",
                "weight": 0.13,
                "density_score": 3,
            },
            {
                "label": "surveillance cameras covering every surface",
                "type": "scene_clause",
                "weight": 0.13,
                "density_score": 3,
            },
            {
                "label": "neon reflections across wet asphalt",
                "type": "scene_clause",
                "weight": 0.10,
                "density_score": 2,
            },
            {
                "label": "crowded night market below transit lines",
                "type": "noun_phrase",
                "weight": 0.10,
                "density_score": 3,
            },
        ],
    },

    "space": {
        "subjects": [
            {
                "label": "generation ship",
                "type": "vehicle",
                "stability": "stable",
                "material_class": ["fabricated"],
                "density_score": 1,
            },
            {
                "label": "derelict alien megastructure",
                "type": "structure",
                "stability": "moderate",
                "material_class": ["fabricated", "hard_mineral"],
                "density_score": 1,
            },
            {
                "label": "lone astronaut",
                "type": "character",
                "stability": "stable",
                "material_class": ["organic", "fabricated"],
                "density_score": 1,
            },
            {
                "label": "terraforming apparatus",
                "type": "structure",
                "stability": "unstable",
                "material_class": ["fabricated"],
                "density_score": 2,
            },
            {
                "label": "solar wind aurora",
                "type": "phenomenon",
                "stability": "moderate",
                "material_class": ["atmospheric"],
                "density_score": 1,
            },
            {
                "label": "shattered moon debris field",
                "type": "phenomenon",
                "stability": "moderate",
                "material_class": ["hard_mineral"],
                "density_score": 2,
            },
            {
                "label": "solar sail vessel",
                "type": "vehicle",
                "stability": "stable",
                "material_class": ["fabricated"],
                "density_score": 1,
            },
        ],

        "subject_weights": [0.17, 0.16, 0.18, 0.08, 0.14, 0.13, 0.14],

        "locations": [
            {
                "label": "in the shadow of a gas giant",
                "valid_for": ["vehicle", "structure", "character"],
                "themes": ["space"],
                "density_score": 1,
            },
            {
                "label": "hollow asteroid interior",
                "valid_for": ["structure", "vehicle"],
                "themes": ["space"],
                "density_score": 0,
            },
            {
                "label": "upper atmosphere of a terraformed ice world",
                "valid_for": ["vehicle", "character", "phenomenon"],
                "themes": ["space"],
                "density_score": 1,
            },
            {
                "label": "stellar nursery, young stars ahead",
                "valid_for": ["phenomenon", "structure"],
                "themes": ["space"],
                "density_score": 2,
            },
            {
                "label": "open void, faint nebula behind",
                "valid_for": ["vehicle", "character", "phenomenon"],
                "themes": ["space"],
                "density_score": 0,
            },
            {
                "label": "decaying orbit above a neutron star",
                "valid_for": ["vehicle", "phenomenon"],
                "themes": ["space"],
                "density_score": 1,
            },
        ],

        "environments": [
            {
                "label": "crescent planet at the edge of frame",
                "type": "noun_phrase",
                "weight": 0.18,
                "density_score": 1,
            },
            {
                "label": "glowing dust clouds lit from within",
                "type": "scene_clause",
                "weight": 0.20,
                "density_score": 2,
            },
            {
                "label": "ring debris casting hard shadows",
                "type": "noun_phrase",
                "weight": 0.18,
                "density_score": 2,
            },
            {
                "label": "starlight bending near a black hole",
                "type": "scene_clause",
                "weight": 0.15,
                "density_score": 1,
            },
            {
                "label": "supernova bloom at the edge of frame",
                "type": "scene_clause",
                "weight": 0.15,
                "density_score": 2,
            },
            {
                "label": "drifting satellite debris in slow rotation",
                "type": "noun_phrase",
                "weight": 0.14,
                "density_score": 2,
            },
        ],
    },
}


# =============================================================================
# LIGHTING
# =============================================================================

LIGHTING_TIME = {
    "universal": [
        {"label": "pre-dawn blue hour",   "weight": 0.14},
        {"label": "golden hour",          "weight": 0.16},
        {"label": "deep overcast midday", "weight": 0.14},
        {"label": "twilight",             "weight": 0.16},
        {"label": "full dark",            "weight": 0.14},
        {"label": "flat grey diffuse",    "weight": 0.12},
        {"label": "harsh noon",           "weight": 0.14},
    ],
    "space_only": [
        {"label": "harsh unfiltered starlight", "weight": 0.30},
        {"label": "eclipse backlight",          "weight": 0.25},
        {"label": "dim red dwarf illumination", "weight": 0.25},
        {"label": "dual-star cross-lighting",   "weight": 0.20},
    ],
}

LIGHT_QUALITY = [
    {"label": "hard directional shadows",      "weight": 0.18},
    {"label": "soft wrap lighting",            "weight": 0.16},
    {"label": "rim-lit silhouette",            "weight": 0.18},
    {"label": "volumetric atmospheric glow",   "weight": 0.14},
    {"label": "specular highlights",           "weight": 0.12},
    {"label": "glowing self-illuminated",      "weight": 0.12},
    {"label": "multiple competing light sources", "weight": 0.10},
]

LIGHTING_INCOMPATIBLE = [
    ("flat grey diffuse",    "rim-lit silhouette"),
    ("flat grey diffuse",    "hard directional shadows"),
    ("deep overcast midday", "specular highlights"),
    ("deep overcast midday", "hard directional shadows"),
    ("harsh noon",           "rim-lit silhouette"),
    ("deep overcast midday", "volumetric atmospheric glow"),
    ("golden hour",          "specular highlights"),
    ("harsh noon",           "soft wrap lighting"),
    ("deep overcast midday", "multiple competing light sources"),
    ("golden hour",          "multiple competing light sources"),
    ("full dark",            "hard directional shadows"),
]

RENDER_LIGHTING_INCOMPATIBLE = [
    ("flat grey diffuse", "photorealistic"),
    ("flat grey diffuse", "oil paint render"),
    ("flat grey diffuse", "matte painting"),
]


# =============================================================================
# MOOD SEMANTICS — SDXL-optimized visual descriptor language
#
# Each mood field now contains visually grounded descriptor chunks
# rather than abstract cinematic prose. These inject directly into
# the final prompt and must activate strong latent representations.
# =============================================================================

MOOD_SEMANTICS = {

    "desolate and abandoned": {
        # Visual: empty ruins, no figures, bleached color, open sky
        "atmosphere": "empty ruins, no signs of life, overcast skies",
        "motion":     "still air, frozen in place",
        "density":    "sparse scene, empty foreground, distant horizon",
        "palette":    "desaturated grey-green tones",
        "weight":     0.14,
    },

    "foreboding and tense": {
        # Visual: compressed sky, heavy shadows, dark storm atmosphere
        "atmosphere": "heavy storm clouds, deep shadows, oppressive atmosphere",
        "motion":     "still before the storm",
        "density":    "dark foreground mass, compressed low horizon",
        "palette":    "dark amber and deep shadow tones",
        "weight":     0.14,
    },

    "serene and vast": {
        # Visual: wide open, clean air, long depth, blue-grey palette
        "atmosphere": "clean open air, wide vista, long depth of field",
        "motion":     "slow drift, gentle movement",
        "density":    "minimal objects, wide open sky",
        "palette":    "cool blue-grey tones, high luminance",
        "weight":     0.14,
    },

    "mythic and ancient": {
        # Visual: dust-haze, massive stone, worn textures, warm ochre
        "atmosphere": "dust haze, crumbling stonework, ancient weathered surfaces",
        "motion":     "perfectly still, monumental scale",
        "density":    "layered rock formations, massive stone structures",
        "palette":    "warm ochre and sandstone tones",
        "weight":     0.14,
    },

    "oppressive and suffocating": {
        # Visual: smog, low visibility, claustrophobic framing
        "atmosphere": "dense smog, low visibility, toxic haze",
        "motion":     "slow drifting smoke, trapped atmosphere",
        "density":    "compressed layers, no open sky visible",
        "palette":    "toxic amber and acid yellow tones",
        "weight":     0.10,
    },

    "melancholic and quiet": {
        # Visual: thin grey light, wet surfaces, isolated figure
        "atmosphere": "thin grey light, wet surfaces, empty streets",
        "motion":     "solitary figure, no crowds",
        "density":    "low density scene, long empty distances",
        "palette":    "muted blue and silver tones",
        "weight":     0.10,
    },

    "violent and turbulent": {
        # Visual: airborne debris, blown dust, kinetic chaos
        "atmosphere": "airborne debris, dust clouds, chaotic atmosphere",
        "motion":     "blown debris, multiple directions of movement",
        "density":    "cluttered foreground, visual noise",
        "palette":    "high contrast, blown highlights and deep shadow",
        "weight":     0.08,
    },

    "clinical and sterile": {
        # Visual: clean whites, hard geometry, no organic elements
        "atmosphere": "clean white light, no atmospheric haze, pristine surfaces",
        "motion":     "mechanical stillness, no organic movement",
        "density":    "empty ordered volumes, hard-edged geometry",
        "palette":    "cool white and metallic grey tones",
        "weight":     0.08,
    },

    "strange and wondrous": {
        # Visual: bioluminescence, impossible scale, glowing atmosphere
        "atmosphere": "bioluminescent glow, strange light sources, ethereal atmosphere",
        "motion":     "slow upward drift, floating particles",
        "density":    "layered glowing elements, scale-defying structures",
        "palette":    "teal and violet luminance, deep black background",
        "weight":     0.08,
    },

    "frenetic and alive": {
        # Visual: crowd motion, neon, rain-wet surfaces, layered signage
        "atmosphere": "crowded streets, neon glow, electric atmosphere",
        "motion":     "busy movement, overlapping crowds",
        "density":    "dense urban scene, no empty surfaces",
        "palette":    "saturated neon, warm artificial light",
        "weight":     0.10,
    },
}


# =============================================================================
# COMPOSITION
# =============================================================================

FRAMING_TYPE = [
    {
        "label": "subject fills the frame, dramatic close composition",
        "weight": 0.13,
        "valid_for": ["character", "vehicle"],
        "density_score": 2,
    },
    {
        "label": "tiny figure beneath a massive environment",
        "weight": 0.18,
        "valid_for": ["character", "vehicle", "structure"],
        "density_score": 0,
    },
    {
        "label": "wide establishing shot, environment dominates",
        "weight": 0.13,
        "valid_for": ["phenomenon", "structure"],
        "density_score": 1,
    },
    {
        "label": "foreground detail framing a distant subject",
        "weight": 0.16,
        "valid_for": ["structure", "character"],
        "density_score": 1,
    },
    {
        "label": "symmetrical architectural wide shot",
        "weight": 0.10,
        "valid_for": ["structure"],
        "density_score": 0,
    },
    {
        "label": "asymmetric rule-of-thirds composition",
        "weight": 0.18,
        "valid_for": ["character", "vehicle", "structure"],
        "density_score": 0,
    },
    {
        "label": "layered depth, foreground frame, midground subject, distant background",
        "weight": 0.12,
        "valid_for": ["structure", "character", "vehicle"],
        "density_score": 1,
    },
]

LENS_CHARACTER = [
    {"label": "ultra-wide cinematic shot",          "weight": 0.18},
    {"label": "wide cinematic composition",         "weight": 0.20},
    {"label": "natural perspective shot",           "weight": 0.18},
    {"label": "slight telephoto compression",       "weight": 0.14},
    {"label": "telephoto compression, stacked depth","weight": 0.05},
    {"label": "shallow depth of field",             "weight": 0.08},
    {"label": "anamorphic wide cinematic",          "weight": 0.10},
]

# Incompatible lens × framing pairs (labels updated to match above)
LENS_FRAMING_INCOMPATIBLE = [
    ("telephoto compression, stacked depth",  "tiny figure beneath a massive environment"),
    ("telephoto compression, stacked depth",  "layered depth, foreground frame, midground subject, distant background"),
    ("ultra-wide cinematic shot",             "symmetrical architectural wide shot"),
    ("shallow depth of field",                "wide establishing shot, environment dominates"),
    ("anamorphic wide cinematic",             "subject fills the frame, dramatic close composition"),
    ("subject fills the frame, dramatic close composition", "dwarfed by"),
    ("telephoto compression, stacked depth",  "wide establishing shot, environment dominates"),
]


# =============================================================================
# CAMERA ANGLE — v2.3 — SDXL-native photographic language
# =============================================================================

CAMERA_ANGLE = [
    {"label": "dramatic low angle, subject looming overhead", "weight": 0.22, "density_score": 0},
    {"label": "eye level",                                    "weight": 0.25, "density_score": 0},
    {"label": "high angle survey shot",                       "weight": 0.20, "density_score": 0},
    {"label": "bird's eye overhead shot",                     "weight": 0.10, "density_score": 0},
    {"label": "Dutch tilt",                                   "weight": 0.05, "density_score": 0},
    {"label": "extreme worm's eye low angle",                 "weight": 0.08, "density_score": 0},
]


# =============================================================================
# ENVIRONMENTAL CONDITION — SDXL-optimized labels
# =============================================================================

ENVIRONMENTAL_CONDITION = [
    {"label": "heavy rain",             "weight": 0.16, "density_score": 2},
    {"label": "snow cover",             "weight": 0.14, "density_score": 1},
    {"label": "heat haze",              "weight": 0.12, "density_score": 1},
    {"label": "dust storm",             "weight": 0.12, "density_score": 2},
    {"label": "wet ground after rain",  "weight": 0.16, "density_score": 1},
    {"label": "dry cracked earth",      "weight": 0.08, "density_score": 0},
    {"label": "clear skies",            "weight": 0.22, "density_score": 0},
]

ENVIRONMENTAL_CONDITION_SPACE = [
    {"label": "solar flare particle wash", "weight": 0.30, "density_score": 2},
    {"label": "dense debris field",        "weight": 0.30, "density_score": 2},
    {"label": "deep vacuum",               "weight": 0.40, "density_score": 0},
]


# =============================================================================
# RENDER STYLE — v2.3
# =============================================================================

RENDER_MEDIUM = [
    {
        "label": "photorealistic",
        "weight": 0.30,
        "incompatible_subject_types": [],
        "incompatible_themes": [],
        "abstract_penalty": True,
        "abstract_boost":   False,
    },
    {
        "label": "matte painting",
        "weight": 0.22,
        "incompatible_subject_types": [],
        "incompatible_themes": [],
        "abstract_penalty": False,
        "abstract_boost":   True,
    },
    {
        "label": "oil paint render",
        "weight": 0.16,
        "incompatible_subject_types": [],
        "incompatible_themes": [],
        "abstract_penalty": False,
        "abstract_boost":   True,
    },
    {
        "label": "concept art",
        "weight": 0.18,
        "incompatible_subject_types": [],
        "incompatible_themes": [],
        "abstract_penalty": False,
        "abstract_boost":   True,
    },
    {
        "label": "architectural visualization",
        "weight": 0.08,
        "incompatible_subject_types": ["character", "phenomenon"],
        "incompatible_themes": ["fantasy"],
        "abstract_penalty": False,
        "abstract_boost":   False,
    },
    {
        "label": "hand-drawn ink with color wash",
        "weight": 0.06,
        "incompatible_subject_types": [],
        "incompatible_themes": ["space"],
        "abstract_penalty": False,
        "abstract_boost":   False,
    },
]

RENDER_STABILITY_MULTIPLIERS = {
    "stable": {
        "photorealistic":               1.0,
        "matte painting":               1.0,
        "oil paint render":             1.0,
        "concept art":                  1.0,
        "architectural visualization":  1.0,
        "hand-drawn ink with color wash": 1.0,
    },
    "moderate": {
        "photorealistic":               0.55,
        "matte painting":               1.30,
        "oil paint render":             1.20,
        "concept art":                  1.25,
        "architectural visualization":  0.80,
        "hand-drawn ink with color wash": 1.00,
    },
    "unstable": {
        "photorealistic":               0.25,
        "matte painting":               1.50,
        "oil paint render":             1.40,
        "concept art":                  1.50,
        "architectural visualization":  0.30,
        "hand-drawn ink with color wash": 1.10,
    },
}

RENDER_QUALITY_MARKERS = [
    {
        "label": "realistic material textures",
        "weight": 0.25,
        "valid_for": ["organic", "hard_mineral", "fabricated"],
        "incompatible_render": ["concept art", "hand-drawn ink with color wash"],
    },
    {
        "label": "volumetric atmospheric glow",
        "weight": 0.20,
        "valid_for": ["organic"],
        "incompatible_render": ["hand-drawn ink with color wash"],
    },
    {
        "label": "fine surface detail",
        "weight": 0.20,
        "valid_for": ["organic", "hard_mineral"],
        "incompatible_render": ["hand-drawn ink with color wash"],
    },
    {
        "label": "atmospheric depth and haze",
        "weight": 0.20,
        "valid_for": ["organic", "hard_mineral", "fabricated", "atmospheric"],
        "incompatible_render": [],
    },
    {
        "label": "specular reflections on polished surfaces",
        "weight": 0.15,
        "valid_for": ["fabricated", "hard_mineral"],
        "incompatible_render": ["hand-drawn ink with color wash", "concept art"],
    },
    {
        "label": "light diffraction on hard surfaces",
        "weight": 0.10,
        "valid_for": ["fabricated"],
        "incompatible_render": ["hand-drawn ink with color wash", "concept art", "oil paint render"],
    },
]


# =============================================================================
# SEMANTIC TEMPLATES — v2.3 SDXL-OPTIMIZED
#
# All templates converted from prose-style narration to
# visual descriptor chunk grammar.
#
# Design rules applied:
#   - Subject labels are visual nouns, not literary descriptions
#   - Location labels ground the scene spatially
#   - Environment labels add visible atmosphere or geometry
#   - Camera angle labels use SDXL-native photographic language
#   - Prose connectives removed: "something has happened here",
#     "at the center of it all", "barely visible through it", etc.
#   - Templates shortened by ~25–30% on average
#   - Fragmented/observational rhythms preserved via comma separation
# =============================================================================

SEMANTIC_TEMPLATES_BY_TYPE = {

    "structure": [

        # Primary upward — compact visual anchor
        {
            "template": "{subject}, {location}, {environment}",
            "uses_condition": False,
            "uses_suffix": False,
            "uses_camera_angle": False,
            "weight": 0.11,
        },

        # Environment-first with dash separator — SDXL responds to this rhythm
        {
            "template": "{environment}, {subject}, {location}",
            "uses_condition": False,
            "uses_suffix": False,
            "uses_camera_angle": False,
            "weight": 0.10,
        },

        # Scale contrast — subject towering
        {
            "template": "{subject} towering over {location}, {environment}",
            "uses_condition": False,
            "uses_suffix": True,
            "uses_camera_angle": False,
            "weight": 0.10,
        },

        # Camera angle explicit — photographic framing
        {
            "template": "{camera_angle}, {subject}, {location}, {environment}",
            "uses_condition": False,
            "uses_suffix": False,
            "uses_camera_angle": True,
            "weight": 0.10,
        },

        # Deep immersion — subject partially obscured by atmosphere
        {
            "template": "{subject} partially hidden by {environment}, {location}",
            "uses_condition": False,
            "uses_suffix": False,
            "uses_camera_angle": False,
            "weight": 0.09,
        },

        # Ruin framing — decay aesthetic
        {
            "template": "ruins of {subject}, {location}, {environment}",
            "uses_condition": False,
            "uses_suffix": False,
            "uses_camera_angle": False,
            "weight": 0.08,
        },

        # Close-detail read
        {
            "template": "{subject}, {location}, {environment} partially obscuring",
            "uses_condition": False,
            "uses_suffix": False,
            "uses_camera_angle": False,
            "weight": 0.08,
        },

        # Scale-establishing
        {
            "template": "{subject}, {location}, {environment} stretching to the horizon",
            "uses_condition": False,
            "uses_suffix": True,
            "uses_camera_angle": False,
            "weight": 0.09,
        },

        # Condition + environment
        {
            "template": "{subject}, {location}, {condition}, {environment}",
            "uses_condition": True,
            "uses_suffix": False,
            "uses_camera_angle": False,
            "weight": 0.10,
        },

        # Dominant silhouette — strong latent activator
        {
            "template": "{subject} silhouetted against {environment}, {location}",
            "uses_condition": False,
            "uses_suffix": False,
            "uses_camera_angle": False,
            "weight": 0.08,
        },

        # Compound location — all three grounding elements as visual chunks
        {
            "template": "{location}, {environment}, {subject} dominating the skyline",
            "uses_condition": False,
            "uses_suffix": False,
            "uses_camera_angle": False,
            "weight": 0.07,
        },
    ],

    "character": [

        # Scale contrast — primary
        {
            "template": "{subject}, {location}, dwarfed by {environment}",
            "uses_condition": False,
            "uses_suffix": False,
            "uses_camera_angle": False,
            "weight": 0.12,
        },

        # Movement through environment
        {
            "template": "{subject} moving through {location}, {environment} ahead",
            "uses_condition": False,
            "uses_suffix": False,
            "uses_camera_angle": False,
            "weight": 0.11,
        },

        # Silhouette — strong graphic read
        {
            "template": "silhouette of {subject}, {environment}, {location}",
            "uses_condition": False,
            "uses_suffix": False,
            "uses_camera_angle": False,
            "weight": 0.11,
        },

        # Compact fragment — strong SDXL chunk rhythm
        {
            "template": "{subject}, {location}, {environment} beyond",
            "uses_condition": False,
            "uses_suffix": True,
            "uses_camera_angle": False,
            "weight": 0.10,
        },

        # Standing — environmental framing
        {
            "template": "{subject}, {location}, {environment} behind them",
            "uses_condition": False,
            "uses_suffix": False,
            "uses_camera_angle": False,
            "weight": 0.09,
        },

        # Rear silhouette — seen from behind looking into the scene
        {
            "template": "{subject} from behind, facing {environment}, {location}",
            "uses_condition": False,
            "uses_suffix": False,
            "uses_camera_angle": False,
            "weight": 0.09,
        },

        # Environment-first — character absorbed
        {
            "template": "{environment}, {subject}, {location}",
            "uses_condition": False,
            "uses_suffix": False,
            "uses_camera_angle": False,
            "weight": 0.08,
        },

        # Condition variant
        {
            "template": "{subject}, {location}, {condition}, {environment}",
            "uses_condition": True,
            "uses_suffix": False,
            "uses_camera_angle": False,
            "weight": 0.11,
        },

        # Camera angle — SDXL-native observational framing
        {
            "template": "{camera_angle}, {subject}, {location}, {environment}",
            "uses_condition": False,
            "uses_suffix": False,
            "uses_camera_angle": True,
            "weight": 0.10,
        },

        # Compact present-tense anchor
        {
            "template": "{subject}, {location}, {environment}",
            "uses_condition": False,
            "uses_suffix": False,
            "uses_camera_angle": False,
            "weight": 0.09,
        },
    ],

    "vehicle": [

        # Motion primary
        {
            "template": "{subject} crossing {location}, {environment}",
            "uses_condition": False,
            "uses_suffix": True,
            "uses_camera_angle": False,
            "weight": 0.14,
        },

        # Static / hovering
        {
            "template": "{subject}, {location}, {environment} behind it",
            "uses_condition": False,
            "uses_suffix": False,
            "uses_camera_angle": False,
            "weight": 0.11,
        },

        # Distant scale read
        {
            "template": "distant view, {subject} crossing {location}, {environment}",
            "uses_condition": False,
            "uses_suffix": True,
            "uses_camera_angle": False,
            "weight": 0.12,
        },

        # Silhouette
        {
            "template": "{subject} silhouetted against {environment}, {location}",
            "uses_condition": False,
            "uses_suffix": False,
            "uses_camera_angle": False,
            "weight": 0.11,
        },

        # Emergence
        {
            "template": "{subject} emerging from {location}, {environment} ahead",
            "uses_condition": False,
            "uses_suffix": False,
            "uses_camera_angle": False,
            "weight": 0.10,
        },

        # Environment-first
        {
            "template": "{environment}, {subject}, {location}",
            "uses_condition": False,
            "uses_suffix": False,
            "uses_camera_angle": False,
            "weight": 0.09,
        },

        # Condition variant
        {
            "template": "{subject} crossing {location}, {condition}, {environment}",
            "uses_condition": True,
            "uses_suffix": False,
            "uses_camera_angle": False,
            "weight": 0.12,
        },

        # Camera angle — establishing shot language
        {
            "template": "{camera_angle}, {subject}, {location}, {environment}",
            "uses_condition": False,
            "uses_suffix": False,
            "uses_camera_angle": True,
            "weight": 0.11,
        },

        # Scale-first — compact anchoring
        {
            "template": "{subject}, {location}, partially obscured by {environment}",
            "uses_condition": False,
            "uses_suffix": False,
            "uses_camera_angle": False,
            "weight": 0.10,
        },
    ],

    "phenomenon": [

        # Spreading — primary
        {
            "template": "{subject} spreading across {location}, {environment}",
            "uses_condition": False,
            "uses_suffix": False,
            "uses_camera_angle": False,
            "weight": 0.14,
        },

        # Caused-by inversion — environment sourced from phenomenon
        {
            "template": "{environment} from {subject}, {location}",
            "uses_condition": False,
            "uses_suffix": False,
            "uses_camera_angle": False,
            "weight": 0.12,
        },

        # Wide survey
        {
            "template": "wide shot, {location}, {subject} dominating, {environment}",
            "uses_condition": False,
            "uses_suffix": True,
            "uses_camera_angle": False,
            "weight": 0.12,
        },

        # Illumination primary — strong lighting activator
        {
            "template": "{location} lit by {subject}, {environment}",
            "uses_condition": False,
            "uses_suffix": False,
            "uses_camera_angle": False,
            "weight": 0.11,
        },

        # Subject consuming — presence declaration
        {
            "template": "{subject} consuming {location}, {environment}",
            "uses_condition": False,
            "uses_suffix": False,
            "uses_camera_angle": False,
            "weight": 0.10,
        },

        # Overhead phenomenon — below looking up
        {
            "template": "{location} beneath {subject}, {environment}",
            "uses_condition": False,
            "uses_suffix": False,
            "uses_camera_angle": False,
            "weight": 0.09,
        },

        # Condition variant
        {
            "template": "{subject} spreading across {location}, {condition}, {environment}",
            "uses_condition": True,
            "uses_suffix": False,
            "uses_camera_angle": False,
            "weight": 0.11,
        },

        # Camera angle — overhead phenomenon
        {
            "template": "{camera_angle}, {subject} above {location}, {environment}",
            "uses_condition": False,
            "uses_suffix": False,
            "uses_camera_angle": True,
            "weight": 0.11,
        },

        # Compact observation — strong chunk grammar
        {
            "template": "{location}, {subject} overhead, {environment}",
            "uses_condition": False,
            "uses_suffix": False,
            "uses_camera_angle": False,
            "weight": 0.10,
        },
    ],
}


# =============================================================================
# RENDER TEMPLATES — unchanged structure, label updated for consistency
# =============================================================================

RENDER_TEMPLATES = [
    {
        "template": "{render_medium}, {lens}",
        "weight": 0.45,
    },
    {
        "template": "{render_medium} with {quality_marker}, {lens}",
        "weight": 0.40,
    },
    {
        "template": "{lens}, {render_medium} aesthetic",
        "weight": 0.15,
    },
]


# =============================================================================
# SCENE_SUFFIX — unchanged from v2.2
# =============================================================================

SCENE_SUFFIX = [
    {
        "label": "",
        "weight": 0.72,
    },
    {
        "label": "barely visible in the distance",
        "weight": 0.10,
    },
    {
        "label": "partially hidden by haze",
        "weight": 0.07,
    },
    {
        "label": "on the horizon",
        "weight": 0.06,
    },
    {
        "label": "framing the horizon",
        "weight": 0.05,
    },
]


# =============================================================================
# TRAIT PAIR MEMORY — v2.3 scaffolding (unchanged)
# =============================================================================

class TraitPairMemory:
    """
    Lightweight in-memory scaffolding for tracking trait co-occurrences.
    Records which pairs appear together across generations.
    Exposes hooks for future reinforcement learning integration.
    """

    def __init__(self):
        self._pairs: dict[tuple[str, str], int] = {}

    def _canonical_pair(self, a: str, b: str) -> tuple[str, str]:
        return (a, b) if a <= b else (b, a)

    def record(self, traits: list[str]) -> None:
        for i in range(len(traits)):
            for j in range(i + 1, len(traits)):
                pair = self._canonical_pair(traits[i], traits[j])
                self._pairs[pair] = self._pairs.get(pair, 0) + 1

    def get_count(self, a: str, b: str) -> int:
        return self._pairs.get(self._canonical_pair(a, b), 0)

    def top_pairs(self, n: int = 20) -> list[tuple[tuple[str, str], int]]:
        return sorted(self._pairs.items(), key=lambda x: x[1], reverse=True)[:n]

    def get_all(self) -> dict[tuple[str, str], int]:
        return dict(self._pairs)

    def record_score(self, a: str, b: str, score: float) -> None:
        pass


# =============================================================================
# DIVERSITY DECAY — v2.3 (unchanged)
# =============================================================================

DIVERSITY_WINDOW_SIZE    = 8
DIVERSITY_DECAY_FACTOR   = 0.55
DIVERSITY_MIN_WEIGHT     = 0.05

class DiversityTracker:
    """
    Rolling window anti-repetition tracker.
    """

    def __init__(
        self,
        window_size: int = DIVERSITY_WINDOW_SIZE,
        decay_factor: float = DIVERSITY_DECAY_FACTOR,
        min_weight: float = DIVERSITY_MIN_WEIGHT,
    ):
        self._window_size   = window_size
        self._decay_factor  = decay_factor
        self._min_weight    = min_weight
        self._history: dict[str, list[str]] = {}

    def push(self, category: str, label: str) -> None:
        history = self._history.setdefault(category, [])
        history.append(label)
        if len(history) > self._window_size:
            history.pop(0)

    def apply_decay(self, category: str, items: list[dict], weight_key: str = "weight") -> list[dict]:
        history = self._history.get(category, [])
        if not history:
            return items

        from collections import Counter
        counts = Counter(history)

        result = []
        for item in items:
            label = item["label"]
            count = counts.get(label, 0)
            if count == 0:
                result.append(item)
            else:
                decayed = item[weight_key] * (self._decay_factor ** count)
                decayed = max(decayed, self._min_weight)
                result.append({**item, weight_key: decayed})

        return result


# =============================================================================
# COMPATIBILITY HELPERS — v2.3 (all v2.2 helpers preserved + new ones)
# =============================================================================

def is_lens_framing_compatible(lens: str, framing: str) -> bool:
    return (lens, framing) not in LENS_FRAMING_INCOMPATIBLE


def is_lighting_compatible(time_label: str, quality_label: str) -> bool:
    return (time_label, quality_label) not in LIGHTING_INCOMPATIBLE


def is_render_lighting_compatible(time_label: str, render_label: str) -> bool:
    return (time_label, render_label) not in RENDER_LIGHTING_INCOMPATIBLE


def is_render_quality_compatible(quality_marker: dict, render_label: str) -> bool:
    return render_label not in quality_marker.get("incompatible_render", [])


def is_render_subject_compatible(render: dict, subject_type: str, theme: str) -> bool:
    if subject_type in render.get("incompatible_subject_types", []):
        return False
    if theme in render.get("incompatible_themes", []):
        return False
    return True


def filter_locations_for_subject(locations: list, subject_type: str, theme: str) -> list:
    return [
        loc for loc in locations
        if subject_type in loc["valid_for"]
        and theme in loc.get("themes", [theme])
    ]


def get_lighting_time(theme: str) -> list:
    if theme == "space":
        return LIGHTING_TIME["space_only"]
    return LIGHTING_TIME["universal"]


def get_environmental_condition(theme: str) -> list:
    if theme == "space":
        return ENVIRONMENTAL_CONDITION_SPACE
    return ENVIRONMENTAL_CONDITION


def get_mood_list() -> list[dict]:
    return [
        {"label": mood_label, "weight": data["weight"]}
        for mood_label, data in MOOD_SEMANTICS.items()
    ]


def apply_mood_theme_weight(mood_label: str, theme_name: str, base_weight: float) -> float:
    compat = MOOD_THEME_COMPATIBILITY.get(mood_label, {})
    if theme_name in compat.get("preferred", []):
        return base_weight * 1.5
    if theme_name in compat.get("suppressed", []):
        return base_weight * MOOD_SUPPRESSED_WEIGHT
    if theme_name in compat.get("rare", []):
        return base_weight * MOOD_RARE_WEIGHT
    return base_weight


def apply_mood_condition_weight(mood_label: str, condition_label: str, base_weight: float) -> float:
    compat = MOOD_CONDITION_COMPATIBILITY.get(mood_label, {})
    if condition_label in compat.get("preferred", []):
        return base_weight * 1.6
    if condition_label in compat.get("suppressed", []):
        return base_weight * MOOD_SUPPRESSED_WEIGHT
    if condition_label in compat.get("rare", []):
        return base_weight * MOOD_RARE_WEIGHT
    return base_weight


def apply_render_stability(render_items: list[dict], stability: SubjectStability) -> list[dict]:
    multipliers = RENDER_STABILITY_MULTIPLIERS.get(stability, {})
    result = []
    for item in render_items:
        multiplier = multipliers.get(item["label"], 1.0)
        adjusted_weight = item["weight"] * multiplier
        result.append({**item, "weight": adjusted_weight})
    return result


def is_camera_angle_framing_compatible(angle: str, framing: str) -> bool:
    return (angle, framing) not in CAMERA_ANGLE_FRAMING_INCOMPATIBLE


def get_camera_angle_affinity_boost(angle: str, subject_type: str) -> float:
    affinity_types = CAMERA_ANGLE_SUBJECT_AFFINITY.get(angle, [])
    return 1.35 if subject_type in affinity_types else 1.0


def score_scene_density(elements: list[dict]) -> int:
    return sum(e.get("density_score", 0) for e in elements)

