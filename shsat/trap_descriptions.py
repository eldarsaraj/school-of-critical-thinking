"""
Parent-friendly descriptions and remediation tips for all 40 distractor trap types.

Each trap key maps to:
- description: what the child did wrong (plain language for parents)
- remediation: a specific, actionable tip the child can practice
"""

TRAP_DESCRIPTIONS = {
    # ── ELA traps (19) ──────────────────────────────────────────────
    "too_broad": {
        "description": "Your child chose an answer that was too general — it could apply to many passages, not just this one.",
        "remediation": "Look for the answer that is specific to the passage. If it could be true about anything, it's probably too broad.",
    },
    "too_narrow": {
        "description": "Your child chose an answer that focused on one small detail instead of the bigger idea the question was asking about.",
        "remediation": "Before choosing, ask: 'Does this cover the whole question, or just one piece of it?'",
    },
    "too_literal": {
        "description": "Your child took the passage at face value when the question was asking about a deeper meaning, tone, or implication.",
        "remediation": "When a question asks about purpose, tone, or what the author suggests, look beyond what the words literally say.",
    },
    "less_precise": {
        "description": "Your child picked an answer that was close but not the best match — another choice captured the meaning more accurately.",
        "remediation": "When two answers seem right, compare them directly. Ask: 'Which one matches the passage more exactly?'",
    },
    "true_but_irrelevant": {
        "description": "Your child chose something that is true based on the passage but doesn't actually answer the question being asked.",
        "remediation": "Re-read the question after picking an answer. Ask: 'Does this answer what they asked, or is it just something true about the passage?'",
    },
    "misidentified_detail": {
        "description": "Your child confused one detail for another — mixing up who did what, when something happened, or which character was involved.",
        "remediation": "When a question asks about a specific detail, go back to the passage and put your finger on the exact sentence before answering.",
    },
    "qualifier_blindness": {
        "description": "Your child missed a critical qualifier like 'always', 'never', 'only', or 'most' that changed the meaning of the answer.",
        "remediation": "Circle or underline qualifiers in both the question and answer choices before comparing them.",
    },
    "opposite": {
        "description": "Your child chose an answer that says the opposite of what the passage actually states or implies.",
        "remediation": "Watch for words like 'not', 'unlike', 'however', and 'instead' in the question. These can flip the meaning.",
    },
    "overcorrection": {
        "description": "Your child over-interpreted the passage — going beyond what the author actually said to reach a stronger conclusion.",
        "remediation": "Stick to what the passage says. If you have to add extra reasoning to make an answer work, it's probably too strong.",
    },
    "surface_match": {
        "description": "Your child chose an answer that used words from the passage but didn't actually answer the question.",
        "remediation": "Before selecting, re-read the question stem. Ask: 'Does this answer the question, or does it just sound familiar?'",
    },
    "inference_leap": {
        "description": "Your child jumped to a conclusion that goes further than what the passage supports.",
        "remediation": "For inference questions, the right answer should feel almost obvious from the passage — if you have to imagine extra information, it's too big a leap.",
    },
    "causal_confusion": {
        "description": "Your child mixed up cause and effect — confusing what caused something with what resulted from it.",
        "remediation": "When a question asks 'why' or 'because', trace the chain: what happened first? What happened as a result?",
    },
    "wrong_logical_relation": {
        "description": "Your child chose an answer that describes the wrong logical relationship — for example, picking a contrast when the passage shows a comparison.",
        "remediation": "Pay attention to transition words in the passage (however, therefore, similarly, although). They signal the logical relationship.",
    },
    "changes_meaning": {
        "description": "Your child chose a revision or answer that subtly changes what the original sentence meant.",
        "remediation": "Before picking a revision, ask: 'Does this say the same thing as the original, just better?' If the meaning shifted, it's wrong.",
    },
    "wrong_placement": {
        "description": "Your child chose to place a sentence or phrase in the wrong location within the passage.",
        "remediation": "Read the sentences before and after the proposed location. The inserted sentence should connect naturally to both.",
    },
    "overgeneralized_rule": {
        "description": "Your child applied a grammar or writing rule too broadly — the rule exists, but it doesn't apply here.",
        "remediation": "Grammar rules have exceptions. If an answer 'fixes' something that wasn't broken, re-read the original to check if it was actually fine.",
    },
    "recognition_as_correctness": {
        "description": "Your child chose an answer because it looked or sounded familiar, not because it was correct.",
        "remediation": "Familiarity is not the same as correctness. Always verify against the passage instead of going with what 'feels right.'",
    },
    "referent_slippage": {
        "description": "Your child lost track of what a pronoun or phrase referred to, applying it to the wrong person, thing, or idea.",
        "remediation": "When you see 'it', 'they', 'this', or 'which', trace back to find exactly what word it replaces before answering.",
    },
    "partly_true_but_wrong": {
        "description": "Your child chose an answer where part of it was correct but another part was wrong, making the whole answer incorrect.",
        "remediation": "Check every part of the answer, not just the beginning. If any part is wrong, the whole answer is wrong.",
    },

    # ── Math traps (18) ─────────────────────────────────────────────
    "wrong_setup": {
        "description": "Your child set up the problem incorrectly — the approach or equation was wrong from the start.",
        "remediation": "Before calculating, write out what you know and what the question is asking. Make sure the equation matches the word problem.",
    },
    "partial_answer": {
        "description": "Your child stopped too early — they found a correct intermediate step but didn't finish the problem.",
        "remediation": "After finding an answer, re-read the question. Ask: 'Did I answer what they asked, or did I just find a number along the way?'",
    },
    "last_step_trap": {
        "description": "Your child did almost everything right but made an error on the very last step of the calculation.",
        "remediation": "The last step is where careless mistakes happen. Slow down and double-check the final calculation.",
    },
    "off_by_operation": {
        "description": "Your child used the wrong operation — for example, adding when they should have subtracted, or multiplying instead of dividing.",
        "remediation": "Underline the key words in the problem (total, difference, each, per) and match them to the right operation before calculating.",
    },
    "sign_error": {
        "description": "Your child made a positive/negative sign error, flipping the sign of a number during calculation.",
        "remediation": "When working with negatives, write out each step and track the signs carefully. Pay extra attention when subtracting negatives.",
    },
    "arithmetic_slip": {
        "description": "Your child understood the problem but made a simple arithmetic mistake during calculation.",
        "remediation": "For important calculations, do them twice — or work backwards from your answer to check it.",
    },
    "wrong_formula": {
        "description": "Your child used the wrong formula for this type of problem.",
        "remediation": "Before plugging in numbers, identify the problem type (area, percent, rate, etc.) and write the correct formula first.",
    },
    "procedure_substitution": {
        "description": "Your child applied a procedure that works for a similar problem type but not this one.",
        "remediation": "Read the problem carefully to identify what makes it different from similar-looking problems. Small differences in wording can change the method.",
    },
    "proportion_inversion": {
        "description": "Your child set up a ratio or proportion upside down — swapping the numerator and denominator.",
        "remediation": "Label each part of the ratio clearly. Ask: 'What's on top? What's on bottom?' and match units before cross-multiplying.",
    },
    "order_of_operations": {
        "description": "Your child performed operations in the wrong order, not following PEMDAS (Parentheses, Exponents, Multiplication/Division, Addition/Subtraction).",
        "remediation": "Write out PEMDAS and work through the expression step by step, doing one operation at a time in the correct order.",
    },
    "unit_error": {
        "description": "Your child worked with the wrong units, mixing up what the numbers represent.",
        "remediation": "Write the units next to every number in your work. When the units don't match, you'll catch the mistake before it spreads.",
    },
    "unit_conversion_error": {
        "description": "Your child made an error converting between units (e.g., inches to feet, minutes to hours).",
        "remediation": "Write out the conversion factor and multiply step by step. Check: did the number get bigger or smaller? Does that make sense?",
    },
    "unsimplified": {
        "description": "Your child found a correct value but didn't simplify it to match the answer choices (e.g., leaving a fraction unreduced).",
        "remediation": "Always check if your answer can be simplified. Look at the answer choices — if yours isn't there, try reducing or rewriting it.",
    },
    "misread_question": {
        "description": "Your child solved the problem correctly but answered a different question than what was asked.",
        "remediation": "Underline exactly what the question asks for before solving. After solving, re-read that underlined part to make sure your answer matches.",
    },
    "wrong_concept": {
        "description": "Your child confused one math concept for another — for example, mixing up area with perimeter, or mean with median.",
        "remediation": "Before starting, identify the concept by name. Say it out loud: 'This is asking for the median, not the mean.' Then apply the right method.",
    },
    "computation_error": {
        "description": "Your child made a calculation error that changed the final answer.",
        "remediation": "Use estimation to check your work. Before calculating exactly, estimate what the answer should be close to. If your answer is far off, re-check.",
    },
    "estimation_failure": {
        "description": "Your child chose an answer that doesn't make sense given the size of the numbers in the problem — a reasonableness check would have caught it.",
        "remediation": "Before looking at choices, estimate the answer. If your calculated answer is very different from your estimate, something went wrong.",
    },
    "fast_pattern_match": {
        "description": "Your child grabbed the first answer that looked right without fully working through the problem.",
        "remediation": "Don't pick an answer just because a number in it appears in the problem. Work through the full solution before looking at choices.",
    },

    # ── General traps (3) ────────────────────────────────────────────
    "introduces_new_error": {
        "description": "Your child chose a revision that fixes one problem but introduces a new error in the process.",
        "remediation": "After picking a revision, re-read the whole sentence with your change. Check that nothing new is broken.",
    },
    "misattributed_error_location": {
        "description": "Your child identified that something was wrong but pointed to the wrong part of the sentence or problem.",
        "remediation": "Read each underlined section separately. Test each one: 'Is this part actually wrong?' Don't assume — verify.",
    },
    "semantic_over_syntactic": {
        "description": "Your child focused on whether the sentence sounds meaningful instead of checking whether the grammar and structure are correct.",
        "remediation": "For grammar questions, check the rules (subject-verb agreement, pronoun reference, parallel structure) before deciding if it 'sounds right.'",
    },
}
