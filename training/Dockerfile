ARG CUDA_VERSION=12.1.0
ARG OS_VERSION=ubuntu20.04
FROM nvcr.io/nvidia/cuda:${CUDA_VERSION}-runtime-${OS_VERSION}

ARG PYTHON_VERSION=3.10
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR code

RUN apt update && apt upgrade -y
RUN apt install software-properties-common curl build-essential -y
RUN add-apt-repository ppa:deadsnakes/ppa -y
RUN apt install python${PYTHON_VERSION} -y
RUN ln -sf /usr/bin/python${PYTHON_VERSION} /usr/bin/python3
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3

RUN apt install python${PYTHON_VERSION}-venv python${PYTHON_VERSION}-dev -y

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt requirements.txt
RUN python3 -m pip install -U $(cat requirements.txt | grep -o -e '^pip==[0-9]*\.[0-9]*\.[0-9]*')
RUN python3 -m pip install -Ur requirements.txt

COPY test.sh test.sh

COPY trainer trainer
COPY recipes recipes
