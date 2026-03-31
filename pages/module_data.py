MODULES = [
    # ── Level 1: Discovering How the World Works ─────────────────────────────
    {
        "number": 1,
        "slug": "seeing-patterns",
        "title": "Seeing Patterns",
        "level": 1,
        "level_title": "Discovering How the World Works",
        "ages": "8–10",
        "core": "The world contains patterns — but not every pattern is real.",
        "is_available": True,
        "amazon_url": None,   # fill once the Amazon listing is live
        "has_sample": True,
        "description": (
            "Children encounter patterns constantly — in sequences, in nature, in other "
            "people's behaviour — but rarely stop to ask whether those patterns are real "
            "or imagined. This module builds the first cognitive skill: seeing structure "
            "before explaining it. Students learn to spot genuine patterns, classify what "
            "they observe, and recognise when an apparent pattern is noise, coincidence, "
            "or wishful thinking."
        ),
        "units": [
            {
                "number": 1,
                "title": "Patterns Everywhere",
                "description": (
                    "What a pattern actually is, and why the brain is so eager to find them. "
                    "Students survey patterns in numbers, shapes, language, and daily life."
                ),
            },
            {
                "number": 2,
                "title": "Classification and Sequences",
                "description": (
                    "Grouping things by shared properties and ordering them by a rule. "
                    "Students practise sorting, labelling, and predicting the next item in a sequence."
                ),
            },
            {
                "number": 3,
                "title": "Analogies",
                "description": (
                    "Recognising that two different things share the same structural relationship. "
                    "Students learn to read analogies, construct their own, and use them to reason "
                    "about unfamiliar situations."
                ),
            },
            {
                "number": 4,
                "title": "Patterns in Nature and Behaviour",
                "description": (
                    "Patterns in living things, seasons, growth, and how people act. "
                    "Students observe and record, then distinguish reliable patterns from "
                    "one-off observations."
                ),
            },
            {
                "number": 5,
                "title": "False Patterns and Superstition",
                "description": (
                    "Why the brain invents patterns that aren't there, and what to do about it. "
                    "Students examine superstitions, lucky streaks, and apophenia — and learn "
                    "to ask for more evidence before trusting a pattern."
                ),
            },
        ],
        "how_it_works": [
            "Each lesson is 20–30 minutes — one per week fits naturally into a school schedule.",
            "No specialist background required. Full lesson plans are included.",
            "Every unit includes exercises, discussion questions, and a short assessment.",
        ],
        "prev_slug": None,
        "prev_title": None,
        "next_slug": "cause-and-effect",
        "next_title": "Cause and Effect",
    },

    # ── Level 1: continued ───────────────────────────────────────────────────
    {
        "number": 2,
        "slug": "cause-and-effect",
        "title": "Cause and Effect",
        "level": 1,
        "level_title": "Discovering How the World Works",
        "ages": "8–10",
        "core": "Understanding something means understanding what produces it.",
        "is_available": False,
        "has_sample": False,
        "topics": ["Cause vs coincidence", "Mechanisms", "Simple experiments",
                   "Chain reactions and multiple causes", "Testing ideas"],
        "prev_slug": "seeing-patterns",
        "prev_title": "Seeing Patterns",
        "next_slug": "chance-and-uncertainty",
        "next_title": "Chance and Uncertainty",
    },
    {
        "number": 3,
        "slug": "chance-and-uncertainty",
        "title": "Chance and Uncertainty",
        "level": 1,
        "level_title": "Discovering How the World Works",
        "ages": "8–10",
        "core": "Smart thinkers make better bets, not perfect predictions.",
        "is_available": False,
        "has_sample": False,
        "topics": ["Randomness and probability", "Coin flips and dice",
                   "Good guesses vs bad guesses", "Luck vs skill",
                   "Thinking under uncertainty"],
        "prev_slug": "cause-and-effect",
        "prev_title": "Cause and Effect",
        "next_slug": "models-and-explanations",
        "next_title": "Models and Explanations",
    },

    # ── Level 2: Understanding Systems and Reasoning ─────────────────────────
    {
        "number": 4,
        "slug": "models-and-explanations",
        "title": "Models and Explanations",
        "level": 2,
        "level_title": "Understanding Systems and Reasoning",
        "ages": "11–13",
        "core": "Every explanation is a model of reality.",
        "is_available": False,
        "has_sample": False,
        "topics": ["Maps vs territory", "Assumptions and simplification",
                   "Testing and improving models", "Limits of models",
                   "Competing explanations"],
        "prev_slug": "chance-and-uncertainty",
        "prev_title": "Chance and Uncertainty",
        "next_slug": "systems-and-feedback",
        "next_title": "Systems and Feedback",
    },
    {
        "number": 5,
        "slug": "systems-and-feedback",
        "title": "Systems and Feedback",
        "level": 2,
        "level_title": "Understanding Systems and Reasoning",
        "ages": "11–13",
        "core": "Systems behave differently from individual events.",
        "is_available": False,
        "has_sample": False,
        "topics": ["Feedback loops", "Equilibrium", "Unintended consequences",
                   "Ecosystems, traffic, social systems", "Complex systems"],
        "prev_slug": "models-and-explanations",
        "prev_title": "Models and Explanations",
        "next_slug": "human-behaviour",
        "next_title": "Human Behaviour",
    },
    {
        "number": 6,
        "slug": "human-behaviour",
        "title": "Human Behaviour",
        "level": 2,
        "level_title": "Understanding Systems and Reasoning",
        "ages": "11–13",
        "core": "People respond to incentives and environments.",
        "is_available": False,
        "has_sample": False,
        "topics": ["Incentives", "Cooperation and competition",
                   "Social norms", "Decision psychology"],
        "prev_slug": "systems-and-feedback",
        "prev_title": "Systems and Feedback",
        "next_slug": "decisions-and-tradeoffs",
        "next_title": "Decisions and Tradeoffs",
    },

    # ── Level 3: Applying Thinking to Real Decisions ─────────────────────────
    {
        "number": 7,
        "slug": "decisions-and-tradeoffs",
        "title": "Decisions and Tradeoffs",
        "level": 3,
        "level_title": "Applying Thinking to Real Decisions",
        "ages": "14–16",
        "core": "Every decision involves tradeoffs.",
        "is_available": False,
        "has_sample": False,
        "topics": ["Opportunity cost", "Decision frameworks",
                   "Risk vs reward", "Long-term thinking"],
        "prev_slug": "human-behaviour",
        "prev_title": "Human Behaviour",
        "next_slug": "truth-and-evidence",
        "next_title": "Truth and Evidence",
    },
    {
        "number": 8,
        "slug": "truth-and-evidence",
        "title": "Truth and Evidence",
        "level": 3,
        "level_title": "Applying Thinking to Real Decisions",
        "ages": "14–16",
        "core": "Good thinking depends on good evidence.",
        "is_available": False,
        "has_sample": False,
        "topics": ["Evaluating claims", "Scientific reasoning",
                   "Evidence vs opinion", "Prediction vs explanation"],
        "prev_slug": "decisions-and-tradeoffs",
        "prev_title": "Decisions and Tradeoffs",
        "next_slug": "understanding-the-world",
        "next_title": "Understanding the World",
    },
    {
        "number": 9,
        "slug": "understanding-the-world",
        "title": "Understanding the World",
        "level": 3,
        "level_title": "Applying Thinking to Real Decisions",
        "ages": "14–16",
        "core": "The world becomes understandable when you see its structure.",
        "is_available": False,
        "has_sample": False,
        "topics": ["Predicting outcomes", "Analysing systems",
                   "Evaluating policies", "Solving real problems"],
        "prev_slug": "truth-and-evidence",
        "prev_title": "Truth and Evidence",
        "next_slug": None,
        "next_title": None,
    },
]

# Lookup by slug
MODULES_BY_SLUG = {m["slug"]: m for m in MODULES}
