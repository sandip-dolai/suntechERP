from django.db import models
from django.core.validators import RegexValidator


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


class ProcessStatusMaster(models.Model):
    """Master for department process status dropdown."""

    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Status name as per Excel (e.g. COMPLETED, PENDING)"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Process Status"
        verbose_name_plural = "Process Statuses"

    def __str__(self):
        return self.name
