from __future__ import annotations
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.db.models import JSONField


class Device(models.Model):
    imei = models.CharField(max_length=17, unique=True, db_index=True)
    alias = models.CharField(max_length=64, blank=True, null=True)

    def __str__(self) -> str:
        return self.alias or self.imei


class FrameRaw(models.Model):
    device = models.ForeignKey(
        Device, on_delete=models.SET_NULL, blank=True, null=True, related_name="frames"
    )
    seq = models.PositiveIntegerField(blank=True, null=True)
    raw = models.TextField()
    checksum_valid = models.BooleanField(default=False)
    processed = models.BooleanField(default=False)
    error = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["seq"]),
        ]

    def __str__(self) -> str:
        return (
            f"FrameRaw({self.device or '?'}, seq={self.seq}, ok={self.checksum_valid})"
        )


class Position(models.Model):
    device = models.ForeignKey(
        Device, on_delete=models.CASCADE, related_name="positions"
    )
    seq = models.PositiveIntegerField()
    timestamp = models.DateTimeField(db_index=True)
    lat = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
    )
    lon = models.DecimalField(
        max_digits=11,
        decimal_places=6,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
    )
    speed_kmh = models.DecimalField(max_digits=6, decimal_places=1)
    course_deg = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(359)]
    )
    alt_m = models.DecimalField(max_digits=7, decimal_places=1)
    fix = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(3)]
    )
    sats = models.PositiveSmallIntegerField()
    hdop = models.DecimalField(max_digits=4, decimal_places=1)
    odom_km = models.DecimalField(max_digits=9, decimal_places=1)
    fuel_pct = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    batt_v = models.DecimalField(max_digits=5, decimal_places=1)
    io_hex = models.CharField(max_length=4)
    io_flags = JSONField(default=dict)
    extensions = JSONField(default=dict)
    frame = models.OneToOneField(
        FrameRaw,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="position",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("device", "seq")
        indexes = [
            models.Index(fields=["device", "timestamp"]),
        ]

    def __str__(self) -> str:
        return f"Position({self.device}, {self.timestamp:%Y-%m-%d %H:%M:%S}Z, seq={self.seq})"


class ProcessingLog(models.Model):
    level = models.CharField(max_length=16, default="INFO")
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    frame = models.ForeignKey(
        FrameRaw, on_delete=models.CASCADE, related_name="logs", null=True, blank=True
    )

    def __str__(self) -> str:
        return (
            f"[{self.created_at:%Y-%m-%d %H:%M:%S}] {self.level}: {self.message[:60]}"
        )
