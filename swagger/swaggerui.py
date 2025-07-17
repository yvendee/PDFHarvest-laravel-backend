# swagger\swaggerui.py
from flasgger import Swagger
import os
import yaml

def load_swagger_docs(docs_path):
    swagger_docs = {}
    
    for filename in os.listdir(docs_path):
        if filename.endswith('.yaml'):
            with open(os.path.join(docs_path, filename), 'r') as file:
                swagger_docs.update(yaml.safe_load(file))

    return swagger_docs

def setup_swagger(app):
    parking_docs_path = os.path.join(os.path.dirname(__file__), 'swagger_docs', 'pdfharvest')
    
    # Load documents from both directories
    swagger_docs = {}
    swagger_docs.update(load_swagger_docs(parking_docs_path))

    swagger = Swagger(app, template={
        "swagger": "2.0",
        "info": {
            "title": "API Documentation",
            "description": "PDF Harvest API",
            "version": "1.0",
        },
        "paths": swagger_docs
    })

