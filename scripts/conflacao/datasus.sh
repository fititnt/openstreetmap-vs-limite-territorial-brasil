#!/bin/bash
#===============================================================================
#
#          FILE:  datasus.sh
#
#         USAGE:  ./scripts/conflacao/datasus.sh
#   DESCRIPTION:  ---
#
#       OPTIONS:  ---
#
#  REQUIREMENTS:  - curl
#                 - unzip
#                 - osmium (https://osmcode.org/osmium-tool/)
#                   - apt install osmium-tool
#          BUGS:  ---
#         NOTES:  ---
#        AUTHOR:  Emerson Rocha <rocha[at]ieee.org>
#       COMPANY:  EticaAI
#       LICENSE:  Public Domain dedication
#                 SPDX-License-Identifier: Unlicense
#       VERSION:  v1.1
#       CREATED:  2023-04-01 17:59 UTC
#      REVISION:  2023-04-01 20:02 BRT extraido de setup.sh
#===============================================================================
set -e

ROOTDIR="$(pwd)"
TEMPDIR="$(pwd)/data/tmp"
CACHEDIR="$(pwd)/data/cache"

# pip install osm_conflate
# cd scripts/temp
# conflate <profile.py> -o result.osm
# conflate velobike.py -o result.osm
# conflate velobike.py -o result.osm --changes changes.geojson

# ftp://ftp.datasus.gov.br/cnes/BASE_DE_DADOS_CNES_202302.ZIP
#    999999/0/0/ftp.datasus.gov.br/cnes/BASE_DE_DADOS_CNES_202302.ZIP
#    -> tbEstabelecimento202302.csv
#        999999/0/0/ftp.datasus.gov.br/cnes/tbEstabelecimento202302.csv
#
# /workspace/git/EticaAI/lexicographi-sine-finibus/officina/999999/0/0/ftp.datasus.gov.br/cnes/tbEstabelecimento202302.csv
# data/tmp/DATASUS-tbEstabelecimento.csv

head data/tmp/DATASUS-tbEstabelecimento.csv

./scripts/csv2geojson.py --lat=NU_LATITUDE --lon=NU_LONGITUDE --delimiter=';' --encoding='latin-1' data/tmp/DATASUS-tbEstabelecimento.csv

head data/tmp/DATASUS-tbEstabelecimento.csv | ./scripts/csv2geojson.py --lat=NU_LATITUDE --lon=NU_LONGITUDE --delimiter=';' --encoding='latin-1'
# https://github.com/mapbox/csv2geojson
# https://pypi.org/project/csv2geojson/
# pip install csv2geojson

exit

./scripts/csv2geojson.py --lat=NU_LATITUDE --lon=NU_LONGITUDE --delimiter=';' --encoding='latin-1' --output-type=GeoJSON --ignore-warnings data/tmp/DATASUS-tbEstabelecimento.csv >data/tmp/DATASUS-tbEstabelecimento.geojson
ogr2ogr -nlt POINT -skipfailures points.shp geojsonfile.json OGRGeoJSON

# ogr2ogr -nlt POINT -skipfailures points.shp geojsonfile.json OGRGeoJSON
ogr2ogr -f GPKG data/tmp/DATASUS-tbEstabelecimento.gpkg data/tmp/DATASUS-tbEstabelecimento.geojson


### Santa catarina ____________________________________________________________
./scripts/csv2geojson.py --lat=NU_LATITUDE --lon=NU_LONGITUDE --delimiter=';' --encoding='latin-1' --output-type=GeoJSONSeq --ignore-warnings --contain-and=CO_ESTADO_GESTOR=42 data/tmp/DATASUS-tbEstabelecimento.csv > data/tmp/DATASUS-tbEstabelecimento_SC.geojsonl

ogr2ogr -f GPKG data/tmp/DATASUS-tbEstabelecimento_SC.gpkg data/tmp/DATASUS-tbEstabelecimento_SC.geojsonl

## Para o iD
# ./scripts/csv2geojson.py --lat=NU_LATITUDE --lon=NU_LONGITUDE --delimiter=';' --encoding='latin-1' --output-type=GeoJSON --ignore-warnings --contain-and=CO_ESTADO_GESTOR=42 data/tmp/DATASUS-tbEstabelecimento.csv > data/tmp/DATASUS-tbEstabelecimento_SC.geojson