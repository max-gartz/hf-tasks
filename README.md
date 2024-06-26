# hf-tasks
HF interview challenge


## Question 1 - Design and deploy a cloud-based machine learning application

### Description
Design and implement a machine learning application on AWS or Azure that uses a Hugging
Face model for a real-world use case. You can choose any machine learning task and Hugging
Face model that you believe is relevant to your use case.
You will need to justify your choice of task and model and explain how they solve a real-world
problem. The application should be deployed on a scalable and fault-tolerant infrastructure, and
the deployment and infrastructure should be documented.

### Solution Approach
For the sake of simplicity I am choosing text classification which has a wide range of real world 
application, especially on social media in the context of content moderation and sentiment analysis.
I will be using the `distilbert-base-uncased` model from Hugging Face and finetune it on the `tweet_eval` dataset.
The application will then be a simple gradio app that takes a text input (corresponding to a tweet)
and classifies the tweet into a set of emotions (anger, sadness, joy and optimism). 
In real life, with access to the twitter/X API, this could for example be used to classify sentiment 
for a particular stock or product and inform investment decisions.

### Infrastructure
I used AWS for this task. I created a simple gradio app deployed on an ECS Fargate cluster.
The app invokes the text classification model endpoint hosted on a SageMaker endpoint.
The app is secured with AWS Cognito and a load balancer in front of the ECS frontend service.

I set up Identity federation to authenticate with AWS from the CI pipeline (`.github/workflows/ci.yaml`), 
which, next to some basic code quality control, builds a docker image for the app defined in `./frontend`.

The infrastructure is defined with terraform in the `./terraform` directory.
It is split into 3 configurations:
- `./terraform/backend` - which sets up the s3 bucket for the remote terraform state (saving its own state locally)
- `./terraform/base` - which sets up some basic infrastructure like vpc, s3 buckets and ecr repositories.
- `./terraform/deployments` - which deploys the ECS Fargate cluster, the app, the SageMaker endpoint as well as a load balancer and cognito.

The reasoning for this is that this provides a simple way of deploying the infrastructure in stages.
The deployments configuration can only be deployed after the base configuration has been deployed
and the respective images are built and pushed to the ECR repositories.

As a side note, I used Philipp Schmid's [terraform module](https://registry.terraform.io/modules/philschmid/sagemaker-huggingface/aws/latest)
to deploy the SageMaker endpoint. I had to do some modification though to allow for newer versions and therefore
copied the module code into the `./terraform/deployments/modules/huggingface_sagemaker` directory.

---

## Question 2 - Resuming Training

### Description
Question about Trainer. We have someone using Hugging Face Trainer to finetune on our cluster.
If there is an error during the training job, any data not explicitly synced to external storage is
lost. This includes any model checkpoints. Design a recommended way for syncing checkpoints
to external storage (e.g., s3) instead of just writing them locally during training.

### Solution Approach
One of the possible ways of dealing with this situation is to use the built-in push to hub callback.
This allows to easily synchronize the model checkpoints to the Hugging Face Hub and pick training back up from there.
Alternatively, if we want to stick to external storage like s3, gcs or azure blob storage, we can use the 
`Trainer`'s `callbacks` argument to add a custom `RemoteStorageCallback` callback that syncs the model 
to the external storage on every save event, as determined by the trainer arguments. We have to 
take extra care though, when it comes to resuming training from those checkpoints as the trainer does 
not natively support reading from remote storage. This means, we will have to make sure the checkpoint 
is copied to the local storage before resuming training.

### Details
I implemented the custom callback in `./training/trainer/callbacks.py` and added it to 
the `Trainer` in `./training/trainer/train.py`. The callback implementation supports any fsspec 
based file system, which includes s3, gcs and azure blob storage.
For the sake of simplicity, I decided to only support explicitly provided checkpoints for resuming 
training in the example training script. This means it does not support auto-detecting the latest checkpoint.

---

## Question 3 - Container Creation and Testing Exercise

