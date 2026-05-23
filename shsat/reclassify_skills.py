import os
import sys

# Ensure the project root is on sys.path so Django can find the 'config' package.
# This script lives in shsat/, so go up one level to the project root.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from shsat.models import Question, Test

t = Test.objects.get(title='Practice Test 1')

# Each tuple: (section, stage, question_number, new_skill)
#
# ELA skill values used:
#   punctuation, usage_agreement, sentence_structure, main_idea,
#   supporting_detail, inference, vocabulary, authors_craft
#
# Math skill values used:
#   number_operations, fractions_decimals_percents, ratios_proportions,
#   algebra, functions_patterns, geometry, statistics_data, probability

updates = [
    # ── ELA ROUTING ─────────────────────────────────────────────────────────
    # Q1: "good" → "well" — adverb vs adjective, a usage (grammar) issue
    ('ELA', 'routing',  1, 'usage_agreement'),
    # Q2: neither…nor subject-verb agreement (singular "teacher" → "was")
    ('ELA', 'routing',  2, 'usage_agreement'),
    # Q3: dangling modifier — "Running through the park" attaches to leaves
    ('ELA', 'routing',  3, 'sentence_structure'),
    # Q4: irregular past tense "spreaded" → "spread"
    ('ELA', 'routing',  4, 'usage_agreement'),
    # Q5: comma splice fixed with semicolon
    ('ELA', 'routing',  5, 'sentence_structure'),
    # Q6: "According to the passage, what percentage…" — explicit fact
    ('ELA', 'routing',  6, 'supporting_detail'),
    # Q7: "bioluminescence most nearly means" — word in context
    ('ELA', 'routing',  7, 'vocabulary'),
    # Q8: why was chemosynthesis significant? — implied broader meaning
    ('ELA', 'routing',  8, 'inference'),
    # Q9: "According to the passage, how did early researchers study…"
    ('ELA', 'routing',  9, 'supporting_detail'),
    # Q10: "author most likely mentions…implications stretch beyond Earth" — author's purpose
    ('ELA', 'routing', 10, 'authors_craft'),
    # Q11: "How does the structure of the passage support the main idea" — text structure
    ('ELA', 'routing', 11, 'authors_craft'),
    # Q12: "According to the passage, why do Maya's friends expect her to sell"
    ('ELA', 'routing', 12, 'supporting_detail'),
    # Q13: "missing tooth in a polished smile" — figurative/implied meaning
    ('ELA', 'routing', 13, 'inference'),
    # Q14: "What most likely changes Maya's thinking by the end" — inference
    ('ELA', 'routing', 14, 'inference'),
    # Q15: "preserved most nearly means" — word in context
    ('ELA', 'routing', 15, 'vocabulary'),
    # Q16: "What does Maya do each morning" — explicit detail
    ('ELA', 'routing', 16, 'supporting_detail'),
    # Q17: "author most likely includes the detail about naming the clocks…in order to" — author's purpose
    ('ELA', 'routing', 17, 'authors_craft'),
    # Q18: "According to the passage, approximately how many…participated"
    ('ELA', 'routing', 18, 'supporting_detail'),
    # Q19: "which best describes conditions that pushed African Americans to leave" — inference/synthesis
    ('ELA', 'routing', 19, 'inference'),
    # Q20: "redlining most nearly refers to" — vocabulary in context
    ('ELA', 'routing', 20, 'vocabulary'),
    # Q21: "According to the passage, what cultural movement grew out of…"
    ('ELA', 'routing', 21, 'supporting_detail'),
    # Q22: "Why does the author include the paragraph about discrimination in the North" — author's purpose
    ('ELA', 'routing', 22, 'authors_craft'),
    # Q23: "Which statement best describes the author's overall point" — central idea / main idea
    ('ELA', 'routing', 23, 'main_idea'),
    # Q24: "According to Passage A, what is one reason teachers support allowing smartphones"
    ('ELA', 'routing', 24, 'supporting_detail'),
    # Q25: "What does the author of Passage B mean by…task-switches" — implied meaning
    ('ELA', 'routing', 25, 'inference'),
    # Q26: "How does Passage A's view differ from Passage B's" — comparing perspectives / inference
    ('ELA', 'routing', 26, 'inference'),
    # Q27: "Which statement would most strengthen Passage B" — rhetorical / argumentative function
    ('ELA', 'routing', 27, 'authors_craft'),
    # Q28: "cognitive capacity most nearly means" — vocabulary
    ('ELA', 'routing', 28, 'vocabulary'),
    # Q29: "student who agrees with Passage A would most likely respond…" — inference / synthesis
    ('ELA', 'routing', 29, 'inference'),

    # ── ELA EASY MODULE ──────────────────────────────────────────────────────
    # Q1: dangling modifier — "After studying…the test" should be "Carlos felt"
    ('ELA', 'easy_module',  1, 'sentence_structure'),
    # Q2: collective noun "committee" takes singular verb "is"
    ('ELA', 'easy_module',  2, 'usage_agreement'),
    # Q3: "Studys" → "Studies" — irregular noun plural
    ('ELA', 'easy_module',  3, 'usage_agreement'),
    # Q4: parallel structure — "reading, playing, cooking" (not "to cook")
    ('ELA', 'easy_module',  4, 'sentence_structure'),
    # Q5: "Which statement about worker bees can best be supported by the passage"
    ('ELA', 'easy_module',  5, 'supporting_detail'),
    # Q6: "Why does author most likely include…Nobel Prize" — author's purpose
    ('ELA', 'easy_module',  6, 'authors_craft'),
    # Q7: "Which idea is most strongly supported by the contrast" — inference from contrast
    ('ELA', 'easy_module',  7, 'inference'),
    # Q8: "obscures most nearly means" — vocabulary in context
    ('ELA', 'easy_module',  8, 'vocabulary'),
    # Q9: "which would most likely happen if all honeybees disappeared" — inference
    ('ELA', 'easy_module',  9, 'inference'),
    # Q10: "How does the final paragraph contribute to the overall structure" — text structure
    ('ELA', 'easy_module', 10, 'authors_craft'),
    # Q11: "cafeteria…like weather, something happening to him" — inferred emotion
    ('ELA', 'easy_module', 11, 'inference'),
    # Q12: "According to the passage, what does Tomás notice…while Sasha is talking"
    ('ELA', 'easy_module', 12, 'supporting_detail'),
    # Q13: "soon felt like a country he could not find on any map" — figurative phrase meaning
    ('ELA', 'easy_module', 13, 'vocabulary'),
    # Q14: "narrator's description…most strongly suggests that" — inference from detail
    ('ELA', 'easy_module', 14, 'inference'),
    # Q15: "According to the passage, what does Sasha invite Tomás to do"
    ('ELA', 'easy_module', 15, 'supporting_detail'),
    # Q16: "final sentence…mainly suggests" — inferred theme/meaning
    ('ELA', 'easy_module', 16, 'inference'),
    # Q17: "According to the passage, what is the main difference between magma and lava"
    ('ELA', 'easy_module', 17, 'supporting_detail'),
    # Q18: "Why does the author most likely include the example of Mount Tambora" — author's purpose
    ('ELA', 'easy_module', 18, 'authors_craft'),
    # Q19: "How does the structure of the passage support the author's overall view" — text structure
    ('ELA', 'easy_module', 19, 'authors_craft'),
    # Q20: "fertile most nearly means" — vocabulary
    ('ELA', 'easy_module', 20, 'vocabulary'),
    # Q21: "which factor most likely explains why shield volcanoes rarely kill" — inference
    ('ELA', 'easy_module', 21, 'inference'),
    # Q22: "What is the main purpose of the final paragraph" — author's purpose / structure
    ('ELA', 'easy_module', 22, 'authors_craft'),
    # Q23: "why is it inaccurate to describe Rosa Parks's act as spontaneous" — inference
    ('ELA', 'easy_module', 23, 'inference'),
    # Q24: "According to the passage, how did boycott organizers ensure participants could still get to work"
    ('ELA', 'easy_module', 24, 'supporting_detail'),
    # Q25: "Why does the author include Parks's quoted statement" — author's purpose
    ('ELA', 'easy_module', 25, 'authors_craft'),
    # Q26: "What can be inferred…about the boycott's broader importance"
    ('ELA', 'easy_module', 26, 'inference'),
    # Q27: "unconstitutional most nearly means" — vocabulary
    ('ELA', 'easy_module', 27, 'vocabulary'),
    # Q28: "How does the author organize the information" — text structure / organization
    ('ELA', 'easy_module', 28, 'authors_craft'),

    # ── ELA HARD MODULE ──────────────────────────────────────────────────────
    # Q1: "data show" vs "data shows" — plural subject-verb agreement
    ('ELA', 'hard_module',  1, 'usage_agreement'),
    # Q2: "whoever" vs "whomever" — pronoun case
    ('ELA', 'hard_module',  2, 'usage_agreement'),
    # Q3: revise sentence to strengthen argumentative function — rhetorical choice
    ('ELA', 'hard_module',  3, 'authors_craft'),
    # Q4: where to place new sentence for best evidence — organization / structure
    ('ELA', 'hard_module',  4, 'authors_craft'),
    # Q5: "According to Schwartz's research, why do consumers feel less satisfied" — explicit detail
    ('ELA', 'hard_module',  5, 'supporting_detail'),
    # Q6: "which of the following would a satisficer most likely do" — inference from definition
    ('ELA', 'hard_module',  6, 'inference'),
    # Q7: "liberal individualism most nearly refers to" — vocabulary in context
    ('ELA', 'hard_module',  7, 'vocabulary'),
    # Q8: "Why does the author specify that Schwartz is careful not to advocate for authoritarianism" — author's purpose
    ('ELA', 'hard_module',  8, 'authors_craft'),
    # Q9: "How does the first paragraph…relate to the rest of the passage" — text structure
    ('ELA', 'hard_module',  9, 'authors_craft'),
    # Q10: "passage implies maximizers experience more regret…primarily because" — inference
    ('ELA', 'hard_module', 10, 'inference'),
    # Q11: "accent that sounded like nobody's home country" — implied/figurative meaning
    ('ELA', 'hard_module', 11, 'inference'),
    # Q12: "what does the immigration officer's renaming symbolize" — inferred symbolic meaning
    ('ELA', 'hard_module', 12, 'inference'),
    # Q13: "interior translation most nearly means" — vocabulary/figurative phrase
    ('ELA', 'hard_module', 13, 'vocabulary'),
    # Q14: "what does narrator suggest about the self that…crossed the ocean and did not arrive" — inference
    ('ELA', 'hard_module', 14, 'inference'),
    # Q15: "laughing at something just outside the frame primarily serves to" — author's craft / purpose
    ('ELA', 'hard_module', 15, 'authors_craft'),
    # Q16: "which statement best describes the narrator's attitude toward grandmother's silence" — inference
    ('ELA', 'hard_module', 16, 'inference'),
    # Q17: "According to the passage, what is the moral failure that meritocracy risks producing" — explicit detail
    ('ELA', 'hard_module', 17, 'supporting_detail'),
    # Q18: "passage argues successful people may not fully deserve rewards because" — explicit argument
    ('ELA', 'hard_module', 18, 'supporting_detail'),
    # Q19: "solidarity most nearly means" — vocabulary
    ('ELA', 'hard_module', 19, 'vocabulary'),
    # Q20: "phrase…We do not typically deserve credit…is used to argue that" — inference/implied argument
    ('ELA', 'hard_module', 20, 'inference'),
    # Q21: "How does Sandel's proposed remedy relate to his critique" — text structure / rhetorical logic
    ('ELA', 'hard_module', 21, 'authors_craft'),
    # Q22: "author mentions aristocratic arrangements…in order to" — author's purpose
    ('ELA', 'hard_module', 22, 'authors_craft'),
    # Q23: "What does Passage A identify as the primary cause" — explicit detail
    ('ELA', 'hard_module', 23, 'supporting_detail'),
    # Q24: "how would author of Passage A most likely respond to Passage B's claim" — inference
    ('ELA', 'hard_module', 24, 'inference'),
    # Q25: "phrase with the confidence of those who have never had to live…is an example of" — rhetorical technique
    ('ELA', 'hard_module', 25, 'authors_craft'),
    # Q26: "Both passages agree that" — inference across texts
    ('ELA', 'hard_module', 26, 'inference'),
    # Q27: "market liberalization most nearly means" — vocabulary
    ('ELA', 'hard_module', 27, 'vocabulary'),
    # Q28: "Which would serve as strongest evidence for Passage B and weakest for Passage A" — inference / evaluation
    ('ELA', 'hard_module', 28, 'inference'),

    # ── MATH ROUTING ─────────────────────────────────────────────────────────
    # Q1: 3² + 4² = 25 — exponents and basic arithmetic
    ('Math', 'routing',  1, 'number_operations'),
    # Q2: 4x + 6 = 30 — linear equation
    ('Math', 'routing',  2, 'algebra'),
    # Q3: perimeter of rectangle 11×7
    ('Math', 'routing',  3, 'geometry'),
    # Q4: 15% of 240 — percent calculation
    ('Math', 'routing',  4, 'fractions_decimals_percents'),
    # Q5: 2/5 = 0.4 — converting fraction to decimal
    ('Math', 'routing',  5, 'fractions_decimals_percents'),
    # Q6: 4 × $3.50 — basic multiplication (unit price)
    ('Math', 'routing',  6, 'number_operations'),
    # Q7: original price before 20% discount (reverse percent) → $100
    ('Math', 'routing',  7, 'fractions_decimals_percents'),
    # Q8: ratio 3:7, blue=42, find red — ratio/proportion
    ('Math', 'routing',  8, 'ratios_proportions'),
    # Q9: y = 3x − 5 when x = 4 — function evaluation / substitution
    ('Math', 'routing',  9, 'algebra'),
    # Q10: 2n − 3 = 11 — linear equation
    ('Math', 'routing', 10, 'algebra'),
    # Q11: 60 mph × 2.5 hours — speed/distance/time (rate)
    ('Math', 'routing', 11, 'ratios_proportions'),
    # Q12: three consecutive even integers sum to 78 — linear equation
    ('Math', 'routing', 12, 'algebra'),
    # Q13: area of square side=9
    ('Math', 'routing', 13, 'geometry'),
    # Q14: supplementary angles (180° − 65°)
    ('Math', 'routing', 14, 'geometry'),
    # Q15: Pythagorean theorem, legs 6 and 8
    ('Math', 'routing', 15, 'geometry'),
    # Q16: area of circle r=5
    ('Math', 'routing', 16, 'geometry'),
    # Q17: P(red) = 4/10 — simple probability
    ('Math', 'routing', 17, 'probability'),
    # Q18: mean of five test scores — statistics
    ('Math', 'routing', 18, 'statistics_data'),
    # Q19: P(> 5 on spinner 1–8) — probability
    ('Math', 'routing', 19, 'probability'),
    # Q20: median of {3,7,9,11,14,18} — statistics
    ('Math', 'routing', 20, 'statistics_data'),
    # Q21: Emma = 2×Liam, total $96 — linear system / algebra
    ('Math', 'routing', 21, 'algebra'),
    # Q22: 2.5 cups / 12 cookies → x cups / 30 cookies — proportion
    ('Math', 'routing', 22, 'ratios_proportions'),
    # Q23: percent markup $60→$90 — percent change
    ('Math', 'routing', 23, 'fractions_decimals_percents'),
    # Q24: 3(x−4) = 2(x+1)+5 — multi-step linear equation
    ('Math', 'routing', 24, 'algebra'),
    # Q25: (2³×3²)÷(2×3) — order of operations with exponents
    ('Math', 'routing', 25, 'number_operations'),
    # Q26: triangle angles (2x+5)+(3x+10)+(x+15)=180 — geometry + algebra
    ('Math', 'routing', 26, 'geometry'),
    # Q27: two pipes fill pool in 6h and 4h — combined rate (work problems)
    ('Math', 'routing', 27, 'ratios_proportions'),
    # Q28: P(both red) without replacement — compound probability
    ('Math', 'routing', 28, 'probability'),
    # Q29: buy-two-get-one-free, 6 shirts at $25 — percent/discount arithmetic
    ('Math', 'routing', 29, 'fractions_decimals_percents'),

    # ── MATH EASY MODULE ─────────────────────────────────────────────────────
    # Q1: −12 + 4×(−3) − (−8) — order of operations, integers
    ('Math', 'easy_module',  1, 'number_operations'),
    # Q2: 3x − 7 = 2x + 5 — linear equation
    ('Math', 'easy_module',  2, 'algebra'),
    # Q3: order 2/5, 0.45, 3/8, 42% — converting and comparing fractions/decimals/percents
    ('Math', 'easy_module',  3, 'fractions_decimals_percents'),
    # Q4: 25% discount, jacket $54 → original price — reverse percent
    ('Math', 'easy_module',  4, 'fractions_decimals_percents'),
    # Q5: |−6+(−4)|×3 − |2−5| — absolute value, order of operations
    ('Math', 'easy_module',  5, 'number_operations'),
    # Q6: 2/3 + 3/4 — fraction addition
    ('Math', 'easy_module',  6, 'fractions_decimals_percents'),
    # Q7: −2x+5≥11 — inequality (flip sign when dividing by negative)
    ('Math', 'easy_module',  7, 'algebra'),
    # Q8: (1/3)n + 8 = 20 — linear equation
    ('Math', 'easy_module',  8, 'algebra'),
    # Q9: 12h + 50 = 194 — linear equation (hourly wage + bonus)
    ('Math', 'easy_module',  9, 'algebra'),
    # Q10: 2, 6, 18, 54, … next term — geometric sequence/pattern
    ('Math', 'easy_module', 10, 'functions_patterns'),
    # Q11: rectangular garden perimeter (length = 2w+3, w=5)
    ('Math', 'easy_module', 11, 'geometry'),
    # Q12: isosceles triangle perimeter (two equal sides = 13, total = 38)
    ('Math', 'easy_module', 12, 'geometry'),
    # Q13: rectangular box volume (10×4×5)
    ('Math', 'easy_module', 13, 'geometry'),
    # Q14: same-side interior angles on parallel lines (supplementary)
    ('Math', 'easy_module', 14, 'geometry'),
    # Q15: mean vs median of 5-day temperature data
    ('Math', 'easy_module', 15, 'statistics_data'),
    # Q16: P(not blue) from bag — complement probability
    ('Math', 'easy_module', 16, 'probability'),
    # Q17: mode of {5,8,7,9,8,7} — bimodal, statistics
    ('Math', 'easy_module', 17, 'statistics_data'),
    # Q18: 40% of 30 students — percent of a quantity
    ('Math', 'easy_module', 18, 'fractions_decimals_percents'),
    # Q19: Jaylen spends 1/4 on food then 1/3 of remainder — sequential fractions
    ('Math', 'easy_module', 19, 'ratios_proportions'),
    # Q20: 60 mph, how many minutes for 50 miles — rate/unit conversion
    ('Math', 'easy_module', 20, 'ratios_proportions'),
    # Q21: 3 paperbacks × $8 + 2 hardcovers × $15 — multi-item arithmetic
    ('Math', 'easy_module', 21, 'number_operations'),
    # Q22: 3n−7 between 20 and 30, find largest integer n — compound inequality
    ('Math', 'easy_module', 22, 'algebra'),
    # Q23: (−2)³ + (−3)² − (−4) — integer exponents, signs
    ('Math', 'easy_module', 23, 'number_operations'),
    # Q24: right triangle leg (5-12-13 triple, Pythagorean theorem)
    ('Math', 'easy_module', 24, 'geometry'),
    # Q25: mean of {3,7,4,8,3}
    ('Math', 'easy_module', 25, 'statistics_data'),
    # Q26: square perimeter=52, find area — two-step geometry
    ('Math', 'easy_module', 26, 'geometry'),
    # Q27: sum=50, difference=14 (system of equations, find larger number)
    ('Math', 'easy_module', 27, 'algebra'),
    # Q28: 40% markup then 25% discount on $80 — sequential percent changes
    ('Math', 'easy_module', 28, 'fractions_decimals_percents'),

    # ── MATH HARD MODULE ─────────────────────────────────────────────────────
    # Q1: 5x−3(x−2)=22 — linear equation with distribution
    ('Math', 'hard_module',  1, 'algebra'),
    # Q2: right triangle with variable legs, solve quadratic (5-12-13)
    ('Math', 'hard_module',  2, 'geometry'),
    # Q3: |−7+3|−|2−9| = 4−7 = −3 — absolute value arithmetic
    ('Math', 'hard_module',  3, 'number_operations'),
    # Q4: 2⁻³ × 2⁵ = 2² — exponent rules (same base, add exponents)
    ('Math', 'hard_module',  4, 'number_operations'),
    # Q5: integers with product=−36 and sum=−5 — number sense / factoring
    ('Math', 'hard_module',  5, 'number_operations'),
    # Q6: f(x) = x²−4x+3, evaluate f(5) — function notation/evaluation
    ('Math', 'hard_module',  6, 'functions_patterns'),
    # Q7: system 2x+y=10, x−y=2 — linear system of equations
    ('Math', 'hard_module',  7, 'algebra'),
    # Q8: x²−5x+6=0, which value is a solution — quadratic equation
    ('Math', 'hard_module',  8, 'algebra'),
    # Q9: sum of first n integers formula, n=20 — applying formula (sequence/function)
    ('Math', 'hard_module',  9, 'functions_patterns'),
    # Q10: line through (1,3) and (4,12), find equation — slope/linear equation
    ('Math', 'hard_module', 10, 'algebra'),
    # Q11: similar triangles area ratio 3²:5² — geometry (similarity)
    ('Math', 'hard_module', 11, 'geometry'),
    # Q12: cone volume V=(1/3)πr²h — geometry formula
    ('Math', 'hard_module', 12, 'geometry'),
    # Q13: distance between (−2,3) and (4,−5) — distance formula / geometry
    ('Math', 'hard_module', 13, 'geometry'),
    # Q14: cylinder minus cone volume — composite geometry
    ('Math', 'hard_module', 14, 'geometry'),
    # Q15: inclusion-exclusion: sport, instrument, both, find neither
    ('Math', 'hard_module', 15, 'statistics_data'),
    # Q16: remove lowest score, which measure of center changes most — statistics
    ('Math', 'hard_module', 16, 'statistics_data'),
    # Q17: P(first red, second green) without replacement — compound probability
    ('Math', 'hard_module', 17, 'probability'),
    # Q18: P(Spanish but not French) using set subtraction — probability
    ('Math', 'hard_module', 18, 'probability'),
    # Q19: bacteria doubles every 3 hours, after 12 hours — exponential pattern
    ('Math', 'hard_module', 19, 'functions_patterns'),
    # Q20: car depreciates 15%/year for 2 years — sequential percent change
    ('Math', 'hard_module', 20, 'fractions_decimals_percents'),
    # Q21: pipe fills tank (1/8/hr), pipe drains (1/12/hr), net rate — combined rates
    ('Math', 'hard_module', 21, 'ratios_proportions'),
    # Q22: Train A at 60 mph, Train B at 80 mph, when does B catch A — rate/distance
    ('Math', 'hard_module', 22, 'ratios_proportions'),
    # Q23: n³ < 200, greatest positive integer n — number operations (cubes)
    ('Math', 'hard_module', 23, 'number_operations'),
    # Q24: a²−b²=40, a−b=5, find a+b — difference of squares (algebraic identity)
    ('Math', 'hard_module', 24, 'algebra'),
    # Q25: 0.50a + 0.75o = 6.00, a≥3, o≥3, maximize a — integer constraint algebra
    ('Math', 'hard_module', 25, 'algebra'),
    # Q26: square side=10, inscribed circle, area inside square but outside circle
    ('Math', 'hard_module', 26, 'geometry'),
    # Q27: simple interest I=PRT, find years to reach $6,500
    ('Math', 'hard_module', 27, 'ratios_proportions'),
    # Q28: sequence term1=2, each term = 2×prev+3, find 4th term — recursive pattern
    ('Math', 'hard_module', 28, 'functions_patterns'),
]

changed = 0
not_found = []

for section, stage, qnum, skill in updates:
    n = Question.objects.filter(
        test=t,
        section=section,
        stage=stage,
        question_number=qnum,
    ).update(skill=skill)
    if n == 0:
        not_found.append((section, stage, qnum, skill))
    changed += n

print(f"Updated {changed} questions.")

if not_found:
    print(f"\nWARNING: {len(not_found)} question(s) not found in the database:")
    for item in not_found:
        print(f"  section={item[0]}, stage={item[1]}, question_number={item[2]}, intended_skill={item[3]}")
else:
    print("All questions matched successfully.")
