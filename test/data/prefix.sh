#!/bin/sh

datadir="$(dirname "$0")"

exec tar cvf "$datadir/prefix.tar" -C "$datadir/prefix" .
