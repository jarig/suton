FROM docker.elastic.co/logstash/logstash:7.7.0

ARG TON_USER_GID=1001

# Remove example config
RUN rm -f /usr/share/logstash/pipeline/logstash.conf
RUN rm -f /usr/share/logstash/config/pipelines.yml

# Copy configs
ADD pipeline /usr/share/logstash/pipeline
ADD config /usr/share/logstash/config

USER root
RUN groupadd --gid "$TON_USER_GID" ton
RUN usermod -a -G ton logstash


USER logstash
ENV TON_WORK_DIR=/var/ton-work
ENV TON_LOG_DIR=/var/ton-work/log
ENV TON_CONTROL_LOG_DIR=/var/ton-control/log
