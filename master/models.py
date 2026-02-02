from django.db import models
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError


# Company Master
class CompanyMaster(models.Model):
    """Supplier / Customer master."""

    code = models.CharField(
        max_length=30,
        unique=True,
        help_text="Unique company code (e.g. SUP-001)",
        validators=[RegexValidator(r"^[A-Z\-]+$", "Only uppercase and hyphen")],
    )

    code2 = models.CharField(
        max_length=30,
        unique=True,  # <-- REQUIRED based on your new requirement
        verbose_name="Numeric Code",
        validators=[
            RegexValidator(r"^[0-9]+$", "Only numbers allowed")
        ],  # simplified numeric validator
    )

    name = models.CharField(max_length=200)
    address = models.TextField(blank=True)
    contact_person = models.CharField(max_length=150, blank=True)
    phone = models.CharField(
        max_length=20,
        blank=True,
        validators=[
            RegexValidator(r"^[0-9]+$", "Only digits allowed")
        ],  # recommended improvement
    )
    email = models.EmailField(blank=True)

    class Meta:
        ordering = ["code"]
        verbose_name = "Company"
        verbose_name_plural = "Companies"

    def __str__(self):
        return f"{self.code} - {self.code2} – {self.name}"


# Status Process Master
class ProcessStatusMaster(models.Model):
    """Master for department process status dropdown."""

    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Status name as per Excel (e.g. COMPLETED, PENDING)",
    )
    color_code = models.CharField(
        max_length=7,
        default="#6c757d",
        help_text="HEX color code (e.g. #28a745)",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Process Status"
        verbose_name_plural = "Process Statuses"

    def __str__(self):
        return self.name


# Department Process Master
DEPARTMENT_CHOICES = [
    ("Marketing", "Marketing"),
    ("Design", "Design"),
    ("Production", "Production"),
    ("Quality", "Quality"),
    ("Logistics", "Logistics"),
]


# Department Process Master
class DepartmentProcessMaster(models.Model):
    """
    Master list of processes executed step-by-step.
    Sequence defines GLOBAL execution order.
    Department is IMMUTABLE after creation.
    """

    department = models.CharField(
        max_length=50,
        choices=DEPARTMENT_CHOICES,
        help_text="Owning department (cannot be changed later)",
    )

    name = models.CharField(
        max_length=200,
        help_text="Process name as per Excel",
    )

    sequence = models.PositiveIntegerField(
        unique=True,  # ✅ GLOBAL ORDER
        help_text="Global execution order (1, 2, 3...)",
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Disable instead of deleting or changing department",
    )

    class Meta:
        ordering = ["sequence"]
        verbose_name = "Department Process"
        verbose_name_plural = "Department Processes"
        indexes = [
            models.Index(fields=["sequence"]),
        ]

    def __str__(self):
        return f"[{self.sequence}] {self.department} - {self.name}"

    def clean(self):
        # Enforce valid sequence
        if self.sequence <= 0:
            raise ValidationError(
                {"sequence": "Sequence must be a positive number starting from 1."}
            )

        # Prevent department change
        if self.pk:
            old = DepartmentProcessMaster.objects.get(pk=self.pk)
            if old.department != self.department:
                raise ValidationError(
                    {
                        "department": (
                            "Department cannot be changed. "
                            "Deactivate this process and create a new one."
                        )
                    }
                )

    def save(self, *args, **kwargs):
        self.name = self.name.strip().upper()
        self.full_clean()
        super().save(*args, **kwargs)
