import uuid

from django.db import models
from django.contrib.auth.models import User


class Parent(models.Model):
    PLATFORM_CHOICES = [("shsat", "SHSAT"), ("hunter", "Hunter")]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="shsat_profile")
    platform = models.CharField(max_length=10, choices=PLATFORM_CHOICES, default="shsat")
    child_nickname = models.CharField(max_length=100, blank=True, default="")
    child_grade = models.PositiveSmallIntegerField(null=True, blank=True)
    target_schools = models.JSONField(default=list, blank=True)
    subscription_status = models.CharField(max_length=20, default="free")
    stripe_customer_id = models.CharField(max_length=100, blank=True, default="")
    stripe_subscription_id = models.CharField(max_length=100, blank=True, default="")
    has_paid = models.BooleanField(default=False)
    hunter_has_paid = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=True)  # True so existing accounts are unaffected
    email_verification_token = models.UUIDField(default=uuid.uuid4, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} (parent)"


class Test(models.Model):
    EXAM_TYPE_CHOICES = [("shsat", "SHSAT"), ("hunter", "Hunter")]
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    source = models.CharField(max_length=200, blank=True, default="")
    is_free = models.BooleanField(default=True)
    is_published = models.BooleanField(default=False)
    order = models.PositiveSmallIntegerField(default=0)
    is_adaptive = models.BooleanField(default=False)
    is_drill = models.BooleanField(default=False)
    routing_threshold = models.FloatField(default=0.60)
    exam_type = models.CharField(max_length=20, choices=EXAM_TYPE_CHOICES, default="shsat")

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title

    def ela_questions(self):
        return self.questions.filter(section="ELA").order_by("question_number")

    def math_questions(self):
        return self.questions.filter(section="Math").order_by("question_number")

    def total_questions(self):
        return self.questions.count()

    @property
    def displayed_question_count(self):
        """For adaptive tests, count routing + one module (what the student actually sees)."""
        if self.is_adaptive:
            ela_r = self.questions.filter(section="ELA", stage="routing").count()
            math_r = self.questions.filter(section="Math", stage="routing").count()
            ela_m = self.questions.filter(section="ELA", stage="easy_module").count()
            math_m = self.questions.filter(section="Math", stage="easy_module").count()
            return ela_r + math_r + ela_m + math_m
        return self.questions.count()


class Question(models.Model):
    SECTION_CHOICES = [
        ("ELA", "ELA"), ("Math", "Math"),
        ("reading_comprehension", "Reading Comprehension"),
        ("quantitative_reasoning", "Quantitative Reasoning"),
        ("math_achievement", "Math Achievement"),
        ("writing", "Writing"),
    ]
    TYPE_CHOICES = [
        ("multiple_choice", "Multiple Choice"),
        ("grid_in", "Grid-In"),
        ("essay", "Essay"),
    ]
    DIFFICULTY_CHOICES = [("easy", "Easy"), ("medium", "Medium"), ("hard", "Hard")]
    STAGE_CHOICES = [
        ("routing", "Routing"),
        ("easy_module", "Easy Module"),
        ("hard_module", "Hard Module"),
    ]
    SKILL_CHOICES = [
        # ELA
        ("punctuation", "Punctuation"),
        ("usage_agreement", "Usage & Agreement"),
        ("sentence_structure", "Sentence Structure"),
        ("main_idea", "Main Idea & Central Claim"),
        ("supporting_detail", "Supporting Detail"),
        ("evidence_selection", "Evidence Selection"),
        ("inference", "Inference & Implication"),
        ("vocabulary", "Vocabulary in Context"),
        ("authors_craft", "Author's Craft & Organization"),
        ("cross_passage_synthesis", "Cross-passage Synthesis"),
        # Math
        ("number_operations", "Number & Operations"),
        ("ratios_proportions", "Ratios & Proportions"),
        ("algebra", "Algebra & Functions"),
        ("geometry", "Geometry"),
        ("statistics_data", "Statistics & Data"),
        ("probability", "Probability"),
        ("multistep_word_problems", "Multi-step Word Problems"),
    ]

    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name="questions")
    section = models.CharField(max_length=30, choices=SECTION_CHOICES)
    stage = models.CharField(max_length=15, choices=STAGE_CHOICES, default="standard")
    question_number = models.PositiveSmallIntegerField()
    question_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="multiple_choice")
    topic = models.CharField(max_length=100, blank=True, default="")
    skill = models.CharField(max_length=50, choices=SKILL_CHOICES, blank=True, default="")
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default="medium")
    distractor_types = models.JSONField(default=dict, blank=True)

    # Passage (shared across a group of questions)
    passage_group_id = models.CharField(max_length=50, blank=True, default="")
    passage_title = models.CharField(max_length=200, blank=True, default="")
    passage_text = models.TextField(blank=True, default="")

    image = models.ImageField(upload_to="shsat/questions/", blank=True, null=True)
    question_text = models.TextField()
    choice_a = models.TextField(blank=True, default="")
    choice_b = models.TextField(blank=True, default="")
    choice_c = models.TextField(blank=True, default="")
    choice_d = models.TextField(blank=True, default="")
    choice_e = models.TextField(blank=True, default="")
    correct_answer = models.CharField(max_length=20)  # A/B/C/D/E or numeric string for grid-in
    explanation = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["section", "stage", "question_number"]
        unique_together = [("test", "section", "stage", "question_number")]

    def __str__(self):
        return f"{self.test} – {self.section} Q{self.question_number}"


