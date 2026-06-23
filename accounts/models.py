from django.conf import settings
from django.db import models
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    SEEKER = 'seeker'
    CARETAKER = 'caretaker'
    ADMIN = 'admin'
    ROLE_CHOICES = [
        (SEEKER, 'House seeker'),
        (CARETAKER, 'Caretaker'),
        (ADMIN, 'Admin'),
    ]

    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    SUSPENDED = 'suspended'
    APPROVAL_CHOICES = [
        (PENDING, 'Pending review'),
        (APPROVED, 'Approved'),
        (REJECTED, 'Rejected'),
        (SUSPENDED, 'Suspended'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=SEEKER)
    phone = models.CharField(max_length=30, blank=True)
    phone_verified = models.BooleanField(default=False)
    approval_status = models.CharField(max_length=20, choices=APPROVAL_CHOICES, default=PENDING)
    verification_note = models.CharField(max_length=255, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    @property
    def can_publish_listings(self):
        return self.approval_status == self.APPROVED and self.phone_verified

    def approve(self):
        self.approval_status = self.APPROVED
        self.approved_at = timezone.now()
        self.save(update_fields=['approval_status', 'approved_at'])

    def __str__(self):
        return f'{self.user.username} ({self.get_role_display()})'


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_profile(sender, instance, created, **kwargs):
    if created:
        role = Profile.ADMIN if instance.is_superuser else Profile.SEEKER
        approval_status = Profile.APPROVED if instance.is_superuser else Profile.PENDING
        Profile.objects.create(user=instance, role=role, approval_status=approval_status, phone_verified=instance.is_superuser)
