from django import forms
from django.contrib.auth.models import User


class StartForm(forms.Form):
    name = forms.CharField(
        label="Your name",
        max_length=120,
        widget=forms.TextInput(attrs={
            "placeholder": "Full name",
            "autocomplete": "name",
            "class": "ax-input",
        }),
    )
    email = forms.EmailField(
        label="Email address",
        widget=forms.EmailInput(attrs={
            "placeholder": "you@example.com",
            "autocomplete": "email",
            "class": "ax-input",
        }),
    )

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()

    def clean_name(self):
        return self.cleaned_data["name"].strip()


_INPUT = {"class": "ax-input"}


class SignupForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={**_INPUT, "placeholder": "Email address", "autocomplete": "email"}),
    )
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={**_INPUT, "placeholder": "Password", "autocomplete": "new-password"}),
    )
    password2 = forms.CharField(
        label="Confirm password",
        widget=forms.PasswordInput(attrs={**_INPUT, "placeholder": "Confirm password", "autocomplete": "new-password"}),
    )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(username=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        cd = super().clean()
        p1, p2 = cd.get("password1", ""), cd.get("password2", "")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Passwords don't match.")
        return cd

    def save(self):
        email = self.cleaned_data["email"]
        return User.objects.create_user(
            username=email, email=email, password=self.cleaned_data["password1"]
        )


class LoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={**_INPUT, "placeholder": "Email address", "autocomplete": "email"}),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={**_INPUT, "placeholder": "Password", "autocomplete": "current-password"}),
    )

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()
