from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class CaretakerSignUpForm(UserCreationForm):
    email = forms.EmailField(required=False)
    phone = forms.CharField(required=False, max_length=30)

    class Meta:
        model = User
        fields = ['username', 'email', 'phone', 'password1', 'password2']



class HouseSeekerSignUpForm(UserCreationForm):
    email = forms.EmailField(required=False)
    phone = forms.CharField(required=False, max_length=30)

    class Meta:
        model = User
        fields = ['username', 'email', 'phone', 'password1', 'password2']
