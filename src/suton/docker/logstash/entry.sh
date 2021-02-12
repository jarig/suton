#!/bin/bash

# Map environment variables to entries in logstash.yml.
# Note that this will mutate logstash.yml in place if any such settings are found.
# This may be undesirable, especially if logstash.yml is bind-mounted from the
# host system.
env2yaml /usr/share/logstash/config/logstash.yml

export LS_JAVA_OPTS="-Dls.cgroup.cpuacct.path.override=/ -Dls.cgroup.cpu.path.override=/ $LS_JAVA_OPTS"

sudo chmod g+r -R $TON_LOG_DIR

if [[ -d $TON_CONTROL_WORK_DIR/configs/logstash && -n "$(ls -A $TON_CONTROL_WORK_DIR/configs/logstash)" ]]; then
  sudo ln -s $TON_CONTROL_WORK_DIR/configs/logstash/ton_control/*.conf /usr/share/logstash/pipeline/ton_control/
  sudo ln -s $TON_CONTROL_WORK_DIR/configs/logstash/ton_validator/*.conf /usr/share/logstash/pipeline/ton_validator/
  sudo ln -s $TON_CONTROL_WORK_DIR/configs/logstash/host/*.conf /usr/share/logstash/pipeline/host/
  sudo chmod -R o+r /usr/share/logstash/pipeline/*
fi
sudo chown -R logstash:logstash /usr/share/logstash/pipeline/

if [[ -z $1 ]] || [[ ${1:0:1} == '-' ]] ; then
  exec logstash "$@"
else
  exec "$@"
fi