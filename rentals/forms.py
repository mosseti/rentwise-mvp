from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from accounts.models import Profile
from .models import Building, ListingReport, Unit, UnitImage, ViewingRequest

User = get_user_model()


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('widget', MultipleFileInput(attrs={'multiple': True}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_file_clean(d, initial) for d in data]
        return [single_file_clean(data, initial)] if data else []


class BuildingForm(forms.ModelForm):
    class Meta:
        model = Building
        fields = ['area', 'name', 'image', 'landmark', 'description', 'latitude', 'longitude', 'amenities', 'is_published']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'latitude': forms.NumberInput(attrs={'step': '0.000001'}),
            'longitude': forms.NumberInput(attrs={'step': '0.000001'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['image'].label = 'Building photo'
        self.fields['image'].help_text = 'Upload a clear exterior or entrance photo from your device. This is shown to house seekers.'


class AdminBuildingForm(BuildingForm):
    class Meta(BuildingForm.Meta):
        fields = ['caretaker'] + BuildingForm.Meta.fields

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['caretaker'].queryset = User.objects.filter(
            profile__role__in=[Profile.CARETAKER, Profile.ADMIN]
        ).order_by('username')
        self.fields['caretaker'].help_text = 'Admin can assign drafts to any caretaker. Public visibility still requires approval and phone verification.'


class UnitForm(forms.ModelForm):
    uploaded_images = MultipleFileField(
        required=False,
        label='Unit photos',
        help_text='Upload one or more photos from your device. These are what house seekers will see online.',
    )
    replace_existing_images = forms.BooleanField(
        required=False,
        label='Replace existing photos',
        help_text='Tick this only when you want to remove the current photos and use the new uploads.',
    )

    class Meta:
        model = Unit
        fields = ['building', 'unit_type', 'label', 'rent', 'deposit', 'service_charge', 'status', 'uploaded_images', 'replace_existing_images', 'notes']
        widgets = {'notes': forms.Textarea(attrs={'rows': 3})}

    def __init__(self, *args, caretaker=None, **kwargs):
        super().__init__(*args, **kwargs)
        if caretaker is not None:
            self.fields['building'].queryset = Building.objects.filter(caretaker=caretaker)
        else:
            self.fields['building'].queryset = Building.objects.select_related('caretaker', 'area').all()
        if not (self.instance and self.instance.pk):
            self.fields.pop('replace_existing_images')

    def save(self, commit=True):
        unit = super().save(commit=commit)
        if commit:
            self.save_uploaded_images(unit)
        return unit

    def save_uploaded_images(self, unit):
        uploaded_files = self.cleaned_data.get('uploaded_images') or []
        replace_existing = self.cleaned_data.get('replace_existing_images', False)

        if replace_existing:
            unit.images.all().delete()

        start_index = unit.images.count()
        for offset, image_file in enumerate(uploaded_files):
            UnitImage.objects.create(unit=unit, image=image_file, sort_order=start_index + offset)



class ViewingRequestForm(forms.ModelForm):
    class Meta:
        model = ViewingRequest
        fields = ['name', 'phone', 'message']
        widgets = {'message': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Example: I would like to view this unit tomorrow afternoon.'})}

    def save(self, commit=True):
        request = super().save(commit=False)
        request.source = 'viewing_form'
        if commit:
            request.save()
        return request


class ListingReportForm(forms.ModelForm):
    class Meta:
        model = ListingReport
        fields = ['name', 'phone', 'reason', 'details']
        widgets = {
            'details': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Tell us what looks wrong so the team can review the listing.'}),
        }


class CaretakerCreateForm(UserCreationForm):
    email = forms.EmailField(required=False)
    first_name = forms.CharField(required=False)
    last_name = forms.CharField(required=False)
    phone = forms.CharField(required=False)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'phone', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=commit)
        user.email = self.cleaned_data.get('email', '')
        user.first_name = self.cleaned_data.get('first_name', '')
        user.last_name = self.cleaned_data.get('last_name', '')
        if commit:
            user.save()
            user.profile.role = Profile.CARETAKER
            user.profile.phone = self.cleaned_data.get('phone', '')
            user.profile.approval_status = Profile.APPROVED
            user.profile.phone_verified = bool(user.profile.phone)
            user.profile.save()
        return user


class CaretakerProfileForm(forms.ModelForm):
    first_name = forms.CharField(required=False)
    last_name = forms.CharField(required=False)
    email = forms.EmailField(required=False)
    is_active = forms.BooleanField(required=False)

    class Meta:
        model = Profile
        fields = ['role', 'phone', 'phone_verified', 'approval_status', 'verification_note']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = self.instance.user
        self.fields['first_name'].initial = user.first_name
        self.fields['last_name'].initial = user.last_name
        self.fields['email'].initial = user.email
        self.fields['is_active'].initial = user.is_active

    def save(self, commit=True):
        profile = super().save(commit=False)
        user = profile.user
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        user.is_active = self.cleaned_data['is_active']
        if commit:
            user.save()
            profile.save()
        return profile
