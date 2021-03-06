# -*- coding: utf-8 -*-
from django.db.models import get_model
from rest_framework import serializers

from networkapi.util.serializers import DynamicFieldsModelSerializer


class UserGroupV3Serializer(DynamicFieldsModelSerializer):

    name = serializers.Field(source='nome')

    class Meta:
        UGrupo = get_model('grupo', 'UGrupo')
        model = UGrupo
        fields = (
            'id',
            'name'
        )


class EquipmentGroupV3Serializer(DynamicFieldsModelSerializer):

    name = serializers.Field(source='nome')

    class Meta:
        UGrupo = get_model('grupo', 'EGrupo')
        model = UGrupo
        fields = (
            'id',
            'name'
        )
