from django.core.management.base import BaseCommand
from shsat.models import Test, Question

ELA_QUESTIONS = [
    # Revising/Editing
    {
        "question_number": 1,
        "question_type": "multiple_choice",
        "topic": "Revising/Editing",
        "difficulty": "easy",
        "passage_group_id": "",
        "passage_title": "",
        "passage_text": "",
        "question_text": (
            "Which of the following is the best way to combine the two sentences below?\n\n"
            "The scientist conducted the experiment carefully. She recorded every result in her notebook."
        ),
        "choice_a": "The scientist conducted the experiment carefully, and she recorded every result in her notebook.",
        "choice_b": "The scientist conducted the experiment carefully she recorded every result in her notebook.",
        "choice_c": "The scientist conducted the experiment carefully; however, she recorded every result in her notebook.",
        "choice_d": "The scientist conducted the experiment carefully, but she recorded every result in her notebook.",
        "correct_answer": "A",
        "explanation": "Two independent clauses can be joined with a comma and coordinating conjunction 'and' when the ideas are related and sequential. 'However' implies contrast, which doesn't fit here.",
    },
    {
        "question_number": 2,
        "question_type": "multiple_choice",
        "topic": "Revising/Editing",
        "difficulty": "medium",
        "passage_group_id": "",
        "passage_title": "",
        "passage_text": "",
        "question_text": (
            "Read the paragraph and answer the question.\n\n"
            "(1) Many cities have begun replacing streetlights with LED bulbs. (2) LED bulbs use significantly less energy than traditional bulbs. (3) They also last much longer. (4) Critics argue that the upfront cost is too high. (5) Despite this, most cities recoup the cost within three years.\n\n"
            "Which sentence, if added after sentence 3, would best support the paragraph's main idea?"
        ),
        "choice_a": "Some residents prefer the warmer color of traditional bulbs.",
        "choice_b": "This reduces maintenance costs, since workers need to replace bulbs less often.",
        "choice_c": "LED technology was first developed in the 1960s.",
        "choice_d": "The mayor announced the LED initiative at a press conference last spring.",
        "correct_answer": "B",
        "explanation": "The paragraph argues for the practical benefits of LED streetlights. Choice B directly supports the cost and maintenance advantages already described in sentences 2 and 3.",
    },
    # Passage-based reading
    {
        "question_number": 3,
        "question_type": "multiple_choice",
        "topic": "Reading Comprehension",
        "difficulty": "medium",
        "passage_group_id": "ela_passage_1",
        "passage_title": "The Urban Forest",
        "passage_text": (
            "Trees in cities do more than provide shade. Urban forests — the collective term for all trees "
            "growing in a city — filter air pollutants, reduce stormwater runoff, and lower temperatures in "
            "neighborhoods that would otherwise become heat islands. Studies show that streets lined with "
            "mature trees can be up to 10 degrees cooler than streets without them.\n\n"
            "Despite these benefits, urban trees face serious threats. Soil compaction from foot traffic and "
            "construction damages root systems. Pollution weakens tree immune systems, making them vulnerable "
            "to pests. And when budgets are cut, tree maintenance is often the first thing to go.\n\n"
            "Some cities have responded by passing urban forestry ordinances that require developers to plant "
            "one tree for every tree removed during construction. Others have launched community planting "
            "programs that recruit volunteers to help maintain the urban forest. These efforts recognize a "
            "simple truth: a city without trees is a city that is harder to live in."
        ),
        "question_text": "According to the passage, what is one reason urban trees are vulnerable to pests?",
        "choice_a": "Cities do not plant enough trees to sustain healthy populations.",
        "choice_b": "Pollution weakens trees, reducing their ability to resist infestation.",
        "choice_c": "Budget cuts mean trees are rarely watered or fertilized.",
        "choice_d": "Foot traffic prevents tree roots from absorbing nutrients.",
        "correct_answer": "B",
        "explanation": "The passage states directly: 'Pollution weakens tree immune systems, making them vulnerable to pests.' This is choice B.",
    },
    {
        "question_number": 4,
        "question_type": "multiple_choice",
        "topic": "Reading Comprehension",
        "difficulty": "medium",
        "passage_group_id": "ela_passage_1",
        "passage_title": "The Urban Forest",
        "passage_text": "",  # Same passage group — no need to repeat
        "question_text": (
            "Which statement best describes the author's purpose in the final paragraph?"
        ),
        "choice_a": "To argue that volunteer programs are more effective than government ordinances.",
        "choice_b": "To show that the problem of urban tree loss is too large to solve.",
        "choice_c": "To present solutions that cities are using and emphasize why trees matter.",
        "choice_d": "To criticize developers who remove trees during construction.",
        "correct_answer": "C",
        "explanation": "The final paragraph describes two types of city responses (ordinances and volunteer programs) and ends with a positive conclusion about why trees matter. The tone is constructive, not critical.",
    },
    {
        "question_number": 5,
        "question_type": "multiple_choice",
        "topic": "Reading Comprehension",
        "difficulty": "hard",
        "passage_group_id": "ela_passage_1",
        "passage_title": "The Urban Forest",
        "passage_text": "",
        "question_text": (
            "As used in the passage, the word 'reckon' most closely means:\n\n"
            "Wait — re-read: 'These efforts recognize a simple truth: a city without trees is a city that is harder to live in.'\n\n"
            "What does the author imply by calling this a 'simple truth'?"
        ),
        "choice_a": "The idea is obvious and requires no evidence.",
        "choice_b": "The idea is straightforward but often ignored or undervalued.",
        "choice_c": "The idea is too simple to guide complex city planning.",
        "choice_d": "The idea was recently discovered by urban scientists.",
        "correct_answer": "B",
        "explanation": "By framing it as a 'simple truth,' the author implies it should be self-evident — yet the need to state it suggests it has been overlooked. The passage's examples of budget cuts and threats reinforce that this obvious fact is often ignored in practice.",
    },
]

