from django.db import models
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError


# Item / Material Master
class ItemMaster(models.Model):
    """Item / Material master."""

    code = models.CharField(
        max_length=30,
        unique=True,
        help_text="Unique item code (e.g. ITM-001)",
        validators=[
            RegexValidator(r"^[A-Z0-9\-]+$", "Only uppercase, numbers and hyphen")
        ],
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    uom = models.CharField(max_length=20, verbose_name="Unit of Measure", default="NOS")

    class Meta:
        ordering = ["code"]
        verbose_name = "Item"
        verbose_name_plural = "Items"

    def __str__(self):
        return f"{self.code} – {self.name}"


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


class DepartmentProcessMaster(models.Model):
    """
    Master list of department-wise processes.
    These processes apply to ALL POs.
    Department is IMMUTABLE after creation.
    """

    department = models.CharField(
        max_length=50,
        choices=DEPARTMENT_CHOICES,
        help_text="Owning department (cannot be changed later)",
    )

    name = models.CharField(max_length=200, help_text="Process name as per Excel")

    is_active = models.BooleanField(
        default=True, help_text="Disable instead of deleting or changing department"
    )

    class Meta:
        unique_together = ("department", "name")
        ordering = ["department", "name"]
        verbose_name = "Department Process"
        verbose_name_plural = "Department Processes"
        indexes = [
            models.Index(fields=["department"]),
        ]

    def __str__(self):
        return f"{self.department} - {self.name}"

    def clean(self):
        """
        Prevent department change after creation.
        """
        if self.pk:
            old = DepartmentProcessMaster.objects.get(pk=self.pk)
            if old.department != self.department:
                raise ValidationError(
                    {
                        "department": "Department cannot be changed. "
                        "Deactivate this process and create a new one."
                    }
                )

    def save(self, *args, **kwargs):
        # Keep Excel consistency
        self.name = self.name.strip().upper()
        self.full_clean()  # enforces clean()
        super().save(*args, **kwargs)
