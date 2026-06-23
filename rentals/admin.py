from django.contrib import admin
from .models import Area, Building, ContactLead, ListingReport, Unit, UnitImage, ViewingRequest, AssistantMessage, SavedProperty


class UnitImageInline(admin.TabularInline):
    model = UnitImage
    extra = 1


class UnitInline(admin.TabularInline):
    model = Unit
    extra = 0


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    list_display = ('name', 'latitude', 'longitude')


@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    list_display = ('name', 'area', 'caretaker', 'is_published', 'latitude', 'longitude')
    list_filter = ('area', 'is_published')
    search_fields = ('name', 'landmark', 'caretaker__username')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [UnitInline]


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ('building', 'unit_type', 'label', 'rent', 'deposit', 'service_charge', 'status')
    list_filter = ('status', 'unit_type', 'building__area')
    inlines = [UnitImageInline]


@admin.register(UnitImage)
class UnitImageAdmin(admin.ModelAdmin):
    list_display = ('unit', 'caption', 'sort_order', 'image_url', 'image')
    search_fields = ('unit__building__name', 'caption', 'image_url')


@admin.register(ViewingRequest)
class ViewingRequestAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'unit', 'created_at')
    search_fields = ('name', 'phone', 'unit__building__name')


@admin.register(AssistantMessage)
class AssistantMessageAdmin(admin.ModelAdmin):
    list_display = ('role', 'user', 'session_key', 'created_at')
    search_fields = ('content', 'user__username', 'session_key')


@admin.register(SavedProperty)
class SavedPropertyAdmin(admin.ModelAdmin):
    list_display = ('user', 'saved_building', 'unit', 'created_at')
    search_fields = ('user__username', 'unit__building__name', 'building__name', 'building__area__name')
    list_filter = ('created_at',)


@admin.register(ContactLead)
class ContactLeadAdmin(admin.ModelAdmin):
    list_display = ('method', 'unit', 'user', 'created_at')
    list_filter = ('method', 'created_at')
    search_fields = ('unit__building__name', 'user__username', 'session_key')


@admin.register(ListingReport)
class ListingReportAdmin(admin.ModelAdmin):
    list_display = ('building', 'unit', 'reason', 'status', 'created_at')
    list_filter = ('status', 'reason', 'created_at')
    search_fields = ('building__name', 'unit__label', 'name', 'phone', 'details')