class TestAttempt(models.Model):
    parent = models.ForeignKey(Parent, on_delete=models.CASCADE, related_name="attempts")
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name="attempts")
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    # Snapshot of questions at start (ordered list of IDs)
    started_with = models.JSONField(default=list)
    total_seconds = models.PositiveIntegerField(null=True, blank=True)

    # Adaptive module assignment (set after routing stage, if test.is_adaptive)
    ela_module = models.CharField(max_length=10, blank=True, default="")   # 'easy' or 'hard'
    math_module = models.CharField(max_length=10, blank=True, default="")

    # Computed scores (filled on submission)
    ela_correct = models.PositiveSmallIntegerField(null=True, blank=True)
    math_correct = models.PositiveSmallIntegerField(null=True, blank=True)
    ela_scaled = models.PositiveSmallIntegerField(null=True, blank=True)
    math_scaled = models.PositiveSmallIntegerField(null=True, blank=True)
    composite_score = models.PositiveSmallIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.parent} – {self.test} ({self.started_at:%Y-%m-%d})"


class Answer(models.Model):
    attempt = models.ForeignKey(TestAttempt, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="answers")
    selected_answer = models.CharField(max_length=1, blank=True, default="")
    essay_text = models.TextField(blank=True, default="")
    is_correct = models.BooleanField(null=True, blank=True)
    is_flagged = models.BooleanField(default=False)
    time_spent_seconds = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        unique_together = [("attempt", "question")]

    def __str__(self):
        return f"{self.attempt} – Q{self.question.question_number}: {self.selected_answer}"


class ManualScore(models.Model):
    parent = models.ForeignKey(Parent, on_delete=models.CASCADE, related_name="manual_scores")
    date = models.DateField()
    source_name = models.CharField(max_length=200)
    ela_correct = models.PositiveSmallIntegerField()
    ela_total = models.PositiveSmallIntegerField(default=57)
    math_correct = models.PositiveSmallIntegerField()
    math_total = models.PositiveSmallIntegerField(default=57)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.parent} – {self.source_name} ({self.date})"


class CutoffScore(models.Model):
    school_name = models.CharField(max_length=200)
    school_short = models.CharField(max_length=50)
    admissions_year = models.PositiveSmallIntegerField()
    cutoff_score = models.PositiveSmallIntegerField()
    approximate_seats = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ["-cutoff_score"]
        unique_together = [("school_short", "admissions_year")]

    def __str__(self):
        return f"{self.school_short} {self.admissions_year}: {self.cutoff_score}"


class QuestionReport(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="reports")
    attempt = models.ForeignKey(TestAttempt, on_delete=models.SET_NULL, null=True, blank=True, related_name="reports")
    parent = models.ForeignKey(Parent, on_delete=models.SET_NULL, null=True, blank=True)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Report on {self.question} ({self.created_at:%Y-%m-%d})"


# ---------------------------------------------------------------------------
# Proxy models — used purely for admin separation (no new DB tables)
# ---------------------------------------------------------------------------

class SHSATParent(Parent):
    class Meta:
        proxy = True
        verbose_name = "SHSAT Parent"
        verbose_name_plural = "SHSAT Parents"


class HunterParent(Parent):
    class Meta:
        proxy = True
        verbose_name = "Hunter Parent"
        verbose_name_plural = "Hunter Parents"
