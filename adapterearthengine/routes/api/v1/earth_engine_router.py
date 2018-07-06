import json
import csv
import copy
import logging

from flask import jsonify, request, Response, stream_with_context, Blueprint
from CTRegisterMicroserviceFlask import request_to_microservice

from adapterearthengine.routes.api import error
from adapterearthengine.services import EarthEngineService, QueryService
from adapterearthengine.errors import SqlFormatError, GEEQueryError, GeojsonNotFound
from adapterearthengine.serializers import serialize_query, serialize_fields

earth_engine_endpoints = Blueprint('endpoints', __name__)


def build_query(rq):
    dataset = rq.get_json().get('dataset').get('data')
    sql = rq.args.get('sql', None) or rq.get_json().get('sql', None)
    # sql or fs
    if sql:
        result_query = '?sql='+sql
    else:
        fs = copy.deepcopy(rq.args) or copy.deepcopy(rq.get_json())
        if fs.get('dataset'):
            del fs['dataset']

        result_query = '?tableName="' + dataset.get('attributes', None).get('tableName') + '"'
        try:
            for key in fs.keys():
                param = '&' + key + '=' + fs.get(key)
                result_query += param
        except TypeError as e:
            logging.debug("ERROR HERE")
            raise
    return result_query


@earth_engine_endpoints.route('/query/<dataset_id>', methods=['POST'])
def query(dataset_id):
    """Query GEE Dataset Endpoint"""
    logging.info('Doing GEE Query')

    sql = request.args.get('sql', None) or request.get_json().get('sql', None)
    result_query = build_query(request)

    try:
        if sql:
            query_type = 'sql'
        else:
            query_type = 'fs'
        json_sql = QueryService.convert(result_query, query_type=query_type)
        
    except SqlFormatError as e:
        logging.error('[ROUTER]: '+e.message)
        return error(status=400, detail=e.message)
    except Exception as e:
        logging.error('[ROUTER]: '+str(e))
        return error(status=500, detail="Error performing query")

    try:
        response = EarthEngineService.execute_query(json_sql).response()
    except GEEQueryError as e:
        logging.error('[ROUTER]: '+e.message)
        return error(status=400, detail=e.message)
    except Exception as e:
        # hotfix until library developments
        if str(e) == "'_init_cols'": return error(status=500, detail="Query not supported. Please visit https://doc.apihighways.org/ to obtain more information on supported queries.")
        logging.error('[ROUTER]: '+str(e))
        return error(status=500, detail=str(e))

    # @TODO
    meta = {}
    return jsonify(serialize_query(response, meta)), 200


@earth_engine_endpoints.route('/fields/<dataset_id>', methods=['POST'])
def fields(dataset_id):
    """Get GEE Dataset Fields Endpoint"""
    logging.info('Getting fields of a GEE Dataset')

    dataset = request.get_json().get('dataset').get('data')
    table_name = dataset.get('attributes').get('tableName')
    sql = '?sql=SELECT * FROM \"' + table_name + '\" LIMIT 1'

    # Convert query
    json_sql = QueryService.convert(sql, query_type='sql')

    try:
        response = EarthEngineService.execute_query(json_sql).metadata
    except GEEQueryError as e:
        logging.error('[ROUTER]: '+e.message)
        return error(status=400, detail=e.message)
    except Exception as e:
        logging.error('[ROUTER]: '+str(e))
        return error(status=500, detail='Generic Error')

    return jsonify(data=serialize_fields(response, table_name)), 200


@earth_engine_endpoints.route('/download/<dataset_id>', methods=['POST'])
def download(dataset_id):
    """Download GEE Dataset Endpoint"""
    logging.info('Downloading GEE Dataset')

    sql = request.args.get('sql', None) or request.get_json().get('sql', None)
    try:
        result_query = build_query(request)
    except TypeError as e:
        return error(status=501, detail="Download not supported for this dataset. Please visit https://doc.apihighways.org/ to obtain more information on supported queries.")
    try:
        if sql:
            query_type = 'sql'
        else:
            query_type = 'fs'
        json_sql = QueryService.convert(result_query, query_type=query_type)
    except SqlFormatError as e:
        logging.error('[ROUTER]: '+e.message)
        return error(status=400, detail=e.message)
    except Exception as e:
        logging.error('[ROUTER]: '+str(e))
        return error(status=500, detail='Generic Error')

    try:
        response = EarthEngineService.execute_query(json_sql).response()
    except GEEQueryError as e:
        logging.error('[ROUTER]: '+e.message)
        return error(status=400, detail=e.message)
    except Exception as e:
        logging.error('[ROUTER]: '+str(e))

    # @TODO
    meta = {}
    # @TODO download content-type
    return jsonify(data=serialize_query(response, meta)), 200


@earth_engine_endpoints.route('/rest-datasets/gee', methods=['POST'])
def register_dataset():
    """Register GEE Dataset Endpoint"""
    logging.info('Registering new GEE Dataset')

    table_name = request.get_json().get('connector').get('table_name')
    sql = '?sql=SELECT * FROM \"' + table_name + '\" LIMIT 1'

    # Convert query
    json_sql = QueryService.convert(sql, query_type='sql')

    try:
        response = EarthEngineService.execute_query(json_sql).metadata
        status = 1
    except GEEQueryError as e:
        logging.error('[ROUTER]: '+e.message)
        status = 2
    except Exception as e:
        logging.error('[ROUTER]: '+str(e))
        status = 2

    config = {
        'uri': '/dataset/'+request.get_json().get('connector').get('id'),
        'method': 'PATCH',
        'body': {'status': status}
    }
    response = request_to_microservice(config)
    return jsonify(data=serialize_fields(response, table_name)), 200
