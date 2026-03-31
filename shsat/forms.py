from django import forms
from django.contrib.auth.models import User
from django.contrib.auth import authenticate

from .models import Parent, ManualScore


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
