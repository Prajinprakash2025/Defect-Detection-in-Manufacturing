from rest_framework import viewsets, permissions
from core_inventory.models import Batch, Product
from inspections.models import Inspection, Defect
from rest_framework.serializers import ModelSerializer

class ProductSerializer(ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'

class BatchSerializer(ModelSerializer):
    product = ProductSerializer(read_only=True)
    class Meta:
        model = Batch
        fields = '__all__'

class InspectionSerializer(ModelSerializer):
    batch = BatchSerializer(read_only=True)
    class Meta:
        model = Inspection
        fields = '__all__'

class DefectSerializer(ModelSerializer):
    inspection = InspectionSerializer(read_only=True)
    class Meta:
        model = Defect
        fields = '__all__'

class BatchViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Batch.objects.all()
    serializer_class = BatchSerializer
    permission_classes = [permissions.IsAuthenticated]

class InspectionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Inspection.objects.all()
    serializer_class = InspectionSerializer
    permission_classes = [permissions.IsAuthenticated]

class DefectViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Defect.objects.all()
    serializer_class = DefectSerializer
    permission_classes = [permissions.IsAuthenticated]
