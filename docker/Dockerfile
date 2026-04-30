ARG BASE_IMAGE=ghcr.io/synerbi/sirf:edge
FROM ${BASE_IMAGE} AS base

USER jovyan
RUN pip install pydicom
RUN pip install ismrmrd
RUN pip install nii2dcm


USER root
ARG DEBIAN_FRONTEND=noninteractive

WORKDIR /workdir
COPY reco_scripts/ reco_scripts/

COPY recon_stgeorge.sh .
RUN chmod +x recon_stgeorge.sh

RUN mkdir -p data && chown jovyan:users data



