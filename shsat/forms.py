from django import forms
from django.contrib.auth.models import User
from django.contrib.auth import authenticate

from .models import Parent, ManualScore, Question, Test


DISTRACTOR_CHOICES = [
    ("", "-- none --"),
    ("ELA", [
        ("too_broad", "(E) Too Broad"),
        ("too_narrow", "(E) Too Narrow"),
        ("too_literal", "(E) Too Literal"),
        ("true_but_irrelevant", "(E) True but Irrelevant"),
        ("misidentified_detail", "(E) Misidentified Detail"),
        ("qualifier_blindness", "(E) Qualifier Blindness"),
        ("opposite", "(E) Opposite"),
        ("overcorrection", "(E) Overcorrection"),
        ("surface_match", "(E) Surface Match"),
        ("inference_leap", "(E) Inference Leap"),
        ("causal_confusion", "(E) Causal Confusion"),
        ("overgeneralized_rule", "(E) Overgeneralized Rule"),
        ("recognition_as_correctness", "(E) Recognition as Correctness"),
        ("referent_slippage", "(E) Referent Slippage"),
        ("partly_true_but_wrong", "(E) Partly True but Wrong"),
    ]),
    ("Math", [
        ("partial_answer", "(M) Partial Answer"),
        ("last_step_trap", "(M) Last Step Trap"),
        ("off_by_operation", "(M) Wrong Operation"),
        ("sign_error", "(M) Sign Error"),
        ("wrong_formula", "(M) Wrong Formula"),
        ("procedure_substitution", "(M) Procedure Substitution"),
        ("proportion_inversion", "(M) Proportion Inversion"),
        ("order_of_operations", "(M) Order of Operations"),
        ("unit_error", "(M) Unit/Conversion Error"),
        ("unsimplified", "(M) Unsimplified Answer"),
        ("computation_error", "(M) Computation Error"),
        ("estimation_failure", "(M) Estimation Failure"),
        ("fast_pattern_match", "(M) Fast Pattern Match"),
    ]),
    ("General", [
        ("misattributed_error_location", "Misattributed Error Location"),
        ("semantic_over_syntactic", "Semantic Over Syntactic"),
    ]),
]


class TestForm(forms.ModelForm):
    class Meta:
        model = Test
        fields = ["title", "source", "order", "is_free", "is_published", "is_adaptive", "routing_threshold"]
        labels = {
            "source": "Source (e.g. Official SHSAT Handbook 2025)",
            "order": "Display order (lower = first)",
            "routing_threshold": "Routing threshold (0.0–1.0, e.g. 0.60 = 60%)",
        }


class QuestionEditForm(forms.ModelForm):
    distractor_a = forms.ChoiceField(choices=DISTRACTOR_CHOICES, required=False, label="Choice A trap")
    distractor_b = forms.ChoiceField(choices=DISTRACTOR_CHOICES, required=False, label="Choice B trap")
    distractor_c = forms.ChoiceField(choices=DISTRACTOR_CHOICES, required=False, label="Choice C trap")
    distractor_d = forms.ChoiceField(choices=DISTRACTOR_CHOICES, required=False, label="Choice D trap")

    class Meta:
        model = Question
        fields = [
            "section", "stage", "question_number", "skill", "difficulty", "question_type", "topic",
            "passage_group_id", "passage_title", "passage_text",
            "question_text", "choice_a", "choice_b", "choice_c", "choice_d",
            "correct_answer", "explanation",
        ]
        widgets = {
            "question_text": forms.Textarea(attrs={"rows": 6}),
            "passage_text": forms.Textarea(attrs={"rows": 10}),
            "explanation": forms.Textarea(attrs={"rows": 8}),
            "choice_a": forms.Textarea(attrs={"rows": 4}),
            "choice_b": forms.Textarea(attrs={"rows": 4}),
            "choice_c": forms.Textarea(attrs={"rows": 4}),
            "choice_d": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.distractor_types:
            dt = self.instance.distractor_types
            self.fields["distractor_a"].initial = dt.get("A", "")
            self.fields["distractor_b"].initial = dt.get("B", "")
            self.fields["distractor_c"].initial = dt.get("C", "")
            self.fields["distractor_d"].initial = dt.get("D", "")

    def save(self, commit=True):
        instance = super().save(commit=False)
        dt = {}
        for letter, field in [("A", "distractor_a"), ("B", "distractor_b"),
                               ("C", "distractor_c"), ("D", "distractor_d")]:
            val = self.cleaned_data.get(field, "")
            if val:
                dt[letter] = val
        instance.distractor_types = dt
        if commit:
            instance.save()
        return instance


class SignupForm(forms.Form):
    first_name = forms.CharField(max_length=150, label="Your first name")
    email = forms.EmailField(label="Email address")
    password1 = forms.CharField(widget=forms.PasswordInput, label="Password")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirm password")

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Passwords do not match.")
        return cleaned

    def save(self):
        data = self.cleaned_data
        user = User.objects.create_user(
            username=data["email"].lower(),
            email=data["email"].lower(),
            password=data["password1"],
            first_name=data["first_name"],
        )
        return user


class LoginForm(forms.Form):
    email = forms.EmailField(label="Email address")
    password = forms.CharField(widget=forms.PasswordInput, label="Password")

    def clean(self):
        cleaned = super().clean()
        email = cleaned.get("email", "").lower()
        password = cleaned.get("password")
        if email and password:
            user = authenticate(email=email, password=password)
            if user is None:
                raise forms.ValidationError("Email or password is incorrect.")
            cleaned["user"] = user
        return cleaned


class ManualScoreForm(forms.ModelForm):
    class Meta:
        model = ManualScore
        fields = ["date", "source_name", "ela_correct", "ela_total", "math_correct", "math_total", "notes"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {
            "source_name": "Test source (e.g. SHSAT Prep Book 2024, p.45)",
            "ela_correct": "ELA correct",
            "ela_total": "ELA total questions",
            "math_correct": "Math correct",
            "math_total": "Math total questions",
        }


class NotesForm(forms.Form):
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": "Add notes about this attempt…"}),
        label="Notes",
    )


class AccountForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, label="Your first name")

    class Meta:
        model = Parent
        fields = ["child_nickname", "child_grade", "target_schools"]
        widgets = {
            "target_schools": forms.HiddenInput(),
        }
        labels = {
            "child_nickname": "Child's first name (or nickname)",
            "child_grade": "Child's current grade",
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        if user:
            self.fields["first_name"].initial = user.first_name

    def save(self, commit=True):
        parent = super().save(commit=False)
        if self.user:
            self.user.first_name = self.cleaned_data["first_name"]
            self.user.save(update_fields=["first_name"])
        if commit:
            parent.save()
        return parent
