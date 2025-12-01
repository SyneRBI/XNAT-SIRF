#!/bin/bash

. /opt/SIRF-SuperBuild/INSTALL/bin/env_sirf.sh
pip install pydicom --upgrade --upgrade-strategy eager
cp /input/* /workdir/data
cp data/20170809_NEMA_UCL.n.hdr data/norm.n.hdr
convertSiemensInterfileToSTIR.sh data/20170809_NEMA_MUMAP_UCL.v.hdr data/umap.v.hdr
sed -i.bak 's/\r\([^\n]\)/\r\n\1/g' data/norm.n.hdr
sed -i.bak 's/\r\([^\n]\)/\r\n\1/g' data/umap.v.hdr
sed -i.bak2 -e 's#\(!name of data file:=\)#\1/input/#' data/umap.v.hdr
sed -i.bak2 -e 's#\(!name of data file:=\)#\1/input/#' data/norm.n.hdr
cd /workdir/data
python /workdir/reco_scripts/pet_osem_recon.py /workdir/data /output