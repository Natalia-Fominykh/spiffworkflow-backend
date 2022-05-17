"""Api."""
import os

from flask import Blueprint
from flask import request

from ..models.user import UserModel
from spiff_workflow_webapp.spiff_workflow_connector import parse
from spiff_workflow_webapp.spiff_workflow_connector import run

from SpiffWorkflow.bpmn.serializer.workflow import BpmnWorkflowSerializer
from SpiffWorkflow.camunda.serializer.task_spec_converters import UserTaskConverter
from SpiffWorkflow.dmn.serializer.task_spec_converters import BusinessRuleTaskConverter
from spiff_workflow_webapp.models.process_model import ProcessModel


wf_spec_converter = BpmnWorkflowSerializer.configure_workflow_spec_converter([ UserTaskConverter, BusinessRuleTaskConverter ])
serializer = BpmnWorkflowSerializer(wf_spec_converter)

api = Blueprint("api", __name__)


@api.route("/run_process", methods=['POST'])
def run_process():
    """Run_process."""
    content = request.json

    homedir = os.environ.get("HOME")
    process = "order_product"
    dmn = [
        f"{homedir}/projects/github/sartography/SpiffExample/bpmn/product_prices.dmn",
        f"{homedir}/projects/github/sartography/SpiffExample/bpmn/shipping_costs.dmn",
    ]
    bpmn = [
        f"{homedir}/projects/github/sartography/SpiffExample/bpmn/multiinstance.bpmn",
        f"{homedir}/projects/github/sartography/SpiffExample/bpmn/call_activity_multi.bpmn",
    ]

    workflow = None
    process_model = ProcessModel.query.filter().first()
    if process_model is None:
        workflow = parse(process, bpmn, dmn)
    else:
        workflow = serializer.deserialize_json(process_model.bpmn_json)
    response = run(workflow, content.get("task_identifier"), content.get("answer"))

    return {"response": response}
