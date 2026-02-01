from django import forms
from django.core.exceptions import ValidationError
from accounts.models import User
from django.contrib.auth.forms import ReadOnlyPasswordHashField


class UserCreationForm(forms.ModelForm):
    """A form for creating new users. Includes all the required fields plus a password"""

    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ["email", "first_name", "last_name", "phone_number"]

    # ensure that two provided passwords match
    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise ValidationError("Passwords don't match")

    # set password and save to the database
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()

        return user


class UserChangeForm(forms.ModelForm):
    """A form for updating users. Includes all the fields on the users, but replaces the password field"""

    password = ReadOnlyPasswordHashField()

    class Meta:
        model = User
        fields = ["email", "first_name", "last_name", "phone_number"]
