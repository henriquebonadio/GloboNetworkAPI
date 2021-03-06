# -*- coding:utf-8 -*-

# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import glob
import logging
import commands
from django.db.transaction import commit_on_success
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from networkapi.api_rack.permissions import Read, Write
from networkapi.api_rack import facade, exceptions
from networkapi.api_rack.serializers import RackSerializer
from networkapi.api_rest import exceptions as api_exceptions
from networkapi.system.facade import get_value as get_variable
from django.core.exceptions import ObjectDoesNotExist
from networkapi.system import exceptions as var_exceptions
from networkapi.equipamento.models import Equipamento, EquipamentoAmbiente


log = logging.getLogger(__name__)

@permission_classes((IsAuthenticated, Write))
class RackView(APIView):


    @commit_on_success
    def post(self, request, *args, **kwargs):
        try:
            log.info("Add Rack")

            data_ = request.DATA
            if not data_:
                raise exceptions.InvalidInputException()

            rack_dict = dict()

            try:
                rack_dict['number'] = int(data_.get('number'))
            except:
                raise exceptions.InvalidInputException("O número do Rack não foi informado.")
            rack_dict['name'] = data_.get('name')
            rack_dict['sw1_mac'] = data_.get('mac_address_sw1')
            rack_dict['sw2_mac'] = data_.get('mac_address_sw2')
            rack_dict['sw3_mac'] = data_.get('mac_address_ilo')

            if not data_.get('id_sw1'):
                rack_dict['sw1_id'] = None
            else:
                rack_dict['sw1_id'] = data_.get('id_sw1')
            if not data_.get('id_sw2'):
                rack_dict['sw2_id'] = None
            else:
                rack_dict['sw2_id'] = data_.get('id_sw2')
            if not data_.get('id_ilo'):
                rack_dict['sw3_id'] = None
            else:
                rack_dict['sw3_id'] = data_.get('id_ilo')

            rack = facade.save_rack(self.request.user, rack_dict)

            datas = dict()
            rack_serializer = RackSerializer(rack)
            datas['rack'] = rack_serializer.data

            return Response(datas, status=status.HTTP_201_CREATED)

        except (exceptions.RackNumberDuplicatedValueError, exceptions.RackNameDuplicatedError,
                exceptions.InvalidInputException) as exception:
            log.exception(exception)
            raise exception
        except Exception, exception:
            log.exception(exception)
            raise api_exceptions.NetworkAPIException()

class RackDeployView(APIView):

    @permission_classes((IsAuthenticated, Write))
    @commit_on_success
    def post(self, *args, **kwargs):
        try:
            log.info("RACK deploy.")

            rack_id = kwargs.get("rack_id")
            rack = facade.get_by_pk(self.request.user, rack_id)

            try:
                PATH_TO_ADD_CONFIG = get_variable("path_to_add_config")
                REL_PATH_TO_ADD_CONFIG = get_variable("rel_path_to_add_config")
            except ObjectDoesNotExist:
                raise var_exceptions.VariableDoesNotExistException("Erro buscando a variável PATH_TO_ADD_CONFIG ou REL_PATH_TO_ADD_CONFIG.")

            path_config = PATH_TO_ADD_CONFIG +'*'+rack.nome+'*'
            arquivos = glob.glob(path_config)

            #Get all files and search for equipments of the rack
            for var in arquivos:
                filename_equipments = var.split('/')[-1]
                rel_filename = "../../"+REL_PATH_TO_ADD_CONFIG+filename_equipments
                #Check if file is config relative to this rack
                if rack.nome in filename_equipments:
                    #Apply config only in spines. Leaves already have all necessary config in startup
                    if "ADD" in filename_equipments:
                        #Check if equipment in under maintenance. If so, does not aplly on it
                        equipment_name = filename_equipments.split('-ADD-')[0]
                        try:
                            equip = Equipamento.get_by_name(equipment_name)
                            if not equip.maintenance:
                                (erro, result) = commands.getstatusoutput("/usr/bin/backuper -T acl -b %s -e -i %s -w 300" % (rel_filename, equipment_name))
                                if erro:
                                    raise exceptions.RackAplError()
                        except exceptions.RackAplError, e:
                            raise e
                        except:
                            #Error equipment not found, do nothing
                            pass

            datas = dict()
            success_map = dict()

            success_map['rack_conf'] = True
            datas['sucesso'] = success_map

            return Response(datas, status=status.HTTP_201_CREATED)

        except exceptions.RackAplError, exception:
            log.exception(exception)
            raise exceptions.RackAplError("Falha ao aplicar as configuracoes: %s" %(result))
        except exceptions.RackNumberNotFoundError, exception:
            log.exception(exception)
            raise exceptions.RackNumberNotFoundError()
        except var_exceptions.VariableDoesNotExistException, exception:
            log.error(exception)
            raise var_exceptions.VariableDoesNotExistException("Erro buscando a variável PATH_TO_ADD_CONFIG ou REL_PATH_TO_ADD_CONFIG.")
        except Exception, exception:
            log.exception(exception)
            raise api_exceptions.NetworkAPIException(exception)
