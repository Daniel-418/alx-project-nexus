from rest_framework import serializers

from payments.models import Payment


class PaymentInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ["method"]


class PaymentOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            "id",
            "order",
            "method",
            "status",
            "currency",
            "price",
            "transaction_id",
            "paid_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
