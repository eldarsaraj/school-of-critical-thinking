MODULES = [
    # ── Level 1: Discovering How the World Works ─────────────────────────────
    {
        "number": 1,
        "slug": "seeing-patterns",
        "title": "Seeing Patterns",
        "level": 1,
        "level_title": "Discovering How the World Works",
        "ages": "8–11",
        "core": "The world contains patterns, but not every pattern is real.",
        "is_available": True,
        "amazon_url": None,   # fill once the Amazon listing is live
        "has_sample": True,
        "description": (
            "Children encounter patterns constantly, in sequences, in nature, in other "
            "people's behavior, but rarely stop to ask whether those patterns are real "
            "or imagined. This module builds the first cognitive skill: seeing structure "
            "before explaining it. Students learn to spot genuine patterns, classify what "
            "they observe, and recognize when an apparent pattern is noise, coincidence, "
            "or wishful thinking. Designed as a weekly supplement: one lesson fits "
            "alongside any existing homeschool or after-school curriculum without displacing it."
        ),
        "at_a_glance": [
            ("Age range", "8–11"),
            ("Duration", "52 lessons · one per week · one full school year"),
            ("Lesson length", "20–30 minutes"),
            ("Format", "Paperback and ebook"),
            ("Who teaches it", "Parent-led · no specialist background required"),
            ("Independent use", "Lessons can be read by the child, but exercises and discussion questions are designed for parent–child dialogue"),
            ("Viewpoint", "Worldview-neutral · compatible with any religious or secular core curriculum"),
            ("Intended use", "Weekly supplement · works alongside any core curriculum"),
            ("Grade equivalent", "Roughly grades 3–6, but skill-based rather than grade-locked"),
        ],
        "who_it_is_for": (
            "This module is designed for children aged 8–11, whether they are homeschooled "
            "full-time or studying at home after school. It works as a standalone course or "
            "as part of the full nine-module curriculum. Parents with no background in "
            "philosophy, logic, or education can teach it directly from the book. It is "
            "equally suited to children who are advanced readers and those who prefer to "
            "work through lessons with a parent."
        ),
        "how_you_teach_it": (
            "Each lesson opens with a short story or real-world example that the parent "
            "reads aloud or the child reads independently. A thinking question follows, "
            "designed to spark a conversation, not to be answered in a workbook. "
            "Exercises and discussion questions complete each lesson; these are where the "
            "parent's role matters most. Total preparation time per lesson is minimal: "
            "the lesson plan is built into the book."
        ),
        "units": [
            {
                "number": 1,
                "title": "Discovering Patterns",
                "lessons": "Lessons 1–10",
                "description": (
                    "Patterns are hiding everywhere: in forests, in music, in the way people "
                    "behave, even in the shapes of snowflakes. These ten lessons train students "
                    "to notice the hidden order in the world around them for the first time."
                ),
            },
            {
                "number": 2,
                "title": "Recognizing Patterns",
                "lessons": "Lessons 11–20",
                "description": (
                    "Now things get sharper. Students learn how patterns are actually built: "
                    "how to sort and classify, find sequences, spot growth and cycles, and "
                    "predict what comes next with increasing precision."
                ),
            },
            {
                "number": 3,
                "title": "Hidden Patterns",
                "lessons": "Lessons 21–30",
                "description": (
                    "The patterns found so far were sitting on the surface. Now students learn "
                    "to find patterns that are hidden, buried beneath appearances, encoded in "
                    "games and language, embedded in group behavior and markets."
                ),
            },
            {
                "number": 4,
                "title": "When Patterns Mislead",
                "lessons": "Lessons 31–40",
                "description": (
                    "The most important section of the book. The brain is so good at finding "
                    "patterns that it regularly invents ones that aren't there. Students learn "
                    "to recognize coincidences, superstitions, confirmation bias, and the "
                    "difference between correlation and causation."
                ),
            },
            {
                "number": 5,
                "title": "Using Patterns to Think",
                "lessons": "Lessons 41–52",
                "description": (
                    "The payoff. Students learn to use patterns as active thinking tools: "
                    "to predict outcomes, learn faster from mistakes, build better habits, "
                    "and see the world with the kind of structural clarity most people never develop."
                ),
            },
        ],
        "how_it_works": [
            "Each lesson is 20-30 minutes; one per week fits naturally into a school schedule.",
            "No specialist background required. Full lesson plans are included.",
            "Lessons are built around stories and discussion questions, not worksheets. The exercises require thinking and conversation, not fill-in-the-blank answers.",
            "Every unit includes exercises, discussion questions, and a short assessment.",
        ],
        "book": {
            "title": "Seeing Patterns",
            "cover": "images/books/seeing-patterns-single-cover.jpg",
            "tagline": (
                "The complete Seeing Patterns module in book form: "
                "52 structured lessons for ages 8-11, ready to use at home or in the classroom."
            ),
            "buy_url": "https://www.amazon.com/dp/B0GX6NJ22H",
        },
        "prev_slug": None,
        "prev_title": None,
        "next_slug": "chance-and-uncertainty",
        "next_title": "Chance and Uncertainty",
    },

    # ── Level 1: continued ───────────────────────────────────────────────────
    {
        "number": 2,
        "slug": "chance-and-uncertainty",
        "title": "Chance and Uncertainty",
        "level": 1,
        "level_title": "Discovering How the World Works",
        "ages": "8–11",
        "core": "Smart thinkers make better bets, not perfect predictions.",
        "is_available": False,
        "has_sample": False,
        "topics": ["Randomness and probability", "Coin flips and dice",
                   "Good guesses vs bad guesses", "Luck vs skill",
                   "Thinking under uncertainty"],
        "prev_slug": "seeing-patterns",
        "prev_title": "Seeing Patterns",
        "next_slug": "cause-and-effect",
        "next_title": "Cause and Effect",
    },
    {
        "number": 3,
        "slug": "cause-and-effect",
        "title": "Cause and Effect",
        "level": 1,
        "level_title": "Discovering How the World Works",
        "ages": "8–11",
        "core": "Understanding something means understanding what produces it.",
        "is_available": False,
        "has_sample": False,
        "topics": ["Cause vs coincidence", "Mechanisms", "Simple experiments",
                   "Chain reactions and multiple causes", "Testing ideas"],
        "prev_slug": "chance-and-uncertainty",
        "prev_title": "Chance and Uncertainty",
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
        "prev_slug": "cause-and-effect",
        "prev_title": "Cause and Effect",
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