### Description
You are part of a team working on a new cloud integration. Your task is to create a Dockerfile that
sets up an environment supporting CUDA for GPU acceleration and the Hugging Face
Transformers library for training LLMs. One of your colleagues already started working on
something for you to take over. The container should run on the latest version of NVIDIA GPUs
H100 and should be tested with a simple script after building. The container will be built inside a
CI environment and should be updatable for version changes.

```Dockerfile
# Use an NVIDIA base image with CUDA support
FROM nvidia/cuda:11.0-base
# Install Python and pip
RUN apt-get update && apt-get install -y python3-pip
# Install Hugging Face transformers
RUN pip3 install transformers
# (Optional) Copy project files
COPY . /app
WORKDIR /app
```

Include instructions on how to distribute the container to a registry (can be AWS, Azure, GCP)
and as a bash script on how to test the functionality of the container.


### Solution Approach
The Dockerfile provided is a good starting point, but it has a few issues.
To be compatible with NVIDIA H100 GPUs we need to choose a base image with a compatible cuda version and
install an appropriate pytorch version. According to [documentation](https://www.nvidia.com/content/dam/en-zz/Solutions/gtcs22/data-center/h100/PB-11133-001_v01.pdf)
the H100 supports CUDA 11.8 or higher, so we should use a base image with that version.
We also need to make sure our pytorch installation is compatible with the chosen CUDA version.
Finally, we can test the container by running it on a machine with an H100 GPU by 
running a simple python script that checks cuda availability. 

### Details
Consider the following adapted parameterized Dockerfile:

```Dockerfile
# Use an NVIDIA base image with CUDA support
ARG CUDA_VERSION=12.1.0
ARG OS_VERSION=ubuntu20.04
FROM nvcr.io/nvidia/cuda:${CUDA_VERSION}-base-${OS_VERSION}

ENV DEBIAN_FRONTEND=noninteractive

# Install Python and pip
ARG PYTHON_VERSION=3.10
RUN apt update && apt upgrade -y
RUN apt install software-properties-common curl build-essential -y
RUN add-apt-repository ppa:deadsnakes/ppa -y
RUN apt install python${PYTHON_VERSION} -y
RUN ln -sf /usr/bin/python${PYTHON_VERSION} /usr/bin/python3
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3
RUN apt install python${PYTHON_VERSION}-venv python${PYTHON_VERSION}-dev -y

# setup virtual environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# upgrade pip
RUN python3 -m pip install pip==23.3.2

# Install Hugging Face transformers
ARG TORCH_VERSION=2.2.0
ARG TRANSFORMERS_VERSION=4.34.0
RUN python3 -m pip install torch==${TORCH_VERSION}
RUN python3 -m pip install transformers==${TRANSFORMERS_VERSION}

COPY tesh.sh test.sh
```

This Dockerfile uses build arguments to allow for easy version changes.
As an example I provide instructions on how to build and push the image to AWS ECR.

Login to aws ecr:
```bash
aws ecr get-login-password --region <region> | docker login --username AWS --password-stdin <account_id>.dkr.ecr.<region>.amazonaws.com
```

Build and push the image:
```bash
docker build -t <account_id>.dkr.ecr.<region>.amazonaws.com/<repository>:<tag> .
docker push <account_id>.dkr.ecr.<region>.amazonaws.com/<repository>:<tag>
```
This will use the default build arguments, but you can also overwrite them with the `--build-arg` flag.

To test the image, run the following command on a machine with an H100 GPU:
```bash
docker run --gpus all <account_id>.dkr.ecr.<region>.amazonaws.com/<repository>:<tag> bash test.sh
```
where `test.sh` is a simple script that checks the availability of the GPU.
```bash
python3 -c "import torch; assert torch.cuda.is_available(), 'CUDA is not available'; print('CUDA is available')"
```

This makes sure not only that the GPU is accessible form within the container, which
can be verified with the `nvidia-smi` command, but also that the pytorch installation is 
compatible with the CUDA version.

A similar approach has been used in `./training/Dockerfile` to build the training image.
This image is built in the CI pipeline and pushed to AWS ECR as an example.
The only difference is that the image does not parameterize the torch and transformers versions, 
which are instead specified in the requirements containing all training dependencies.
