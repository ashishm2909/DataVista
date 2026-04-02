from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
import json
import os
import secrets
import hashlib
from datetime import datetime, timedelta

from .models import UploadedFile, DatasetInfo, Dashboard, ChartConfig, DashboardCollaborator, DashboardShare
from .services.data_processor import DataProcessorService
from .services.chart_service import ChartDataService


def home(request):
    """Home page view"""
    return render(request, 'dashboard/home.html')


def register(request):
    """User registration view"""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}!')
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})


def logout_view(request):
    """Custom logout view that handles both GET and POST"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('home')


@login_required
def upload_file(request):
    """File upload view"""
    if request.method == 'POST':
        return handle_file_upload(request)
    
    # GET request - show upload form
    user_files = UploadedFile.objects.filter(user=request.user).order_by('-upload_date')
    paginator = Paginator(user_files, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'allowed_extensions': ['.xlsx', '.xls', '.csv', '.sql']
    }
    return render(request, 'dashboard/upload.html', context)


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def handle_file_upload(request):
    """Handle AJAX file upload"""
    try:
        if 'file' not in request.FILES:
            return JsonResponse({'success': False, 'error': 'No file provided'})
        
        uploaded_file = request.FILES['file']
        file_name = uploaded_file.name
        file_size = uploaded_file.size
        
        # Validate file extension
        allowed_extensions = ['.xlsx', '.xls', '.csv', '.sql']
        file_extension = os.path.splitext(file_name)[1].lower()
        
        if file_extension not in allowed_extensions:
            return JsonResponse({
                'success': False, 
                'error': f'File type {file_extension} not supported. Allowed types: {", ".join(allowed_extensions)}'
            })
        
        # Validate file size (100MB limit)
        max_size = 100 * 1024 * 1024  # 100MB
        if file_size > max_size:
            return JsonResponse({
                'success': False, 
                'error': 'File size exceeds 100MB limit'
            })
        
        # Determine file type
        file_type = 'csv'  # default
        if file_extension in ['.xlsx', '.xls']:
            file_type = 'excel'
        elif file_extension == '.csv':
            file_type = 'csv'
        elif file_extension == '.sql':
            file_type = 'sql'
        
        # Create UploadedFile instance
        file_obj = UploadedFile.objects.create(
            user=request.user,
            file=uploaded_file,
            file_name=file_name,
            file_type=file_type,
            file_size=file_size
        )
        
        # Process file in background (for demo, we'll do it synchronously)
        try:
            data_processor = DataProcessorService()
            dataset_info = data_processor.process_uploaded_file(file_obj)
            
            return JsonResponse({
                'success': True,
                'file_id': file_obj.id,
                'message': 'File uploaded and processed successfully',
                'dataset_info': {
                    'row_count': dataset_info.row_count,
                    'column_count': dataset_info.column_count,
                    'columns': dataset_info.columns
                }
            })
            
        except Exception as processing_error:
            return JsonResponse({
                'success': False,
                'error': f'Error processing file: {str(processing_error)}'
            })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Upload failed: {str(e)}'
        })


@login_required
def dataset_detail(request, file_id):
    """Dataset detail view"""
    file_obj = get_object_or_404(UploadedFile, id=file_id, user=request.user)
    
    if not file_obj.processed:
        messages.error(request, 'File is still being processed or failed to process.')
        return redirect('upload_file')
    
    try:
        dataset_info = DatasetInfo.objects.get(uploaded_file=file_obj)
        chart_service = ChartDataService()
        
        # Get dataset summary
        summary = chart_service.get_dataset_summary(dataset_info)
        
        # Get suggested charts
        suggested_charts = chart_service.get_suggested_charts(dataset_info)
        
        context = {
            'file_obj': file_obj,
            'dataset_info': dataset_info,
            'summary': summary,
            'suggested_charts': suggested_charts
        }
        
        return render(request, 'dashboard/dataset_detail.html', context)
        
    except DatasetInfo.DoesNotExist:
        messages.error(request, 'Dataset information not found.')
        return redirect('upload_file')


@login_required
def create_dashboard(request, file_id):
    """Create dashboard from dataset"""
    file_obj = get_object_or_404(UploadedFile, id=file_id, user=request.user)
    dataset_info = get_object_or_404(DatasetInfo, uploaded_file=file_obj)
    
    if request.method == 'POST':
        dashboard_name = request.POST.get('dashboard_name', f'Dashboard for {file_obj.file_name}')
        description = request.POST.get('description', '')
        
        # Create dashboard
        dashboard = Dashboard.objects.create(
            user=request.user,
            dataset=dataset_info,
            name=dashboard_name,
            description=description
        )
        
        messages.success(request, f'Dashboard "{dashboard_name}" created successfully!')
        return redirect('dashboard_view', dashboard_id=dashboard.id)
    
    context = {
        'file_obj': file_obj,
        'dataset_info': dataset_info
    }
    return render(request, 'dashboard/create_dashboard.html', context)


@login_required
def dashboard_view(request, dashboard_id):
    """Dashboard view"""
    dashboard = get_object_or_404(Dashboard, id=dashboard_id, user=request.user)
    charts = ChartConfig.objects.filter(dashboard=dashboard).order_by('position_y', 'position_x')
    
    chart_service = ChartDataService()
    chart_data = []
    
    for chart in charts:
        try:
            data = chart_service.generate_chart_data(chart)
            chart_data.append({
                'id': chart.id,
                'config': chart,
                'data': json.dumps(data)  # Serialize to JSON string
            })
        except Exception as e:
            # Log error but continue with other charts
            chart_data.append({
                'id': chart.id,
                'config': chart,
                'error': str(e)
            })
    
    context = {
        'dashboard': dashboard,
        'chart_data': chart_data,
        'dataset_info': dashboard.dataset
    }
    
    return render(request, 'dashboard/dashboard_view.html', context)


@login_required
def dashboard_list(request):
    """List user's dashboards"""
    dashboards = Dashboard.objects.filter(user=request.user).order_by('-updated_at')
    paginator = Paginator(dashboards, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj
    }
    return render(request, 'dashboard/dashboard_list.html', context)


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def add_chart(request, dashboard_id):
    """Add chart to dashboard via AJAX"""
    try:
        dashboard = get_object_or_404(Dashboard, id=dashboard_id, user=request.user)
        data = json.loads(request.body)
        
        chart_config = ChartConfig.objects.create(
            dashboard=dashboard,
            chart_type=data.get('chart_type'),
            title=data.get('title'),
            x_axis=data.get('x_axis', ''),
            y_axis=data.get('y_axis', ''),
            color_column=data.get('color_column', ''),
            aggregation=data.get('aggregation', 'count'),
            filters=data.get('filters', {}),
            position_x=data.get('position_x', 0),
            position_y=data.get('position_y', 0),
            width=data.get('width', 6),
            height=data.get('height', 4)
        )
        
        # Generate chart data
        chart_service = ChartDataService()
        chart_data = chart_service.generate_chart_data(chart_config)
        
        return JsonResponse({
            'success': True,
            'chart_id': chart_config.id,
            'chart_data': chart_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@csrf_exempt
@require_http_methods(["DELETE"])
@login_required
def delete_chart(request, chart_id):
    """Delete chart from dashboard"""
    try:
        chart = get_object_or_404(ChartConfig, id=chart_id, dashboard__user=request.user)
        chart.delete()
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@require_http_methods(["GET"])
@login_required
def get_chart_data(request, chart_id):
    """Get chart data via AJAX"""
    try:
        chart = get_object_or_404(ChartConfig, id=chart_id, dashboard__user=request.user)
        chart_service = ChartDataService()
        chart_data = chart_service.generate_chart_data(chart)
        
        return JsonResponse({
            'success': True,
            'chart_data': chart_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@require_http_methods(["GET"])
@login_required
def get_dataset_columns(request, file_id):
    """Get dataset columns for chart configuration"""
    try:
        file_obj = get_object_or_404(UploadedFile, id=file_id, user=request.user)
        dataset_info = get_object_or_404(DatasetInfo, uploaded_file=file_obj)
        
        return JsonResponse({
            'success': True,
            'columns': dataset_info.columns,
            'numeric_columns': dataset_info.numeric_columns,
            'categorical_columns': dataset_info.categorical_columns,
            'date_columns': dataset_info.date_columns
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
def delete_file(request, file_id):
    """Delete uploaded file and associated data"""
    file_obj = get_object_or_404(UploadedFile, id=file_id, user=request.user)
    
    if request.method == 'POST':
        try:
            # Delete physical file
            if file_obj.file and os.path.exists(file_obj.file.path):
                os.remove(file_obj.file.path)
            
            # Delete cached CSV if exists
            cache_path = os.path.join(settings.MEDIA_ROOT, 'cache', f'{file_obj.id}_processed.csv')
            if os.path.exists(cache_path):
                os.remove(cache_path)
            
            file_name = file_obj.file_name
            file_obj.delete()
            
            messages.success(request, f'File "{file_name}" deleted successfully.')
            
        except Exception as e:
            messages.error(request, f'Error deleting file: {str(e)}')
    
    return redirect('upload_file')


@login_required
def delete_dashboard(request, dashboard_id):
    """Delete dashboard"""
    dashboard = get_object_or_404(Dashboard, id=dashboard_id, user=request.user)
    
    if request.method == 'POST':
        dashboard_name = dashboard.name
        dashboard.delete()
        messages.success(request, f'Dashboard "{dashboard_name}" deleted successfully.')
        return redirect('dashboard_list')
    
    context = {'dashboard': dashboard}
    return render(request, 'dashboard/confirm_delete_dashboard.html', context)


# Collaboration and Sharing API Endpoints

@csrf_exempt
@require_http_methods(["GET", "POST"])
@login_required
def dashboard_share_settings(request, dashboard_id):
    """Get or update dashboard share settings"""
    try:
        dashboard = get_object_or_404(Dashboard, id=dashboard_id, user=request.user)
        
        if request.method == 'GET':
            # Get current share settings
            share_settings, created = DashboardShare.objects.get_or_create(
                dashboard=dashboard,
                defaults={'public_link_enabled': dashboard.is_public}
            )
            
            return JsonResponse({
                'success': True,
                'settings': {
                    'is_public': dashboard.is_public,
                    'public_link_enabled': share_settings.public_link_enabled,
                    'embed_enabled': share_settings.embed_enabled,
                    'password_protected': share_settings.password_protected,
                    'public_token': share_settings.public_token
                }
            })
        
        elif request.method == 'POST':
            # Update share settings
            data = json.loads(request.body)
            is_public = data.get('is_public', False)
            embed_enabled = data.get('embed_enabled', False)
            public_link_enabled = data.get('public_link_enabled', is_public)
            
            # Update dashboard public status
            dashboard.is_public = is_public
            dashboard.save()
            
            # Update or create share settings
            share_settings, created = DashboardShare.objects.get_or_create(
                dashboard=dashboard
            )
            
            share_settings.public_link_enabled = public_link_enabled
            share_settings.embed_enabled = embed_enabled
            
            # Generate public token if making public
            if is_public and not share_settings.public_token:
                share_settings.public_token = secrets.token_urlsafe(32)
            elif not is_public:
                share_settings.public_token = None  # Clear token when making private
            
            share_settings.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Share settings updated successfully',
                'is_public': is_public,
                'public_url': f'/dashboard/{dashboard.id}/public/' if is_public else None
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@csrf_exempt
@require_http_methods(["GET", "POST", "DELETE"])
@login_required
def dashboard_collaborators(request, dashboard_id):
    """Manage dashboard collaborators"""
    try:
        dashboard = get_object_or_404(Dashboard, id=dashboard_id, user=request.user)
        
        if request.method == 'GET':
            # Get list of collaborators
            collaborators = DashboardCollaborator.objects.filter(dashboard=dashboard).select_related('user')
            
            collaborator_list = []
            for collab in collaborators:
                collaborator_list.append({
                    'email': collab.user.email,
                    'username': collab.user.username,
                    'permission': collab.permission,
                    'invited_at': collab.invited_at.isoformat(),
                    'accepted_at': collab.accepted_at.isoformat() if collab.accepted_at else None
                })
            
            return JsonResponse({
                'success': True,
                'collaborators': collaborator_list
            })
        
        elif request.method == 'POST':
            # Add new collaborator
            data = json.loads(request.body)
            email = data.get('email')
            permission = data.get('permission', 'view')
            
            if not email:
                return JsonResponse({
                    'success': False,
                    'error': 'Email is required'
                })
            
            # Check if user exists
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'User with this email does not exist'
                })
            
            # Check if already a collaborator
            if DashboardCollaborator.objects.filter(dashboard=dashboard, user=user).exists():
                return JsonResponse({
                    'success': False,
                    'error': 'User is already a collaborator'
                })
            
            # Don't allow adding the owner as collaborator
            if user == dashboard.user:
                return JsonResponse({
                    'success': False,
                    'error': 'Cannot add dashboard owner as collaborator'
                })
            
            # Create collaborator
            collaborator = DashboardCollaborator.objects.create(
                dashboard=dashboard,
                user=user,
                permission=permission,
                invited_by=request.user,
                accepted_at=datetime.now()  # Auto-accept for demo
            )
            
            # Send email notification (optional)
            try:
                send_mail(
                    subject=f'You\'ve been invited to collaborate on "{dashboard.name}"',
                    message=f'You have been invited to collaborate on the dashboard "{dashboard.name}" with {permission} permissions.',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=True
                )
            except:
                pass  # Email sending is optional
            
            return JsonResponse({
                'success': True,
                'message': f'Collaborator {email} added successfully'
            })
        
        elif request.method == 'DELETE':
            # Remove collaborator
            data = json.loads(request.body)
            email = data.get('email')
            
            if not email:
                return JsonResponse({
                    'success': False,
                    'error': 'Email is required'
                })
            
            try:
                user = User.objects.get(email=email)
                collaborator = DashboardCollaborator.objects.get(dashboard=dashboard, user=user)
                collaborator.delete()
                
                return JsonResponse({
                    'success': True,
                    'message': f'Collaborator {email} removed successfully'
                })
            
            except (User.DoesNotExist, DashboardCollaborator.DoesNotExist):
                return JsonResponse({
                    'success': False,
                    'error': 'Collaborator not found'
                })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def duplicate_dashboard(request, dashboard_id):
    """Duplicate a dashboard"""
    try:
        dashboard = get_object_or_404(Dashboard, id=dashboard_id, user=request.user)
        
        # Create new dashboard
        new_dashboard = Dashboard.objects.create(
            user=request.user,
            dataset=dashboard.dataset,
            name=f"{dashboard.name} (Copy)",
            description=dashboard.description,
            chart_configs=dashboard.chart_configs,
            layout_config=dashboard.layout_config,
            is_public=False  # Copies are private by default
        )
        
        # Copy all charts
        charts = ChartConfig.objects.filter(dashboard=dashboard)
        for chart in charts:
            ChartConfig.objects.create(
                dashboard=new_dashboard,
                chart_type=chart.chart_type,
                title=chart.title,
                x_axis=chart.x_axis,
                y_axis=chart.y_axis,
                color_column=chart.color_column,
                aggregation=chart.aggregation,
                filters=chart.filters,
                position_x=chart.position_x,
                position_y=chart.position_y,
                width=chart.width,
                height=chart.height
            )
        
        return JsonResponse({
            'success': True,
            'message': 'Dashboard duplicated successfully',
            'dashboard_id': new_dashboard.id
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@require_http_methods(["GET"])
@login_required
def shared_dashboards(request):
    """Get dashboards shared with the current user"""
    try:
        # Get dashboards where user is a collaborator
        collaborations = DashboardCollaborator.objects.filter(
            user=request.user
        ).select_related('dashboard', 'dashboard__user', 'dashboard__dataset')
        
        shared_dashboards = []
        for collab in collaborations:
            dashboard = collab.dashboard
            shared_dashboards.append({
                'id': dashboard.id,
                'name': dashboard.name,
                'description': dashboard.description,
                'owner': {
                    'username': dashboard.user.username,
                    'email': dashboard.user.email
                },
                'permission': collab.permission,
                'created_at': dashboard.created_at.isoformat(),
                'updated_at': dashboard.updated_at.isoformat(),
                'chart_count': dashboard.charts.count(),
                'dataset_name': dashboard.dataset.uploaded_file.file_name
            })
        
        return JsonResponse({
            'success': True,
            'dashboards': shared_dashboards
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@require_http_methods(["GET"])
def dashboard_export_pdf(request, dashboard_id):
    """Export dashboard as PDF"""
    try:
        # Check if user has access to this dashboard
        dashboard = get_object_or_404(Dashboard, id=dashboard_id)
        
        # Check permissions - owner or collaborator or public
        has_access = (
            dashboard.user == request.user or 
            dashboard.is_public or
            (request.user.is_authenticated and 
             DashboardCollaborator.objects.filter(dashboard=dashboard, user=request.user).exists())
        )
        
        if not has_access:
            return HttpResponse('Access denied', status=403)
        
        charts = ChartConfig.objects.filter(dashboard=dashboard).order_by('position_y', 'position_x')
        chart_service = ChartDataService()
        
        # Generate HTML content for PDF
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>{dashboard.name} - Dashboard Export</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background: white; color: black; }}
                .header {{ text-align: center; margin-bottom: 30px; border-bottom: 2px solid #333; padding-bottom: 20px; }}
                .chart-section {{ margin-bottom: 40px; page-break-inside: avoid; }}
                .chart-title {{ font-size: 18px; font-weight: bold; margin-bottom: 10px; color: #333; }}
                .chart-info {{ background: #f5f5f5; padding: 10px; margin-bottom: 15px; border-radius: 5px; }}
                .stats {{ display: flex; justify-content: space-around; margin: 20px 0; }}
                .stat-item {{ text-align: center; padding: 10px; background: #f8f9fa; border-radius: 5px; }}
                .footer {{ margin-top: 50px; text-align: center; color: #666; font-size: 12px; }}
                .watermark {{ position: fixed; bottom: 10px; right: 10px; color: #ccc; font-size: 10px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{dashboard.name}</h1>
                <p><strong>Dataset:</strong> {dashboard.dataset.uploaded_file.file_name}</p>
                <p><strong>Generated on:</strong> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
                <p><strong>Created by:</strong> {dashboard.user.username}</p>
            </div>
            
            <div class="stats">
                <div class="stat-item">
                    <h3>{len(charts)}</h3>
                    <p>Charts</p>
                </div>
                <div class="stat-item">
                    <h3>{dashboard.dataset.row_count:,.0f}</h3>
                    <p>Data Rows</p>
                </div>
                <div class="stat-item">
                    <h3>{dashboard.dataset.column_count}</h3>
                    <p>Columns</p>
                </div>
            </div>
        """
        
        # Add chart information
        for chart in charts:
            try:
                data = chart_service.generate_chart_data(chart)
                html_content += f"""
                <div class="chart-section">
                    <h2 class="chart-title">{chart.title}</h2>
                    <div class="chart-info">
                        <p><strong>Chart Type:</strong> {chart.get_chart_type_display()}</p>
                        <p><strong>X-Axis:</strong> {chart.x_axis or 'Not specified'}</p>
                        <p><strong>Y-Axis:</strong> {chart.y_axis or 'Not specified'}</p>
                        <p><strong>Aggregation:</strong> {chart.aggregation.title()}</p>
                        <p><strong>Data Points:</strong> {len(data.get('data', {}).get('labels', []))} items</p>
                    </div>
                </div>
                """
            except Exception as e:
                html_content += f"""
                <div class="chart-section">
                    <h2 class="chart-title">{chart.title}</h2>
                    <div class="chart-info">
                        <p><strong>Error:</strong> {str(e)}</p>
                    </div>
                </div>
                """
        
        html_content += f"""
            <div class="footer">
                <p>This dashboard was exported from Data Dashboard Platform</p>
                <p>For the interactive version, visit the dashboard online</p>
            </div>
            <div class="watermark">Data Dashboard Platform</div>
        </body>
        </html>
        """
        
        # For now, return the HTML content directly
        # In production, you could use libraries like WeasyPrint or Puppeteer
        response = HttpResponse(html_content, content_type='text/html')
        response['Content-Disposition'] = f'attachment; filename="{dashboard.name}_export.html"'
        
        # Note: To generate actual PDF, you would need:
        # 1. pip install weasyprint (for Python PDF generation)
        # 2. Or use a service like Puppeteer/Playwright for Chrome PDF generation
        # 3. Replace the above with actual PDF generation code
        
        return response
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'PDF export failed: {str(e)}'
        })


@require_http_methods(["GET"])
def dashboard_public_view(request, dashboard_id):
    """Public view of a shared dashboard"""
    try:
        dashboard = get_object_or_404(Dashboard, id=dashboard_id, is_public=True)
        charts = ChartConfig.objects.filter(dashboard=dashboard).order_by('position_y', 'position_x')
        
        chart_service = ChartDataService()
        chart_data = []
        
        for chart in charts:
            try:
                data = chart_service.generate_chart_data(chart)
                chart_data.append({
                    'id': chart.id,
                    'config': chart,
                    'data': json.dumps(data)
                })
            except Exception as e:
                chart_data.append({
                    'id': chart.id,
                    'config': chart,
                    'error': str(e)
                })
        
        context = {
            'dashboard': dashboard,
            'chart_data': chart_data,
            'dataset_info': dashboard.dataset,
            'is_public_view': True
        }
        
        return render(request, 'dashboard/dashboard_public.html', context)
        
    except Dashboard.DoesNotExist:
        return HttpResponse('Dashboard not found or not public', status=404)
    except Exception as e:
        return HttpResponse(f'Error loading dashboard: {str(e)}', status=500)

