from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render

from accounts.models import Profile
from .forms import CaretakerSignUpForm, HouseSeekerSignUpForm


def dashboard_for_user(user):
    """Return the right landing page after login based on the user's role."""
    profile = getattr(user, 'profile', None)
    if user.is_staff or (profile and profile.role == Profile.ADMIN):
        return 'admin_caretaker_list'
    if profile and profile.role == Profile.CARETAKER:
        return 'caretaker_dashboard'
    if profile and profile.role == Profile.SEEKER:
        return 'seeker_dashboard'
    return 'home'


class RoleBasedLoginView(LoginView):
    template_name = 'accounts/login.html'

    def get_success_url(self):
        next_url = self.get_redirect_url()
        if next_url:
            return next_url
        return redirect(dashboard_for_user(self.request.user)).url


def signup(request):
    if request.method == 'POST':
        form = CaretakerSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.email = form.cleaned_data.get('email', '')
            user.save(update_fields=['email'])
            user.profile.phone = form.cleaned_data.get('phone', '')
            user.profile.role = Profile.CARETAKER
            user.profile.approval_status = Profile.PENDING
            user.profile.phone_verified = False
            user.profile.save(update_fields=['phone', 'role', 'approval_status', 'phone_verified'])
            login(request, user)
            messages.success(request, 'Account created. Your caretaker profile is pending admin approval before listings go public.')
            return redirect(dashboard_for_user(user))
    else:
        form = CaretakerSignUpForm()
    return render(request, 'accounts/signup.html', {'form': form})


def seeker_signup(request):
    if request.method == 'POST':
        form = HouseSeekerSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.email = form.cleaned_data.get('email', '')
            user.save(update_fields=['email'])
            user.profile.phone = form.cleaned_data.get('phone', '')
            user.profile.role = Profile.SEEKER
            user.profile.approval_status = Profile.APPROVED
            user.profile.phone_verified = False
            user.profile.save(update_fields=['phone', 'role', 'approval_status', 'phone_verified'])
            login(request, user)
            messages.success(request, 'Account created. You can now save homes and come back to them later.')
            return redirect('seeker_dashboard')
    else:
        form = HouseSeekerSignUpForm()
    return render(request, 'accounts/seeker_signup.html', {'form': form})
