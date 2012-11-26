#!/bin/bash
thrift --gen py:dynamic,slots,utf8strings,new_style -out . users.thrift
