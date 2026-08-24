import uuid
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Item(models.Model):
    DIMENSION_CHOICES = [
        ("U", "Uncertainty Handling"),
        ("M", "Model Awareness"),
        ("C", "Causal Reasoning"),
        ("A", "Abstraction Control"),
        ("E", "Trust Distribution"),
    ]
    FORMAT_CHOICES = [
        ("tf_confidence_block", "True/False + Confidence Block"),
        ("mc", "Multiple Choice"),
        ("mc_multi", "Multiple Choice Multi-Part"),
        ("select_all", "Select All That Apply"),
        ("scope_grid", "Scope Grid"),
        ("allocate", "Allocate"),
        ("two_step", "Two-Step"),
        ("open_text", "Open Text"),
    ]

    item_id = models.CharField(max_length=20)
    dimension = models.CharField(max_length=1, choices=DIMENSION_CHOICES)
    format = models.CharField(max_length=30, choices=FORMAT_CHOICES)
    tier = models.PositiveSmallIntegerField(null=True, blank=True)
    domain = models.CharField(max_length=50, blank=True)
    tag = models.CharField(max_length=100, blank=True)
    # Stores the full item object from items.json verbatim.
    # Formats differ too much to normalize; JSONB + loader is the right choice.
    payload = models.JSONField()
    # False for open_text (E-04) and any future unscored items.
    scored = models.BooleanField(default=True)
    # Field-test items: served, stored, excluded from scoring.
    # Bank has none yet; the hook is here so v2 can add them without a migration.
    field_test = models.BooleanField(default=False)
    form_version = models.PositiveSmallIntegerField(default=1)
    active = models.BooleanField(default=True)
    # Fixed display order. Do not randomize in v1.
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        unique_together = [("item_id", "form_version")]
        ordering = ["position"]

    def __str__(self):
        return f"{self.item_id} (v{self.form_version})"


class Form(models.Model):
    """Records which item set + scoring version constitutes a live form."""
    form_id = models.CharField(max_length=50, unique=True)
    form_version = models.PositiveSmallIntegerField()
    scoring_version = models.PositiveSmallIntegerField()
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.form_id} v{self.form_version}"


class Session(models.Model):
    STATE_CHOICES = [
        ("started", "Started"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("expired", "Expired"),
    ]

    # Nullable for anonymous (Beta). Assign on signup to carry results over.
    user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="axis5_sessions",
    )
    # Email captured at start. Used to send the results link in Beta.
    email = models.EmailField(blank=True)
    # Name captured at start. Displayed on the results page.
    name = models.CharField(max_length=120, blank=True)
    form_version = models.PositiveSmallIntegerField(default=1)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    state = models.CharField(max_length=20, choices=STATE_CHOICES, default="started")
    user_agent = models.TextField(blank=True)
    # Store a hash of the IP, not the IP itself.
    ip_hash = models.CharField(max_length=64, blank=True)
    # Token for token-based results access (Beta). Becomes FK-based when auth is added.
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    # Ordered list of Item PKs for this session (includes any field_test items).
    # Fixed at session creation; never changes. Used for position/progress tracking.
    item_sequence = models.JSONField(default=list)

    def __str__(self):
        return f"Session {self.pk} <{self.email}> ({self.state})"


class Response(models.Model):
    """One row per (session, item). value stores the raw answer as submitted."""
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name="responses")
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="responses")
    # Raw response value — format varies by item type (see SPEC §6).
    # Never modified after creation; corrections create a new Response.
    value = models.JSONField()
    # Timing: milliseconds from page load to first interaction / last submit.
    ms_first = models.PositiveIntegerField(null=True, blank=True)
    ms_total = models.PositiveIntegerField(null=True, blank=True)
    # How many times the answer changed before final submission.
    n_changes = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("session", "item")]

    def __str__(self):
        return f"Response {self.session_id}/{self.item.item_id}"


class Result(models.Model):
    """
    Scoring cache. Fully reproducible from Response rows + scoring_version.
    Never recompute at view time — render from this payload only.
    """
    session = models.OneToOneField(Session, on_delete=models.CASCADE, related_name="result")
    form_version = models.PositiveSmallIntegerField()
    scoring_version = models.PositiveSmallIntegerField()
    # Full output of score_session(): dimensions, calibration, per-item, flags.
    payload = models.JSONField()
    # Quality flags computed at completion: rapid_responding, straightlining, incomplete.
    quality_flags = models.JSONField(default=list)
    computed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Result for session {self.session_id}"
