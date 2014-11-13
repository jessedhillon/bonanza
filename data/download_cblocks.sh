#!/usr/bin/env bash

for i in $(seq -f "%02g" 1 56); do
    wget http://www2.census.gov/geo/tiger/GENZ2013/cb_2013_${i}_bg_500k.zip
done

for f in *.zip; do
    unzip ${f} \*.sh* \*.prj \*.dbf
done
