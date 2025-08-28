from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect
from .forms import BulkUploadForm
from .models import FrameRaw, Position, Device, ProcessingLog
from .services import process_bulk


admin.site.register(ProcessingLog)
admin.site.register(Device)
admin.site.register(Position)


@admin.register(FrameRaw)
class FrameRawAdmin(admin.ModelAdmin):
    list_display = ("id", "device", "seq", "processed", "error")

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "bulk-upload/",
                self.admin_site.admin_view(self.bulk_upload_view),
                name="frameraw_bulk_upload",
            ),
        ]
        return custom_urls + urls

    def bulk_upload_view(self, request):
        if request.method == "POST":
            form = BulkUploadForm(request.POST)
            if form.is_valid():
                results = process_bulk(form.cleaned_data["data"])
                self.message_user(
                    request,
                    f"Processed {results['total']} frames: "
                    f"{results['ok']} OK, {results['errors']} errors",
                )
                return redirect("..")  # back to changelist
        else:
            form = BulkUploadForm()

        context = {
            **self.admin_site.each_context(request),  # 🔑 adds admin site context
            "opts": self.model._meta,
            "form": form,
            "title": "Bulk Upload Frames",
        }
        return render(
            request,
            "admin/tracker/frameraw/bulk_upload.html",
            context,
        )
