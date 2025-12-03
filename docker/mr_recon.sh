#!/bin/bash

. /opt/SIRF-SuperBuild/INSTALL/bin/env_sirf.sh
pip install pydicom --upgrade --upgrade-strategy eager
gadgetron &
python /workdir/reco_scripts/mr_direct_recon.py /input /output