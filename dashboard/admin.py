from django.contrib import admin
from .models import UploadedFile, DatasetInfo, Dashboard, ChartConfig, DashboardCollaborator, DashboardShare, SubscriptionPlan, UserSubscription, Payment

@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    list_display = ['file_name', 'user', 'file_type', 'file_size', 'upload_date', 'processed']
    list_filter = ['file_type', 'processed', 'upload_date']
    search_fields = ['file_name', 'user__username']
    readonly_fields = ['upload_date']

@admin.register(DatasetInfo)
class DatasetInfoAdmin(admin.ModelAdmin):
    list_display = ['uploaded_file', 'row_count', 'column_count', 'created_at']
    list_filter = ['created_at']
    readonly_fields = ['created_at']

@admin.register(Dashboard)
class DashboardAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'dataset', 'is_public', 'created_at', 'updated_at']
    list_filter = ['is_public', 'created_at']
    search_fields = ['name', 'user__username']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(ChartConfig)
class ChartConfigAdmin(admin.ModelAdmin):
    list_display = ['title', 'dashboard', 'chart_type', 'position_x', 'position_y']
    list_filter = ['chart_type']
    search_fields = ['title', 'dashboard__name']

@admin.register(DashboardCollaborator)
class DashboardCollaboratorAdmin(admin.ModelAdmin):
    list_display = ['dashboard', 'user', 'permission', 'invited_by', 'invited_at', 'accepted_at']
    list_filter = ['permission', 'invited_at', 'accepted_at']
    search_fields = ['dashboard__name', 'user__username', 'user__email']
    readonly_fields = ['invited_at']

@admin.register(DashboardShare)
class DashboardShareAdmin(admin.ModelAdmin):
    list_display = ['dashboard', 'public_link_enabled', 'embed_enabled', 'password_protected', 'created_at']
    list_filter = ['public_link_enabled', 'embed_enabled', 'password_protected', 'created_at']
    search_fields = ['dashboard__name']
    readonly_fields = ['created_at', 'updated_at', 'public_token']


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'plan_type', 'price_usd', 'price_inr', 'max_dashboards', 'max_uploads_per_month', 'is_active']
    list_filter = ['plan_type', 'is_active', 'public_sharing', 'pdf_export', 'api_access']
    search_fields = ['name']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'plan_type', 'is_active')
        }),
        ('USD Pricing', {
            'fields': ('price_usd', 'yearly_price_usd')
        }),
        ('INR Pricing', {
            'fields': ('price_inr', 'yearly_price_inr')
        }),
        ('Limits', {
            'fields': ('max_dashboards', 'max_uploads_per_month', 'max_file_size_mb', 'max_collaborators')
        }),
        ('Features', {
            'fields': ('public_sharing', 'pdf_export', 'api_access', 'custom_branding', 'priority_support')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'plan', 'status', 'billing_cycle', 'start_date', 'end_date', 'current_dashboards']
    list_filter = ['status', 'billing_cycle', 'plan__plan_type', 'start_date']
    search_fields = ['user__username', 'user__email', 'plan__name']
    readonly_fields = ['created_at', 'updated_at', 'stripe_customer_id', 'stripe_subscription_id']
    
    fieldsets = (
        ('User & Plan', {
            'fields': ('user', 'plan', 'status', 'billing_cycle')
        }),
        ('Dates', {
            'fields': ('start_date', 'end_date', 'trial_end_date')
        }),
        ('Usage Tracking', {
            'fields': ('current_dashboards', 'uploads_this_month', 'last_upload_reset')
        }),
        ('Payment Integration', {
            'fields': ('stripe_customer_id', 'stripe_subscription_id'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['user', 'amount', 'currency', 'status', 'description', 'created_at']
    list_filter = ['status', 'currency', 'created_at']
    search_fields = ['user__username', 'user__email', 'description', 'stripe_payment_intent_id']
    readonly_fields = ['created_at', 'updated_at', 'stripe_payment_intent_id', 'stripe_charge_id']
    
    fieldsets = (
        ('Payment Information', {
            'fields': ('user', 'subscription', 'amount', 'currency', 'status', 'description')
        }),
        ('Payment Gateway', {
            'fields': ('stripe_payment_intent_id', 'stripe_charge_id'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('metadata', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
