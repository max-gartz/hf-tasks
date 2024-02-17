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
I will be using the `bert-base-uncased` model from Hugging Face and finetune it on the `tweet_eval` dataset.
The application will then be a simple gradio app that takes a text input (corresponding to a tweet)
and classifies the tweet into a set of emotions (anger, sadness, joy and optimism). 
In real life, with access to the twitter/X API, this could for example be used to classify sentiment 
for a particular stock or product and inform investment decisions.

### Infrastructure
I will be using AWS for this task. After running a training job on sagemaker, 
the model will be deployed on sagemaker endpoints and the app will be hosted on ECS Fargate. 
The infrastructure will be defined in Terraform and the deployment will be automated using GitHub Actions. 
Docker images for training and deployment will be built using GitHub Actions and pushed to ECR.
Authentication with AWS will be done using Identity Federation.

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
`Trainer`'s `callbacks` argument to add a `RemoteStorageCallback` callback that syncs the model 
to the external storage on every save event, as determined by the trainer arguments.

### Details
Check out the solution to Question 1 for an applied example of that.

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
install an appropriate pytorch versions.
Finally, we can simply test the container by running it on a machine with an H100 GPU by 
running a simple python script that checks cuda availability. 

### Details
See the implementation of the used training image for Question 1 and the test.sh script.
In the defined GitHub workflow that builds the image, I defined the cuda version
via a build arguments. This can easily be extended to support different cuda versions using 
a matrix strategy in the GitHub workflow.

Login to aws ecr:
```bash
aws ecr get-login-password --region <region> | docker login --username AWS --password-stdin <account_id>.dkr.ecr.<region>.amazonaws.com
```

Build and push the image:
```bash
docker build -t <account_id>.dkr.ecr.<region>.amazonaws.com/<repository>:<tag> .
docker push <account_id>.dkr.ecr.<region>.amazonaws.com/<repository>:<tag>
```

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




