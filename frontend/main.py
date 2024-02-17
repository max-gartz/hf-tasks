import json
import os
from typing import Dict, Any

import boto3
import gradio as gr

SAGEMAKER_ENDPOINT = os.environ.get("SAGEMAKER_ENDPOINT")
SAGEMAKER_REGION = os.environ.get("SAGEMAKER_REGION")

session = boto3.Session()
runtime = session.client(service_name="sagemaker-runtime", region_name=SAGEMAKER_REGION)


def fn(tweet: str) -> Dict[str, Any]:
    response = runtime.invoke_endpoint(
        EndpointName=SAGEMAKER_ENDPOINT,
        ContentType="application/json",
        Body=json.dumps(dict(inputs=tweet, parameters=dict(return_all_scores=True)))
    )
    preds = json.loads(response["Body"].read().decode("utf-8"))
    return {pred["label"]: pred["score"] for pred in preds[0]}


interface = gr.Interface(
    fn=fn,
    inputs=[gr.Textbox(label="Tweet")],
    outputs=[gr.Label(label="Emotions")]
)

if __name__ == '__main__':
    interface.launch(
        server_name=os.environ.get("HOST", "0.0.0.0"),  # nosec
        server_port=os.environ.get("PORT", 7860)
    )
