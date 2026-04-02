from django.db import models
from django.contrib.auth.models import User
import json
from datetime import datetime

def upload_to_user_directory(instance, filename):
    """Upload files to user-specific directory"""
    return f'uploads/user_{instance.user.id}/{filename}'

class UploadedFile(models.Model):
    """Model to store uploaded files metadata"""
    FILE_TYPES = [
        ('excel', 'Excel File'),
        ('csv', 'CSV File'),
        ('sql', 'SQL File'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    file = models.FileField(upload_to=upload_to_user_directory)
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=10, choices=FILE_TYPES)
    file_size = models.BigIntegerField()  # in bytes
    upload_date = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
    processing_error = models.TextField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.file_name} - {self.user.username}"
    
    class Meta:
        ordering = ['-upload_date']

class DatasetInfo(models.Model):
    """Model to store processed dataset information"""
    uploaded_file = models.OneToOneField(UploadedFile, on_delete=models.CASCADE)
    columns = models.JSONField(default=list)  # Store column names and types
    row_count = models.IntegerField(default=0)
    column_count = models.IntegerField(default=0)
    numeric_columns = models.JSONField(default=list)
    categorical_columns = models.JSONField(default=list)
    date_columns = models.JSONField(default=list)
    summary_stats = models.JSONField(default=dict)  # Basic stats for numeric columns
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Dataset: {self.uploaded_file.file_name}"

