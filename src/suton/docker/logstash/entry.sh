#!/bin/bash

# Map environment variables to entries in logstash.yml.
# Note that this will mutate logstash.yml in place if any such settings are found.
# This may be undesirable, especially if logstash.yml is bind-mounted from the
# host system.
env2yaml /usr/share/logstash/config/logstash.yml

export LS_JAVA_OPTS="-Dls.cgroup.cpuacct.path.override=/ -Dls.cgroup.cpu.path.override=/ $LS_JAVA_OPTS"

sudo chmod g+r -R $TON_LOG_DIR

if [[ -d $TON_CONTROL_WORK_DIR/configs/logstash && -n "$(ls -A $TON_CONTROL_WORK_DIR/configs/logstash)" ]]; then
  sudo cp -f $TON_CONTROL_WORK_DIR/configs/logstash/*.conf /usr/share/logstash/pipeline/ton_control/
fi
if [[ -d $TON_WORK_DIR/configs/logstash && -n "$(ls -A $TON_WORK_DIR/configs/logstash)" ]]; then
  sudo cp -f $TON_WORK_DIR/configs/logstash/*.conf /usr/share/logstash/pipeline/ton_validator/
fi
sudo chown -R logstash:logstash /usr/share/logstash/pipeline/


if [[ -z $1 ]] || [[ ${1:0:1} == '-' ]] ; then
  exec logstash "$@"
else
  exec "$@"
fi