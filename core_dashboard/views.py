from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth
from inspections.models import Inspection, Defect, Alert
import json
from django.core.serializers.json import DjangoJSONEncoder

def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'registration/login.html')

@login_required
def dashboard(request):
    # Base Query
    if request.user.role == 'inspector':
        base_qs = Inspection.objects.filter(uploaded_by=request.user)
    else:
        base_qs = Inspection.objects.all()

    # Summary Cards
    total_inspections = base_qs.count()
    total_defects = base_qs.filter(status='Defective').count()
    defect_rate = (total_defects / total_inspections * 100) if total_inspections > 0 else 0
    pending_alerts = Alert.objects.filter(alert_status='Unread').count()
    
    # NEW: Total Users (Admin Only) - "Reflects 3 different users"
    total_users = 0
    if request.user.role == 'admin':
        from django.contrib.auth import get_user_model
        User = get_user_model()
        total_users = User.objects.count()

    # Monthly Trends
    if total_inspections > 0:
        monthly_trends = base_qs.annotate(month=TruncMonth('timestamp')) \
            .values('month') \
            .annotate(total=Count('id'), defective=Count('id', filter=Q(status='Defective'))) \
            .order_by('month')
        
        trend_labels = [entry['month'].strftime('%b %Y') for entry in monthly_trends]
        trend_data_total = [entry['total'] for entry in monthly_trends]
        trend_data_defective = [entry['defective'] for entry in monthly_trends]
    else:
        trend_labels = []
        trend_data_total = []
        trend_data_defective = []

    # Defect Type Distribution
    # Use base_qs for filtering context if needed, but Defect model is separate. 
    # Link Defect back to Inspection for filtering
    defect_types = Defect.objects.filter(inspection__in=base_qs).values('defect_type').annotate(total=Count('id'))
    dtype_labels = [entry['defect_type'] for entry in defect_types] if defect_types else []
    dtype_data = [entry['total'] for entry in defect_types] if defect_types else []

    # Severity Distribution
    severity_dist = Defect.objects.filter(inspection__in=base_qs).values('severity').annotate(total=Count('id'))
    severity_labels = [entry['severity'] for entry in severity_dist] if severity_dist else []
    severity_data = [entry['total'] for entry in severity_dist] if severity_dist else []

    # Recent Inspections
    recent_inspections = base_qs.order_by('-timestamp')[:5]

    # --- Smart Insights ---
    # 1. Batch with Highest Defect Percentage
    # Get stats per batch
    batch_stats = base_qs.values('batch__batch_number') \
        .annotate(total=Count('id'), defective=Count('id', filter=Q(status='Defective')))
    
    top_batch = None
    highest_rate = -1
    
    for stat in batch_stats:
        if stat['total'] > 0:
            rate = (stat['defective'] / stat['total']) * 100
            if rate > highest_rate:
                highest_rate = rate
                top_batch = {
                    'batch__batch_number': stat['batch__batch_number'],
                    'defect_count': stat['defective'],
                    'defect_rate': round(rate, 1)
                }

    # 2. Defect Trend (Compare last 7 days vs previous 7 days)
    from django.utils import timezone
    from datetime import timedelta
    now = timezone.now()
    
    # Use base_qs.filter(...) instead of Inspection.objects.filter(...)
    last_7_days = base_qs.filter(timestamp__gte=now - timedelta(days=7), status='Defective').count()
    prev_7_days = base_qs.filter(timestamp__gte=now - timedelta(days=14), timestamp__lt=now - timedelta(days=7), status='Defective').count()
    
    if prev_7_days > 0:
        trend_diff = last_7_days - prev_7_days
        trend_percent = (trend_diff / prev_7_days) * 100
        trend_direction = 'Increased' if trend_diff > 0 else 'Decreased'
    else:
        trend_direction = 'Stable' if last_7_days == 0 else 'Increased'
        trend_percent = 100 if last_7_days > 0 else 0

    context = {
        'total_inspections': total_inspections,
        'total_defects': total_defects,
        'defect_rate': round(defect_rate, 2),
        'pending_alerts': pending_alerts,
        'total_users': total_users,
        'trend_labels': json.dumps(trend_labels),
        'trend_data_total': json.dumps(trend_data_total),
        'trend_data_defective': json.dumps(trend_data_defective),
        'dtype_labels': json.dumps(dtype_labels),
        'dtype_data': json.dumps(dtype_data),
        'severity_labels': json.dumps(severity_labels),
        'severity_data': json.dumps(severity_data),
        'recent_inspections': recent_inspections,
        # Insights
        'top_batch': top_batch,
        'trend_direction': trend_direction,
        'trend_percent': abs(round(trend_percent, 1)),
    }

    return render(request, 'dashboard/dashboard.html', context)

@login_required
def about(request):
    return render(request, 'about.html')