class Dashboard(models.Model):
    """Model to store dashboard configurations"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    dataset = models.ForeignKey(DatasetInfo, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    chart_configs = models.JSONField(default=list)  # Store chart configurations
    layout_config = models.JSONField(default=dict)  # Store dashboard layout
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} - {self.user.username}"
    
    class Meta:
        ordering = ['-updated_at']

class ChartConfig(models.Model):
    """Model to store individual chart configurations"""
    CHART_TYPES = [
        ('bar', 'Bar Chart'),
        ('line', 'Line Chart'),
        ('pie', 'Pie Chart'),
        ('scatter', 'Scatter Plot'),
        ('histogram', 'Histogram'),
        ('box', 'Box Plot'),
    ]
    
    dashboard = models.ForeignKey(Dashboard, on_delete=models.CASCADE, related_name='charts')
    chart_type = models.CharField(max_length=20, choices=CHART_TYPES)
    title = models.CharField(max_length=255)
    x_axis = models.CharField(max_length=100, blank=True)
    y_axis = models.CharField(max_length=100, blank=True)
    color_column = models.CharField(max_length=100, blank=True)
    aggregation = models.CharField(max_length=50, default='count')  # count, sum, avg, etc.
    filters = models.JSONField(default=dict)  # Column filters
    position_x = models.IntegerField(default=0)
    position_y = models.IntegerField(default=0)
    width = models.IntegerField(default=6)  # Grid width (1-12)
    height = models.IntegerField(default=4)  # Grid height
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.title} ({self.chart_type})"
    
    class Meta:
        ordering = ['position_y', 'position_x']


class DashboardCollaborator(models.Model):
    """Model to store dashboard collaboration permissions"""
    PERMISSION_CHOICES = [
        ('view', 'View Only'),
        ('edit', 'Edit'),
        ('admin', 'Admin'),
    ]
    
    dashboard = models.ForeignKey(Dashboard, on_delete=models.CASCADE, related_name='collaborators')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    permission = models.CharField(max_length=10, choices=PERMISSION_CHOICES, default='view')
    invited_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_invitations')
    invited_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['dashboard', 'user']
        ordering = ['-invited_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.dashboard.name} ({self.permission})"


class DashboardShare(models.Model):
    """Model to store dashboard sharing settings"""
    dashboard = models.OneToOneField(Dashboard, on_delete=models.CASCADE, related_name='share_settings')
    public_link_enabled = models.BooleanField(default=False)
    embed_enabled = models.BooleanField(default=False)
    public_token = models.CharField(max_length=64, unique=True, null=True, blank=True)
    password_protected = models.BooleanField(default=False)
    password = models.CharField(max_length=128, null=True, blank=True)
    expiry_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Share settings for {self.dashboard.name}"


class SubscriptionPlan(models.Model):
    """Model to store subscription plans"""
    PLAN_TYPES = [
        ('free', 'Free'),
        ('basic', 'Basic'),
        ('pro', 'Pro'),
        ('enterprise', 'Enterprise'),
    ]
    
    name = models.CharField(max_length=50)
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPES, unique=True)
    
    # USD Pricing
    price_usd = models.DecimalField(max_digits=10, decimal_places=2)  # Monthly price in USD
    yearly_price_usd = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # INR Pricing
    price_inr = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Monthly price in INR
    yearly_price_inr = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Feature limits
    max_dashboards = models.IntegerField(default=5)
    max_uploads_per_month = models.IntegerField(default=10)
    max_file_size_mb = models.IntegerField(default=50)  # in MB
    max_collaborators = models.IntegerField(default=3)
    
    # Features
    public_sharing = models.BooleanField(default=True)
    pdf_export = models.BooleanField(default=True)
    api_access = models.BooleanField(default=False)
    custom_branding = models.BooleanField(default=False)
    priority_support = models.BooleanField(default=False)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} - ${self.price_usd}/month"
    
    def get_price(self, currency='USD'):
        """Get price in specified currency"""
        if currency == 'INR':
            return self.price_inr
        return self.price_usd
    
    def get_yearly_price(self, currency='USD'):
        """Get yearly price in specified currency"""
        if currency == 'INR':
            return self.yearly_price_inr or (self.price_inr * 12)
        return self.yearly_price_usd or (self.price_usd * 12)
    
    class Meta:
        ordering = ['price_usd']


class UserSubscription(models.Model):
    """Model to store user subscription information"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
        ('trial', 'Trial'),
    ]
    
    BILLING_CYCLES = [
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='trial')
    billing_cycle = models.CharField(max_length=10, choices=BILLING_CYCLES, default='monthly')
    
    # Subscription dates
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True, blank=True)
    trial_end_date = models.DateTimeField(null=True, blank=True)
    
    # Payment info
    stripe_customer_id = models.CharField(max_length=100, null=True, blank=True)
    stripe_subscription_id = models.CharField(max_length=100, null=True, blank=True)
    
    # Usage tracking
    current_dashboards = models.IntegerField(default=0)
    uploads_this_month = models.IntegerField(default=0)
    last_upload_reset = models.DateTimeField(auto_now_add=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.plan.name} ({self.status})"
    
    def is_feature_available(self, feature):
        """Check if a specific feature is available for this subscription"""
        return getattr(self.plan, feature, False)
    
    def can_create_dashboard(self):
        """Check if user can create more dashboards"""
        return self.current_dashboards < self.plan.max_dashboards
    
    def can_upload_file(self):
        """Check if user can upload more files this month"""
        return self.uploads_this_month < self.plan.max_uploads_per_month
    
    def reset_monthly_limits(self):
        """Reset monthly usage limits"""
        from datetime import datetime, timedelta
        now = datetime.now()
        if (now - self.last_upload_reset).days >= 30:
            self.uploads_this_month = 0
            self.last_upload_reset = now
            self.save()


class Payment(models.Model):
    """Model to store payment transactions"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    subscription = models.ForeignKey(UserSubscription, on_delete=models.CASCADE, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Payment gateway info
    stripe_payment_intent_id = models.CharField(max_length=200, null=True, blank=True)
    stripe_charge_id = models.CharField(max_length=200, null=True, blank=True)
    
    # Transaction details
    description = models.TextField(null=True, blank=True)
    metadata = models.JSONField(default=dict)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"${self.amount} - {self.user.username} ({self.status})"
    
    class Meta:
        ordering = ['-created_at']
