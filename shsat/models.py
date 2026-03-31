from django.db import models
from django.contrib.auth.models import User


class Parent(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="shsat_profile")
    child_nickname = models.CharField(max_length=100, blank=True, default="")
    child_grade = models.PositiveSmallIntegerField(null=True, blank=True)
    target_schools = models.JSONField(default=list, blank=True)
    subscription_status = models.CharField(max_length=20, default="free")
    stripe_customer_id = models.CharField(max_length=100, blank=True, default="")
    stripe_subscription_id = models.CharField(max_length=100, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} (parent)"


class Test(models.Model):
    title = models.CharField(max_length=200)
    source = models.CharField(max_length=200, blank=True, default="")
    is_free = models.BooleanField(default=True)
    is_published = models.BooleanField(default=False)
    order = models.PositiveSmallIntegerField(default=0)

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


class Question(models.Model):
    SECTION_CHOICES = [("ELA", "ELA"), ("Math", "Math")]
    TYPE_CHOICES = [
        ("multiple_choice", "Multiple Choice"),
        ("grid_in", "Grid-In"),
    ]
    DIFFICULTY_CHOICES = [("easy", "Easy"), ("medium", "Medium"), ("hard", "Hard")]

    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name="questions")
    section = models.CharField(max_length=10, choices=SECTION_CHOICES)
    question_number = models.PositiveSmallIntegerField()
    question_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="multiple_choice")
    topic = models.CharField(max_length=100, blank=True, default="")
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default="medium")

    # Passage (shared across a group of questions)
    passage_group_id = models.CharField(max_length=50, blank=True, default="")
    passage_title = models.CharField(max_length=200, blank=True, default="")
    passage_text = models.TextField(blank=True, default="")

    question_text = models.TextField()
    choice_a = models.TextField(blank=True, default="")
    choice_b = models.TextField(blank=True, default="")
    choice_c = models.TextField(blank=True, default="")
    choice_d = models.TextField(blank=True, default="")
    correct_answer = models.CharField(max_length=1)  # A, B, C, D
    explanation = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["section", "question_number"]
        unique_together = [("test", "section", "question_number")]

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
    is_correct = models.BooleanField(null=True, blank=True)
    is_flagged = models.BooleanField(default=False)

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
