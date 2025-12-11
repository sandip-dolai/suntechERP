from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    DEPARTMENT_CHOICES = [
        ("Marketing", "Marketing"),
        ("Design", "Design"),
        ("Production", "Production"),
        ("Quality", "Quality"),
        ("Admin", "Admin"),
    ]

    department = models.CharField(max_length=50, choices=DEPARTMENT_CHOICES, blank=True)

    # Explicitly set related_name to avoid conflicts
    groups = models.ManyToManyField(
        "auth.Group",
        related_name="customuser_set",
        blank=True,
        help_text="The groups this user belongs to.",
    )
    user_permissions = models.ManyToManyField(
        "auth.Permission",
        related_name="customuser_permissions_set",
        blank=True,
        help_text="Specific permissions for this user.",
    )

    def __str__(self):
        return self.username


class Profile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    contact_number = models.CharField(max_length=15, blank=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"
