#!/bin/bash

set -e

pushd examples
svgs=`ls *.svg`
popd

rm -f examples_out/*.dxf
for svg in ${svgs}; do
cat examples/${svg} | python src/main.py > examples_out/${svg}.dxf
done