MATH_QUESTIONS = [
    {
        "question_number": 1,
        "question_type": "multiple_choice",
        "topic": "Algebra",
        "difficulty": "easy",
        "passage_group_id": "",
        "passage_title": "",
        "passage_text": "",
        "question_text": "If 3x − 7 = 14, what is the value of x?",
        "choice_a": "3",
        "choice_b": "5",
        "choice_c": "7",
        "choice_d": "9",
        "correct_answer": "C",
        "explanation": "3x − 7 = 14 → 3x = 21 → x = 7.",
    },
    {
        "question_number": 2,
        "question_type": "multiple_choice",
        "topic": "Number Theory",
        "difficulty": "easy",
        "passage_group_id": "",
        "passage_title": "",
        "passage_text": "",
        "question_text": (
            "A bag contains 4 red marbles, 6 blue marbles, and 2 green marbles. "
            "If one marble is chosen at random, what is the probability it is blue?"
        ),
        "choice_a": "1/6",
        "choice_b": "1/3",
        "choice_c": "1/2",
        "choice_d": "2/3",
        "correct_answer": "C",
        "explanation": "6 blue out of 12 total = 6/12 = 1/2.",
    },
    {
        "question_number": 3,
        "question_type": "multiple_choice",
        "topic": "Geometry",
        "difficulty": "medium",
        "passage_group_id": "",
        "passage_title": "",
        "passage_text": "",
        "question_text": (
            "A rectangle has a length of 12 cm and a width of 5 cm. "
            "What is the length of its diagonal?"
        ),
        "choice_a": "11 cm",
        "choice_b": "13 cm",
        "choice_c": "15 cm",
        "choice_d": "17 cm",
        "correct_answer": "B",
        "explanation": "By the Pythagorean theorem: √(12² + 5²) = √(144 + 25) = √169 = 13.",
    },
    {
        "question_number": 4,
        "question_type": "multiple_choice",
        "topic": "Algebra",
        "difficulty": "medium",
        "passage_group_id": "",
        "passage_title": "",
        "passage_text": "",
        "question_text": (
            "A store sells notebooks for $3 each and pens for $1.50 each. "
            "Maria buys a total of 10 items and spends exactly $24. "
            "How many notebooks did she buy?"
        ),
        "choice_a": "4",
        "choice_b": "5",
        "choice_c": "6",
        "choice_d": "8",
        "correct_answer": "C",
        "explanation": "Let n = notebooks, p = pens. n + p = 10 and 3n + 1.5p = 24. Substituting p = 10 − n: 3n + 1.5(10 − n) = 24 → 3n + 15 − 1.5n = 24 → 1.5n = 9 → n = 6.",
    },
    {
        "question_number": 5,
        "question_type": "multiple_choice",
        "topic": "Statistics",
        "difficulty": "medium",
        "passage_group_id": "",
        "passage_title": "",
        "passage_text": "",
        "question_text": (
            "The ages of five students are: 13, 14, 13, 15, and 16. "
            "What is the positive difference between the mean and the median of these ages?"
        ),
        "choice_a": "0",
        "choice_b": "0.2",
        "choice_c": "0.5",
        "choice_d": "1",
        "correct_answer": "B",
        "explanation": "Sorted: 13, 13, 14, 15, 16. Median = 14. Mean = (13+14+13+15+16)/5 = 71/5 = 14.2. Difference = 14.2 − 14 = 0.2.",
    },
]


class Command(BaseCommand):
    help = "Seed a demo SHSAT practice test with sample questions"

    def handle(self, *args, **options):
        test, created = Test.objects.get_or_create(
            title="Demo Practice Test",
            defaults={
                "source": "School of Critical Thinking",
                "is_free": True,
                "is_published": True,
                "order": 1,
            },
        )
        if not created:
            # Republish and clear existing questions so we can re-seed cleanly
            test.is_published = True
            test.save()
            test.questions.all().delete()
            self.stdout.write("Existing demo test found — questions cleared and re-seeded.")

        for q in ELA_QUESTIONS:
            Question.objects.create(test=test, section="ELA", **q)

        for q in MATH_QUESTIONS:
            Question.objects.create(test=test, section="Math", **q)

        total = test.questions.count()
        self.stdout.write(self.style.SUCCESS(
            f"Done — '{test.title}' has {total} questions ({len(ELA_QUESTIONS)} ELA, {len(MATH_QUESTIONS)} Math)."
        ))
