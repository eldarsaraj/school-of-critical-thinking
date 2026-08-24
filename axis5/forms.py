from django import forms


class StartForm(forms.Form):
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
