FROM docker.elastic.co/logstash/logstash:7.7.0

# Remove example config
RUN rm -f /usr/share/logstash/pipeline/logstash.conf
RUN rm -f /usr/share/logstash/config/logstash.yml

# Copy configs
ADD pipeline/ /usr/share/logstash/pipeline/
ADD config/ /usr/share/logstash/config/

ARG TON_WORK_DIR=/var/ton-work
ARG TON_LOG_DIR=/var/ton-work/log
ARG TONCONTROL_LOG_DIR=/var/ton-control/log

ENV TON_WORK_DIR=$TON_WORK_DIR
ENV TON_LOG_DIR=$TON_LOG_DIR
ENV TONCONTROL_LOG_DIR=$TONCONTROL_LOG_DIR