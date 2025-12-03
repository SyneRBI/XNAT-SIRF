ARG BASE_IMAGE=ghcr.io/synerbi/sirf:petric2
FROM ${BASE_IMAGE} AS base

USER root
ARG DEBIAN_FRONTEND=noninteractive

WORKDIR /workdir
COPY reco_scripts/ reco_scripts/

COPY mr_recon.sh .
RUN chmod +x mr_recon.sh

COPY pet_recon.sh .
RUN chmod +x pet_recon.sh

RUN mkdir -p data && chown jovyan:users data



